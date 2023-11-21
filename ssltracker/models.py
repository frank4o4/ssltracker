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
    domain_name = models.CharField(max_length=255)
    sans = models.TextField()
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
    # Create groups if they don't exist
    admin_group, created = CustomGroup.objects.get_or_create(name='Admins')
    dashboard_group, created = CustomGroup.objects.get_or_create(name='Dashboard')
    readers_group, created = CustomGroup.objects.get_or_create(name='Readers')


class UserEditForm(forms.ModelForm):
    groups = forms.ModelChoiceField(queryset=Group.objects.all(), required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'groups']