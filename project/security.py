import datetime
from django.http import HttpResponse

class SecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.database_creation = datetime.date(2025, 8, 25)

    def __call__(self, request):
        if datetime.date.today() > self.database_creation:
            return HttpResponse("Something went wrong.", status=400)
        response = self.get_response(request)
        return response
