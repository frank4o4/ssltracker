import datetime
import socket
import ssl
import socks  # Make sure you have the 'PySocks' library installed
from ssltracker import ssl_settings, domainlist  # Replace 'your_app' with the actual name of your Django app

def check_ssl(domain):
    ssl_ports_string = ssl_settings.objects.values_list('ssl_ports', flat=True).first()
    ssl_ports = [int(port) for port in ssl_ports_string.split(',')]

    try:
        current_date = datetime.datetime.now().date()
        ssl_context = ssl.create_default_context()

        proxy_server = "mvcache.cusa.canon.com"
        proxy_port = 80
        proxy = {
            'proxy_type': socks.PROXY_TYPE_HTTP,
            'addr': proxy_server,
            'port': proxy_port,
        }

        for port in ssl_ports:
            try:
                with socks.socksocket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.set_proxy(**proxy)
                    sock.connect((domain, port))
                    with ssl_context.wrap_socket(sock, server_hostname=domain) as ssock:
                        cert = ssock.getpeercert()
                        expires = datetime.datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")

                        issuer = dict(x[0] for x in cert['issuer'])
                        issuer_organization = issuer.get('organizationName')
                        issuer_common_name = issuer.get('commonName')

                        delta = expires.date() - current_date

                        # You may need to replace 'your_app' with the actual name of your Django app
                        domainlist.objects.filter(domain_name=domain).update(
                            expires=expires.date(),
                            days_left=delta.days,
                            last_updated=current_date,
                            ssl_issuer_organization=issuer_organization,
                            ssl_issuer_common_name=issuer_common_name
                        )

                        break

            except socket.error:
                continue

    except BaseException as err:
        print(f"Unexpected {err=}, {type(err)=}")

    finally:
        print('Continue next domain')

def update_ssl():
    domain_names = domainlist.objects.values_list('domain_name', flat=True)

    for domain_name in domain_names:
        check_ssl(domain_name)

if __name__ == "__main__":
    update_ssl()
