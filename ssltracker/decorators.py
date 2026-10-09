# decorators.py
from django.shortcuts import render
from functools import wraps
from django.http import HttpResponseForbidden

def group_required(*group_names):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.user.is_authenticated and (request.user.is_superuser or request.user.groups.filter(name__in=group_names).exists()):
                return view_func(request, *args, **kwargs)
            else:
                return render(request, 'ssltracker/access.html', status=403)

        return _wrapped_view

    return decorator
