"""Real separate-process queue/claim race test using a disposable SQLite database."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
BOOT = '''
import os, sys
os.environ['SSLTRACKER_SQLITE'] = '1'
os.environ['DJANGO_SETTINGS_MODULE'] = 'ssltracker.settings'
from django.conf import settings
settings.DATABASES['default']['NAME'] = sys.argv[1]
import django
django.setup()
'''


def main():
    with tempfile.TemporaryDirectory() as temporary:
        db = str(Path(temporary) / 'race.sqlite3')
        def command(code):
            return [sys.executable, '-c', BOOT + code, db]
        subprocess.run(command("from django.core.management import call_command\ncall_command('migrate', verbosity=0)"), cwd=ROOT, check=True)
        for operation, expected in [
            ("from ssltracker.jobs import enqueue_scan\nr, created = enqueue_scan()\nprint(int(created))", 1),
            ("from ssltracker.jobs import claim_next\nprint(int(claim_next() is not None))", 1),
        ]:
            processes = [subprocess.Popen(command(operation), cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) for _ in range(8)]
            winners = 0
            for process in processes:
                output, error = process.communicate(timeout=30)
                assert process.returncode == 0, error
                winners += int(output.strip())
            assert winners == expected, f'{winners} winners, expected {expected}'
        print('PASS: 8 concurrent enqueue processes created one run; 8 worker processes claimed it once.')


if __name__ == '__main__':
    main()
