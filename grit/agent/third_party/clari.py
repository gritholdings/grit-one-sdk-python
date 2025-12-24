import json
import logging
import time
from datetime import datetime, timedelta
from typing import Iterator, Dict, List, Optional, Any
from dataclasses import dataclass

import requests
from requests.models import PreparedRequest
from django.conf import settings


logger = logging.getLogger(__name__)


@dataclass
class ClariConfig:
    """Configuration for Clari API integration."""
    api_key: str
    api_password: str
    base_url: str = "https://rest-api.copilot.clari.com"
    max_calls_per_sync: int = 50
    page_size: int = 100
    request_timeout: int = 30
    throttle_delay: float = 0.2


class ClariAPIError(Exception):
    """Custom exception for Clari API errors."""
    pass


def get_secret_value(account, key: str) -> Optional[str]:
    """
    Helper function to retrieve secret value from account metadata.
    
    Args:
        account: Account instance with metadata containing secrets
        key: Secret key to retrieve
        
    Returns:
        Secret value if found, None otherwise
    """
    if not account or not account.metadata:
        return None
        
    secrets = account.metadata.get('secrets', [])
    for secret in secrets:
        if secret.get('key') == key:
            return secret.get('value')
    return None


class ClariAPIClient:
    """
    Clari API client for fetching sales call data and integrating with Django data automation.
    
    This service follows the existing patterns established for OpenAI and AWS integrations
    in the grit.agent package.
    """
    
    def __init__(self, account, config: Optional[ClariConfig] = None):
        self.account = account
        
        if config:
            self.config = config
        else:
            # Get API credentials from account secrets
            api_key = get_secret_value(account, "CLARI_API_KEY")
            api_password = get_secret_value(account, "CLARI_API_PASSWORD")
            
            if not api_key or not api_password:
                raise ClariAPIError("CLARI_API_KEY and CLARI_API_PASSWORD must be configured in account secrets")
            
            self.config = ClariConfig(
                api_key=api_key,
                api_password=api_password,
                base_url=getattr(settings, 'CLARI_API_BASE_URL', "https://rest-api.copilot.clari.com"),
                max_calls_per_sync=getattr(settings, 'CLARI_MAX_CALLS_PER_SYNC', 50),
                page_size=getattr(settings, 'CLARI_PAGE_SIZE', 100),
                request_timeout=getattr(settings, 'CLARI_REQUEST_TIMEOUT', 30),
                throttle_delay=getattr(settings, 'CLARI_THROTTLE_DELAY', 0.2)
            )
        
        self.headers = {
            "X-Api-Key": self.config.api_key,
            "X-Api-Password": self.config.api_password
        }
        
        self.calls_url = f"{self.config.base_url}/calls"
        self.details_url = f"{self.config.base_url}/call-details"

    def fetch_calls_page(self, skip: int = 0, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Fetch a page of calls with optional filters.
        
        Args:
            skip: Number of records to skip for pagination
            filters: Optional dictionary of filters to apply
            
        Returns:
            Dictionary containing calls data and pagination info
            
        Raises:
            ClariAPIError: If API request fails
        """
        params = {
            "filterStatus": "POST_PROCESSING_DONE",
            "sortTime": "desc",
            "skip": skip,
            "limit": self.config.page_size,
            "includePagination": False,
        }
        
        # Apply additional filters if provided
        if filters:
            if filters.get('deal_stage_before_call'):
                params["deal_stage_before_call"] = filters['deal_stage_before_call']
            if filters.get('time_gte'):
                params["filterTimeGte"] = filters['time_gte']
            if filters.get('time_lt'):
                params["filterTimeLt"] = filters['time_lt']
            if filters.get('allowed_emails'):
                # Convert to query items for multiple filterUser parameters
                query_items = list(params.items())
                for email in filters['allowed_emails']:
                    query_items.append(("filterUser", email))
                
                req = PreparedRequest()
                req.prepare_url(self.calls_url, query_items)
                url = req.url
            else:
                url = self.calls_url
        else:
            url = self.calls_url
            
        try:
            logger.debug(f"Fetching calls page: skip={skip}, filters={filters}")
            response = requests.get(
                url, 
                headers=self.headers, 
                params=params if 'query_items' not in locals() else None,
                timeout=self.config.request_timeout
            )
            response.raise_for_status()
            return response.json()
            
        except requests.RequestException as e:
            error_msg = f"Failed to fetch calls page: {str(e)}"
            logger.error(error_msg)
            raise ClariAPIError(error_msg) from e

    def fetch_call_details(self, call_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed information for a specific call including transcript.
        
        Args:
            call_id: Unique identifier for the call
            
        Returns:
            Dictionary containing detailed call information or None if not found
            
        Raises:
            ClariAPIError: If API request fails unexpectedly
        """
        params = {
            "id": call_id,
            "includeAudio": "true",
            "includeVideo": "true",
        }
        
        try:
            logger.debug(f"Fetching call details for: {call_id}")
            response = requests.get(
                self.details_url,
                headers=self.headers,
                params=params,
                timeout=self.config.request_timeout
            )
            
            # Handle expected 400/404 for missing calls
            if response.status_code in {400, 404}:
                logger.warning(f"Call details not found for: {call_id}")
                return None
                
            # Handle 504 gateway timeout with retry logic
            if response.status_code == 504:
                logger.warning(f"Gateway timeout for call: {call_id}")
                return None
                
            response.raise_for_status()
            result = response.json()
            return result.get("call")
            
        except requests.RequestException as e:
            error_msg = f"Failed to fetch call details for {call_id}: {str(e)}"
            logger.error(error_msg)
            raise ClariAPIError(error_msg) from e

    def iter_calls_filtered(self, filters: Optional[Dict[str, Any]] = None, max_calls: Optional[int] = None) -> Iterator[Dict[str, Any]]:
        """
        Iterate over all calls that match the given filters.
        
        Args:
            filters: Optional dictionary of filters to apply
            max_calls: Maximum number of calls to return (defaults to config setting)
            
        Yields:
            Dictionary containing call metadata
        """
        if max_calls is None:
            max_calls = self.config.max_calls_per_sync
            
        skip = 0
        seen = 0
        max_pages = 100  # Safety limit to avoid infinite loops
        
        logger.info(f"Starting filtered call iteration with max_calls={max_calls}")
        
        for page in range(max_pages):
            try:
                data = self.fetch_calls_page(skip, filters)
                calls = data.get("calls", [])
                
                if not calls:
                    logger.info(f"No more calls found at page {page}")
                    break
                    
                for call in calls:
                    # Apply additional user filtering if specified
                    if filters and filters.get('allowed_emails'):
                        if not self._is_user_allowed(call, filters['allowed_emails']):
                            continue
                            
                    yield call
                    seen += 1
                    
                    if seen >= max_calls:
                        logger.info(f"Reached max_calls limit: {max_calls}")
                        return
                        
                skip += len(calls)
                
                # API-friendly throttling
                time.sleep(self.config.throttle_delay)
                
            except ClariAPIError as e:
                logger.error(f"Error fetching page {page}: {e}")
                break
                
        logger.info(f"Completed call iteration. Total calls processed: {seen}")

    def _is_user_allowed(self, call: Dict[str, Any], allowed_emails: List[str]) -> bool:
        """
        Check if any internal attendee is in the allowed emails list.
        
        Args:
            call: Call metadata dictionary
            allowed_emails: List of allowed email addresses
            
        Returns:
            True if any attendee is allowed, False otherwise
        """
        if not allowed_emails:
            return True
            
        allowed_emails_lower = {email.lower() for email in allowed_emails}
        
        for user in call.get("users", []):
            email = user.get("userEmail", "").lower()
            if email in allowed_emails_lower:
                logger.debug(f"Allowed user found: {email}")
                return True
                
        logger.debug(f"No allowed users found in call: {call.get('id')}")
        return False

    def fetch_calls_with_details(self, filters: Optional[Dict[str, Any]] = None, max_calls: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch calls with full details including transcripts for data automation.
        
        This method combines call metadata with detailed information and is optimized
        for integration with DataAutomationProject workflows.
        
        Args:
            filters: Optional dictionary of filters to apply
            max_calls: Maximum number of calls to return
            
        Returns:
            List of dictionaries containing enriched call data suitable for JSON storage
        """
        enriched_calls = []
        
        logger.info("Starting comprehensive call data fetch")
        
        for call in self.iter_calls_filtered(filters, max_calls):
            try:
                # Fetch detailed information
                details = self.fetch_call_details(call.get("id"))
                
                if not details or not details.get("transcript"):
                    logger.warning(f"Skipping call {call.get('id')} - no transcript available")
                    continue
                    
                # Enrich call data with details
                enriched_call = self._enrich_call_data(call, details)
                enriched_calls.append(enriched_call)
                
                # Throttle requests
                time.sleep(self.config.throttle_delay)
                
            except Exception as e:
                logger.error(f"Error processing call {call.get('id')}: {e}")
                continue
                
        logger.info(f"Successfully fetched {len(enriched_calls)} calls with details")
        return enriched_calls

    def _enrich_call_data(self, call: Dict[str, Any], details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine call metadata with detailed information into a comprehensive data structure.
        
        Args:
            call: Basic call metadata
            details: Detailed call information including transcript
            
        Returns:
            Enriched call data dictionary optimized for JSON storage
        """
        # Extract key information for easy access
        call_id = call.get("id")
        call_time = call.get("time")
        
        # Build participant mapping
        participants = self._build_participant_mapping(details)
        
        # Enhance transcript with speaker names
        transcript = self._enhance_transcript(details.get("transcript", []), participants)
        
        # Extract key metrics
        metrics = call.get("metrics", {})
        summary = details.get("summary", {})
        
        # Build enriched data structure
        enriched_data = {
            # Core identifiers
            "call_id": call_id,
            "call_time": call_time,
            "call_date": call_time[:10] if call_time else None,
            
            # Basic metadata
            "title": call.get("title", ""),
            "status": call.get("status", ""),
            
            # Business context
            "account_name": call.get("account_name", ""),
            "deal_name": call.get("deal_name", ""),
            "deal_value": call.get("deal_value", ""),
            "deal_close_date": call.get("deal_close_date", ""),
            "deal_stage_before_call": call.get("deal_stage_before_call", ""),
            "contact_names": call.get("contact_names", []),
            
            # CRM integration
            "crm_info": call.get("crm_info", {}),
            
            # Call metrics
            "metrics": {
                "duration_seconds": metrics.get("call_duration", 0),
                "talk_listen_ratio": metrics.get("talk_listen_ratio", 0),
                "num_questions_asked": metrics.get("num_questions_asked", 0),
                "engaging_questions": metrics.get("engaging_questions", 0),
                "total_speak_duration": metrics.get("total_speak_duration", 0),
                "longest_monologue_duration": metrics.get("longest_monologue_duration", 0)
            },
            
            # Participants
            "participants": participants,
            
            # Content
            "transcript": transcript,
            "summary": {
                "full_summary": summary.get("full_summary", ""),
                "key_takeaways": summary.get("key_takeaways", ""),
                "topics_discussed": summary.get("topics_discussed", []),
                "action_items": summary.get("key_action_items", [])
            },
            
            # Additional data
            "competitor_sentiments": details.get("competitor_sentiments", []),
            "bookmark_timestamps": call.get("bookmark_timestamps", []),
            
            # Processing metadata
            "fetched_at": datetime.now().isoformat(),
            "api_version": "clari_v1"
        }
        
        return enriched_data

    def _build_participant_mapping(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Build a mapping of participant IDs to names and details."""
        participants = {}
        
        # Map internal users
        for user in details.get("users", []):
            person_id = user.get("personId")
            if person_id is not None:
                email = user.get("userEmail", "")
                participants[person_id] = {
                    "name": email.split("@")[0].replace(".", " ").title() if email else f"User {user.get('userId', 'Unknown')}",
                    "email": email,
                    "is_organizer": user.get("isOrganizer", False),
                    "is_internal": True,
                    "user_id": user.get("userId")
                }
        
        # Map external participants
        for ext in details.get("externalParticipants", []):
            person_id = ext.get("personId")
            if person_id is not None:
                name = (
                    ext.get("name") or
                    ext.get("email") or
                    ext.get("phone") or
                    f"External {person_id}"
                )
                participants[person_id] = {
                    "name": name,
                    "email": ext.get("email", ""),
                    "phone": ext.get("phone", ""),
                    "is_internal": False
                }
        
        return participants

    def _enhance_transcript(self, transcript: List[Dict[str, Any]], participants: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Enhance transcript segments with speaker information."""
        enhanced_transcript = []
        
        for segment in transcript:
            enhanced_segment = segment.copy()
            person_id = segment.get("personId")
            
            if person_id is not None and person_id in participants:
                enhanced_segment["speaker_name"] = participants[person_id]["name"]
                enhanced_segment["speaker_email"] = participants[person_id].get("email", "")
                enhanced_segment["is_internal_speaker"] = participants[person_id].get("is_internal", False)
            else:
                enhanced_segment["speaker_name"] = f"Unknown Speaker {person_id}" if person_id is not None else "Unknown"
                enhanced_segment["speaker_email"] = ""
                enhanced_segment["is_internal_speaker"] = False
                
            enhanced_transcript.append(enhanced_segment)
            
        return enhanced_transcript

    def get_call_analytics(self, call_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract key analytics from call data for reporting and Blueprint schemas.
        
        Args:
            call_data: Enriched call data dictionary
            
        Returns:
            Dictionary containing key analytics suitable for Blueprint validation
        """
        metrics = call_data.get("metrics", {})
        transcript = call_data.get("transcript", [])
        
        # Calculate speaking time distribution
        internal_speakers = []
        external_speakers = []
        
        for segment in transcript:
            duration = segment.get("end", 0) - segment.get("start", 0)
            if segment.get("is_internal_speaker", False):
                internal_speakers.append(duration)
            else:
                external_speakers.append(duration)
        
        total_internal_time = sum(internal_speakers)
        total_external_time = sum(external_speakers)
        total_time = total_internal_time + total_external_time
        
        analytics = {
            "call_id": call_data.get("call_id"),
            "call_date": call_data.get("call_date"),
            "duration_minutes": round(metrics.get("duration_seconds", 0) / 60, 2),
            "talk_listen_ratio": metrics.get("talk_listen_ratio", 0),
            "questions_asked": metrics.get("num_questions_asked", 0),
            "engaging_questions": metrics.get("engaging_questions", 0),
            "internal_speak_percentage": round((total_internal_time / total_time * 100), 2) if total_time > 0 else 0,
            "external_speak_percentage": round((total_external_time / total_time * 100), 2) if total_time > 0 else 0,
            "deal_value": call_data.get("deal_value", ""),
            "deal_stage": call_data.get("deal_stage_before_call", ""),
            "account_name": call_data.get("account_name", ""),
            "topics_count": len(call_data.get("summary", {}).get("topics_discussed", [])),
            "action_items_count": len(call_data.get("summary", {}).get("action_items", [])),
            "participant_count": len(call_data.get("participants", {}))
        }
        
        return analytics


# Convenience function for easy integration with data automation workflows
def create_clari_client(account, config: Optional[ClariConfig] = None) -> ClariAPIClient:
    """
    Factory function to create a configured Clari API client.
    
    Args:
        account: Account instance containing Clari API credentials in secrets
        config: Optional configuration object
        
    Returns:
        Configured ClariAPIClient instance
    """
    return ClariAPIClient(account, config)