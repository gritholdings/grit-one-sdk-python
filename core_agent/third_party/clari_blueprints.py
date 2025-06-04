"""
Predefined Blueprint schemas for Clari sales call data validation and extraction.

These schemas can be used with DataAutomationProject to define what data fields
should be extracted and validated from Clari API responses.
"""

# Standard Clari Call Summary Blueprint
CLARI_CALL_SUMMARY_BLUEPRINT = {
    "name": "Clari Call Summary",
    "description": "Extract key summary information from Clari sales calls",
    "schema": {
        "type": "object",
        "properties": {
            "call_id": {
                "type": "string",
                "description": "Unique identifier for the call"
            },
            "call_date": {
                "type": "string",
                "format": "date",
                "description": "Date of the call (YYYY-MM-DD)"
            },
            "account_name": {
                "type": "string",
                "description": "Name of the customer account"
            },
            "deal_name": {
                "type": "string",
                "description": "Name or title of the deal"
            },
            "deal_value": {
                "type": "number",
                "description": "Monetary value of the deal"
            },
            "deal_stage": {
                "type": "string",
                "description": "Sales stage before the call"
            },
            "duration_minutes": {
                "type": "number",
                "description": "Call duration in minutes"
            },
            "participant_count": {
                "type": "integer",
                "description": "Number of participants on the call"
            }
        },
        "required": ["call_id", "call_date", "account_name"]
    }
}

# Detailed Clari Call Analytics Blueprint
CLARI_CALL_ANALYTICS_BLUEPRINT = {
    "name": "Clari Call Analytics",
    "description": "Extract detailed analytics and metrics from Clari sales calls",
    "schema": {
        "type": "object",
        "properties": {
            "call_id": {
                "type": "string",
                "description": "Unique identifier for the call"
            },
            "call_date": {
                "type": "string",
                "format": "date",
                "description": "Date of the call"
            },
            "account_name": {
                "type": "string",
                "description": "Customer account name"
            },
            "deal_value": {
                "type": "number",
                "description": "Deal value in dollars"
            },
            "talk_listen_ratio": {
                "type": "number",
                "description": "Ratio of talking to listening time"
            },
            "questions_asked": {
                "type": "integer",
                "description": "Number of questions asked during the call"
            },
            "engaging_questions": {
                "type": "integer",
                "description": "Number of engaging questions asked"
            },
            "duration_minutes": {
                "type": "number",
                "description": "Total call duration in minutes"
            },
            "summary": {
                "type": "string",
                "description": "AI-generated call summary"
            },
            "action_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "action_item": {"type": "string"},
                        "owner_name": {"type": "string"}
                    }
                },
                "description": "List of action items identified in the call"
            },
            "topics_discussed": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "start_timestamp": {"type": "string"}
                    }
                },
                "description": "Topics discussed during the call"
            }
        },
        "required": ["call_id", "call_date", "account_name"]
    }
}

# Deal Pipeline Blueprint
CLARI_DEAL_PIPELINE_BLUEPRINT = {
    "name": "Clari Deal Pipeline",
    "description": "Extract deal pipeline information from Clari sales calls",
    "schema": {
        "type": "object",
        "properties": {
            "call_id": {
                "type": "string",
                "description": "Unique call identifier"
            },
            "call_date": {
                "type": "string",
                "format": "date",
                "description": "Date of the call"
            },
            "account_name": {
                "type": "string",
                "description": "Customer account name"
            },
            "deal_name": {
                "type": "string",
                "description": "Deal name or opportunity title"
            },
            "deal_value": {
                "type": "number",
                "description": "Deal value in dollars"
            },
            "deal_stage_before": {
                "type": "string",
                "description": "Deal stage before the call"
            },
            "deal_close_date": {
                "type": "string",
                "format": "date",
                "description": "Expected deal close date"
            },
            "crm_deal_id": {
                "type": "string",
                "description": "CRM system deal identifier"
            },
            "crm_account_id": {
                "type": "string",
                "description": "CRM system account identifier"
            },
            "contact_names": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Names of contacts on the call"
            }
        },
        "required": ["call_id", "account_name", "deal_name"]
    }
}

# Sales Rep Performance Blueprint
CLARI_REP_PERFORMANCE_BLUEPRINT = {
    "name": "Clari Sales Rep Performance",
    "description": "Extract sales representative performance metrics from calls",
    "schema": {
        "type": "object",
        "properties": {
            "call_id": {
                "type": "string",
                "description": "Unique call identifier"
            },
            "call_date": {
                "type": "string",
                "format": "date",
                "description": "Date of the call"
            },
            "rep_name": {
                "type": "string",
                "description": "Name of the sales representative"
            },
            "account_name": {
                "type": "string",
                "description": "Customer account name"
            },
            "talk_listen_ratio": {
                "type": "number",
                "description": "Rep's talk to listen ratio"
            },
            "questions_asked": {
                "type": "integer",
                "description": "Number of questions asked by rep"
            },
            "engaging_questions": {
                "type": "integer",
                "description": "Number of engaging questions asked"
            },
            "call_duration": {
                "type": "number",
                "description": "Total call duration in minutes"
            },
            "deal_value": {
                "type": "number",
                "description": "Associated deal value"
            },
            "deal_stage": {
                "type": "string",
                "description": "Deal stage before call"
            }
        },
        "required": ["call_id", "rep_name", "account_name"]
    }
}

# Simple Call Log Blueprint
CLARI_CALL_LOG_BLUEPRINT = {
    "name": "Clari Call Log",
    "description": "Basic call logging information for record keeping",
    "schema": {
        "type": "object",
        "properties": {
            "call_id": {
                "type": "string",
                "description": "Unique call identifier"
            },
            "call_time": {
                "type": "string",
                "format": "date-time",
                "description": "Full timestamp of the call"
            },
            "title": {
                "type": "string",
                "description": "Call title or subject"
            },
            "account_name": {
                "type": "string",
                "description": "Customer account name"
            },
            "duration_minutes": {
                "type": "number",
                "description": "Call duration in minutes"
            },
            "participant_count": {
                "type": "integer",
                "description": "Number of participants"
            },
            "has_transcript": {
                "type": "boolean",
                "description": "Whether transcript is available"
            }
        },
        "required": ["call_id", "call_time", "account_name"]
    }
}

# Transcript Text Extraction Blueprint
CLARI_TRANSCRIPT_TEXT_BLUEPRINT = {
    "name": "Clari Transcript Text",
    "description": "Extract plain text from call transcripts for chatbot integration",
    "schema": {
        "type": "object",
        "properties": {
            "call_id": {
                "type": "string",
                "description": "Unique call identifier"
            },
            "call_date": {
                "type": "string",
                "format": "date",
                "description": "Date of the call"
            },
            "account_name": {
                "type": "string",
                "description": "Customer account name"
            },
            "transcript_text": {
                "type": "string",
                "description": "Plain text transcript with speaker attribution"
            },
            "transcript_clean": {
                "type": "string",
                "description": "Clean transcript text without speaker names for chatbot processing"
            },
            "participant_count": {
                "type": "integer",
                "description": "Number of participants on the call"
            },
            "duration_minutes": {
                "type": "number",
                "description": "Call duration in minutes"
            },
            "word_count": {
                "type": "integer",
                "description": "Total word count in transcript"
            }
        },
        "required": ["call_id", "transcript_text", "transcript_clean"]
    }
}

# Collection of all predefined blueprints
PREDEFINED_CLARI_BLUEPRINTS = [
    CLARI_CALL_SUMMARY_BLUEPRINT,
    CLARI_CALL_ANALYTICS_BLUEPRINT,
    CLARI_DEAL_PIPELINE_BLUEPRINT,
    CLARI_REP_PERFORMANCE_BLUEPRINT,
    CLARI_CALL_LOG_BLUEPRINT,
    CLARI_TRANSCRIPT_TEXT_BLUEPRINT
]


def create_clari_blueprint(blueprint_config):
    """
    Helper function to create a Blueprint model instance from a blueprint configuration.
    
    Args:
        blueprint_config: Dictionary containing blueprint configuration
        
    Returns:
        Blueprint model instance (not saved to database)
    """
    from ..models import Blueprint
    
    return Blueprint(
        name=blueprint_config["name"],
        description=blueprint_config["description"],
        schema=blueprint_config["schema"]
    )


def get_blueprint_by_name(name: str):
    """
    Get a predefined blueprint configuration by name.
    
    Args:
        name: Name of the blueprint
        
    Returns:
        Blueprint configuration dictionary or None if not found
    """
    for blueprint in PREDEFINED_CLARI_BLUEPRINTS:
        if blueprint["name"] == name:
            return blueprint
    return None


def list_available_blueprints():
    """
    List all available predefined Clari blueprints.
    
    Returns:
        List of blueprint names and descriptions
    """
    return [
        {
            "name": blueprint["name"],
            "description": blueprint["description"]
        }
        for blueprint in PREDEFINED_CLARI_BLUEPRINTS
    ]