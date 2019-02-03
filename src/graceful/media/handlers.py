import falcon
import mimeparse

from graceful.media.base import BaseMediaHandler
from graceful.media.json import JSONHandler


class MediaHandlers(BaseMediaHandler):
    """A media handler that manages internet media type handlers.

    Args:
        default_media_type (str): The default internet media type to use when
            deserializing a response
        handlers (dict): A dict-like object that allows you to configure the
            media types that you would like to handle

    Attributes:
        default_media_type (str): The default internet media type to use when
            deserializing a response
        handlers (dict): A dict-like object that allows you to configure the
            media types that you would like to handle. By default, a handler is
            provided for the ``application/json`` media type.
    """

    def __init__(self, default_media_type='application/json', handlers=None):
        self.default_media_type = default_media_type
        self.handlers = handlers or {
            'application/json': JSONHandler(),
            'application/json; charset=UTF-8': JSONHandler()
        }
        if handlers is not None:
            extra_handlers = {
                media_type: handler
                for handler in handlers.values()
                for media_type in handler.allowed_media_types
                if media_type not in self.handlers
            }
            self.handlers.update(extra_handlers)
        if self.default_media_type not in self.handlers:
            raise ValueError("no handler for default media type '{}'".format(
                default_media_type))
        super().__init__(extra_media_types=list(self.handlers))

    def deserialize(self, stream, content_type, content_length, handler=None):
        """Deserialize the body stream from a :class:`falcon.Request`.

        Args:
            stream (io.BytesIO): Input data to deserialize
            content_type (str): Type of request content
            content_length (int): Length of request content
            handler (BaseMediaHandler): A media handler for deserialization

        Returns:
            object: A deserialized object.

        Raises:
            falcon.HTTPBadRequest: An error occurred on attempt to
                deserialization an invalid stream.

        """
        handler = handler or self.lookup_handler(content_type)
        return handler.deserialize(stream, content_type, content_length)

    def serialize(self, media, content_type, handler=None):
        """Serialize the media object for a :class:`falcon.Response`.

        Args:
            media (object): A Python data structure to serialize
            content_type (str): Type of response content
            handler (BaseMediaHandler): A media handler for serialization

        Returns:
            A serialized (a ``str`` or  ``bytes`` instance) representation from
                the `media` object.

        """
        handler = handler or self.lookup_handler(content_type)
        return handler.serialize(media, content_type)

    def handle_response(self, resp, *, media, **kwargs):
        """Process a single :class:`falcon.Response` object.

        Args:
            resp (falcon.Response): The response object to process
            media (object): A Python data structure to serialize

        """
        content_type = resp.content_type or self.media_type
        default_media_type = resp.options.default_media_type
        handler = self.lookup_handler(content_type, default_media_type)
        super().handle_response(resp, media=media, handler=handler)
        resp.content_type = handler.media_type

    def handle_request(self, req, *, content_type=None, **kwargs):
        """Process a single :class:`falcon.Request` object.

        Args:
            req (falcon.Request): The request object to process
            content_type (str): Type of request content

        Raises:
            falcon.HTTPUnsupportedMediaType: If `content_type` is not supported

        """
        content_type = content_type or req.content_type
        default_media_type = req.options.default_media_type
        handler = self.lookup_handler(content_type, default_media_type)
        super().handle_request(req, content_type=content_type, handler=handler)

    def lookup_handler(self, media_type, default_media_type=None):
        """Lookup media handler by media type.

        Args:
            media_type (str): A media type of the registered media handler
            default_media_type (str): The default media type to use when
                `media_type` is not specified

        Returns:
            BaseMediaHandler: A media handler.

        Raises:
            falcon.HTTPUnsupportedMediaType: If `content_type` is not supported

        """
        if media_type == '*/*' or not media_type:
            media_type = default_media_type or self.media_type
        handler = self.handlers.get(media_type, None)
        if handler is None:
            try:
                resolved = mimeparse.best_match(self.handlers, media_type)
                assert not resolved
                handler = self.handlers[resolved]
            except (AssertionError, KeyError, ValueError):
                allowed = ', '.join("'{}'".format(media_type)
                                    for media_type in self.allowed_media_types)
                raise falcon.HTTPUnsupportedMediaType(
                    description="'{}' is an unsupported media type, supported "
                                "media types: {}".format(media_type, allowed))
            else:
                self.handlers[media_type] = handler
        return handler

    @property
    def media_type(self):
        """The default media type to use when deserializing a response."""
        return self.default_media_type
