# stdlib
import logging
from datetime import datetime
from typing import Dict
# lib
from cloudcix.api import Membership
from cloudcix.auth import get_admin_token
from dateutils import relativedelta
from django.conf import settings
from rest_framework.test import APITestCase


__all__ = [
    'TestBase',
]


class TestBase(APITestCase):
    """
    The base for all test cases in the API
    """

    token_cache: Dict[int, str] = {}

    def setUp(self):
        """
        Turn off warning log messages
        """
        super(TestBase, self).setUp()
        # Disable log warnings during tests
        logging.getLogger('django').setLevel(logging.ERROR)
        logging.getLogger('jaeger_tracing').setLevel(logging.ERROR)

    def get_token_for_user_id(self, user_id: int) -> str:
        """
        Retrieve a token for the specified user using the /auth/login/ endpoint created in Membership
        :param user_id: The id of the user to retrieve a token for
        :return: A valid token for the specified user
        """
        cache = self.token_cache.get(user_id, None)
        if cache is not None:
            return cache
        admin_token = get_admin_token()
        if user_id == 1:
            return admin_token
        # If not, update the user's password and then get a token for them
        password = settings.TEST_PASSWORD
        data = {
            'password': password,
            'expiry_date': (datetime.utcnow() + relativedelta(years=1)).isoformat(),
        }
        response = Membership.user.partial_update(token=admin_token, pk=user_id, data=data)
        # Now generate a token for the user
        user = response.json()['content']
        token_data = {
            'email': user['email'],
            'password': password,
            'api_key': user['member']['api_key'],
        }
        token = Membership.token.create(data=token_data).json()['token']
        self.token_cache[user_id] = token
        return token
