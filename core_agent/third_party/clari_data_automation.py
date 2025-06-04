import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from django.apps import apps
from ..models import DataAutomationProject, DataAutomationInvocation
from .clari import create_clari_client, ClariAPIError


logger = logging.getLogger(__name__)


class ClariDataAutomationService:
    """
    Data automation service for Clari API integration.
    
    This service handles the execution of Clari data fetching operations within
    the existing DataAutomationProject framework, storing results in DataAutomationInvocation
    metadata for further processing and analysis.
    """
    
    @staticmethod
    def execute_clari_data_fetch(project: DataAutomationProject, filters: Optional[Dict[str, Any]] = None) -> DataAutomationInvocation:
        """
        Execute Clari data fetch operation for a DataAutomationProject.
        
        Args:
            project: DataAutomationProject instance
            filters: Optional filters for Clari API call filtering
            
        Returns:
            DataAutomationInvocation instance with results stored in metadata
        """
        # Create invocation record
        invocation = DataAutomationInvocation.objects.create(
            data_automation_project=project,
            status=DataAutomationInvocation.Status.CREATED,
            metadata={
                'operation_type': 'clari_data_fetch',
                'filters': filters or {},
                'started_at': datetime.now().isoformat()
            }
        )
        
        try:
            # Update status to in progress
            invocation.status = DataAutomationInvocation.Status.IN_PROGRESS
            invocation.save()
            
            logger.info(f"Starting Clari data fetch for project {project.id}")
            
            # Get user's account for API credentials
            account = project.account
            if not account:
                raise ValueError("Project must be associated with an account for Clari integration")
            
            # Create Clari client
            clari_client = create_clari_client(account)
            
            # Merge project metadata filters with provided filters
            project_filters = project.metadata.get('clari_filters', {}) if project.metadata else {}
            combined_filters = {**project_filters, **(filters or {})}
            
            # Fetch calls with details
            max_calls = combined_filters.get('max_calls', 50)
            call_data = clari_client.fetch_calls_with_details(
                filters=combined_filters,
                max_calls=max_calls
            )
            
            # Process data through any configured blueprints
            processed_data = ClariDataAutomationService._process_through_blueprints(
                project, call_data
            )
            
            # Generate analytics for summary
            analytics = ClariDataAutomationService.get_clari_analytics_from_data(call_data)
            
            # Create formatted summary for text_input field
            summary_lines = [
                f"Clari Data Fetch Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Total Calls Retrieved: {len(call_data)}",
                ""
            ]
            
            # Add date range if available
            if call_data:
                call_dates = [call.get('call_date') for call in call_data if call.get('call_date')]
                if call_dates:
                    summary_lines.extend([
                        f"Date Range: {min(call_dates)} to {max(call_dates)}",
                        ""
                    ])
            
            # Add analytics summary
            if analytics:
                summary_lines.extend([
                    "Key Metrics:",
                    f"- Total Duration: {analytics.get('total_duration_hours', 0):.1f} hours",
                    f"- Average Call Duration: {analytics.get('avg_duration_minutes', 0):.1f} minutes",
                    f"- Unique Accounts: {analytics.get('unique_accounts_count', 0)}",
                    f"- Total Deal Value: ${analytics.get('total_deal_value', 0):,.2f}",
                    ""
                ])
            
            # Add filters applied
            if combined_filters:
                summary_lines.append("Filters Applied:")
                for key, value in combined_filters.items():
                    if value:
                        summary_lines.append(f"- {key.replace('_', ' ').title()}: {value}")
                summary_lines.append("")
            
            # Check if transcript blueprint is being used and add transcript text for chatbot consumption
            transcript_blueprint_used = any(
                blueprint.name == "Clari Transcript Text" 
                for blueprint in project.blueprints.all()
            )
            
            if transcript_blueprint_used and call_data:
                summary_lines.extend([
                    "TRANSCRIPT DATA FOR CHATBOT PROCESSING:",
                    "="*50,
                    ""
                ])
                
                # Add clean transcript text from all calls for easy chatbot consumption
                for i, call in enumerate(call_data, 1):
                    transcript_text = ClariDataAutomationService._extract_transcript_text(call, include_speakers=False)
                    if transcript_text:
                        summary_lines.extend([
                            f"Call {i} - {call.get('account_name', 'Unknown Account')} ({call.get('call_date', 'Unknown Date')}):",
                            transcript_text,
                            "",
                            "-" * 30,
                            ""
                        ])
                
                summary_lines.extend([
                    "="*50,
                    ""
                ])
            
            summary_lines.append("Full data available in clari_response metadata field.")
            text_input_summary = "\n".join(summary_lines)
            
            # Store results in invocation metadata using the expected structure
            invocation.metadata.update({
                'clari_response': {
                    'calls': call_data,
                    'analytics': analytics,
                    'filters_applied': combined_filters,
                    'fetched_at': datetime.now().isoformat(),
                    'total_calls': len(call_data),
                    'api_version': 'clari_v1'
                },
                'text_input': text_input_summary,
                'completed_at': datetime.now().isoformat(),
                'calls_fetched': len(call_data),
                'processed_data': processed_data
            })
            
            # Update status to success
            invocation.status = DataAutomationInvocation.Status.SUCCESS
            invocation.save()
            
            logger.info(f"Successfully completed Clari data fetch for project {project.id}. Fetched {len(call_data)} calls.")
            
        except Exception as e:
            logger.error(f"Error in Clari data fetch for project {project.id}: {str(e)}")
            
            # Update status to error and store error information
            invocation.status = DataAutomationInvocation.Status.ERROR
            invocation.metadata.update({
                'error_at': datetime.now().isoformat(),
                'error_message': str(e),
                'error_type': type(e).__name__
            })
            invocation.save()
            
        return invocation
    
    @staticmethod
    def _process_through_blueprints(project: DataAutomationProject, call_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Process call data through any configured Blueprint schemas.
        
        Args:
            project: DataAutomationProject with potential Blueprint associations
            call_data: List of enriched call data dictionaries
            
        Returns:
            List of processed data following Blueprint schemas
        """
        if not project.blueprints.exists():
            logger.debug(f"No blueprints configured for project {project.id}")
            return call_data
            
        processed_data = []
        
        for blueprint in project.blueprints.all():
            logger.debug(f"Processing data through blueprint: {blueprint.name}")
            
            blueprint_schema = blueprint.schema or {}
            properties = blueprint_schema.get('properties', {})
            
            for call in call_data:
                processed_call = {}
                
                # Extract fields defined in blueprint schema
                for field_name, field_config in properties.items():
                    field_value = ClariDataAutomationService._extract_field_value(
                        call, field_name, field_config
                    )
                    processed_call[field_name] = field_value
                
                # Add metadata about processing
                processed_call['_blueprint_name'] = blueprint.name
                processed_call['_blueprint_id'] = str(blueprint.id)
                processed_call['_processed_at'] = datetime.now().isoformat()
                processed_call['_original_call_id'] = call.get('call_id')
                
                processed_data.append(processed_call)
        
        return processed_data
    
    @staticmethod
    def _extract_field_value(call_data: Dict[str, Any], field_name: str, field_config: Dict[str, Any]) -> Any:
        """
        Extract field value from call data based on field configuration.
        
        Args:
            call_data: Enriched call data dictionary
            field_name: Name of the field to extract
            field_config: Blueprint field configuration
            
        Returns:
            Extracted field value or None if not found
        """
        # Simple field mapping for common Clari fields
        field_mappings = {
            'call_id': 'call_id',
            'call_date': 'call_date',
            'call_time': 'call_time',
            'title': 'title',
            'account_name': 'account_name',
            'deal_name': 'deal_name',
            'deal_value': 'deal_value',
            'deal_stage': 'deal_stage_before_call',
            'duration_minutes': 'metrics.duration_seconds',
            'talk_listen_ratio': 'metrics.talk_listen_ratio',
            'questions_asked': 'metrics.num_questions_asked',
            'summary': 'summary.full_summary',
            'action_items': 'summary.action_items',
            'participant_count': lambda data: len(data.get('participants', {})),
            'transcript_text': lambda data: ClariDataAutomationService._extract_transcript_text(data, include_speakers=True),
            'transcript_clean': lambda data: ClariDataAutomationService._extract_transcript_text(data, include_speakers=False),
            'word_count': lambda data: len(ClariDataAutomationService._extract_transcript_text(data, include_speakers=False).split())
        }
        
        mapping = field_mappings.get(field_name)
        
        if callable(mapping):
            return mapping(call_data)
        elif isinstance(mapping, str):
            # Handle nested field access with dots
            value = call_data
            for key in mapping.split('.'):
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return None
            return value
        else:
            # Direct field access
            return call_data.get(field_name)
    
    @staticmethod
    def _extract_transcript_text(call_data: Dict[str, Any], include_speakers: bool = True) -> str:
        """
        Extract plain text from call transcript data.
        
        Args:
            call_data: Enriched call data dictionary containing transcript
            include_speakers: Whether to include speaker names in the output
            
        Returns:
            Plain text transcript string
        """
        transcript = call_data.get('transcript', [])
        if not transcript:
            return ""
            
        text_segments = []
        
        for segment in transcript:
            text = segment.get('text', '').strip()
            if not text:
                continue
                
            if include_speakers:
                speaker_name = segment.get('speaker_name', 'Unknown Speaker')
                text_segments.append(f"{speaker_name}: {text}")
            else:
                text_segments.append(text)
        
        return "\n".join(text_segments)
    
    @staticmethod
    def _get_date_range(call_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Get the date range of calls in the data."""
        if not call_data:
            return {'start': None, 'end': None}
            
        dates = [call.get('call_date') for call in call_data if call.get('call_date')]
        if not dates:
            return {'start': None, 'end': None}
            
        return {
            'start': min(dates),
            'end': max(dates)
        }
    
    @staticmethod
    def get_clari_analytics_from_data(call_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate analytics directly from call data.
        
        Args:
            call_data: List of call data dictionaries
            
        Returns:
            Dictionary containing analytics and insights
        """
        if not call_data:
            return {}
            
        # Calculate aggregate metrics
        total_calls = len(call_data)
        total_duration = sum(call.get('metrics', {}).get('duration_seconds', 0) for call in call_data)
        total_questions = sum(call.get('metrics', {}).get('num_questions_asked', 0) for call in call_data)
        
        # Deal value analysis
        deal_values = [float(call.get('deal_value', 0) or 0) for call in call_data]
        total_deal_value = sum(deal_values)
        avg_deal_value = total_deal_value / total_calls if total_calls > 0 else 0
        
        return {
            'total_calls': total_calls,
            'total_duration_hours': round(total_duration / 3600, 2),
            'avg_duration_minutes': round(total_duration / 60 / total_calls, 2) if total_calls > 0 else 0,
            'total_questions': total_questions,
            'avg_questions_per_call': round(total_questions / total_calls, 2) if total_calls > 0 else 0,
            'total_deal_value': total_deal_value,
            'avg_deal_value': round(avg_deal_value, 2),
        }
    
    @staticmethod
    def get_clari_analytics(invocation: DataAutomationInvocation) -> Dict[str, Any]:
        """
        Extract analytics from a completed Clari data fetch invocation.
        
        Args:
            invocation: DataAutomationInvocation with Clari data
            
        Returns:
            Dictionary containing analytics and insights
        """
        if not invocation.metadata or invocation.status != DataAutomationInvocation.Status.SUCCESS:
            return {}
            
        call_data = invocation.metadata.get('raw_data', [])
        if not call_data:
            return {}
            
        # Calculate aggregate metrics
        total_calls = len(call_data)
        total_duration = sum(call.get('metrics', {}).get('duration_seconds', 0) for call in call_data)
        total_questions = sum(call.get('metrics', {}).get('num_questions_asked', 0) for call in call_data)
        
        # Deal value analysis
        deal_values = [float(call.get('deal_value', 0) or 0) for call in call_data]
        total_deal_value = sum(deal_values)
        avg_deal_value = total_deal_value / total_calls if total_calls > 0 else 0
        
        # Account analysis
        accounts = {}
        for call in call_data:
            account_name = call.get('account_name', 'Unknown')
            if account_name not in accounts:
                accounts[account_name] = {'calls': 0, 'total_value': 0}
            accounts[account_name]['calls'] += 1
            accounts[account_name]['total_value'] += float(call.get('deal_value', 0) or 0)
        
        # Stage analysis
        stages = {}
        for call in call_data:
            stage = call.get('deal_stage_before_call', 'Unknown')
            stages[stage] = stages.get(stage, 0) + 1
        
        return {
            'total_calls': total_calls,
            'total_duration_hours': round(total_duration / 3600, 2),
            'avg_duration_minutes': round(total_duration / 60 / total_calls, 2) if total_calls > 0 else 0,
            'total_questions': total_questions,
            'avg_questions_per_call': round(total_questions / total_calls, 2) if total_calls > 0 else 0,
            'total_deal_value': total_deal_value,
            'avg_deal_value': round(avg_deal_value, 2),
            'unique_accounts': len(accounts),
            'top_accounts': sorted(accounts.items(), key=lambda x: x[1]['total_value'], reverse=True)[:5],
            'deal_stages': stages,
            'date_range': invocation.metadata.get('summary', {}).get('date_range', {}),
            'processed_at': invocation.metadata.get('completed_at')
        }


# Convenience function for easy integration
def execute_clari_project(project: DataAutomationProject, **kwargs) -> DataAutomationInvocation:
    """
    Convenience function to execute Clari data automation for a project.
    
    Args:
        project: DataAutomationProject instance
        **kwargs: Additional filters and options
        
    Returns:
        DataAutomationInvocation instance with results
    """
    return ClariDataAutomationService.execute_clari_data_fetch(project, kwargs)