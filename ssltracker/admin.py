from django.contrib import admin
from .models import domainlist, contacts,ssl_settings

admin.site.register(domainlist)
admin.site.register(ssl_settings)
admin.site.register(contacts)
