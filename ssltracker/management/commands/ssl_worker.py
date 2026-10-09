import time
from django.core.management.base import BaseCommand
from django.db import close_old_connections
from ssltracker.jobs import claim_next, execute_run


class Command(BaseCommand):
    help = 'Process queued SSL scans. Run separately from the web server.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Process at most one queued run and exit')

    def handle(self, *args, **options):
        self.stdout.write('SSL worker ready')
        while True:
            close_old_connections()
            run = claim_next()
            if run:
                self.stdout.write(f'Processing scan {run.pk}')
                execute_run(run)
            if options['once']:
                return
            if not run:
                time.sleep(2)
