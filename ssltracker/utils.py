import ssl
import socket
import datetime
from django.utils import timezone
from .models import domainlist,contacts,ssl_settings
import requests
import socks

def check_ssl(domain):
    ssl_ports_string = ssl_settings.objects.values_list('ssl_ports', flat=True).first()
    ssl_ports = [int(day) for day in ssl_ports_string.split(',')]

    
    try:
        # Getting current date and time
        current_date = datetime.datetime.now().date()

        # Creating an SSL context
        ssl_context = ssl.create_default_context()

        # Set up the SOCKS proxy
        proxy_server = "mvcache.cusa.canon.com"
        proxy_port=80
        proxy = {
            'proxy_type': socks.PROXY_TYPE_HTTP,
            'addr': proxy_server,
            'port': proxy_port,
        }

        # Iterating over the SSL ports
        for port in ssl_ports:
            try:
                # Establishing a connection with the domain on the current port through the proxy
                with socks.socksocket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.set_proxy(**proxy)
                    sock.connect((domain, port))
                    with ssl_context.wrap_socket(sock, server_hostname=domain) as ssock:
                        # Retrieving SSL certificate information
                        cert = ssock.getpeercert()
                        expires = datetime.datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
                        sans_string = [entry[1] for entry in cert.get('subjectAltName', []) if entry[0] == 'DNS']
                        sans = ', '.join(sans_string)  # Join the list elements into a string
                        sans = sans.replace("[", "").replace("]", "")
                        # Extracting issuer information
                        issuer = dict(x[0] for x in cert['issuer'])
                        issuer_organization = issuer.get('organizationName')
                        issuer_common_name = issuer.get('commonName')
                        

                        # Calculating days left
                        delta = expires.date() - current_date

                        # Updating the domainlist model
                        
                       # Updating the domainlist model
                        domainlist.objects.filter(domain_name=domain).update(
                            expires=expires.date(),
                            days_left=delta.days,
                            last_updated=current_date,
                            ssl_issuer_organization=issuer_organization,
                            ssl_issuer_common_name=issuer_common_name,
                            sans=sans,
                        )

            except socket.error:
                continue

    except BaseException as err:
        print(f"Unexpected {err=}, {type(err)=}")

    finally:
        print('Continue next domain')


def update_ssl():
    domain_names = domainlist.objects.values_list('domain_name', flat=True)

    # For loop to update all domains
    for domain_name in domain_names:
        check_ssl(domain_name)

def check_expiry():
    expiry_days_string = ssl_settings.objects.values_list('expiry_date_check', flat=True).first()
    expiry_days = [int(day) for day in expiry_days_string.split(',')]

    for expiry_day in expiry_days:
        domains = domainlist.objects.filter(days_left=expiry_day)

        for domain in domains:
            domain_name = domain.domain_name
            days_left = domain.days_left
            contact_emails = list(domain.contact_users.values_list('email', flat=True))

            send_email_notification(domain_name, days_left, contact_emails)



def send_email_notification(domain_name,days_left,email_addresses):

    client_id = "40830f72-35e9-405f-8ea7-b7d0c337fba0"
    client_secret = "NIz8Q~T1.VZQpNVbRK8Np2DD9fm.DJS5ym1-9aZQ"
    tenant_id = "5132013a-1c8d-4f87-9f4d-43110f5bc07b"
    resource = "https://graph.microsoft.com"
    api_version = "v1.0"

    # Construct the token endpoint URL
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/token"

    # Construct the payload for the token request
    token_payload = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
        "resource": resource
    }
    
    subject = (f"{domain_name} will be Expiring in {days_left} days")
    message = (f"{domain_name} will be Expiring in {days_left} days")
    recription_list = email_addresses
    From_Email="cci_apps_dev@canada.canon.com"

    # Request the access token
    token_response = requests.post(token_url, data=token_payload)
    token_data = token_response.json()
    access_token = token_data["access_token"]

    # Construct the API endpoint URL for sending an email
    send_email_endpoint = f"{resource}/{api_version}/users/{From_Email}/sendMail"

     # Construct the email payload
    email_payload = {
        "message": {
            "subject": subject,
            "body": {
                "contentType": "Text",
                "content": message
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": recipient_email
                    }
                }
                for recipient_email in recription_list
            ]
        },
        "saveToSentItems": "false"
    }

    # Make a request to send the email using the obtained access token
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    send_email_response = requests.post(send_email_endpoint, json=email_payload, headers=headers)

    if send_email_response.status_code == 202:
        print("Email sent successfully!")
    else:
        print("Error sending email:", send_email_response.status_code)
        print(send_email_response.text)


def get_ip_address(domain_name):
    try:
        ip_address = socket.gethostbyname(domain_name)
        return ip_address
    except socket.error as e:
        print(f"Error: {e}")
        return None


def update_ipAddress():
    domain_names = domainlist.objects.values_list('domain_name', flat=True)
    # For loop to update all domains
    for domain_name in domain_names:
        ipAddress = get_ip_address(domain_name)
        domainlist.objects.filter(domain_name=domain_name).update(
                            ipAddress=ipAddress
                        ) 
