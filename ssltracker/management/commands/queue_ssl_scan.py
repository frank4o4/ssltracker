from django.core.management.base import BaseCommand
from ssltracker.jobs import enqueue_scan


class Command(BaseCommand):
    help = 'Queue a scan (safe to call from cron or Task Scheduler)'

    def add_arguments(self, parser):
        parser.add_argument('--unchecked', action='store_true')

    def handle(self, *args, **options):
        run, created = enqueue_scan(mode='unchecked' if options['unchecked'] else 'all')
        self.stdout.write(f'Scan {run.pk}: ' + ('queued' if created else 'already active'))
