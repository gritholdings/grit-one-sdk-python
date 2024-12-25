from .utils import record_usage, get_remaining_units

class UsageTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Only track usage for chat-related endpoints
        if request.path.startswith('/api/chat/') and request.method == 'POST':
            if request.user.is_authenticated:
                remaining_units = get_remaining_units(request.user)
                if remaining_units > 0:
                    record_usage(request.user)
                else:
                    response.status_code = 403
                    response.content = b'{"error": "No units remaining in subscription"}'
        
        return response
