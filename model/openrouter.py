"""
AI Models

This module provides functionality to generate summaries using AI models via OpenRouter.
"""

import logging
import httpx
from utils.config import (
    SUMMARY_PROMPT_TEMPLATE,
    OPENROUTER_API_KEY,
    DEFAULT_MODEL
)

logger = logging.getLogger("TelegramMessageAnalyzer")


async def generate_summary_with_ai(
    messages_text: str,
    model: str = DEFAULT_MODEL,
    prompt_template: str = SUMMARY_PROMPT_TEMPLATE
) -> str:
    """
    Generate a summary using OpenRouter API.
    
    Args:
        messages_text: The text of messages to summarize
        model: The model to use for summarization
        prompt_template: The prompt template to use for the summary
        
    Returns:
        The generated summary
    """
    try:
        prompt = prompt_template.format(messages=messages_text)
        
        # Log which model we're using
        logger.info(f"Generating summary using {model} model via OpenRouter API")
        
        # Prepare a simple payload following the example
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        # Use a simple approach similar to the example but with httpx async
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                json=payload
            )
            
            # Log the response status
            logger.info(f"OpenRouter API response status: {response.status_code}")
            
            # Get the response data
            response_data = response.json()
            logger.debug(f"OpenRouter API response: {response_data}")
            
            # Extract the summary from the response
            ai_summary = response_data["choices"][0]["message"]["content"]
        
        logger.info("AI summary generated successfully")
        return ai_summary
    except Exception as e:
        logger.error(f"Error generating AI summary via OpenRouter: {str(e)}", exc_info=True)
        raise




    

