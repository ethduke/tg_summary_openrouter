#!/usr/bin/env python3
"""
Telegram Message Analyzer

This script fetches and analyzes messages from Telegram chats, with options to:
1. Focus on specific users' messages
2. Preserve conversation context
3. Generate AI-powered summaries using an LLM via OpenRouter

Usage:
  python main.py -c CHANNEL_ID -u USERNAME1 USERNAME2 -n 200 -o output.md -f markdown
"""

import asyncio
import logging
import argparse
import sys
from typing import Union, Optional, List, Dict, Any, Tuple
from model.openrouter import generate_summary_with_ai
from utils.config import (
    TELEGRAM_API_ID, 
    TELEGRAM_API_HASH, 
    TELEGRAM_STRING_SESSION,
    TELEGRAM_CHANNEL_ID,
    DEFAULT_MODEL,
    DEFAULT_MESSAGE_LIMIT
)
from utils.prompt_loader import get_prompt
from utils.formatters import (
    format_results,
    write_output
)
from model.message_analyzer import TelegramMessageAnalyzer

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)



async def analyze_messages(
    api_id: int, 
    api_hash: str, 
    session_string: str, 
    chat_id: Union[str, int], 
    target_users: Optional[List[str]] = None, 
    limit: int = 200, 
    model: str = DEFAULT_MODEL,
    unread_only: bool = False
) -> Dict[str, Any]:
    """
    Fetch and analyze messages from a Telegram chat, with optional user filtering.
    
    Args:
        api_id: Telegram API ID
        api_hash: Telegram API Hash
        session_string: StringSession for resuming an existing session
        chat_id: Chat ID to analyze
        target_users: List of usernames or user IDs to focus on
        limit: Maximum number of messages to fetch
        model: OpenRouter model to use for summarization
        unread_only: Whether to fetch only unread messages
        
    Returns:
        Analysis results including conversation structure and summaries
    """
    # Ensure we have a session string - if not, create a new session
    if not session_string:
        logger.warning("No session string provided. A new session will be created.")
    
    # Use async context manager for the analyzer
    async with TelegramMessageAnalyzer(api_id, api_hash, session_string) as analyzer:
        if unread_only:
            # Fetch only unread messages from the specified channel
            unread_data = await analyzer.get_channel_unread_messages(chat_id)
            
            if unread_data["unread_count"] == 0:
                return {
                    "status": "info",
                    "message": "No unread messages found in the specified chat",
                    "chat_title": unread_data["chat_title"]
                }
            
            # Extract messages from the unread data
            messages = unread_data["unread_messages"]
            chat_title = unread_data["chat_title"]
        else:
            # Fetch regular messages
            messages, chat_title = await analyzer.fetch_messages(chat_id, limit=limit)
            
            if not messages:
                return {
                    "status": "error",
                    "message": "No messages found in the specified chat"
                }
        
        # Process and filter messages
        filtered_messages, extended_messages = filter_and_extend_messages(messages, target_users)
        
        # Organize messages by participant
        participants = organize_by_participant(extended_messages)
        
        # Initialize summaries
        overall_summary = None
        participant_summaries = {}
        
        if extended_messages:
            # Generate summaries
            overall_summary, participant_summaries = await generate_summaries(
                extended_messages, 
                participants, 
                model
            )
        
        # Compile results
        results = {
            "status": "success",
            "chat_title": chat_title,
            "target_users": target_users,
            "message_count": {
                "total": len(messages),
                "filtered": len(filtered_messages),
                "with_context": len(extended_messages)
            },
            "date_range": get_date_range(filtered_messages),
            "text_summaries": {
                "overall_summary": overall_summary,
                "by_participant": participant_summaries
            }
        }
        
        # Add unread specific information if requested
        if unread_only:
            results["unread_count"] = unread_data["unread_count"]
        
        return results

def filter_and_extend_messages(
    messages: List[Dict[str, Any]], 
    target_users: Optional[List[str]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Filter messages by target users and extend with context messages.
    
    Args:
        messages: List of all messages
        target_users: Optional list of target usernames or IDs
        
    Returns:
        Tuple of (filtered messages, extended messages with context)
    """
    if not target_users:
        return messages, messages
    
    # Convert usernames to lowercase for case-insensitive matching
    target_users_lower = [u.lower().strip('@') if isinstance(u, str) else str(u) for u in target_users]
    
    # Filter messages from target users
    filtered_messages = []
    for msg in messages:
        sender_name = msg.get("sender_name", "").lower().strip('@')
        sender_id = str(msg.get("sender_id", ""))
        
        if sender_name in target_users_lower or sender_id in target_users_lower:
            filtered_messages.append(msg)
    
    # Extend filtered_messages with context messages (replies to target users)
    # Create a set of message IDs that are referenced in replies
    context_message_ids = {
        msg.get("reply_to_msg_id") 
        for msg in filtered_messages 
        if msg.get("is_reply") and msg.get("reply_to_msg_id")
    }
    
    # Add context messages from the original messages list
    filtered_ids = {msg["id"] for msg in filtered_messages}
    context_messages = [
        msg for msg in messages 
        if msg["id"] in context_message_ids and msg["id"] not in filtered_ids
    ]
    
    extended_messages = filtered_messages + context_messages
    return filtered_messages, extended_messages

def organize_by_participant(messages: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Organize messages by participant.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        Dictionary mapping participant names to their messages
    """
    participants = {}
    for msg in messages:
        sender_name = msg.get("sender_name", "Unknown")
        if sender_name not in participants:
            participants[sender_name] = []
        participants[sender_name].append(msg)
    return participants

def get_date_range(messages: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    """
    Get the date range of messages.
    
    Args:
        messages: List of message dictionaries
        
    Returns:
        Dictionary with earliest and latest timestamps
    """
    if not messages:
        return {"earliest": None, "latest": None}
    
    # Messages are typically in reverse chronological order
    return {
        "earliest": messages[-1]["timestamp"] if messages else None,
        "latest": messages[0]["timestamp"] if messages else None
    }

async def generate_summaries(
    extended_messages: List[Dict[str, Any]],
    participants: Dict[str, List[Dict[str, Any]]],
    model: str
) -> Tuple[Optional[str], Dict[str, str]]:
    """
    Generate overall and participant summaries in a single API call to avoid rate limiting.
    
    Args:
        extended_messages: List of all messages with context
        participants: Dictionary mapping participant names to their messages
        model: OpenRouter model to use for summarization
        
    Returns:
        Tuple of (overall summary, participant summaries dictionary)
    """
    # Format all messages with timestamps and participant names
    all_formatted_messages = []
    for msg in sorted(extended_messages, key=lambda m: m["datetime"]):
        # Format differently based on whether it's a forwarded message
        if msg.get("is_forwarded", False):
            forwarded_source = msg.get("forwarded_from", "Unknown Source")
            formatted_message = f"[{msg['timestamp']}] {msg['sender_name']} shared content originally by {forwarded_source}: {msg['text']}"
        else:
            formatted_message = f"[{msg['timestamp']}] {msg['sender_name']}: {msg['text']}"
        all_formatted_messages.append(formatted_message)
    
    all_messages_text = "\n".join(all_formatted_messages)
    
    # Create participants list for the prompt
    participant_names = list(participants.keys())

    # Extract trader names from messages
    trader_names = set()
    for msg in extended_messages:
        try:
            message_text = msg.get("text", "")
            if "from: 💰" in message_text or "💰" in message_text:
                # Try multiple approaches to extract trader name
                if "💰" in message_text and "【" in message_text:
                    # Extract trader name between 💰 and 【
                    trader_start = message_text.find("💰") + 1
                    trader_end = message_text.find("【")
                    if trader_start > 0 and trader_end > trader_start:
                        trader_name = message_text[trader_start:trader_end].strip()
                        if trader_name:  # Only add non-empty names
                            trader_names.add(trader_name)
                elif "from: 💰" in message_text:
                    # Try to extract after "from: 💰"
                    parts = message_text.split("from: 💰", 1)
                    if len(parts) > 1 and parts[1].strip():
                        # Take the first word/segment as the trader name
                        trader_name = parts[1].split()[0].strip()
                        if trader_name:
                            trader_names.add(trader_name)
        except Exception as e:
            logger.warning(f"Error extracting trader name: {str(e)}")
            continue
    
    # Convert set to sorted list for consistent ordering
    trader_names = sorted(list(trader_names))

    # Load and format the prompt template from file
    try:
        # Get the additional prompt template
        prompt_template = get_prompt("overall_prompt")
        
        participants_str = ', '.join(participant_names) if participant_names else 'None'
        prompt = prompt_template.format(
            participants=participants_str,
            messages=all_messages_text
        )
    except Exception as e:
        logger.error(f"Error loading or formatting prompt template: {e}")

    # Make a single API call to generate all summaries
    logger.info(f"Generating unified summary using {model} model via OpenRouter")
    
    try:
        unified_response = await generate_summary_with_ai(
            all_messages_text,
            model,
            prompt
        )
        
        # Parse the response to extract overall summary and participant summaries
        overall_summary = None
        participant_summaries = {}
        
        # Extract overall summary
        if "```overall" in unified_response and "```" in unified_response:
            overall_start = unified_response.find("```overall") + 10
            overall_end = unified_response.find("```", overall_start)
            if overall_end > overall_start:
                overall_summary = unified_response[overall_start:overall_end].strip()
        
        # Extract participant summaries
        if "```participants" in unified_response and "```" in unified_response:
            participants_start = unified_response.find("```participants") + 14
            participants_end = unified_response.find("```", participants_start)
            if participants_end > participants_start:
                participants_text = unified_response[participants_start:participants_end].strip()
                
                # Process each line to extract participant summaries
                for line in participants_text.split('\n'):
                    if ']' in line and '[' in line:
                        # Extract participant name and summary
                        participant_start = line.find('[') + 1
                        participant_end = line.find(']')
                        if participant_end > participant_start:
                            participant = line[participant_start:participant_end]
                            summary_start = line.find(':', participant_end) + 1
                            if summary_start > 0:
                                summary = line[summary_start:].strip()
                                participant_summaries[participant] = summary
                    elif ':' in line:
                        # Alternative format without brackets
                        parts = line.split(':', 1)
                        if len(parts) == 2:
                            participant = parts[0].strip()
                            summary = parts[1].strip()
                            participant_summaries[participant] = summary
        
        # If parsing failed, use the entire response as the overall summary
        if overall_summary is None:
            overall_summary = unified_response
            logger.warning("Failed to parse structured response, using entire response as overall summary")
        
        return overall_summary, participant_summaries
            
    except Exception as e:
        logger.error(f"Error generating unified summary: {str(e)}")
        return f"Error generating unified summary: {str(e)}", {}

async def main():
    """Parse command line arguments and run the analyzer."""
    parser = argparse.ArgumentParser(description='Analyze and summarize Telegram messages with conversation context')
    parser.add_argument('-c', '--chat-id', type=str, default=None,
                        help=f'Chat ID to analyze (default: {TELEGRAM_CHANNEL_ID})')
    parser.add_argument('-u', '--users', type=str, nargs='+',
                        help='Target users to focus on (usernames or IDs)')
    parser.add_argument('-n', '--num-messages', type=int, default=DEFAULT_MESSAGE_LIMIT,
                        help=f'Maximum number of messages to fetch (default: {DEFAULT_MESSAGE_LIMIT})')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output file for results (default: print to console)')
    parser.add_argument('-f', '--format', choices=['text', 'json', 'markdown'], default='text',
                        help='Output format (default: text)')
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL,
                        help=f'OpenRouter model to use (default: {DEFAULT_MODEL})')
    parser.add_argument('--unread', action='store_true',
                        help='Fetch only unread messages from the channel')
    args = parser.parse_args()
    
    # Use the default channel ID from config if not specified in args
    chat_id = args.chat_id if args.chat_id is not None else TELEGRAM_CHANNEL_ID
    
    if chat_id is None:
        logger.error("No chat ID provided and no default found in config.")
        logger.error("Please specify a chat ID with -c/--chat-id or set TELEGRAM_CHANNEL_ID in your config.")
        sys.exit(1)
    
    try:
        results = await analyze_messages(
            TELEGRAM_API_ID, 
            TELEGRAM_API_HASH, 
            TELEGRAM_STRING_SESSION, 
            chat_id,
            args.users,
            args.num_messages,
            args.model,
            args.unread
        )
        
        # Format and output results
        output_text = format_results(results, args.format)
        write_output(output_text, args.output)
        
    except Exception as e:
        logger.error(f"Error analyzing messages: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 