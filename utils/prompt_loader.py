import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

def load_markdown_file(filename: str) -> Optional[str]:
    """
    Load content from a Markdown file.
    
    Args:
        filename: Path to the Markdown file
        
    Returns:
        File content as string or None if loading fails
    """
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error loading markdown file {filename}: {e}")
        return None

def get_prompt(prompt_name: str, default_prompt: Optional[str] = None) -> str:
    """
    Get a prompt template by name, looking for .md files.
    
    Args:
        prompt_name: Name of the prompt (without extension)
        default_prompt: Fallback prompt to use if file loading fails
        
    Returns:
        Prompt template string
    """
    # Get the base directory of the project
    base_dir = Path(__file__).parent.parent
    prompt_dir = base_dir / "data" / "prompts"
    
    # Check for Markdown file
    md_path = prompt_dir / f"{prompt_name}.md"
    if md_path.exists():
        result = load_markdown_file(str(md_path))
        if result:
            return result
    
    # Fallback to default prompt
    if default_prompt:
        logger.warning(f"Could not load prompt '{prompt_name}' from file. Using default prompt.")
        return default_prompt
    else:
        raise ValueError(f"Prompt '{prompt_name}' not found and no default provided.") 