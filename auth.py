# python
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# libs
import jwt
from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication
from rest_framework.request import Request
from jaeger_client import Span

# optional imports
if 'membership' in settings.INSTALLED_APPS and not settings.TESTING:
    from cloudcix_rest.exceptions import UserExpired
    from membership.models import User as CloudCIXUser
    from membership.serializers import UserSerializer
else:
    from cloudcix.api import Membership
    from cloudcix_rest.exceptions import ErrorPropagator


__all__ = [
    'CloudCIXTokenAuth',
]

with open(settings.PUBLIC_KEY_FILE) as f:
    PUBLIC_KEY = f.read()


class User:
    """
    A class to represent the User currently using the API. Will be populated from Membership and attached to every
    request as `request.user`
    """
    is_active = True

    # Type hinting vars that come from the API
    address: Dict
    administrator: bool
    department: Dict
    email: str
    expiry_date: datetime
    extra: Dict
    first_name: str
    global_active: bool
    global_user: bool
    id: int
    image: Optional[str]
    job_title: str
    language: Dict
    last_login: datetime
    member: Dict
    notifications: List[Dict]
    phones: List[Dict]
    pk: int
    token: str

    def __init__(self, uid: int, token: str, span: Span = None) -> None:
        """
        Initializes a new user using a user id from a JWT token payload
        :param uid: The user id retrieved from the JWT payload
        :param token: The actual token sent. Used to ensure the User is still authenticated.
        :param span: The parent span for the creation of a User to track time taken
        """
        tracer = settings.TRACER
        logger = logging.getLogger('cloudcix_rest.auth.User')

        # Save the token for `is_authenticated` purposes
        self.token = token

        # Check the cache for user_uid
        cache_key = f'user_{uid}'
        user = cache.get(cache_key)

        # Get the data for the user, using the api unless Membership is installed
        with tracer.start_span('retrieving_user_object', child_of=span) as api_span:
            if user is None:
                if 'membership' in settings.INSTALLED_APPS and not settings.TESTING:
                    # Get the User from the DB
                    api_span.set_tag('retrieved_from', 'db')
                    with settings.TRACER.start_span('retrieve_from_db', child_of=api_span):
                        obj = CloudCIXUser.objects.get(pk=uid)
                    with settings.TRACER.start_span('serializing_user', child_of=api_span):
                        user = UserSerializer(instance=obj).data

                    # Check expiry date
                    with settings.TRACER.start_span('checking_expiry_date', child_of=api_span):
                        if type(user['expiry_date']) == datetime:
                            user['expiry_date'] = user['expiry_date'].isoformat()
                        expiry_date = datetime.strptime(
                            user['expiry_date'].split('T')[0], '%Y-%m-%d',
                        )
                        if expiry_date.date() < datetime.utcnow().date() and not user['administrator']:
                            raise UserExpired()

                else:
                    api_span.set_tag('retrieved_from', 'api')
                    # Try and read the membership api data
                    with settings.TRACER.start_span('fetching_user', child_of=api_span) as request_span:
                        response = Membership.user.read(token=token, pk=uid, span=request_span)
                        if response.status_code != status.HTTP_200_OK:
                            # Re-raise any errors from requesting the User
                            raise ErrorPropagator(response)
                    try:
                        user = response.json()['content']
                    except (KeyError, json.decoder.JSONDecodeError):
                        logger.error('Error decoding user API response', exc_info=True)
                        raise
                with tracer.start_span('setting_cache', child_of=api_span):
                    if not settings.TESTING:
                        # Set the user back into the cache for one minute
                        cache.set(cache_key, user, 1 * 60)
            else:
                api_span.set_tag('retrieved_from', 'cache')

        # Set the attributes of this User instance using information retrieved
        with tracer.start_span('setting_user_obj_attributes', child_of=span):
            for k, v in user.items():
                setattr(self, k, v)
            self.pk = self.id

    def is_authenticated(self) -> bool:
        """
        States whether the user object is authenticated.
        :return: A flag stating whether or not the user is authenticated
        """
        # Token is valid if it hasn't expired, so try and decode it
        try:
            jwt.decode(self.token, PUBLIC_KEY, algorithms=['RS256'])
            return True
        except jwt.ExpiredSignatureError:
            return False

    @property
    def is_global(self) -> bool:
        """
        Determines whether or not the User object can be treated as global.
        This is added purely as shorthand for wherever they used to use
            `if request.user.global_user and request.user.global_active`
        :return: A flag determining whether the User should be treated as local or global for a method
        """
        return self.global_user and self.global_active


class CloudCIXTokenAuth(TokenAuthentication):
    """
    Extends the Django REST Framework's TokenAuthentication system with our usage of the JWT protocol and LDAP
    """

    def authenticate(self, request: Request) -> Optional[Tuple[User, str]]:
        """
        Given a user's request object, attempt to authenticate them
        :param request: The user's request
        :return: The User object to attach to the request, and the token they authenticated with to authenticate further
                 requests
        """
        # Ensure that there is a token sent in the header
        tracer = settings.TRACER
        token = request.META.get('HTTP_X_AUTH_TOKEN', None)
        if token is None:
            return None
        # Ensure that the sent token is still valid
        with tracer.start_span('validating_token', child_of=request.span):
            try:
                payload = jwt.decode(token, PUBLIC_KEY, algorithms=['RS256'])
            except jwt.ExpiredSignatureError:
                # It is a jwt token and it's bad so raise permission denied
                raise exceptions.AuthenticationFailed('JWT token is expired. Please login again.')
            except jwt.DecodeError:
                logging.getLogger('cloudcix_rest.auth.authenticate').error(
                    'Error occurred while decoding token',
                    exc_info=True,
                )
                raise exceptions.AuthenticationFailed('An error occurred while decoding your token, try again later.')
            if not payload:
                return None
        with tracer.start_span('creating_request_user', child_of=request.span) as span:
            # Create the User instance to attach to the rest_framework.httprequest
            user = User(payload['uid'], token, span)
            if not user.is_active:
                logging.getLogger('cloudcix_rest.auth.authenticate').error(
                    f'Inactive or deleted user #{user.id} attempted to log in',
                )
                raise exceptions.AuthenticationFailed('User is either inactive or deleted.')
        return user, token

    def authenticate_header(self, request: Request) -> str:
        """
        Return the name of the header that the API expected the token to be sent as the value for.
        :param request: The user's request
        :return: The name of the request header that the token is expected to be sent as the value for
        """
        return 'X-Auth-Token'
