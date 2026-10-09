import subprocess
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch, Mock
from django.contrib.auth.models import User, Group
from django.core.management import call_command
from django.db import IntegrityError, transaction, close_old_connections
from django.template.loader import get_template
from django.test import TestCase, TransactionTestCase, override_settings, Client
from .jobs import enqueue_scan, claim_next, execute_run, probe_domain
from .models import ScanRun, ScanResult, domainlist, ssl_settings, digicert
from .probe import probe

GOOD = {'success': True, 'expires': '2027-01-01', 'ssl_issuer_organization': 'Example CA',
        'ssl_issuer_common_name': 'Example', 'sans': 'example.test', 'ipAddress': '192.0.2.1'}


@override_settings(SSL_SCAN_WORKERS=3, SSL_DIGICERT_SYNC=False)
class ScanTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('operator', password='test-password')
        self.user.groups.add(Group.objects.get(name='Dashboard'))
        self.client.force_login(self.user)

    def test_repeated_and_mixed_requests_join_existing_run(self):
        first, created = enqueue_scan(self.user)
        second, duplicate = enqueue_scan(mode='unchecked')
        self.assertTrue(created)
        self.assertFalse(duplicate)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(ScanRun.objects.count(), 1)

    def test_two_workers_only_one_claim(self):
        enqueue_scan()
        self.assertIsNotNone(claim_next())
        self.assertIsNone(claim_next())

    def test_database_rejects_second_active_slot(self):
        enqueue_scan()
        with self.assertRaises(IntegrityError), transaction.atomic():
            ScanRun.objects.create(active_slot=1)

    def test_post_only_and_reader_denied(self):
        self.assertEqual(self.client.get('/update_ssl/').status_code, 405)
        self.assertEqual(self.client.get('/update_unchecked_ssls/').status_code, 405)
        self.user.groups.clear()
        self.user.groups.add(Group.objects.get(name='Readers'))
        self.assertEqual(self.client.post('/update_ssl/').status_code, 403)
        self.assertEqual(ScanRun.objects.count(), 0)

    def test_csrf_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        self.assertEqual(client.post('/update_ssl/').status_code, 403)

    def test_post_returns_without_network_work(self):
        with patch('ssltracker.jobs.probe_domain') as network:
            response = self.client.post('/update_ssl/')
            self.assertEqual(response.status_code, 302)
            network.assert_not_called()
            self.assertContains(self.client.get(response.url), 'Waiting for the background worker')
            self.assertContains(self.client.get('/scans/'), 'operator')

    def test_over_one_hundred_domains_parallel_and_bounded(self):
        domainlist.objects.bulk_create([domainlist(domain_name=f'd{i}.test') for i in range(125)])
        active = peak = 0
        lock = threading.Lock()
        def fake(*args):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
            time.sleep(.003)
            with lock:
                active -= 1
            return GOOD.copy()
        enqueue_scan()
        run = claim_next()
        with patch('ssltracker.jobs.probe_domain', side_effect=fake):
            execute_run(run)
        run.refresh_from_db()
        self.assertEqual((run.total, run.completed, run.failed, run.status), (125, 125, 0, 'completed'))
        self.assertEqual(ScanResult.objects.count(), 125)
        self.assertIsNone(run.active_slot)
        self.assertGreater(peak, 1)
        self.assertLessEqual(peak, 3)
        self.assertTrue(enqueue_scan()[1])

    def test_failure_keeps_old_certificate_and_records_error(self):
        domain = domainlist.objects.create(domain_name='bad.test', expires='2020-01-01', last_updated='2020-01-01')
        enqueue_scan()
        run = claim_next()
        with patch('ssltracker.jobs.probe_domain', return_value={'success': False, 'error': 'Timed out'}):
            execute_run(run)
        domain.refresh_from_db()
        run.refresh_from_db()
        self.assertEqual(domain.expires, '2020-01-01')
        self.assertEqual(domain.last_updated, '2020-01-01')
        self.assertEqual(run.failed, 1)
        self.assertContains(self.client.get(f'/scans/{run.pk}/'), 'Timed out')

    def test_unchecked_skips_today(self):
        from django.utils import timezone
        domainlist.objects.create(domain_name='fresh.test', last_updated=timezone.localdate().isoformat())
        domainlist.objects.create(domain_name='old.test')
        enqueue_scan(mode='unchecked')
        with patch('ssltracker.jobs.probe_domain', return_value=GOOD) as network:
            execute_run(claim_next())
        self.assertEqual(network.call_count, 1)
        self.assertEqual(network.call_args.args[0], 'old.test')

    def test_hard_timeout_is_failure(self):
        with patch('ssltracker.jobs.subprocess.run', side_effect=subprocess.TimeoutExpired('probe', 30)):
            result = probe_domain('blocked.test', {})
        self.assertFalse(result['success'])
        self.assertIn('deadline', result['error'])

    def test_worker_error_releases_lock(self):
        enqueue_scan()
        run = claim_next()
        with patch('ssltracker.jobs.scan_config', side_effect=ValueError('Invalid ports')):
            with self.assertLogs('ssltracker.jobs', level='ERROR'):
                execute_run(run)
        run.refresh_from_db()
        self.assertEqual(run.status, 'failed')
        self.assertIsNone(run.active_slot)

    def test_empty_scan_finishes(self):
        enqueue_scan()
        execute_run(claim_next())
        self.assertEqual(ScanRun.objects.get().status, 'completed')

    def test_stale_run_is_not_automatically_unlocked(self):
        from django.utils import timezone
        import datetime
        enqueue_scan()
        run = claim_next()
        ScanRun.objects.filter(pk=run.pk).update(heartbeat_at=timezone.now()-datetime.timedelta(hours=1))
        self.assertFalse(enqueue_scan()[1])
        self.assertContains(self.client.get(f'/scans/{run.pk}/'), 'has not reported recently')

    def test_recovery_requires_explicit_stopped_workers_flag(self):
        from django.core.management.base import CommandError
        run, _ = enqueue_scan()
        with self.assertRaises(CommandError):
            call_command('recover_ssl_scan', str(run.pk))
        call_command('recover_ssl_scan', str(run.pk), '--workers-stopped')
        self.assertTrue(enqueue_scan()[1])

    def test_all_templates_compile(self):
        from django.conf import settings
        root = settings.BASE_DIR / 'ssltracker' / 'templates'
        for file in root.rglob('*.html'):
            get_template(str(file.relative_to(root)))

    def test_digicert_truncated_or_bad_response_retains_cache(self):
        from .utils import digiApiGet
        ssl_settings.objects.all().update(digicert_api_key='test-key')
        digicert.objects.create(cert_id='old', cn='old.test')
        response = Mock()
        response.json.return_value = {'data': {'certificateDetailsDTOList': [{}] * 100}}
        with patch('ssltracker.utils.direct_post', return_value=response):
            with self.assertRaises(ValueError):
                digiApiGet()
        self.assertEqual(digicert.objects.get().cert_id, 'old')

    def test_probe_stops_at_first_success(self):
        tls = Mock()
        tls.__enter__ = Mock(return_value=tls)
        tls.__exit__ = Mock(return_value=False)
        tls.getpeercert.return_value = {'notAfter': 'Jan  1 00:00:00 2027 GMT', 'issuer': (), 'subjectAltName': ()}
        tls.getpeername.return_value = ('192.0.2.1', 443)
        context = Mock()
        context.wrap_socket.return_value = tls
        with patch('ssltracker.probe.ssl.create_default_context', return_value=context), patch('ssltracker.probe.socket.create_connection') as connect:
            result = probe({'hostname': 'example.test', 'ports': [443, 8443], 'connect_timeout': 5})
        self.assertTrue(result['success'])
        self.assertEqual(connect.call_count, 1)

    def test_invalid_tls_records_failure(self):
        import ssl
        context = Mock()
        context.wrap_socket.side_effect = ssl.SSLCertVerificationError('expired')
        with patch('ssltracker.probe.ssl.create_default_context', return_value=context), patch('ssltracker.probe.socket.create_connection'):
            result = probe({'hostname': 'example.test', 'ports': [443], 'connect_timeout': 5})
        self.assertFalse(result['success'])
        self.assertIn('expired', result['error'])

    def test_database_requires_slot_for_active_status(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            ScanRun.objects.create(status='queued', active_slot=None)

    def test_real_probe_subprocess_validates_local_tls(self):
        import shutil
        import socket
        import ssl
        if not shutil.which('openssl'):
            self.skipTest('openssl is required for the local TLS fixture')
        with tempfile.TemporaryDirectory() as directory:
            key, cert = str(Path(directory) / 'key.pem'), str(Path(directory) / 'cert.pem')
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                '-keyout', key, '-out', cert, '-days', '1', '-subj', '/CN=localhost',
                '-addext', 'subjectAltName=IP:127.0.0.1'], check=True, capture_output=True)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(cert, key)
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0))
                listener.listen()
                listener.settimeout(5)
                errors = []
                def serve():
                    try:
                        connection, _ = listener.accept()
                        with context.wrap_socket(connection, server_side=True) as tls:
                            tls.recv(1)
                    except Exception as exc:
                        errors.append(exc)
                thread = threading.Thread(target=serve)
                thread.start()
                result = probe_domain('127.0.0.1', {
                    'ports': [listener.getsockname()[1]], 'connect_timeout': 2, 'ca_file': cert})
                thread.join(timeout=6)
                self.assertFalse(errors)
                self.assertTrue(result['success'], result)
                self.assertEqual(result['ipAddress'], '127.0.0.1')

    @override_settings(SSL_DOMAIN_TIMEOUT=.5)
    def test_real_probe_deadline_kills_stalled_tls(self):
        import socket
        release = threading.Event()
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            listener.settimeout(3)
            def serve():
                try:
                    connection, _ = listener.accept()
                    with connection:
                        release.wait(3)
                except OSError:
                    pass
            thread = threading.Thread(target=serve)
            thread.start()
            try:
                result = probe_domain('127.0.0.1', {
                    'ports': [listener.getsockname()[1]], 'connect_timeout': 10})
                self.assertFalse(result['success'])
                self.assertIn('deadline', result['error'])
            finally:
                release.set()
                thread.join(timeout=4)


class InterfaceTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('siteadmin', 'admin@example.test', 'Test-only-password')
        self.client.force_login(self.admin)

    def test_expiry_filters_use_recorded_date_not_stale_day_counter(self):
        from django.utils import timezone
        import datetime
        today = timezone.localdate()
        domainlist.objects.create(domain_name='expired.test', expires=(today-datetime.timedelta(days=1)).isoformat(), days_left='999')
        domainlist.objects.create(domain_name='soon.test', expires=(today+datetime.timedelta(days=7)).isoformat(), days_left='999')
        domainlist.objects.create(domain_name='healthy.test', expires=(today+datetime.timedelta(days=90)).isoformat())
        domainlist.objects.create(domain_name='bad-date.test', expires='invalid')
        page = self.client.get('/?status=expired')
        self.assertContains(page, 'expired.test')
        self.assertNotContains(page, 'soon.test')
        self.assertEqual(page.context['stats']['expired'], 1)
        self.assertEqual(page.context['stats']['soon'], 1)
        self.assertEqual(page.context['stats']['total'], 4)

    def test_filter_and_search_survive_pagination(self):
        domainlist.objects.bulk_create([domainlist(domain_name=f'find{i}.test') for i in range(30)])
        page = self.client.get('/?search=find&status=unchecked')
        self.assertContains(page, 'search=find&amp;status=unchecked&amp;page=2')

    def test_contact_detail_keeps_authenticated_account_navigation(self):
        from .models import contacts
        contact = contacts.objects.create(first_name='Other', last_name='Person', email='other@example.test')
        page = self.client.get(f'/view_user_ssls/{contact.pk}/')
        self.assertContains(page, 'siteadmin')
        self.assertContains(page, 'Other Person')
        self.assertContains(page, 'Workspace')

    def test_destructive_and_email_gets_do_not_mutate(self):
        domain = domainlist.objects.create(domain_name='keep.test')
        self.assertEqual(self.client.get(f'/delete_domain/{domain.pk}/').status_code, 405)
        self.assertTrue(domainlist.objects.filter(pk=domain.pk).exists())
        with patch('ssltracker.views.check_expiry') as send:
            self.assertEqual(self.client.get('/check_expiry/').status_code, 405)
            send.assert_not_called()
        self.assertEqual(self.client.get('/logout/').status_code, 405)

    def test_reader_has_no_mutation_controls(self):
        reader = User.objects.create_user('reader')
        reader.groups.add(Group.objects.get(name='Readers'))
        self.client.force_login(reader)
        page = self.client.get('/')
        self.assertNotContains(page, 'Run SSL scan')
        self.assertNotContains(page, 'Add domain')
        self.assertNotContains(page, 'Administration')
        self.assertContains(page, 'Scan history')

    def test_invalid_user_edit_renders_errors(self):
        page = self.client.post(f'/edit_users/{self.admin.pk}/', {'username': ''})
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'This field is required')

    def test_http_integrations_ignore_environment_routing(self):
        from .utils import direct_post
        with patch('ssltracker.utils.requests.Session') as session_type:
            session = session_type.return_value.__enter__.return_value
            direct_post('https://example.test', timeout=(5,30))
            self.assertIs(session.trust_env, False)
            session.post.assert_called_once_with('https://example.test', timeout=(5,30))
