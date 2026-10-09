import datetime
from django.utils import timezone


def expiry_info(value):
    try:
        days = (datetime.date.fromisoformat(str(value)) - timezone.localdate()).days
    except (TypeError, ValueError):
        return {'state': 'unknown', 'label': 'Unknown', 'days': None}
    if days < 0:
        return {'state': 'expired', 'label': f'Expired {abs(days)}d ago', 'days': days}
    if days == 0:
        return {'state': 'soon', 'label': 'Expires today', 'days': 0}
    return {'state': 'soon' if days <= 30 else 'valid', 'label': f'{days} days left', 'days': days}
