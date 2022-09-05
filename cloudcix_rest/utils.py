# stdlib
from contextlib import contextmanager
from hashlib import blake2b
from typing import Any, Callable, Dict, List, Type
# lib
from django.core.cache import cache
from django.db import models, router, transaction
from django.utils.datastructures import MultiValueDict
from psycopg2 import sql
# local
import errors  # When building Dockerfile, move the Application errors module to `/application_framework`


def memoize(seconds: int = 0) -> Callable:
    """
    Wrapper that caches the result of a function for the specified number of seconds
    :param seconds: How long in seconds to cache the result for
    :return: A wrapper to cache the result of a function
    """
    def inner_cache(method: Callable):
        def x(*args: List[Any], **kwargs: Dict[Any, Any]):
            key_string = f'{method.__module__}{method.__name__}{args}{kwargs}'
            cache_key = blake2b(key_string.encode()).hexdigest()
            result = cache.get(cache_key)
            if result is None:
                # Cache failed, call the method
                result = method(*args, **kwargs)
                if seconds > 0:
                    cache.set(cache_key, result, seconds)
            return result
        return x
    return inner_cache


@memoize(seconds=3600)
def get_error_details(*error_codes: str, language_id: int = None) -> Dict[str, Dict[str, str]]:
    """
    Gathers all the error_codes and details from the `errors` module for the given error codes
    :param error_codes: The error codes to gather the error messages for
    :param language_id: The id of the language the codes should be translated into, or None if no language is
                        set for the user, in which case the English versions will be used
    :return: Dictionary of error_code, detail pairs
    """
    # Use getattr to get all of the specified error codes, ignoring codes that are not defined
    error_details: Dict[str, Dict[str, str]] = {}
    for code in error_codes:
        try:
            detail = getattr(errors, code, None)
        except TypeError:
            print('Error code is not a string:', code, type(code))
            detail = None
        if detail is not None:
            error_details[code] = {'error_code': code, 'detail': detail}
    return error_details


def convert_to_openapi(params: MultiValueDict) -> Dict[str, Any]:
    """
    Accept data that has been parsed by the OpenAPI middleware and convert it back into OpenAPI format. Used for passing
    parameters from one API call to another.
    :param params: A dictionary of query parameters
    :return: A dictionary of parameters ready to be passed to an API
    """
    results: Dict[str, Any] = dict()

    for param_name, param_value in params.items():

        if param_name in ['search', 'exclude']:
            # These are dictionaries
            for field_name, field_value in param_value.items():

                if isinstance(field_value, str) and field_value.lower() in ['true', 'false']:
                    field_value = field_value.lower() == 'true'

                results[f'{param_name}[{field_name}]'] = field_value
        else:
            # Just copy the value to the results
            results[param_name] = param_value

    return results


@contextmanager
def db_lock(model_class: Type[models.Model], using: str = None):
    """
    Lock a database table from modification for the duration of the context manager
    :param model_class: The django model whose table should be locked
    :param using: The name of the database to connect to
    """
    if using is None:
        using = router.db_for_write(model=model_class)

    # Locks can only be acquired within transactions
    with transaction.atomic(using=using):
        cursor = transaction.get_connection(using=using).cursor()
        cursor.execute(
            sql.SQL('LOCK TABLE {} IN EXCLUSIVE MODE').format(sql.Identifier(model_class._meta.db_table)),
        )
        try:
            # Context manager needs one yield statement
            yield
        finally:
            if cursor and not cursor.closed:
                cursor.close()
