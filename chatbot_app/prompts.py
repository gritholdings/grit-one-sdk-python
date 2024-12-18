"""
This module contains all prompt templates used in the sales agent application.
"""

SYSTEM_PROMPTS = {
    "customer_support_expert": """You are an expert in customer support.
    """,
}

def get_prompt(prompt_name: str) -> str:
    """
    Retrieves a system prompt by name.
    
    Args:
        prompt_name (str): The name of the prompt to retrieve
        
    Returns:
        str: The requested prompt template
        
    Raises:
        KeyError: If the prompt name doesn't exist in SYSTEM_PROMPTS
    """
    if prompt_name not in SYSTEM_PROMPTS:
        raise KeyError(f"Prompt '{prompt_name}' not found in SYSTEM_PROMPTS")
    return SYSTEM_PROMPTS[prompt_name]