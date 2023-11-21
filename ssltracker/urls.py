from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='ssltracker/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('update_ssl/', views.update_ssl_view, name='update_ssl'),
    path('check_expiry/', views.email_users, name='email_users'),
    path('add_domain/', views.add_domain, name='add_domain'),
    path('edit_domain/<int:pk>/', views.edit_domain, name='edit_domain'),
    path('delete_domain/<int:pk>/', views.delete_domain, name='delete_domain'),
    path('view_ssl/<int:pk>/', views.view_ssl, name='view_ssl'),
    path('add_contact/', views.add_contact, name='add_contact'),
    path('contacts/', views.list_contacts, name='list_contacts'),
    path('view_user_ssls/<int:user_id>/', views.view_user_ssls, name='view_user_ssls'),
    path('associate_contact_with_domains/<int:contact_id>/', views.associate_contact_with_domains, name='associate_contact_with_domains'),
    path('edit_contact/<int:pk>/', views.edit_contact, name='edit_contact'),
    path('delete_contact/<int:pk>/', views.delete_contact, name='delete_contact'),
    path('edit_ssl_settings/', views.edit_ssl_settings, name='edit_ssl_settings'),
    path('unchecked_ssls', views.view_unchecked_ssls, name='unchecked_ssls'),
    path('import/', views.import_from_csv, name='import_csv'),
    path('import_contacts/', views.import_from_csv2, name='import_contacts'),
    path('register_user/', views.register_user, name='register_user'),
    path('list_users/', views.list_users, name='list_users'),
    path('edit_users/<int:user_id>/', views.edit_users, name='edit_users'),
    path('delete_user/<int:user_id>/', views.delete_user, name='delete_user'),
    path('update_ip/', views.update_ip_view, name='update_ip'),
    path('export-csv-domainlist/', views.export_csv_domainlist, name='export_csv_domainlist'),
    path('export-csv-contacts/', views.export_csv_contacts, name='export_csv_contacts'),
]
