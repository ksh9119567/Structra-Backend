import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import ActivityLog

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up old activity logs to prevent database bloat'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=90,
            help='Delete activity logs older than this many days (default: 90)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(
            self.style.WARNING(
                f'Finding activity logs older than {days} days (before {cutoff_date.date()})...'
            )
        )
        
        old_logs = ActivityLog.objects.filter(timestamp__lt=cutoff_date)
        count = old_logs.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No old activity logs found.'))
            return
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would delete {count} activity logs.'
                )
            )
            
            # Show sample of what would be deleted
            sample = old_logs[:5]
            self.stdout.write('\nSample of logs that would be deleted:')
            for log in sample:
                self.stdout.write(
                    f'  - {log.timestamp} | {log.username} | {log.action} | {log.resource_type}'
                )
            
            if count > 5:
                self.stdout.write(f'  ... and {count - 5} more')
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'Deleting {count} activity logs...'
                )
            )
            
            deleted_count, _ = old_logs.delete()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully deleted {deleted_count} activity logs.'
                )
            )
            
            logger.info(f'Cleaned up {deleted_count} activity logs older than {days} days')
