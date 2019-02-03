from abc import ABCMeta, abstractmethod

import falcon


class BaseMediaHandler(metaclass=ABCMeta):
    """An abstract base class for an internet media type handler.

    Args:
        extra_media_types (list): An extra media types to support when
            deserialize the body stream of request objects

    Attributes:
        allowed_media_types (set): All media types supported for
            deserialization

    """

    def __init__(self, extra_media_types=None):
        """The __init__ method documented in the class level."""
        extra_media_types = extra_media_types or []
        self.allowed_media_types = set([self.media_type] + extra_media_types)

    @abstractmethod
    def deserialize(self, stream, content_type, content_length, **kwargs):
        """Deserialize the body stream from a :class:`falcon.Request`.

        Args:
            stream (io.BytesIO): Input data to deserialize
            content_type (str): Type of request content
            content_length (int): Length of request content

        Returns:
            object: A deserialized object.

        Raises:
            falcon.HTTPBadRequest: An error occurred on attempt to
                deserialization an invalid stream.

        """
        raise NotImplementedError

    @abstractmethod
    def serialize(self, media, content_type, **kwargs):
        """Serialize the media object for a :class:`falcon.Response`.

        Args:
            media (object): A Python data structure to serialize
            content_type (str): Type of response content

        Returns:
            A serialized (``str`` or  ``bytes``) representation of ``media``.

        """
        raise NotImplementedError

    def handle_response(self, resp, *, media, **kwargs):
        """Process a single :class:`falcon.Response` object.

        Args:
            resp (falcon.Response): The response object to process
            media (object): A Python data structure to serialize

        Returns:
            A serialized (``str`` or  ``bytes``) representation of ``media``.

        """
        # sets the Content-Type header
        resp.content_type = self.media_type
        data = self.serialize(media, resp.content_type, **kwargs)
        # a small performance gain by assigning bytes directly to resp.data
        if isinstance(data, bytes):
            resp.data = data
        else:
            resp.body = data
        return data

    def handle_request(self, req, *, content_type=None, **kwargs):
        """Process a single :class:`falcon.Request` object.

        Args:
            req (falcon.Request): The request object to process
            content_type (str): Type of request content

        Returns:
            object: A deserialized object from a :class:`falcon.Request` body.

        Raises:
            falcon.HTTPUnsupportedMediaType: If `content_type` is not supported

        """
        content_type = content_type or req.content_type
        if content_type in self.allowed_media_types:
            return self.deserialize(
                req.stream, content_type, req.content_length, **kwargs)
        else:
            allowed = ', '.join("'{}'".format(media_type)
                                for media_type in self.allowed_media_types)
            raise falcon.HTTPUnsupportedMediaType(
                description="'{}' is an unsupported media type, supported "
                            "media types: {}".format(content_type, allowed))

    @property
    @abstractmethod
    def media_type(self):
        """The media type to use when deserializing a response."""
        raise NotImplementedError
