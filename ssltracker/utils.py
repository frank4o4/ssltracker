import socket
import datetime
from .models import domainlist,ssl_settings,digicert
import requests
import json


def direct_post(url, **kwargs):
    with requests.Session() as session:
        session.trust_env = False
        return session.post(url, **kwargs)


def update_ssl():
    from .jobs import enqueue_scan
    return enqueue_scan()


def check_ssl(domain):
    # Compatibility: do not bypass the global queue with ad-hoc writes.
    return update_ssl()


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
    from django.conf import settings
    From_Email = settings.MS_GRAPH_SENDER
    if not From_Email:
        raise ValueError('Set MS_GRAPH_SENDER before sending expiry notifications')

    # Request the access token
    token_response = direct_post(token_url, data=token_payload, timeout=(5, 30))
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

    send_email_response = direct_post(send_email_endpoint, json=email_payload, headers=headers, timeout=(5, 30))

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
    return update_ssl()


def digiCleanTable():
    # Old cron compatibility: never delete inventory before a successful fetch.
    return None


def digiApiGet():
    """Optional legacy inventory sync. Refuse potentially truncated responses."""
    from django.db import transaction
    row = ssl_settings.objects.order_by('pk').first()
    if not row or not row.digicert_api_key or row.digicert_api_key == 'digi cert api key':
        raise ValueError('DigiCert API credentials are not configured')
    response = direct_post(row.digicert_api_url,
        json={'pageSize': 100, 'divisionIds': [], 'accountId': row.digicert_account_id},
        headers={'X-DC-DEVKEY': row.digicert_api_key}, timeout=(5, 30))
    response.raise_for_status()
    records = response.json()['data']['certificateDetailsDTOList']
    if not isinstance(records, list) or len(records) >= 100:
        raise ValueError('DigiCert may have more pages. Configure verified pagination before replacing inventory.')
    if not records:
        raise ValueError('Empty DigiCert response; existing inventory retained')
    def date_from_ms(value):
        return datetime.datetime.fromtimestamp(value / 1000, datetime.timezone.utc).date().isoformat()
    objects = []
    for item in records:
        san = item.get('san') or ''
        if isinstance(san, list):
            san = ', '.join(san)
        objects.append(digicert(cert_id=item['certId'], cn=item['cn'], san=san,
            valid_from=date_from_ms(item['validFrom']), expiry_date=date_from_ms(item['expiryDate']),
            last_updated=datetime.date.today().isoformat()))
    with transaction.atomic():
        digicert.objects.all().delete()
        digicert.objects.bulk_create(objects)


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

