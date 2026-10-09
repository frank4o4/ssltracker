def navigation(request):
    user = request.user
    groups = set(user.groups.values_list('name', flat=True)) if user.is_authenticated else set()
    admin = user.is_authenticated and (user.is_superuser or 'Admins' in groups)
    return {'can_manage': admin or 'Dashboard' in groups, 'can_admin': admin}
