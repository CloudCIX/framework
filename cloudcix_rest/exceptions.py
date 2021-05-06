# stdlib
from typing import Dict

# libs
from rest_framework.exceptions import APIException
from rest_framework import status
from rest_framework.response import Response

# local
from .utils import get_error_details


class UserExpired(APIException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'User is expired. Cannot log in.'


class ErrorPropagator(APIException):
    """
    Class for taking a response, extracting the details from it, and raising it as an error
    """
    def __init__(self, response):
        self.status_code = response.status_code
        data = response.json()
        detail = data['detail']
        code = data['code']
        super(ErrorPropagator, self).__init__(detail, code)


class APIExceptionBase(Response):
    """
    New base class for returning exceptions as responses instead of handling them as exceptions
    """

    def __init__(self, **data) -> None:
        """
        Create an instance of a JsonResponse for this exception.
        :param data: Keyword args from subclasses to be passed to the super as data
        """
        detail = self.default_detail
        if 'error_code' in data:
            messages = get_error_details(data['error_code'])
            try:
                detail = messages[data['error_code']]['detail']
            except KeyError:
                raise KeyError(
                    f'The error code "{data["error_code"]}" was raised but no error message was defined for it.',
                )

        data.setdefault('detail', detail)
        super(APIExceptionBase, self).__init__(data, status=self.status_code)


class Http400(APIExceptionBase):
    """
    Exception for HTTP 400: Bad Request
    """
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'Bad request.'

    def __init__(self, errors: Dict[str, Dict[str, str]] = None, **kwargs) -> None:
        """
        Create a HTTP 400 error
        :param errors: Errors from the controller that caused this error
        :param args: Optional positional args
        :param kwargs: Optional keyword args
        """
        if errors is not None:
            kwargs['errors'] = errors
        super(Http400, self).__init__(**kwargs)


class Http403(APIExceptionBase):
    """
    Exception for HTTP 403: Forbidden
    """
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'You do not have permission to perform this action.'


class Http404(Http403):
    """
    Exception for HTTP 404: Not Found
    """
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'Not Found.'


class Http409(Http403):
    """
    Exception for HTTP 409: Conflict
    """
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Conflict.'


class Http503(Http403):
    """
    Exception for HTTP 503: Service Unavailable
    """
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = 'Service unavailable.'
