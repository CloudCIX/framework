"""
Move this to wherever once we establish a setup for the Application Framework
"""
import re
from collections import deque
from typing import Callable, Deque
from time import perf_counter

from cloudcix_metrics import prepare_metrics
from django.http.response import HttpResponseBase
from rest_framework.request import Request

from metrics.client_ip import post_client_ip
from metrics.response_time import post_response_time

GetResponseType = Callable[[Request], HttpResponseBase]


class OpenAPIDeepObjectParserMiddleware:
    """
    This middleware will transform the GET parameters received from the user and turn any OAPI deepObject types into
    nested dictionaries

    OAPI deepObject example: ?search[name]=yes&exclude[name]=no

    Turning these into nested dictionaries makes the search and exclude validation a lot easier
    """

    def __init__(self, get_response: GetResponseType) -> None:
        """
        Set up this middleware class
        :param get_response: A callable that calls the next part in the chain.
                             This might be another middleware or the view itself.
        """
        self.get_response = get_response
        self.pattern = re.compile(r'(?P<dict>[a-zA-z][a-zA-Z0-9]+)\[(?P<key>.+)\]')

    def __call__(self, request: Request) -> HttpResponseBase:
        """
        This method is run when the middleware is called by Django
        :param request: The current request object passed from the last part of the chain
        :returns: The response to be returned to the user
        """
        # Before we pass on the request, we should alter the GET params
        # Find all deepObject style params and transform them
        new_get = request.GET.copy()
        transformed: Deque = deque()
        for k in request.GET.keys():
            match = self.pattern.match(k)
            if match:
                # Attempt to get the named dict
                new_get.setdefault(match['dict'], {})[match['key']] = request.GET[k]
                transformed.append(k)
        for k in transformed:
            new_get.pop(k)
        request.GET = new_get

        # Now pass the request to the next part of the chain and return what
        # comes back
        return self.get_response(request)


class MetricsMiddleware:
    """
    This middleware will handle the generation and logging of response time metrics to our influx instance
    """

    def __init__(self, get_response: GetResponseType) -> None:
        """
        Set up this middleware class
        :param get_response: A callable that calls the next part in the chain.
                             This might be another middleware or the view itself.
        """
        self.get_response = get_response

    def __call__(self, request: Request) -> HttpResponseBase:
        """
        This method is run when the middleware is called by Django to deal with metrics
        :param request: The current request object passed from the last part of the chain
        :returns: The response to be returned to the user
        """
        start = perf_counter()
        response = self.get_response(request)
        time = perf_counter() - start
        prepare_metrics(post_response_time, time=time, response=response, request=request)
        prepare_metrics(post_client_ip, response=response, request=request)
        return response
