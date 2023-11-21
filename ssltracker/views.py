from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from .models import domainlist,contacts,ssl_settings
from django.contrib.auth.models import User
from .decorators import group_required
from django.db.models import F
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from .utils import update_ssl,check_expiry,update_ipAddress
from .forms import DomainListForm, ContactListForm,SSLSettingsForm,DomainEditForm,ContactAssociationForm,AddUserForm,UserEditForm
from django.core.paginator import Paginator
from django.db.models import Q
from datetime import datetime
import csv
from django.http import HttpResponse

@login_required
def index(request):
    # Get the search query from the request's GET parameters
    search_query = request.GET.get('search')
    
    # Filter the data based on the search query
    data = domainlist.objects.all().order_by(F('expires').asc(nulls_last=True))
    if search_query:
        data = data.filter(Q(domain_name__icontains=search_query))
    
    # Set the number of records per page
    records_per_page = 25

    # Create a Paginator object
    paginator = Paginator(data, records_per_page)

    # Get the current page number from the request's GET parameters
    page_number = request.GET.get('page')

    # Get the Page object for the requested page number
    page_obj = paginator.get_page(page_number)

    # Pass the page object and search query to the template
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }

    unchecked_count = unchecked_notification(request)  # Pass the 'request' object
    context['unchecked_notification_count'] = unchecked_count

    
    return render(request, 'ssltracker/home.html', context)

def login_view(request):
    return render(request, 'ssltracker/login.html')

def logout_view(request):
    auth_logout(request)
    return redirect('index')


@group_required('Admins', 'Dashboard')
@login_required
def update_ssl_view(request):
    update_ssl()
    return redirect('index')

@group_required('Admins', 'Dashboard')
@login_required
def update_ip_view(request):
    update_ipAddress()
    return redirect('index')



@group_required('Admins', 'Dashboard')
@login_required
def email_users(request):
    check_expiry()
    return redirect('index')

@group_required('Admins', 'Dashboard')
@login_required
def add_domain(request):
    if request.method == 'POST':
        form = DomainListForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = DomainListForm()
    
    context = {'form': form}
    return render(request, 'ssltracker/add_domain.html', context)

@group_required('Admins', 'Dashboard')
@login_required
def edit_domain(request, pk):
    domain = get_object_or_404(domainlist, pk=pk)
    if request.method == 'POST':
        form = DomainEditForm(request.POST, instance=domain)
        if form.is_valid():
            form.save()
            return redirect('index')
    else:
        form = DomainEditForm(instance=domain)
    
    context = {'form': form}
    return render(request, 'ssltracker/edit_domain.html', context)

@group_required('Admins','Dashboard')
@login_required
def delete_domain(request, pk):
    domain = domainlist.objects.get(id=pk)
    domain.delete()
    return redirect('index')

@group_required('Admins', 'Readers', 'Dashboard')
@login_required
def view_ssl(request, pk):
    data = get_object_or_404(domainlist, pk=pk)
    contacts = data.contact_users.all()  # Retrieve the related contacts
    context = {'data': data, 'contacts': contacts}  # Include the contacts in the context
    return render(request, 'ssltracker/view_ssl.html', context)

@group_required('Admins', 'Dashboard')
@login_required
def add_contact(request):
    if request.method == 'POST':
        form = ContactListForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('list_contacts')
    else:
        form = ContactListForm()
    
    context = {'form': form}
    return render(request, 'ssltracker/add_contact.html', context)

@group_required('Admins', 'Readers', 'Dashboard')
@login_required
def list_contacts(request):
    data = contacts.objects.all()
    context = {'data': data}
    return render(request, 'ssltracker/contacts.html', context)

@group_required('Admins', 'Readers', 'Dashboard')
@login_required
def view_user_ssls(request, user_id):
    user = contacts.objects.get(pk=user_id)
    ssls = user.domainlist_set.all()
    context = {'user': user, 'ssls': ssls}
    return render(request, 'ssltracker/user_ssls.html', context)

@group_required('Admins','Dashboard')
@login_required
def associate_contact_with_domains(request, contact_id):
    contact = get_object_or_404(contacts, id=contact_id)

    if request.method == 'POST':
        form = ContactAssociationForm(request.POST, user=contact)
        if form.is_valid():
            domains = form.cleaned_data['domains']
            contact.domainlist_set.set(domains)
            return redirect('view_user_ssls', user_id=contact_id)
    else:
        form = ContactAssociationForm(user=contact)

    context = {'contact': contact, 'form': form}
    return render(request, 'ssltracker/associate_contact_with_domains.html', context)

@group_required('Admins','Dashboard')
@login_required
def edit_contact(request, pk):
    domain = get_object_or_404(contacts, pk=pk)
    if request.method == 'POST':
        form = ContactListForm(request.POST, instance=domain)
        if form.is_valid():
            form.save()
            return redirect('list_contacts')
    else:
        form = ContactListForm(instance=domain)
    
    context = {'form': form}
    return render(request, 'ssltracker/edit_contact.html', context)

@group_required('Admins','Dashboard')
@login_required
def delete_contact(request, pk):
    contact = contacts.objects.get(id=pk)
    contact.delete()
    return redirect('list_contacts')

@group_required('Admins')
@login_required
def edit_ssl_settings(request):
    sslobj = get_object_or_404(ssl_settings, pk=1)
    if request.method == 'POST':
        form = SSLSettingsForm(request.POST, instance=sslobj)
        if form.is_valid():
            form.save()
            return redirect('edit_ssl_settings')
    else:
        form = SSLSettingsForm(instance=sslobj)
    
    context = {'form': form}
    return render(request, 'ssltracker/edit_ssl_settings.html', context)

@group_required('Admins', 'Readers', 'Dashboard')
@login_required
def unchecked_notification(request):
    today = datetime.today().date()
    unchecked_count = domainlist.objects.exclude(last_updated=today).count()
    return unchecked_count

@group_required('Admins', 'Readers', 'Dashboard')
@login_required
def view_unchecked_ssls(request):
    today = datetime.today().date()
    unchecked_ssls = domainlist.objects.exclude(last_updated=today)
   
    # Set the number of records per page
    records_per_page = 25

    # Create a Paginator object
    paginator = Paginator(unchecked_ssls, records_per_page)

    # Get the current page number from the request's GET parameters
    page_number = request.GET.get('page')

    # Get the Page object for the requested page number
    page_obj = paginator.get_page(page_number)

    # Pass the page object and search query to the template
    context = {
        'page_obj': page_obj,
        'unchecked_ssls': unchecked_ssls,
    }
    return render(request, 'ssltracker/unchecked_ssls.html', context)



def import_from_csv(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('utf-8')
        csv_data = csv.reader(decoded_file.splitlines(), delimiter=',')

        for row in csv_data:
            if len(row) >= 3:
                id, domain_name, certLocation = row[0], row[1], row[2]
                domain, created = domainlist.objects.get_or_create(
                    id=id,
                    defaults={
                        'domain_name': domain_name,
                        'certLocation': certLocation,
                    }
                )
        
        return redirect('import_csv')

    return render(request, 'ssltracker/import_csv.html')

def import_from_csv2(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        decoded_file = csv_file.read().decode('utf-8')
        csv_data = csv.reader(decoded_file.splitlines(), delimiter=',')

        for row in csv_data:
            if len(row) >= 4:  # Make sure you have enough fields in the CSV row
                id, first_name, middle_name, last_name, email = row
                contact, created = contacts.objects.get_or_create(
                    id=id,
                    defaults={
                        'first_name': first_name,
                        'middle_name': middle_name,
                        'last_name': last_name,
                        'email': email,
                    }
                )
        
        return redirect('import_contacts')  # Redirect to the same page or a different page after importing

    return render(request, 'ssltracker/import_contacts.html')


@login_required
@group_required('Admins')
def register_user(request):
    if request.method == 'POST':
        form = AddUserForm(request.POST)
        if form.is_valid():
            form.save()
            # Redirect to a success page or other desired view
            return redirect('register_user')
    else:
        form = AddUserForm()

    return render(request, 'ssltracker/add_user.html', {'form': form})

@login_required
@group_required('Admins')
def list_users(request):
    users = User.objects.all()
    return render(request, 'ssltracker/list_users.html', {'users': users})






@login_required
@group_required('Admins')
def edit_users(request, user_id):
    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('edit_users', user.id)
    else:
        form = UserEditForm(instance=user)

    return render(request, 'ssltracker/edit_users.html', {'form': form, 'user': user})



@login_required
@group_required('Admins')
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.delete()
    return redirect('list_users')



@login_required
@group_required('Admins')
def export_csv_domainlist(request):
    
    queryset = domainlist.objects.all()

    response = HttpResponse(content_type='text/csv')
        
    response['Content-Disposition'] = 'attachment; filename="domainlist.csv"'

    csv_writer = csv.writer(response)
    csv_writer.writerow(['ID', 'Domain Name', 'SANs', 'SSL Issuer Organization', 'SSL Issuer Common Name',
                         'Expires', 'Days Left', 'Last Updated', 'Cert Location', 'IP Address'])
    
    for obj in queryset:
        csv_writer.writerow([obj.id, obj.domain_name, obj.sans, obj.ssl_issuer_organization,
                             obj.ssl_issuer_common_name, obj.expires, obj.days_left,
                             obj.last_updated, obj.certLocation, obj.ipAddress])

    return response

@login_required
@group_required('Admins')
def export_csv_contacts(request):
    
    queryset = contacts.objects.all()

    response = HttpResponse(content_type='text/csv')
        
    response['Content-Disposition'] = 'attachment; filename="contact_list.csv"'

    csv_writer = csv.writer(response)
    csv_writer.writerow(['ID', 'first_name', 'middle_name', 'last name', 'email'])
    
    for obj in queryset:
        csv_writer.writerow([obj.id, obj.first_name, obj.middle_name, obj.last_name,
                             obj.email])

    return response


