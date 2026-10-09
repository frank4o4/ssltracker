"""Persistent single-flight queue; only the worker writes scan results."""
import datetime
import json
import logging
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from .models import ScanRun, ScanResult, domainlist, ssl_settings

logger = logging.getLogger(__name__)


def enqueue_scan(user=None, mode='all'):
    if mode not in ('all', 'unchecked'):
        raise ValueError('Unknown scan mode')
    # The database unique constraint arbitrates simultaneous requests/processes.
    for _ in range(3):
        try:
            with transaction.atomic():
                run = ScanRun.objects.create(active_slot=1, requested_by=user, mode=mode)
            return run, True
        except IntegrityError:
            run = ScanRun.objects.filter(active_slot=1).first()
            if run:
                return run, False
    raise RuntimeError('Could not enqueue scan; please retry')


def claim_next():
    run = ScanRun.objects.filter(active_slot=1, status='queued').first()
    if run and ScanRun.objects.filter(pk=run.pk, status='queued').update(
            status='running', started_at=timezone.now(), heartbeat_at=timezone.now()):
        run.refresh_from_db()
        return run
    return None


def scan_config():
    row = ssl_settings.objects.order_by('pk').first()
    ports = list(dict.fromkeys(int(p.strip()) for p in (row.ssl_ports if row else '443').split(',')))
    if not ports or len(ports) > 20 or any(p < 1 or p > 65535 for p in ports):
        raise ValueError('Configure between 1 and 20 valid SSL ports')
    if not 1 <= settings.SSL_SCAN_WORKERS <= 32:
        raise ValueError('SSL_SCAN_WORKERS must be between 1 and 32')
    if settings.SSL_CONNECT_TIMEOUT <= 0 or settings.SSL_DOMAIN_TIMEOUT <= 0:
        raise ValueError('SSL timeouts must be positive')
    return {'ports': ports, 'connect_timeout': settings.SSL_CONNECT_TIMEOUT,
            'ca_file': settings.SSL_CA_FILE}


def probe_domain(hostname, config):
    # A subprocess gives DNS, TCP and TLS one hard overall deadline.
    try:
        process = subprocess.run([sys.executable, '-m', 'ssltracker.probe'],
            input=json.dumps(dict(config, hostname=hostname)), capture_output=True,
            text=True, timeout=settings.SSL_DOMAIN_TIMEOUT, cwd=settings.BASE_DIR)
        if process.returncode:
            return {'success': False, 'error': 'Probe process failed; check worker configuration'}
        return json.loads(process.stdout)
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': f'Domain exceeded {settings.SSL_DOMAIN_TIMEOUT:g}s deadline'}


def save_result(run, pk, hostname, result):
    success = bool(result.get('success'))
    with transaction.atomic():
        # Keep a result for deleted/renamed domains, but do not overwrite their data.
        domain = domainlist.objects.filter(pk=pk, domain_name=hostname).first()
        if domain and success:
            today = timezone.localdate()
            fields = {key: result[key] for key in (
                'expires', 'ssl_issuer_organization', 'ssl_issuer_common_name', 'sans')}
            if result.get('ipAddress'):
                fields['ipAddress'] = result['ipAddress']
            fields.update(last_updated=today.isoformat(),
                          days_left=(datetime.date.fromisoformat(result['expires']) - today).days)
            domainlist.objects.filter(pk=pk, domain_name=hostname).update(**fields)
        ScanResult.objects.create(run=run, domain=domain, hostname=hostname,
                                  success=success, error=result.get('error', '')[:2000])
        run.completed += 1
        run.failed += int(not success)
        run.heartbeat_at = timezone.now()
        run.save(update_fields=['completed', 'failed', 'heartbeat_at'])


def execute_run(run):
    try:
        config = scan_config()
        if settings.SSL_DIGICERT_SYNC and run.mode == 'all':
            from .utils import digiApiGet, update_domainlist_from_digicert
            try:
                digiApiGet()
                update_domainlist_from_digicert()
            except Exception:
                logger.exception('DigiCert inventory sync failed')
                run.message = 'DigiCert sync failed or may be truncated; existing inventory retained. See worker log.'
                run.save(update_fields=['message'])
        query = domainlist.objects.order_by('pk')
        if run.mode == 'unchecked':
            query = query.exclude(last_updated=timezone.localdate().isoformat())
        # Freeze membership so inserts/edits during the run cannot shift pagination.
        snapshot = list(query.values_list('pk', 'domain_name'))
        run.total = len(snapshot)
        domains = iter(snapshot)
        run.save(update_fields=['total'])
        with ThreadPoolExecutor(max_workers=settings.SSL_SCAN_WORKERS) as pool:
            pending = {}
            def fill():
                while len(pending) < settings.SSL_SCAN_WORKERS:
                    item = next(domains, None)
                    if item is None:
                        break
                    pk, hostname = item
                    pending[pool.submit(probe_domain, hostname, config)] = item
            fill()
            while pending:
                done, _ = wait(pending, timeout=2, return_when=FIRST_COMPLETED)
                ScanRun.objects.filter(pk=run.pk).update(heartbeat_at=timezone.now())
                for future in done:
                    pk, hostname = pending.pop(future)
                    try:
                        result = future.result()
                    except Exception as exc:
                        result = {'success': False, 'error': str(exc)[:2000]}
                    save_result(run, pk, hostname, result)
                fill()
        run.status = 'completed'
    except Exception:
        logger.exception('SSL run %s failed', run.pk)
        run.status = 'failed'
        run.message = 'Worker error; see the worker log. Completed results have been retained.'
    # A hard kill intentionally leaves the lock held. Never expire it while a
    # paused worker could resume and write over a new run.
    run.active_slot = None
    run.finished_at = timezone.now()
    run.save(update_fields=['status', 'message', 'active_slot', 'finished_at'])
