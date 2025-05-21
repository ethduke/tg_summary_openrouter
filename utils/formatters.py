"""
Formatters for Telegram Message Analysis output.

This module contains functions for formatting analysis results in different formats
(text, markdown, JSON) and writing the output to a file or console.
"""

import json
import logging
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

def clean_summary(summary: str) -> str:
    """
    Clean up a summary text, handling error messages and ensuring it's displayable.
    
    Args:
        summary: The summary text to clean
        
    Returns:
        Cleaned summary text
    """
    if not summary:
        return "No summary available."
    
    # Handle error messages
    if summary.startswith("Error generating"):
        return f"*{summary}*"
    
    # Remove thinking blocks if they exist
    if "<think>" in summary and "</think>" in summary:
        think_start = summary.find("<think>")
        think_end = summary.find("</think>") + len("</think>")
        return summary[think_end:].strip()
    
    return summary

def format_results(results: Dict[str, Any], format_type: str) -> str:
    """
    Format analysis results based on the specified format type.
    
    Args:
        results: The analysis results dictionary
        format_type: The format to use ('text', 'json', or 'markdown')
        
    Returns:
        Formatted output as a string
    """
    if results["status"] != "success":
        return f"Error: {results.get('message', 'Unknown error')}"
    
    # If summaries were generated, format them directly
    if results["text_summaries"]["overall_summary"]:
        return format_summary_results(results)
    
    # Otherwise format based on the specified format type
    if format_type == 'json':
        return json.dumps(results, indent=2)
    elif format_type == 'markdown':
        return format_as_markdown(results)
    else:  # text format
        return format_as_text(results)

def format_summary_results(results: Dict[str, Any]) -> str:
    """
    Format results with AI-generated summaries.
    
    Args:
        results: The analysis results dictionary
        
    Returns:
        Markdown-formatted summary
    """
    output = f"# Telegram Chat Analysis: {results['chat_title']}\n\n"
    output += f"Messages analyzed: {results['message_count']['with_context']}\n"
    output += f"Date Range: {results['date_range']['earliest']} to {results['date_range']['latest']}\n\n"
    
    # Overall summary - directly use the generated format
    clean_overall = clean_summary(results["text_summaries"]["overall_summary"])
    output += clean_overall + "\n\n"
    
    # Participant summaries
    output += "## Participant Summaries\n\n"
    for participant, summary in results["text_summaries"]["by_participant"].items():
        clean_participant = clean_summary(summary)
        output += f"### {participant}\n\n"
        output += f"{clean_participant}\n\n"
    
    return output

def format_as_markdown(results: Dict[str, Any]) -> str:
    """
    Format results as markdown.
    
    Args:
        results: The analysis results dictionary
        
    Returns:
        Markdown-formatted output
    """
    output = f"# Telegram Chat Summary: {results['chat_title']}\n\n"
    
    if results["target_users"]:
        output += f"**Users**: {', '.join(results['target_users'])}\n"
    
    output += f"**Messages**: {results['message_count']['filtered']} (with context: {results['message_count']['with_context']})\n"
    output += f"**Date Range**: {results['date_range']['earliest']} to {results['date_range']['latest']}\n\n"
    
    return output

def format_as_text(results: Dict[str, Any]) -> str:
    """
    Format results as plain text.
    
    Args:
        results: The analysis results dictionary
        
    Returns:
        Plain text formatted output
    """
    output = f"Telegram Chat: {results['chat_title']}\n"
    
    if results["target_users"]:
        output += f"Users: {', '.join(results['target_users'])}\n"
    
    output += f"Messages: {results['message_count']['filtered']} (with context: {results['message_count']['with_context']})\n"
    output += f"Date Range: {results['date_range']['earliest']} to {results['date_range']['latest']}\n\n"
    
    return output

def write_output(output_text: str, output_file: Optional[str]) -> None:
    """
    Write output text to file or print to console.
    
    Args:
        output_text: The formatted output text to write
        output_file: Optional file path to write to (None to print to console)
    """
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output_text)
            logger.info(f"Results saved to {output_file}")
        except IOError as e:
            logger.error(f"Error writing to file {output_file}: {e}")
            # Fall back to console output
            logger.info(output_text)
    else:
        # Just log the output instead of printing to console
        logger.info(output_text)
        return output_text 