from django.contrib import admin
from .models import domainlist, contacts,ssl_settings,ssl_logs,digicert

admin.site.register(domainlist)
admin.site.register(ssl_settings)
admin.site.register(contacts)
admin.site.register(ssl_logs)
admin.site.register(digicert)