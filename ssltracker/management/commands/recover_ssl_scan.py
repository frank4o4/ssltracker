from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from ssltracker.models import ScanRun


class Command(BaseCommand):
    help = 'Release an abandoned run ONLY after all worker processes have been stopped'

    def add_arguments(self, parser):
        parser.add_argument('run_id', type=int)
        parser.add_argument('--workers-stopped', action='store_true')

    def handle(self, *args, **options):
        if not options['workers_stopped']:
            raise CommandError('Stop every SSL worker first, then pass --workers-stopped')
        count = ScanRun.objects.filter(pk=options['run_id'], active_slot=1).update(
            active_slot=None, status='failed', finished_at=timezone.now(),
            message='Abandoned run released by operator after stopping workers. Queue a new scan.')
        self.stdout.write(f'Released {count} run(s)')
