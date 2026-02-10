OPENAI_MODEL_CONFIG = {
    "gpt-4o": {
        "price_per_1m_tokens_input": 2.5,
        "price_per_1m_tokens_output": 10,
    },
    "gpt-4.1": {
        "price_per_1m_tokens_input": 2,
        "price_per_1m_tokens_output": 8,
    },
    "gpt-4.1-mini": {
        "price_per_1m_tokens_input": 0.4,
        "price_per_1m_tokens_output": 1.6,
    },
    "gpt-4.5": {
        "price_per_1m_tokens_input": 75,
        "price_per_1m_tokens_output": 150,
    },
    "o1": {
        "price_per_1m_tokens_input": 15,
        "price_per_1m_tokens_output": 60,
    },
    "o3": {
        "price_per_1m_tokens_input": 2,
        "price_per_1m_tokens_output": 8,
    },
    "gpt-5": {
        "price_per_1m_tokens_input": 1.25,
        "price_per_1m_tokens_output": 10.00,
    },
    "gpt-5-mini": {
        "price_per_1m_tokens_input": 0.25,
        "price_per_1m_tokens_output": 2.00,
    },
    "gpt-5.1": {
        "price_per_1m_tokens_input": 1.25,
        "price_per_1m_tokens_output": 10.00,
    },
    "gpt-5.2": {
        "price_per_1m_tokens_input": 1.75,
        "price_per_1m_tokens_output": 14.00,
    },
}
DEFAULT_OPENAI_MODEL = "gpt-5"
CLAUDE_MODEL_CONFIG = {
    "claude-sonnet-4-5": {
        "price_per_1m_tokens_input": 3,
        "price_per_1m_tokens_output": 15,
    },
    "claude-haiku-4-5": {
        "price_per_1m_tokens_input": 1,
        "price_per_1m_tokens_output": 5,
    },
    "claude-opus-4-5": {
        "price_per_1m_tokens_input": 5,
        "price_per_1m_tokens_output": 25,
    },
    "claude-opus-4-6": {
        "price_per_1m_tokens_input": 5,
        "price_per_1m_tokens_output": 25,
    }
}
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-5"
