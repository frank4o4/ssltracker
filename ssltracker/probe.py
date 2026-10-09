"""Standalone bounded TLS probe. No Django imports or database access."""
import datetime
import json
import socket
import ssl
import sys


def probe(config):
    host = config['hostname'].strip().encode('idna').decode('ascii')
    context = ssl.create_default_context(cafile=config.get('ca_file'))
    errors = []
    for port in config['ports']:
        try:
            sock = None
            try:
                sock = socket.create_connection((host, port), timeout=config['connect_timeout'])
                with context.wrap_socket(sock, server_hostname=host) as tls:
                    cert = tls.getpeercert()
                    expiry = datetime.datetime.fromtimestamp(
                        ssl.cert_time_to_seconds(cert['notAfter']), datetime.timezone.utc).date()
                    issuer = dict(pair for rdn in cert.get('issuer', ()) for pair in rdn)
                    return {'success': True, 'expires': expiry.isoformat(),
                            'ssl_issuer_organization': issuer.get('organizationName', ''),
                            'ssl_issuer_common_name': issuer.get('commonName', ''),
                            'sans': ', '.join(v for k, v in cert.get('subjectAltName', ()) if k == 'DNS'),
                            'ipAddress': tls.getpeername()[0]}
            finally:
                if sock is not None:
                    sock.close()
        except (OSError, ValueError) as exc:
            errors.append(f'Port {port}: {exc}')
    return {'success': False, 'error': '; '.join(errors)[:2000]}


if __name__ == '__main__':
    try:
        result = probe(json.load(sys.stdin))
    except Exception as exc:
        result = {'success': False, 'error': str(exc)[:2000]}
    print(json.dumps(result))
