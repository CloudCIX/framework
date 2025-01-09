"""
Database Routers are required when there are multiple DATABASES set up in the
settings.

These classes help inform Django which DB certain models should be routed to
for various operations
- Read
- Write
- Relations
- Migrations

This stuff could be used when it comes to sharding out the DBs too.
"""

# stdlib
from typing import Any, Dict, Optional, Type
# libs
from django.db.models import Model


class CloudCIXRouter:
    """
    This class controls Django's DB functionality to ensure that all cloudcix_rest models get routed to the default DB
    """

    def db_for_read(self, model: Type[Model], **hints: Dict[str, Any]) -> Optional[str]:
        """
        Specifies the DB to use to read objects of the specified Model
        :param model: The class of Model to route to a DB
        :param hints: Any hints that can be given to help the routing decision
        :return: The name of the DB to route reads to
        """
        return 'default' if model._meta.app_label == 'cloudcix_rest' else None

    def db_for_write(self, model: Type[Model], **hints: Dict[str, Any]) -> Optional[str]:
        """
        Specifies the DB to use to write objects of the specified Model
        :param model: The class of Model to route to a DB
        :param hints: Any hints that can be given to help the routing decision
        :return: The name of the DB to route writes to
        """
        return 'default' if model._meta.app_label == 'cloudcix_rest' else None

    def allow_relation(self, model1: Type[Model], model2: Type[Model], **hints: Dict[str, Any]) -> Optional[bool]:
        """
        Determine whether relations such as FOREIGN KEY are allowed between two
        classes of Model
        :param model1: The first model class being tested
        :param model2: The second model class being tested
        :param hints: Any hints that can be given to help the decision
        :return: A flag that states whether a relation is allowed between the
                 two supplied model classes.
        """
        return True if model1._meta.app_label == 'cloudcix_rest' and model2._meta.app_label == 'cloudcix_rest' else None

    def allow_migrate(
            self,
            db: str,
            app_label: str,
            model_name: Optional[str] = None,
            **hints: Dict[str, Any],
    ) -> Optional[bool]:
        """
        Determine whether a migration is allowed to be run on a given DB
        :param db: The name of the database being checked
        :param app_label: The label of the app being checked
        :param model: The model class involved in the migration
        :param hints: Any hints that can be given to help the decision
        :return: A flag that states whether the migration is allowed
        """
        return True if app_label == 'cloudcix_rest' and db == 'default' else None
