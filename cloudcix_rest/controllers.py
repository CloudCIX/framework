# stdlib
import re
from collections import deque
from typing import Any, Callable, cast, Deque, Dict, List, Optional, Tuple, Type
# libs
from django.conf import settings
from django.db.models import Model
from django.db.models.fields import Field
from jaeger_client import Span
from rest_framework.request import QueryDict, Request
# local
from .utils import get_error_details


__all__ = [
    'ControllerBase',
]


LIST_PATTERN = re.compile(r'[\[\]()\'\"]')


class ControllerBase:
    """
    Base Controller class for all controllers.

    Contains the validation methods for all of the list parameters, as well as
    basic methods and attributes for all controllers to use.
    """

    # Default list of filter operators for string and number types
    DEFAULT_STRING_FILTER_OPERATORS = ('in', 'icontains', 'iendswith', 'iexact', 'istartswith')

    DEFAULT_NUMBER_FILTER_OPERATORS = ('gt', 'gte', 'in', 'isnull', 'lt', 'lte', 'range')

    class Meta:
        """
        Metadata about the base controller.

        REST controllers migrate their config data into this Meta class

        :var allowed_ordering:  A list of strings representing model fields that can be used by
                                the user to order the data. Defaults to an empty list.
        :var normal_list_limit: The default value of limit that is used when no limit is passed by the user.
                                Defaults to 50.
        :var max_list_limit:    The maximum allowed value for the limit parameter. Defaults to 100.
        :var model:             The model that will be used for Create or Update versions of the Controller.
                                This will be used to create the `controller.instance` property.
        :var search_fields:     A map of model fields to the search extensions that can be used to modify the searches.
                                e.g {'name': ['icontains']} allows searching by name and name__icontains.
                                Defaults to an empty dictionary
        :var validation_order:  A list of names for validate_ methods dictating which ones to run and in which order.
                                Defaults to ('search', 'exclude', 'limit', 'page', 'order') which is the usual
                                for list controllers.
        """
        allowed_ordering: Tuple[str, ...] = ()
        max_list_limit: int = 100
        model: Optional[Type[Model]] = None
        normal_list_limit: int = 50
        search_fields: Dict[str, Tuple[str, ...]] = {}
        validation_order: Tuple[str, ...] = ('search', 'exclude', 'limit', 'page', 'order')

    def __init__(
            self,
            request: Request = None,
            instance: Model = None,
            data: QueryDict = None,
            partial: bool = False,
            span: Span = None,
    ) -> None:
        """
        Create a new controller.
        :param request: The request sent by the User
        :param instance: The model instance to update (only for update controllers)
        :param data: The data being validated. Either request.GET or request.POST depending on the method
        :param partial: Flag stating whether or not the update is partial. On a partial update, missing data will be
                        skipped when running the `validate_` methods. Otherwise, a `None` will be passed into the
                        corresponding `validate_` method.
        :param span: A Span instance that is the parent span of the controller. Passing this in will allow us to record
                     time taken to run the validation methods in the controller.
        """
        # Create a dict for the output, valid data
        self.cleaned_data: dict = {}
        # Store the passed data that needs to be validated
        self.data: QueryDict = data or QueryDict()
        # Create a shortcut to the model's get_field method if the model exists
        if self.Meta.model is not None:
            self.get_field: Callable[[str], Field] = self.Meta.model._meta.get_field
        # Store whether or not the update is partial
        self.partial: bool = partial
        # Store the request so we can access things like the user id
        self.request: Request = request
        # Store a span that is used in the view to wrap the controller section, which can create children for each
        # validation method
        self.span = span
        # Store the validation functions in a dictionary
        self.validate_funcs: Dict[str, Callable[[Any], Optional[str]]] = {}
        for field in self.Meta.validation_order:
            method = getattr(self, f'validate_{field}', None)
            if callable(method):
                self.validate_funcs[field] = method

        # Create a dict for storing errors in
        self._errors: dict = {}
        # Store the model instance (if any)
        self._instance: Optional[Model] = instance
        # Ensure that the setup done in the .instance property is only done once
        self._instance_prepared: bool = False
        # Store whether or not the `is_valid` method has been run already
        self._validated: bool = False
        # Create a list for storing warnings
        self._warnings: Deque[str] = deque()

    def is_valid(self) -> bool:
        """
        Attempts to validate the user data by looping through the names in`self.validation_order` and running the
        corresponding `validate_<name>` method to validate the data
        """
        for field, method in self.validate_funcs.items():
            # Skip if partial is True and the field isnt in the data
            if self.partial and field not in self.data:
                continue
            # Get the dirty (uncleaned) value from the sent data and validate it
            if hasattr(self.data, 'getlist'):
                dirty_value = self.data.getlist(field)
                # For some reason, even though I set None as a default it still returns an empty list if the key is not
                # present in the querydict
                if len(dirty_value) == 0:
                    dirty_value = None
                elif len(dirty_value) == 1:
                    dirty_value = dirty_value[0]
            else:
                dirty_value = self.data.get(field, None)
            # Strip the value if it is a string
            if isinstance(dirty_value, str):
                dirty_value = dirty_value.strip()
            # Run the validation method
            parent_span = None
            if self.span is not None:
                # Remember the parent span, then create a child span off of it and assign it to self.span
                parent_span = self.span
                self.span = settings.TRACER.start_span(f'validate_{field}', child_of=parent_span)
            err = method(dirty_value)
            if err is not None:
                if self.span is not None:
                    self.span.set_tag('error', 'True')
                    self.span.set_tag('error_code', err)
                self._errors[field] = err
            if self.span is not None:
                self.span.finish()
                # Assign the parent span back to self.span
                self.span = parent_span
        self._validated = True
        # Controller is valid if there were no errors
        return self._errors == {}

    # Properties
    @property
    def instance(self) -> Model:
        """
        After validating the user data, create an instance of self.Meta.model that uses the passed data
        (and model if one was passed) to create (or update) it
        :return: An instance of self.Meta.model with the cleaned data used to populate it's fields
        """
        if self._instance_prepared:
            return self._instance
        # Ensure that the model has been specified and the controller validated
        if self.Meta.model is None:
            raise AttributeError('Controller.Meta.model must be specified in order to create an instance.')
        if not self._validated:
            raise AttributeError('You must run the `is_valid` method before trying to create an instance.')
        if self._errors != {}:
            raise AttributeError('Cannot create a model instance as there was some errors with the data.')
        # 2 cases; create & update
        # Get the model fields
        model_fields = {field.name for field in self.Meta.model._meta.fields}
        # If update (or instance is called twice when create)
        if self._instance is not None:
            for k, v in self.cleaned_data.items():
                if k in model_fields:
                    setattr(self._instance, k, v)
        else:
            # Create
            self._instance = self.Meta.model(**self.cleaned_data)
        # Update the _instance_prepared flag now that it's set up
        self._instance_prepared = True
        return self._instance

    @property
    def errors(self) -> Dict[str, Dict[str, str]]:
        """
        Render errors generated by ServiceValidationErrors into full error messages by checking the Repository API and
        getting messages for the error codes
        :return: A dictionary of each field to a dict of the error code and the message for that code
                 (if one can be retrieved from the API)
        """
        # If no error class has been specified then we can't get the messages
        language_id = None
        if hasattr(self.request, 'user'):
            language_id = getattr(self.request.user, 'language', {}).get('id', None)
        error_codes = get_error_details(
            *self._errors.values(),
            language_id=language_id,  # Language ID does nothing right now
        )
        missing: Deque[str] = deque()
        errors: Dict[str, Dict[str, str]] = {}
        for field, code in self._errors.items():
            try:
                errors[field] = error_codes[code]
            except KeyError:
                missing.append(code)
        if len(missing) > 0:
            raise KeyError(
                f'The following error codes were raised but no messages were defined for them; {", ".join(missing)}',
            )
        return errors

    @property
    def warnings(self) -> List[str]:
        """
        Turn the deque of warnings into a list so that it can be serialized
        This method is purely just to remove `list` calls in all the views
        :return: self._warnings as a list instead of a deque
        """
        return list(self._warnings)

    # List / Default validation methods
    def validate_search(self, search: Optional[Dict[str, Any]]):
        """
        Validate the sent search parameters by ensuring that the specified
        filters are allowed by the controller and the corresponding values are allowed for the chosen operator
        :param search: The search deep object dict from the request params or None if either nothing was
                       sent or the request uses the old form of sending search params (DEPRECATED)
        """
        # First check if we need to use the compat method
        if search is None:
            # Get a dict of search params from the request dict directly
            search = {
                k: v for k, v in self.data.items()
                # Ignore the other list params, and anything starting with exclude__
                if k != 'format' and
                k not in self.Meta.validation_order and
                not k.startswith('exclude__')
            }
            # If this dict isn't empty, add a DeprecationWarning
            if search != {}:
                self._warnings.append(
                    'DeprecationWarning: The old form of specifying search filters is deprecated and will be removed '
                    'soon. Please now use the OpenAPI deepObject style to specify filters; '
                    'e.g. "name__icontains=hi" should become "search[name__icontains]=hi".',
                )
        # Now we validate the stuff that was sent
        # Leave value validation to the view as much as possible to raise
        # errors on bad values
        clean_search = {}
        for name, value in search.items():
            # Check that name is an allowed search field
            # Either the whole thing is a key in the search field or
            # .split('__')[:-1] is a key and [-1] is in the value list
            segments = name.split('__')
            name_without_op, op = '__'.join(segments[:-1]), segments[-1]
            # Invalid if the full filter isn't in the search fields,
            # the name without the possible op isn't in the search fields
            # or the op isn't allowed for that name
            search_fields = self.Meta.search_fields
            if name not in search_fields and name_without_op not in search_fields:
                self._warnings.append(
                    f'SearchFilterWarning: {name} is an invalid filter for this list method and was skipped.',
                )
                continue
            # Now we know that either name without op or name is in the fields
            if (name_without_op in search_fields and op not in
                    search_fields[name_without_op]):
                self._warnings.append(
                    f'SearchFilterWarning: {name} is an invalid filter for this list method as the specified operator'
                    ' is invalid for the name, and was skipped.',
                )
                continue

            # Figure out which name we're using
            if name in search_fields:
                search_name, search_op = str(name), None
            else:
                search_name, search_op = str(name_without_op), str(op)
            value = str(value)
            # Now do some minor type coercions if needed
            if search_op in ['in', 'range']:
                # The value should be coming in as a list string
                value = LIST_PATTERN.sub('', value).split(',')
                # Strip the strings inside and remove empty values
                value = list(filter(None, (v.strip() for v in value)))
                # For range we might as well check if the range is 2
                if search_op == 'range' and len(list(value)) != 2:
                    self._warnings.append(
                        f'SearchFilterWarning: {name} is an invalid filter as it contains an invalid '
                        '"range" parameter. Ensure that "range" parameters are sent as strings of '
                        '2-tuples, e.g. "search[number__range]=(10, 15)".',
                    )
                    continue
            # Booleans
            elif search_op == 'isnull' or value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
            # Params that we can tell need to be numbers
            elif search_op in ['year', 'month', 'day', 'week_day', 'hour', 'minute']:
                try:
                    value = int(value)
                except ValueError:
                    self._warnings.append(
                        f'SearchFilterWarning: {name} is an invalid filter as it requires an integer '
                        'value and the received value was not a valid integer.',
                    )
                    continue
            # If we make it here, the filter is valid from what we can tell
            # Something might still go wrong when trying to use it though
            key = '__'.join(filter(None, [search_name, search_op]))
            clean_search[key] = value
        # Save the cleaned out search values
        self.cleaned_data['search'] = clean_search

    def validate_exclude(self, exclude: Optional[Dict[str, Any]]):
        """
        Validate the sent exclude parameters by ensuring that the specified
        filters are allowed by the controller and the corresponding values are allowed for the chosen operator
        :param exclude: The exclude deep object dict from the request params or None if either nothing was sent or
                        the request uses the old form of sending search params (DEPRECATED)
        """
        # First check if we need to use the compat method
        if exclude is None:
            # Get a dict of search params from the request dict directly
            exclude = {
                k.replace('exclude__', ''): v
                for k, v in self.data.items()
                # Ignore the other list params, and anything starting with exclude__
                if k != 'format' and
                k not in self.Meta.validation_order and
                k.startswith('exclude__')
            }
            # If this dict isn't empty, add a DeprecationWarning
            if exclude != {}:
                self._warnings.append(
                    'DeprecationWarning: The old form of specifying exclude filters is deprecated and will be removed'
                    ' soon. Please now use the OpenAPI deepObject style to specify filters; '
                    'e.g. "exclude__name__icontains=hi" should become "exclude[name__icontains]=hi".',
                )
        # Now we validate the stuff that was sent
        # Leave value validation to the view as much as possible to raise
        # errors on bad values
        clean_exclude = {}
        for name, value in exclude.items():
            # Check that name is an allowed search field
            # Either the whole thing is a key in the search field or
            # .split('__')[:-1] is a key and [-1] is in the value list
            segments = name.split('__')
            name_without_op, op = '__'.join(segments[:-1]), segments[-1]
            # Invalid if the full filter isn't in the search fields,
            # the name without the possible op isn't in the search fields
            # or the op isn't allowed for that name
            search_fields = self.Meta.search_fields
            if name not in search_fields and name_without_op not in search_fields:
                self._warnings.append(
                    f'ExcludeFilterWarning: {name} is an invalid filter for this list method and was skipped.',
                )
                continue
            # Now we know that either name without op or name is in the fields
            if name_without_op in search_fields and op not in search_fields[name_without_op]:
                self._warnings.append(
                    f'ExcludeFilterWarning: {name} is an invalid filter for this list method as the specified'
                    ' operator is invalid for the name, and was skipped.',
                )
                continue
            # Figure out which name we're using
            if name in search_fields:
                exclude_name, exclude_op = str(name), None
            else:
                exclude_name, exclude_op = str(name_without_op), str(op)
            value = str(value)
            # Now do some minor type coercions if needed
            if exclude_op in ['in', 'range']:
                # The value should be coming in as a list string
                value = LIST_PATTERN.sub('', value).split(',')
                # Strip the strings inside and remove empty values
                value = list(filter(None, (v.strip() for v in value)))
                # For range we might as well check if the range is 2
                if exclude_op == 'range' and len(list(value)) != 2:
                    self._warnings.append(
                        f'ExcludeFilterWarning: {name} is an invalid filter as it contains an invalid'
                        '"range" parameter. Ensure that "range" parameters are sent as strings of '
                        '2-tuples, e.g. "search[number__range]=(10, 15)".',
                    )
                    continue
            # Booleans
            elif exclude_op == 'isnull' or value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
            # Params that we can tell need to be numbers
            elif exclude_op in ['year', 'month', 'day', 'week_day', 'hour', 'minute']:
                try:
                    value = int(value)
                except ValueError:
                    self._warnings.append(
                        f'ExcludeFilterWarning: {name} is an invalid filter as it requires an integer value and the'
                        ' received value was not a valid integer.',
                    )
                    continue
            # If we make it here, the filter is valid from what we can tell
            # Something might still go wrong when trying to use it though
            key = '__'.join(filter(None, [exclude_name, exclude_op]))
            clean_exclude[key] = value
        # Save the cleaned out exclude values
        self.cleaned_data['exclude'] = clean_exclude

    def validate_limit(self, limit: Optional[int]):
        """
        Validate the limit parameter by ensuring its a valid integer in the range 1 -> self.Meta.max_list_limit
        :param limit: The limit parameter sent by the user, if any
        """
        try:
            # Cast here to avoid linter warnings
            limit = int(cast(int, limit))
            if limit < 1 or limit > self.Meta.max_list_limit:
                limit = self.Meta.normal_list_limit
        except (TypeError, ValueError):
            # TypeError raised when doing int(None) for some reason
            limit = self.Meta.normal_list_limit
        self.cleaned_data['limit'] = limit

    def validate_page(self, page: Optional[int]):
        """
        Validate the page number parameter as best we can from here without knowing the total number of
        records by ensuring it's a non-negative int
        :param page: The page parameter sent by the user, if any
        """
        try:
            # Cast here to avoid linter warnings
            page = int(cast(int, page))
        except (TypeError, ValueError):
            page = 0
        self.cleaned_data['page'] = max(page, 0)

    def validate_order(self, order: Optional[str]):
        if order is None:
            order = self.Meta.allowed_ordering[0]
        # Ensure that the order is valid for the model
        desc = order.startswith('-')
        if desc:
            order = order.lstrip('-')
        if order in self.Meta.allowed_ordering:
            self.cleaned_data['order'] = ''.join(['-' if desc else '', order])
        else:
            # Give the default
            self.cleaned_data['order'] = self.Meta.allowed_ordering[0]
