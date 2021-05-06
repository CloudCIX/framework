# lib
from django.contrib.postgres.fields import JSONField
from django.db import models


__all__ = [
    'APILog',
    'BaseManager',
    'BaseModel',
]


class APILog(models.Model):
    """
    Logs of successful API requests by user which can be used to charge people for the use of the API
    """
    datetime = models.DateTimeField(auto_now_add=True)
    user_id = models.CharField(max_length=64)
    api_key = models.CharField(max_length=64)
    url = models.URLField()
    method = models.CharField(max_length=10)


class BaseManager(models.Manager):
    """
    The BaseManager used as a base for managers for all the models in the API.
    Since every object ignores records where the `deleted` field is not null, it made sense to put that in here.

    This can be overwritten later for any models with relationships that need
    to be selected / pre-fetched as well.
    """

    def get_queryset(self) -> models.QuerySet:
        """
        Customise the `get_queryset` method to ignore all deleted__isnull records since we never want to get records
        that are deleted.
        For models that need selecting / pre-fetching, this method can be further extended
        :return: The base queryset, which ignores deleted records, and can be further acted upon
        """
        # No select or prefetch related calls in Country but I wrote this to
        # get into the habit for later
        return super().get_queryset().filter(deleted__isnull=True)


class BaseModel(models.Model):
    """
    Base Model for all models in CloudCIX.

    Provides base level fields that are needed in all models in our API.
    Provided fields:
        - `created`: DateTime field representing when the record is created
        - `updated`: DateTime field representing the last time the record was updated
        - `deleted`: DateTime field representing the time at which the record was deleted. This is needed as we don't
                     actually delete records from our database
        - `extra`: A JSON field for any extra data that might be needed for the record

    Also automatically overwrites the `objects` manager with our BaseManager
    """
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    deleted = models.DateTimeField(null=True)
    extra = JSONField(default=dict)
    # Overwrite the default manager with our base one
    objects = BaseManager()

    class Meta:
        """
        Meta information about the model. Used to control various settings such as default ordering, table name, etc.
        """
        # Make Django aware that this is an abstract base class
        abstract = True
