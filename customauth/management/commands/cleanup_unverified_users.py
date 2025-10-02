from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from customauth.models import CustomUser


class Command(BaseCommand):
    help = 'Clean up unverified user accounts older than specified days'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Delete unverified users older than this many days (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']

        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days)

        # Find unverified users older than cutoff
        unverified_users = CustomUser.objects.filter(
            is_email_verified=False,
            date_joined__lt=cutoff_date
        )

        count = unverified_users.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(f'No unverified users older than {days} days found.')
            )
            return

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would delete {count} unverified users:')
            )
            for user in unverified_users[:10]:  # Show first 10
                self.stdout.write(
                    f'  - {user.email} (registered: {user.date_joined.date()})'
                )
            if count > 10:
                self.stdout.write(f'  ... and {count - 10} more')
        else:
            # Perform deletion
            deleted_count, _ = unverified_users.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {deleted_count} unverified users older than {days} days.'
                )
            )