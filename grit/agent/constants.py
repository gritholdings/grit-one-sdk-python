from typing import Iterable, List, Optional, Tuple, Union
ModelChoice = Tuple[str, Union[str, List[Tuple[str, str]]]]
OPENAI_MODEL_CONFIG = {
    "gpt-5.5": {
        "price_per_1m_tokens_input": 5,
        "price_per_1m_tokens_output": 30.00,
    },
    "gpt-5.4": {
        "price_per_1m_tokens_input": 2.5,
        "price_per_1m_tokens_output": 15.00,
    },
    "gpt-5.4-mini": {
        "price_per_1m_tokens_input": 0.75,
        "price_per_1m_tokens_output": 4.50,
    },
    "gpt-5.2": {
        "price_per_1m_tokens_input": 1.75,
        "price_per_1m_tokens_output": 14.00,
    },
    "gpt-5.1": {
        "price_per_1m_tokens_input": 1.25,
        "price_per_1m_tokens_output": 10.00,
    },
    "gpt-5-mini": {
        "price_per_1m_tokens_input": 0.25,
        "price_per_1m_tokens_output": 2.00,
    },
    "gpt-5": {
        "price_per_1m_tokens_input": 1.25,
        "price_per_1m_tokens_output": 10.00,
    },
    "o3": {
        "price_per_1m_tokens_input": 2,
        "price_per_1m_tokens_output": 8,
    },
    "gpt-4.1-mini": {
        "price_per_1m_tokens_input": 0.4,
        "price_per_1m_tokens_output": 1.6,
    },
    "gpt-4.1": {
        "price_per_1m_tokens_input": 2,
        "price_per_1m_tokens_output": 8,
    },
    "gpt-4o": {
        "price_per_1m_tokens_input": 2.5,
        "price_per_1m_tokens_output": 10,
    }
}
DEFAULT_OPENAI_MODEL = "gpt-5.4"
CLAUDE_MODEL_CONFIG = {
    "claude-opus-4-8": {
        "price_per_1m_tokens_input": 5,
        "price_per_1m_tokens_output": 25,
    },
    "claude-opus-4-7": {
        "price_per_1m_tokens_input": 5,
        "price_per_1m_tokens_output": 25,
    },
    "claude-opus-4-6": {
        "price_per_1m_tokens_input": 5,
        "price_per_1m_tokens_output": 25,
    },
    "claude-sonnet-4-6": {
        "price_per_1m_tokens_input": 3,
        "price_per_1m_tokens_output": 15,
    },
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
}
DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-6"
BEDROCK_MODEL_CONFIG = {
    "us.anthropic.claude-opus-4-8": {
        "price_per_1m_tokens_input": 5,
        "price_per_1m_tokens_output": 25,
    },
    "us.anthropic.claude-opus-4-7": {
        "price_per_1m_tokens_input": 5,
        "price_per_1m_tokens_output": 25,
    },
    "us.anthropic.claude-sonnet-4-6": {
        "price_per_1m_tokens_input": 3,
        "price_per_1m_tokens_output": 15,
    },
    "us.anthropic.claude-haiku-4-5-20251001-v1:0": {
        "price_per_1m_tokens_input": 1,
        "price_per_1m_tokens_output": 5,
    },
}
REASONING_EFFORT_CHOICES = [
    ('', 'Default'),
    ('none', 'None - No reasoning (lowest latency)'),
    ('minimal', 'Minimal - Fastest responses with minimal reasoning'),
    ('low', 'Low - Faster responses with less reasoning'),
    ('medium', 'Medium - Balanced speed and reasoning'),
    ('high', 'High - More thorough reasoning'),
    ('xhigh', 'Extra High - Most thorough reasoning'),
]
REASONING_CAPABLE_MODEL_PREFIXES = ('gpt-5', 'o1', 'o3')
MODEL_PROVIDER_GROUPS = (
    ('openai', 'OpenAI', OPENAI_MODEL_CONFIG),
    ('anthropic', 'Anthropic (API)', CLAUDE_MODEL_CONFIG),
    ('bedrock', 'Anthropic (Bedrock)', BEDROCK_MODEL_CONFIG),
)


def get_grouped_model_choices(enabled_providers: Optional[Iterable[str]] = None,
                              include_value: Optional[str] = None,
                              placeholder: str = 'Select a model...') -> List[ModelChoice]:
    enabled = None if enabled_providers is None else set(enabled_providers)
    choices: List[ModelChoice] = [('', placeholder)]
    known = set()
    for key, label, config in MODEL_PROVIDER_GROUPS:
        if enabled is not None and key not in enabled:
            continue
        options = [(model_name, model_name) for model_name in config]
        if options:
            choices.append((label, options))
            known.update(config.keys())
    if include_value and include_value not in known:
        choices.append(('Current', [(include_value, include_value)]))
    return choices
