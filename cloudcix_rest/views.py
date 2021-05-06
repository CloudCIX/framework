# stdlib
import atexit
import json
from multiprocessing.dummy import Pool as ThreadPool
# libs
from django.conf import settings
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView as BaseView
# local
from .models import APILog


__all__ = [
    'APIView',
    'DocumentationView',
]

DOCUMENTATION = None
if settings.DOCS_PATH:
    with open(settings.DOCS_PATH) as f:
        DOCUMENTATION = json.load(f)

# Set up a thread pool to async the API Logging
POOL = ThreadPool(2)


# Set up a method that will close the pool at program exit, and register it to atexit
def stop_pool():
    POOL.close()
    POOL.join()


atexit.register(stop_pool)


class APIView(BaseView):
    """
    Extend the rest_framework.views.APIView with logging of API calls to the DB
    so we can charge for the use of the API in the future
    """

    def dispatch(self, request: Request, *args, **kwargs) -> Response:
        """
        Dispatch a request to the correct view handler.
        Also, log the request in the APILog DB to enable charging later
        :param request: The request object representing the User's request
        :param args: Any extra positional arguments
        :param kwargs: Any extra keyword arguments
        :return: The response of whichever view is called
        """
        # Dispatch to the view
        response = super(APIView, self).dispatch(request, *args, **kwargs)
        # Asynchronously save an API Log on a successful request for logging purposes
        POOL.apply_async(self.log, args=(request, response))
        return response

    def log(self, request: Request, response: Response):
        """
        For a successful request, create an API Log row in the DB for logging purposes
        :param request: The request object coming from the User
        :param response: The response object to return to the User
        """
        # Don't do APILogging in test
        if settings.TESTING:
            return
        url = request.build_absolute_uri().split('?')[0]
        if 'auth' not in url and 200 <= response.status_code < 300:
            APILog.objects.create(
                user_id=request.user.pk,
                api_key=request.user.member['api_key'],
                url=url,
                method=request.method,
            )


class DocumentationView(APIView):
    """
    View class for returning the generated documentation for the Swagger frontend to read from.

    No authentication is needed for this view
    """
    permission_classes = (AllowAny,)

    def get(self, request: Request) -> Response:
        """
        Return the Documentation string as application/json
        """
        return Response(DOCUMENTATION)
