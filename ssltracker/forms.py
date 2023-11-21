from django import forms
from .models import domainlist, contacts,ssl_settings
from django.forms import ModelForm, TextInput, EmailInput,Select,CheckboxInput
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User,Group

class DomainListForm(forms.ModelForm):
    class Meta:
        model = domainlist
        fields = ['domain_name']
        widgets={
            'domain_name': TextInput(attrs={
                'class': "form-control",
                'style': 'max-width:300px;',
                'placeholder': 'Domain Name'
            })
        }

class DomainEditForm(forms.ModelForm):
    contact_users = forms.ModelMultipleChoiceField(
        queryset=contacts.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )
    class Meta:
        model = domainlist
        fields = ['domain_name', 'contact_users']
        widgets = {
            'domain_name': TextInput(attrs={
                'class': "form-control",
                'style': 'max-width: 300px;',
                'placeholder': 'Domain Name'
                }),
            
         
        }



class ContactListForm(forms.ModelForm):
    class Meta:
        model = contacts
        fields = ['first_name', 'middle_name', 'last_name', 'email']

    # Widgets for each field
    widgets = {
        'first_name': TextInput(attrs={
            'class': "form-control",
            'style': 'max-width: 300px;',
            'placeholder': 'First Name'
        }),
        'middle_name': TextInput(attrs={
            'class': "form-control",
            'style': 'max-width: 300px;',
            'placeholder': 'Middle Name (Optional)'
        }),
        'last_name': TextInput(attrs={
            'class': "form-control",
            'style': 'max-width: 300px;',
            'placeholder': 'Last Name'
        }),
        'email': EmailInput(attrs={
            'class': "form-control", 
            'style': 'max-width: 300px;',
            'placeholder': 'Email'
        }),
    }

    # Make middle_name field optional
    middle_name = forms.CharField(required=False)
    

class SSLSettingsForm(forms.ModelForm):
    class Meta:
        model = ssl_settings
        fields = ['ssl_ports', 'expiry_date_check']
        
        widgets = {
            'ssl_ports': TextInput(attrs={
                'class': "form-control",
                'style': 'max-width: 300px;',
                }),
            'expiry_date_check': TextInput(attrs={
                'class': "form-control",
                'style': 'max-width: 300px;',
                })
         }


class ContactAssociationForm(forms.Form):
    contact = forms.ModelChoiceField(queryset=contacts.objects.all(), widget=forms.HiddenInput)
    domains = forms.ModelMultipleChoiceField(
        queryset=domainlist.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    def __init__(self, *args, user=None, **kwargs):
        super(ContactAssociationForm, self).__init__(*args, **kwargs)
        if user:
            self.fields['contact'] = forms.ModelChoiceField(
                queryset=contacts.objects.filter(pk=user.pk),
                initial=user.pk,
                widget=forms.HiddenInput
            )
            self.fields['domains'].initial = user.domainlist_set.all()


class AddUserForm(UserCreationForm):
    email = forms.EmailField(required=True)
    group = forms.ModelChoiceField(queryset=Group.objects.all(), required=True)

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if not password:
            password = User.objects.make_random_password()
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
            user.groups.add(self.cleaned_data['group'])
        return user
    



class UserEditForm(forms.ModelForm):
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'groups']