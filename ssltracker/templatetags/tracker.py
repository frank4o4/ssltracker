from django import template
from ssltracker.presentation import expiry_info
register = template.Library()
register.filter('expiry', expiry_info)

@register.simple_tag(takes_context=True)
def page_url(context, page):
    query = context['request'].GET.copy()
    query['page'] = page
    return '?' + query.urlencode()
