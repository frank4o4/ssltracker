from django.db import models
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.contrib.auth.models import Group,User
from django import forms

#
# Database Models
#
class domainlist(models.Model):
    id = models.AutoField(primary_key=True)
    domain_name = models.CharField(max_length=255, unique=True)
    sans = models.TextField(null=True, blank=True)
    ssl_issuer_organization =  models.CharField(max_length=255,null=True)
    ssl_issuer_common_name =  models.CharField(max_length=255,null=True)
    expires = models.CharField(max_length=255,null=True)
    days_left = models.CharField(max_length=50,null=True)
    last_updated = models.CharField(max_length=50,null=True)
    contact_users = models.ManyToManyField('contacts')
    certLocation =  models.CharField(max_length=255,null=True)
    ipAddress =  models.CharField(max_length=255,null=True)
    

    def __str__(self):
        return self.domain_name

class digicert(models.Model):
    cert_id = models.CharField(max_length=255)
    cn = models.CharField(max_length=255)
    san = models.TextField(null=True, blank=True)
    valid_from = models.CharField(max_length=255,null=True)
    expiry_date = models.CharField(max_length=255,null=True)
    last_updated = models.CharField(max_length=50,null=True)


class contacts(models.Model):
    id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=255)
    middle_name = models.CharField(max_length=255, null=True)
    last_name = models.CharField(max_length=255)
    email = models.CharField(max_length=255)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"

class ssl_settings(models.Model):
    id = models.AutoField(primary_key=True)
    ssl_ports = models.CharField(max_length=255)
    expiry_date_check = models.CharField(max_length=255)
    digicert_api_key = models.CharField(max_length=255,default="digi cert api key")
    digicert_account_id = models.CharField(max_length=255,default="digi cert account id")
    digicert_api_url =  models.CharField(max_length=255,default="https://daas.digicert.com/apicontroller/v1/certificate/list")
    msgraph_client_id = models.CharField(max_length=255,default="MSGRAPH client ID")
    msgraph_client_secret = models.CharField(max_length=255, default="MSGRAPH client secret")
    msgraph_tenant_id = models.CharField(max_length=255, default="MSGRAPH tenant ID")
    msgraph_api_url =  models.CharField(max_length=255, default="https://graph.microsoft.com")
    msgraph_api_version =  models.CharField(max_length=15, default="v1.0")

class ssl_logs(models.Model):
    id = models.AutoField(primary_key=True)
    log_date = models.CharField(max_length=255)
    log_time = models.CharField(max_length=255)
    user = models.CharField(max_length=255)
    log_data = models.CharField(max_length=255)




#
# Group Models
#

class CustomGroup(Group):
    pass


@receiver(post_migrate)
def create_groups(sender, **kwargs):
    if sender.name != 'ssltracker':
        return
    # Create groups if they don't exist
    admin_group, created = CustomGroup.objects.get_or_create(name='Admins')
    dashboard_group, created = CustomGroup.objects.get_or_create(name='Dashboard')
    readers_group, created = CustomGroup.objects.get_or_create(name='Readers')


@receiver(post_migrate)
def create_sslsettings(sender, **kwargs):
    #Create SSL default settings
    if sender.name == 'ssltracker' and not ssl_settings.objects.exists():
        ssl_settings.objects.create(ssl_ports='443', expiry_date_check='5,15,30')
    

class UserEditForm(forms.ModelForm):
    groups = forms.ModelChoiceField(queryset=Group.objects.all(), required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'groups']

class ScanRun(models.Model):
    # NULL permits historical rows; the unique value 1 is the global queue lock.
    active_slot = models.PositiveSmallIntegerField(null=True, unique=True, editable=False)
    mode = models.CharField(max_length=12, default='all')
    status = models.CharField(max_length=16, default='queued')
    requested_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True)
    heartbeat_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)
    total = models.PositiveIntegerField(default=0)
    completed = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)
    message = models.TextField(blank=True)

    class Meta:
        ordering = ['-id']
        constraints = [models.CheckConstraint(
            condition=(models.Q(active_slot=1, active_slot__isnull=False, status__in=['queued', 'running']) |
                       models.Q(active_slot__isnull=True, status__in=['completed', 'failed'])),
            name='scan_run_active_state')]


class ScanResult(models.Model):
    run = models.ForeignKey(ScanRun, on_delete=models.CASCADE, related_name='results')
    domain = models.ForeignKey(domainlist, null=True, on_delete=models.SET_NULL)
    hostname = models.CharField(max_length=255)
    success = models.BooleanField()
    error = models.TextField(blank=True)
    checked_at = models.DateTimeField(auto_now_add=True)
