from django.core.management.base import BaseCommand
from django.urls import get_resolver, URLPattern, URLResolver
from django.conf import settings


class Command(BaseCommand):
    help = 'Display all URL patterns in the project'

    def add_arguments(self, parser):
        parser.add_argument(
            '--filter',
            type=str,
            help='Filter URLs by pattern (case-insensitive)',
        )
        parser.add_argument(
            '--name-only',
            action='store_true',
            help='Show only named URLs',
        )

    def handle(self, *args, **options):
        filter_text = options.get('filter', '').lower() if options.get('filter') else ''
        name_only = options.get('name_only', False)
        
        resolver = get_resolver()
        url_patterns = []
        
        def extract_patterns(url_pattern, prefix=''):
            """Recursively extract all URL patterns."""
            if isinstance(url_pattern, URLResolver):
                # This is an included URLconf
                pattern_str = str(url_pattern.pattern)
                new_prefix = prefix + pattern_str
                for pattern in url_pattern.url_patterns:
                    extract_patterns(pattern, new_prefix)
            elif isinstance(url_pattern, URLPattern):
                # This is a regular pattern
                pattern_str = prefix + str(url_pattern.pattern)
                
                # Get view name
                callback = url_pattern.callback
                if callback:
                    if hasattr(callback, '__name__'):
                        view_name = f"{callback.__module__}.{callback.__name__}"
                    else:
                        view_name = str(callback)
                else:
                    view_name = "None"
                
                url_patterns.append({
                    'pattern': pattern_str,
                    'name': url_pattern.name,
                    'view': view_name
                })
        
        # Extract all patterns - start with url_patterns from resolver
        for pattern in resolver.url_patterns:
            extract_patterns(pattern)
        
        # Sort patterns by URL
        url_patterns.sort(key=lambda x: x['pattern'])
        
        # Filter if requested
        if filter_text:
            url_patterns = [
                p for p in url_patterns 
                if filter_text in p['pattern'].lower() 
                or (p['name'] and filter_text in p['name'].lower())
                or filter_text in p['view'].lower()
            ]
        
        # Filter name-only if requested
        if name_only:
            url_patterns = [p for p in url_patterns if p['name']]
        
        # Display results
        if not url_patterns:
            self.stdout.write('No URL patterns found.')
            return
        
        # Calculate column widths
        max_pattern = max(len(p['pattern']) for p in url_patterns) if url_patterns else 0
        max_name = max(len(p['name'] or '') for p in url_patterns) if url_patterns else 0
        
        # Print header
        self.stdout.write(f"{'URL Pattern':<{max_pattern}}  {'Name':<{max_name}}  View")
        self.stdout.write("-" * (max_pattern + max_name + 50))
        
        # Print patterns
        for pattern_info in url_patterns:
            pattern = pattern_info['pattern']
            name = pattern_info['name'] or ''
            view = pattern_info['view']
            
            # Highlight Agent-related URLs
            if 'agent' in pattern.lower() or 'agent' in name.lower():
                self.stdout.write(f">>> {pattern:<{max_pattern}}  {name:<{max_name}}  {view}")
            else:
                self.stdout.write(f"{pattern:<{max_pattern}}  {name:<{max_name}}  {view}")
        
        self.stdout.write(f"\nTotal: {len(url_patterns)} URL patterns")