# jobsearch/middleware.py
from django.http import HttpResponse

class HealthCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/ping/":
            return HttpResponse("pong", content_type="text/plain")
        return self.get_response(request)
