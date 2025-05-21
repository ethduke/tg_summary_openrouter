"""
Telegram Message Analyzer

This module provides functionality to fetch and analyze Telegram messages.
"""

import logging
import atexit
from typing import Dict, List, Tuple, Optional, Any, Union
from datetime import datetime, timedelta, timezone
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import User, Channel, PeerChannel, PeerUser, PeerChat

logger = logging.getLogger("TelegramMessageAnalyzer")

class TelegramMessageAnalyzer:
    """
    Telegram message analyzer that fetches and processes messages.
    """
    
    def __init__(self, api_id: int, api_hash: str, session_string: Optional[str] = None, session_name: str = "TelegramAnalyzer"):
        """
        Initialize the Telegram Message Analyzer.
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API Hash
            session_string: StringSession for resuming an existing session
            session_name: Name for the session file if not using StringSession
        """
        self.logger = logging.getLogger("TelegramMessageAnalyzer")
        
        # Initialize Telegram client with session string if provided
        if session_string:
            self.client = TelegramClient(StringSession(session_string), api_id, api_hash)
            self.logger.info("Using provided session string")
        else:
            self.client = TelegramClient(session_name, api_id, api_hash)
            self.logger.warning("No session string provided. Using local session file.")
            
        # Register disconnect on program exit to avoid breaking the session
        atexit.register(self._disconnect)
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
        
    async def start(self):
        """Start the Telegram client session"""
        await self.client.start()
        self.logger.info("Telegram client started")
    
    def _disconnect(self):
        """Disconnect the client if it's still connected (called on exit)"""
        try:
            if self.client and self.client.is_connected():
                self.client.disconnect()
                self.logger.info("Telegram client disconnected on exit")
        except Exception as e:
            self.logger.error(f"Error disconnecting client on exit: {e}")
    
    async def disconnect(self):
        """Disconnect the client manually"""
        if self.client:
            await self.client.disconnect()
            self.logger.info("Telegram client disconnected")
    
    @staticmethod
    def get_user_display_name(sender: Optional[Union[User, Channel]]) -> str:
        """
        Get a user's display name from a sender object.
        
        Args:
            sender: A Telegram User or Channel object
            
        Returns:
            The user's display name (first_name + last_name or username)
        """
        if not sender:
            return "Unknown"
        
        if isinstance(sender, User):
            if sender.username:
                return f"@{sender.username}"
            else:
                full_name = []
                if hasattr(sender, 'first_name') and sender.first_name:
                    full_name.append(sender.first_name)
                if hasattr(sender, 'last_name') and sender.last_name:
                    full_name.append(sender.last_name)
                return " ".join(full_name) if full_name else "Unknown User"
        elif isinstance(sender, Channel):
            return sender.title if sender.title else "Unknown Channel"
        else:
            return str(sender)
    
    @staticmethod
    def get_datetime_from(lookback_period: int) -> datetime:
        """
        Calculate the datetime from which to fetch messages.
        
        Args:
            lookback_period: Time period in seconds to look back
            
        Returns:
            UTC datetime object representing the lookback point
        """
        return (datetime.utcnow() - timedelta(seconds=lookback_period)).replace(tzinfo=timezone.utc)
    
    def get_peer_from_id(self, chat_id: Union[str, int]) -> Any:
        """
        Convert chat_id string to appropriate Peer object.
        
        Args:
            chat_id: Chat ID to convert
            
        Returns:
            Peer object or original chat_id
        """
        try:
            # Try to convert to integer
            chat_id_int = int(chat_id)
            
            # Handling different types of IDs
            if chat_id_int < 0:
                # For supergroups and channels
                if str(chat_id_int).startswith('-100'):
                    # Strip the -100 prefix to get the actual channel ID
                    channel_id = int(str(abs(chat_id_int))[2:])
                    return PeerChannel(channel_id)
                else:
                    # For older groups
                    return PeerChat(abs(chat_id_int))
            else:
                # For users
                return PeerUser(chat_id_int)
        except ValueError:
            # If it's not an integer, return the string as is
            return chat_id
    
    async def fetch_messages(self, chat_id: Union[str, int, Any], limit: Optional[int] = None, 
                             lookback_period: Optional[int] = None) -> Tuple[List[Dict[str, Any]], str]:
        """
        Fetch messages from the specified chat.
        
        Args:
            chat_id: Chat ID to fetch messages from
            limit: Maximum number of messages to fetch
            lookback_period: Time period in seconds to look back
            
        Returns:
            Tuple of (list of message dictionaries, chat title)
        """
        self.logger.info(f"Fetching messages from chat")
        
        # Convert chat_id to appropriate peer
        peer = self.get_peer_from_id(chat_id) if isinstance(chat_id, (str, int)) else chat_id
        
        # Get chat entity and title
        try:
            chat_entity = await self.client.get_entity(peer)
            chat_title = getattr(chat_entity, 'title', str(chat_id))
        except Exception as e:
            self.logger.error(f"Error getting chat entity: {e}")
            chat_title = str(chat_id)
        
        # Determine fetch criteria (limit or time-based)
        messages = []
        datetime_from = None
        if lookback_period:
            datetime_from = self.get_datetime_from(lookback_period)
            self.logger.info(f"Fetching messages since {datetime_from}")
        
        try:
            async for message in self.client.iter_messages(peer, limit=limit):
                # Skip if before lookback period
                if datetime_from and message.date < datetime_from:
                    break
                
                if not message.text:
                    self.logger.debug("Skipping non-text message")
                    continue
                
                # Get message sender
                try:
                    sender = await message.get_sender()
                    sender_name = self.get_user_display_name(sender)
                    sender_id = sender.id
                except Exception as e:
                    self.logger.warning(f"Error getting sender: {e}")
                    sender_name = "Unknown"
                    sender_id = None
                
                # Check if message is forwarded
                is_forwarded = False
                fwd_from_name = None
                if hasattr(message, 'fwd_from') and message.fwd_from:
                    is_forwarded = True
                    # Try to get the original sender name
                    if hasattr(message.fwd_from, 'from_name') and message.fwd_from.from_name:
                        fwd_from_name = message.fwd_from.from_name
                    elif hasattr(message.fwd_from, 'from_id'):
                        try:
                            fwd_from_entity = await self.client.get_entity(message.fwd_from.from_id)
                            fwd_from_name = self.get_user_display_name(fwd_from_entity)
                        except:
                            fwd_from_name = "Unknown Source"
                    else:
                        fwd_from_name = "Unknown Source"
                
                # Create message dictionary
                msg_dict = {
                    "id": message.id,
                    "datetime": message.date.isoformat(),
                    "timestamp": message.date.strftime("%Y-%m-%d %H:%M:%S"),
                    "text": message.text,
                    "sender_name": sender_name,
                    "sender_id": sender_id,
                    "is_reply": message.is_reply,
                    "is_forwarded": is_forwarded,
                    "forwarded_from": fwd_from_name if is_forwarded else None
                }
                
                # Add reply information if applicable
                if message.is_reply:
                    msg_dict["reply_to_msg_id"] = message.reply_to.reply_to_msg_id
                
                messages.append(msg_dict)
            
            self.logger.info(f"Successfully fetched {len(messages)} messages")
            return messages, chat_title
            
        except Exception as e:
            self.logger.error(f"Error fetching messages: {e}")
            return [], chat_title 

    async def get_channel_unread_messages(self, channel_id: Union[str, int]) -> Dict[str, Any]:
        """
        Get unread messages only from the specified channel (usually from config).
        
        Args:
            channel_id: Channel ID to fetch unread messages from
            
        Returns:
            Dictionary containing chat info and unread messages
        """
        self.logger.info(f"Fetching unread messages from channel {channel_id}")
        
        try:
            # Convert channel_id to appropriate peer
            peer = self.get_peer_from_id(channel_id) if isinstance(channel_id, (str, int)) else channel_id
            
            # Get chat entity and title
            try:
                chat_entity = await self.client.get_entity(peer)
                chat_title = getattr(chat_entity, 'title', str(channel_id))
            except Exception as e:
                self.logger.error(f"Error getting chat entity: {e}")
                chat_title = str(channel_id)
            
            # Find the dialog with unread messages
            dialog = None
            unread_count = 0
            
            # Iterate through dialogs to find the one matching our peer
            async for d in self.client.iter_dialogs():
                if d.entity.id == getattr(chat_entity, 'id', None):
                    dialog = d
                    unread_count = dialog.unread_count
                    break
            
            if not dialog:
                self.logger.warning(f"Could not find dialog for channel {chat_title}")
                return {
                    "chat_id": getattr(chat_entity, 'id', None),
                    "chat_title": chat_title,
                    "unread_count": 0,
                    "unread_messages": []
                }
            
            # If no unread messages, return empty result
            if unread_count == 0:
                self.logger.info(f"No unread messages in channel {chat_title}")
                return {
                    "chat_id": getattr(chat_entity, 'id', None),
                    "chat_title": chat_title,
                    "unread_count": 0,
                    "unread_messages": []
                }
            
            self.logger.info(f"Found {unread_count} unread messages in {chat_title}, fetching...")
            
            # Get unread messages for this dialog
            unread_messages = []
            message_count = 0
            skipped_count = 0
            
            # Keep track of skipped message types
            skipped_types = {}
            
            # Fetch only unread messages (typically, unread messages are the most recent ones)
            async for message in self.client.iter_messages(peer, limit=unread_count):
                message_count += 1
                
                # Check if it's a service message (like user joined, etc.)
                is_service_message = hasattr(message, 'action') and message.action
                
                # Skip non-text messages but count their types
                if is_service_message:
                    # Handle service messages
                    message_type = "service message"
                    skipped_types[message_type] = skipped_types.get(message_type, 0) + 1
                    self.logger.debug(f"Skipping service message")
                    skipped_count += 1
                    continue
                elif not message.text:
                    # Determine message type
                    message_type = "unknown"
                    # Safely check for media attributes
                    if hasattr(message, 'photo') and message.photo:
                        message_type = "photo"
                    elif hasattr(message, 'video') and message.video:
                        message_type = "video"
                    elif hasattr(message, 'document') and message.document:
                        message_type = "document"
                    elif hasattr(message, 'sticker') and message.sticker:
                        message_type = "sticker"
                    elif hasattr(message, 'gif') and message.gif:
                        message_type = "gif"
                    elif hasattr(message, 'voice') and message.voice:
                        message_type = "voice message"
                    elif hasattr(message, 'audio') and message.audio:
                        message_type = "audio"
                    elif hasattr(message, 'poll') and message.poll:
                        message_type = "poll"
                    elif hasattr(message, 'contact') and message.contact:
                        message_type = "contact"
                    elif hasattr(message, 'location') and message.location:
                        message_type = "location"
                    
                    # Update skipped type counter
                    skipped_types[message_type] = skipped_types.get(message_type, 0) + 1
                    
                    self.logger.debug(f"Skipping non-text message (type: {message_type})")
                    skipped_count += 1
                    continue
                
                # Get message sender
                try:
                    sender = await message.get_sender()
                    sender_name = self.get_user_display_name(sender)
                    sender_id = sender.id
                except Exception as e:
                    self.logger.warning(f"Error getting sender: {e}")
                    sender_name = "Unknown"
                    sender_id = None
                
                # Check if message is forwarded
                is_forwarded = False
                fwd_from_name = None
                if hasattr(message, 'fwd_from') and message.fwd_from:
                    is_forwarded = True
                    # Try to get the original sender name
                    if hasattr(message.fwd_from, 'from_name') and message.fwd_from.from_name:
                        fwd_from_name = message.fwd_from.from_name
                    elif hasattr(message.fwd_from, 'from_id'):
                        try:
                            fwd_from_entity = await self.client.get_entity(message.fwd_from.from_id)
                            fwd_from_name = self.get_user_display_name(fwd_from_entity)
                        except:
                            fwd_from_name = "Unknown Source"
                    else:
                        fwd_from_name = "Unknown Source"
                
                # Create message dictionary
                msg_dict = {
                    "id": message.id,
                    "datetime": message.date.isoformat(),
                    "timestamp": message.date.strftime("%Y-%m-%d %H:%M:%S"),
                    "text": message.text,
                    "sender_name": sender_name,
                    "sender_id": sender_id,
                    "is_reply": message.is_reply,
                    "is_forwarded": is_forwarded,
                    "forwarded_from": fwd_from_name if is_forwarded else None
                }
                
                # Add reply information if applicable
                if message.is_reply:
                    msg_dict["reply_to_msg_id"] = message.reply_to.reply_to_msg_id
                
                unread_messages.append(msg_dict)
            
            # Update unread count to reflect actual text messages
            actual_unread_count = len(unread_messages)
            
            chat_info = {
                "chat_id": getattr(chat_entity, 'id', None),
                "chat_title": chat_title,
                "unread_count": actual_unread_count,
                "unread_messages": unread_messages
            }
            
            # Log final summary
            self.logger.info(f"Successfully fetched {actual_unread_count} unread messages from {chat_title}")
            
            # Generate summary of skipped message types
            skipped_summary = ", ".join([f"{count} {msg_type}s" for msg_type, count in skipped_types.items()])
            self.logger.info(f"Summary: {message_count} total, {actual_unread_count} processed, {skipped_count} skipped ({skipped_summary if skipped_count > 0 else ''})")
            
            return chat_info
            
        except Exception as e:
            self.logger.error(f"Error fetching unread messages from channel: {e}")
            return {
                "chat_id": None,
                "chat_title": str(channel_id),
                "unread_count": 0,
                "unread_messages": []
            } 