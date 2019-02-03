import json
import falcon

from graceful.media.base import BaseMediaHandler


class JSONHandler(BaseMediaHandler):
    """JSON media handler."""

    @classmethod
    def dumps(cls, obj, *args, indent=0, **kwargs):
        """Serialize ``obj`` to a JSON formatted string.

        Args:
            obj (object): A Python data structure to serialize
            indent (int): An indention level (“pretty-printing”)

        Returns:
            str: A JSON formatted string representation of ``obj``.

        """
        return json.dumps(obj, *args, indent=indent or None, **kwargs)

    @classmethod
    def loads(cls, s, *args, **kwargs):
        """Deserialize ``s`` to a Python object.

        Args:
            s (bytes): Input bytes containing JSON document to deserialize

        Returns:
            object: Python representation of ``s``.

        Raises:
            ValueError: If the data being deserialized is not a valid JSON
                document

        """
        return json.loads(s.decode('utf-8'), *args, **kwargs)

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
                deserialization an invalid stream

        """
        try:
            return self.loads(stream.read(content_length or 0), **kwargs)
        except ValueError as err:
            raise falcon.HTTPBadRequest(
                title='Invalid JSON',
                description='Could not parse JSON body - {}'.format(err))

    def serialize(self, media, content_type, indent=0, **kwargs):
        """Serialize the media object for a :class:`falcon.Response`.

        Args:
            media (object): A Python data structure to serialize
            content_type (str): Type of response content
            indent (int): An indention level (“pretty-printing”)

        Returns:
            A serialized (``str`` or  ``bytes``) representation of ``media``.

        """
        return self.dumps(media, indent=indent, **kwargs)

    @property
    def media_type(self):
        """The media type to use when deserializing a response."""
        return 'application/json'
