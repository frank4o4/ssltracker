import ssl
import socket
import datetime
from .models import domainlist,ssl_settings,digicert
import requests
import socks
import json

def check_ssl(domain):
    # Getting current date and time
    current_date = datetime.datetime.now().date()
    
    digicert_record = digicert.objects.filter(cn=domain).first()

    if digicert_record:
        expires = digicert_record.expiry_date
        sans = digicert_record.san
        if sans is None:
            sans = "Digi Inc"

        # Ensure expires is a datetime.date object
        if isinstance(expires, str):
            expires = datetime.datetime.strptime(expires, "%Y-%m-%d").date()

        # Calculating days left
        delta = expires - current_date
        days_left = delta.days
        
        update_record = domainlist.objects.filter(domain_name=domain).update(
            sans = sans,
            ssl_issuer_organization="DigiCert Inc",
            expires = expires,
            days_left = days_left,
            last_updated = current_date
        )
        
    else:
        ssl_ports_string = ssl_settings.objects.values_list('ssl_ports', flat=True).first()
        ssl_ports = [int(day) for day in ssl_ports_string.split(',')]

        
        try:
            

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
    client_id = ssl_settings.objects.values_list('msgraph_client_id', flat=True).first()
    client_secret = ssl_settings.objects.values_list('msgraph_client_secret', flat=True).first()
    tenant_id = ssl_settings.objects.values_list('msgraph_tenant_id', flat=True).first()
    resource = ssl_settings.objects.values_list('msgraph_api_url', flat=True).first()
    api_version = ssl_settings.objects.values_list('msgraph_api_version', flat=True).first()
    # client_id = "40830f72-35e9-405f-8ea7-b7d0c337fba0"
    # client_secret = "NIz8Q~T1.VZQpNVbRK8Np2DD9fm.DJS5ym1-9aZQ"
    # tenant_id = "5132013a-1c8d-4f87-9f4d-43110f5bc07b"
    # resource = "https://graph.microsoft.com"
    # api_version = "v1.0"

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

def digiCleanTable():
    # Clean table First before fresh import
    try:
        digicert.objects.all().delete()
        print("API Table Data deleted")
    except Exception as e:
        print(f"An error occurred: {e}")
    


def digiApiGet():
    api_key = ssl_settings.objects.values_list('digicert_api_key', flat=True).first()
    url = ssl_settings.objects.values_list('digicert_api_url', flat=True).first()
    accountId = ssl_settings.objects.values_list('digicert_account_id', flat=True).first()

    payload = {
        "pageSize": 100,
        "divisionIds": [],
        "accountId": accountId,
    }

    # Convert the payload to JSON
    payload_json = json.dumps(payload)

    headers = {
        'X-DC-DEVKEY': api_key,
        'Content-Type': "application/json",
    }

    response = requests.request("POST", url, data=payload_json, headers=headers)

    

    if response.status_code == 200:
        data = response.json()
    
    certificate_details_list = data.get('data', {}).get('certificateDetailsDTOList', [])

    for certificate_details in certificate_details_list:
        cert_id = certificate_details.get('certId', '')
        cn = certificate_details.get('cn', '')
        san  = certificate_details.get('san', '')
        valid_from_timestamp = certificate_details.get('validFrom', 0)
        expiry_date_timestamp = certificate_details.get('expiryDate', 0)

        # Convert timestamp to datetime
        valid_from = datetime.datetime.utcfromtimestamp(valid_from_timestamp / 1000).date()
        expiry_date = datetime.datetime.utcfromtimestamp(expiry_date_timestamp / 1000).date()
        today = datetime.datetime.now().date()

        digi_update = digicert(
            cert_id=cert_id,
            cn=cn,
            san=san,
            valid_from=valid_from,
            expiry_date=expiry_date,
            last_updated=today
        )
        digi_update.save()
        print("API Data uploaded")
    else:
        print("Error", response.status_code)


def update_domainlist_from_digicert():
    
    unique_cns = digicert.objects.values_list('cn', flat=True).distinct()

    
    for cn in unique_cns:
        if not domainlist.objects.filter(domain_name=cn).exists():
            # Check if expiry_date is not more than 15 days old
            cert = digicert.objects.filter(cn=cn).first()
            if cert and cert.expiry_date:
                expiry_date = datetime.datetime.strptime(cert.expiry_date, '%Y-%m-%d')
                if (expiry_date - datetime.datetime.now()).days > 5:
                    
                    new_domain = domainlist(domain_name=cn)
                    new_domain.save()

