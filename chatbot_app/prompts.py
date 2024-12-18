"""
This module contains all prompt templates used in the sales agent application.
"""

SYSTEM_PROMPTS = {
    "customer_support_expert": """You are an expert in customer support.
    """,
}

def get_customer_support_prompt():
    return SYSTEM_PROMPTS["customer_support_expert"]