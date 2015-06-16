# -*- coding: utf-8 -*-
from collections import OrderedDict
from collections.abc import Mapping, MutableMapping

from graceful.fields import BaseField


class MetaSerializer(type):
    """ Metaclass for handling serialization with field objects
    """
    _fields_storage_key = '_fields'

    @classmethod
    def __prepare__(mcs, name, bases, **kwargs):
        """
        Prepare class namespace in a way that ensures order of attributes.
        This needs to be an `OrderedDict` so `_get_params()` method can
        construct fields storage that preserves the same order of fields as
        defined in code.

        Note: this is python3 thing and support for ordering of params in
        descriptions will not be backported to python2 even if this framework
        will get python2 support.
        """
        return OrderedDict()

    @classmethod
    def _get_fields(mcs, bases, namespace):
        """ Pop all field objects from attributes dict (namespace)
        and store them under _field_storage_key atrribute.
        Also collect all fields from base classes in order that ensures
        fields can be overriden.

        :param bases: all base classes of created serializer class
        :param namespace: namespace as dictionary of attributes
        """
        fields = [
            (name, namespace.pop(name))
            for name, attribute
            in list(namespace.items())
            if isinstance(attribute, BaseField)
        ]

        for base in reversed(bases):
            if hasattr(base, mcs._fields_storage_key):
                fields = list(
                    getattr(base, mcs._fields_storage_key).items()
                ) + fields

        return OrderedDict(fields)

    def __new__(mcs, name, bases, namespace):
        namespace[mcs._fields_storage_key] = mcs._get_fields(bases, namespace)
        return super(MetaSerializer, mcs).__new__(
            # note: there is no need preserve order in namespace anymore so
            # we convert it explicitely to dict
            mcs, name, bases, dict(namespace)
        )


class BaseSerializer(object, metaclass=MetaSerializer):

    @property
    def fields(self):
        return getattr(self, self.__class__._fields_storage_key)

    def to_representation(self, obj):
        representation = {}

        for name, field in self.fields.items():
            # note fields do not know their names in source representation
            # but may know what attribute they target from source object
            attribute = self.get_attribute(obj, field.source or name)

            if attribute is None:
                # Skip none attributes so fields do not have to deal with them
                representation[name] = [] if field.many else None
            elif field.many:
                representation[name] = [
                    field.to_representation(item) for item in attribute
                ]
            else:
                representation[name] = field.to_representation(attribute)

        return representation

    def from_representation(self, representation, partial=False):
        return {
            # if field has explicitely specified source then use it
            # else fallback to field name.
            # Note: field does not know its name
            field.source or name: field.validate(
                field.from_representation(
                    representation[name]
                )
            )
            for name, field
            in self.fields.items()
            # if partial allowed then we create only partial object dict
            if not partial or name in representation
        }

    def create(self, data):
        """
        The purpose of this method is not yet defined because we haven't dealt
        with object creation.

        :param data: data to be used when instantiating object
        :return:
        """
        raise NotImplementedError(
            "{cls}.create() method not implemented".format(
                cls=self.__class__.__name__
            )
        )

    def update(self, obj, data):
        """
        The purpose of this method is not yet defined because we haven't dealt
        with object creation.

        :param obj: object instance
        :param data: data to be modified in object instance
        :return:
        """
        raise NotImplementedError(
            "{cls}.update() method not implemented".format(
                cls=self.__class__.__name__
            )
        )

    def get_attribute(self, obj, attr):
        """
        Get attribute from given object instance where 'attribute' can
        be also a key from object if is a dict or any kind of mapping

        note: it will return None if attribute key does not exist

        :param obj: object to retrieve data
        :return:
        """
        # '*' is a special wildcard character that means whole object
        # is passed
        if attr == '*':
            return obj

        # if this is any mapping then instead of attributes use keys
        if isinstance(obj, Mapping):
            return obj.get(attr, None)

        return getattr(obj, attr, None)

    def set_attribute(self, obj, attr, value):
        """
        Set attribute in given object instance where 'attribute' can
        be also a key from object if is a dict or any kind of mapping

        :param obj: object instance to modify
        :param attr: attribute (or key) to change
        :param value: value
        :return:
        """
        # if this is any mutable mapping then instead of attributes use keys
        if isinstance(obj, MutableMapping):
            obj[attr] = value
        else:
            setattr(obj, attr, value)

    def describe(self):
        return OrderedDict([
            (name, field.describe())
            for name, field in self.fields.items()
        ])
