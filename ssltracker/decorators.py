# decorators.py
from django.shortcuts import render
from functools import wraps
from django.http import HttpResponseForbidden

def group_required(*group_names):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if any(request.user.groups.filter(name=group).exists() for group in group_names):
                return view_func(request, *args, **kwargs)
            else:
                return render(request, 'ssltracker/access.html')

        return _wrapped_view

    return decorator
