Content types
-------------

``graceful`` allows for easy and customizable internet media type handling.
By default ``graceful`` only enables a single JSON handler.

However, additional handlers can be configured through the ``media_handler``
attribute on a specified resource.

Here are some resources that be used in the following examples:

.. code-block:: python

    from operator import itemgetter

    from graceful.serializers import BaseSerializer
    from graceful.fields import IntField, RawField
    from graceful.parameters import StringParam
    from graceful.resources.generic import RetrieveAPI, ListCreateAPI


    CATS_STORAGE = [
        {'id': 0, 'name': 'kitty', 'breed': 'siamese'},
        {'id': 1, 'name': 'lucie', 'breed': 'maine coon'},
        {'id': 2, 'name': 'molly', 'breed': 'sphynx'}
    ]


    class CatSerializer(BaseSerializer):
        id = IntField('cat identification number', read_only=True)
        name = RawField('cat name')
        breed = RawField('official breed name')


    class BaseCatResource(RetrieveAPI, with_context=True):
        """Single cat identified by its id."""
        serializer = CatSerializer()

        def get_cat(self, cat_id):
            for cat in CATS_STORAGE:
                if cat['id'] == cat_id:
                    return cat
            else:
                raise falcon.HTTPNotFound

        def retrieve(self, params, meta, context, *, cat_id, **kwargs):
            return self.get_cat(int(cat_id))


    class BaseCatListResource(ListCreateAPI, with_context=True):
        """List of all cats in our API."""
        serializer = CatSerializer()

        breed = StringParam('set this param to filter cats by breed')

        @classmethod
        def get_next_cat_id(cls):
            try:
                return max(CATS_STORAGE, key=itemgetter('id'))['id'] + 1
            except (ValueError, KeyError):
                return 0

        def create(self, params, meta, validated, context, **kwargs):
            validated['id'] = self.get_next_cat_id()
            CATS_STORAGE.append(validated)
            return validated

        def list(self, params, meta, context, **kwargs):
            if 'breed' in params:
                filtered = [
                    cat for cat in CATS_STORAGE
                    if cat['breed'] == params['breed']
                ]
                return filtered
            else:
                return CATS_STORAGE


Custom media handler
~~~~~~~~~~~~~~~~~~~~

Custom media handler can be created by subclassing of :class:`BaseMediaHandler`
class and implementing of two method handlers:

* ``.deserialize(stream, content_type, content_length)``: returns deserialized Python object from a stream
* ``.serialize(media, content_type)``: returns serialized media object

And also implementing of a property that defines the media type of the handler:

* ``media_type``: returns the media type to use when deserializing a response

Lets say you want to write a resource that sends and receives YAML documents.
You can easily do this by creating a new media handler class that represents
a media-type of ``application/yaml`` and can process that data.

Here is an example of how this can be done:

.. code-block:: python

    import falcon
    import yaml

    from graceful.media.base import BaseMediaHandler


    class YAMLHandler(BaseMediaHandler):
        """YAML media handler."""

        def deserialize(self, stream, content_type, content_length, **kwargs):
            try:
                return yaml.load(stream.read(content_length or 0))
            except yaml.error.YAMLError as err:
                raise falcon.HTTPBadRequest(
                    title='Invalid YAML',
                    description='Could not parse YAML body - {}'.format(err))

        def serialize(self, media, content_type, indent=0, **kwargs):
            return yaml.dump(media, indent=indent or None, **kwargs)

        @property
        def media_type(self):
            # 'application/yaml'
            return falcon.MEDIA_YAML

.. note::
    This handler requires the `pyyaml <https://pypi.org/project/PyYAML/>`_
    package, which must be installed in addition to ``graceful`` from PyPI:

    .. code::

        $ pip install pyyaml

Example usage:

.. code-block:: python

    class CatResource(BaseCatResource):
        media_handler = YAMLHandler()


    class CatListResource(BaseCatListResource):
        media_handler = YAMLHandler()


    api = falcon.API()
    api.add_route('/v1/cats/{cat_id}', CatResource())
    api.add_route('/v1/cats/', CatListResource())

Querying:

.. code-block:: yaml

    $ http localhost:8888/v1/cats/0
    HTTP/1.1 200 OK
    Content-Length: 74
    Content-Type: application/yaml
    Date: Fri, 01 Feb 2019 09:07:29 GMT
    Server: waitress

    content: {breed: siamese, id: 0, name: kitty}
    meta:
      params: {indent: 0}

    $ http localhost:8888/v1/cats/?breed=sphynx
    HTTP/1.1 200 OK
    Content-Length: 90
    Content-Type: application/yaml
    Date: Fri, 01 Feb 2019 09:07:53 GMT
    Server: waitress

    content:
    - {breed: sphynx, id: 2, name: molly}
    meta:
      params: {breed: sphynx, indent: 0}

Or access API description issuing ``OPTIONS`` request:

.. code-block:: yaml

    $ http OPTIONS localhost:8888/v1/cats
    HTTP/1.1 200 OK
    Allow: GET, POST, PATCH, OPTIONS
    Content-Length: 1025
    Content-Type: application/yaml
    Date: Fri, 01 Feb 2019 09:08:05 GMT
    Server: waitress

    details: This resource does not have description yet
    fields: !!python/object/apply:collections.OrderedDict
    - - - id
        - {allow_null: false, details: cat identification number, label: null, read_only: true,
          spec: null, type: int, write_only: false}
      - - name
        - {allow_null: false, details: cat name, label: null, read_only: false, spec: null,
          type: raw, write_only: false}
      - - breed
        - {allow_null: false, details: official breed name, label: null, read_only: false,
          spec: null, type: raw, write_only: false}
    methods: [GET, POST, PATCH, OPTIONS]
    name: CatListResource
    params: !!python/object/apply:collections.OrderedDict
    - - - indent
        - {default: '0', details: JSON output indentation. Set to 0 if output should not
            be formatted., label: null, many: false, required: false, spec: null, type: integer}
      - - breed
        - {default: null, details: set this param to filter cats by breed, label: null,
          many: false, required: false, spec: null, type: string}
    path: /v1/cats
    type: list

Adding a new cat named `misty` through YAML document:

.. code-block:: yaml

    $ http POST localhost:8888/v1/cats name="misty" breed="siamese" Content-Type:application/yaml
    HTTP/1.1 201 Created
    Content-Length: 74
    Content-Type: application/yaml
    Date: Fri, 01 Feb 2019 09:10:46 GMT
    Server: waitress

    content: {breed: siamese, id: 3, name: misty}
    meta:
      params: {indent: 0}

    $ http localhost:8888/v1/cats/?breed=siamese
    HTTP/1.1 200 OK
    Content-Length: 131
    Content-Type: application/yaml
    Date: Fri, 01 Feb 2019 09:12:11 GMT
    Server: waitress

    content:
    - {breed: siamese, id: 0, name: kitty}
    - {breed: siamese, id: 3, name: misty}
    meta:
      params: {breed: siamese, indent: 0}

However, JSON document is not allowed in this particular case:

.. code-block:: console

    $ http POST localhost:8888/v1/cats name="daisy" breed="sphynx"
    HTTP/1.1 415 Unsupported Media Type
    Content-Length: 143
    Content-Type: application/json; charset=UTF-8
    Date: Fri, 01 Feb 2019 09:13:42 GMT
    Server: waitress
    Vary: Accept

    {
        "description": "'application/json' is an unsupported media type, supported media types: 'application/yaml'",
        "title": "Unsupported media type"
    }

In general, a media handler can process data of its default internet media type.
However, If a media handler can process the request body of additional media
types, It is possible to configure it through the ``extra_media_types`` parameter.

Here is an example of how this can be done:

.. code-block:: python

    class CatListResource(BaseCatListResource):
        media_handler = YAMLHandler(extra_media_types=['application/json'])


    api = falcon.API()
    api.add_route('/v1/cats/', CatListResource())


Adding a new cat named `misty` through YAML document:

.. code-block:: yaml

    $ http POST localhost:8888/v1/cats name="misty" breed="siamese" Content-Type:application/yaml
    HTTP/1.1 201 Created
    Content-Length: 74
    Content-Type: application/yaml
    Date: Fri, 01 Feb 2019 09:20:03 GMT
    Server: waitress

    content: {breed: siamese, id: 3, name: misty}
    meta:
      params: {indent: 0}


Adding a new cat named `daisy` through JSON document:

.. code-block:: yaml

    $ http POST localhost:8888/v1/cats name="daisy" breed="sphynx"
    HTTP/1.1 201 Created
    Content-Length: 73
    Content-Type: application/yaml
    Date: Fri, 01 Feb 2019 09:20:25 GMT
    Server: waitress

    content: {breed: sphynx, id: 4, name: daisy}
    meta:
      params: {indent: 0}


Custom JSON handler type
~~~~~~~~~~~~~~~~~~~~~~~~

The default JSON media handler using Python’s json module.
If you want to use on other JSON libraries such as ``ujson``,
You can create a custom JSON media handler for that purpose.

Custom JSON media handler can be created by subclassing of :class:`JSONHandler`
class and implementing of two class method handlers:

* ``.dumps(obj, indent=0)``: returns serialized JSON formatted string
* ``.loads(s)``: returns deserialized Python object from a JSON document


Here is an example of how this can be done:

.. code-block:: python

    import ujson

    from graceful.media.json import JSONHandler


    class UltraJSONHandler(JSONHandler):
        """Ultra JSON media handler."""

        @classmethod
        def dumps(cls, obj, *args, indent=0, **kwargs):
            return ujson.dumps(obj, *args, indent=indent, **kwargs)

        @classmethod
        def loads(cls, s, *args, **kwargs):
            return ujson.loads(s.decode('utf-8'), *args, **kwargs)

Alternatively, subclassing of :class:`BaseMediaHandler`:

.. code-block:: python

    import ujson

    from graceful.media.base import BaseMediaHandler


    class UltraJSONHandler(BaseMediaHandler):
        """Ultra JSON media handler."""

        def deserialize(self, stream, content_type, content_length, **kwargs):
            try:
                return ujson.loads(stream.read(content_length or 0), **kwargs)
            except ValueError as err:
                raise falcon.HTTPBadRequest(
                    title='Invalid JSON',
                    description='Could not parse JSON body - {}'.format(err))

        def serialize(self, media, content_type, indent=0, **kwargs):
            return ujson.dumps(media, indent=indent, **kwargs)

        @property
        def media_type(self):
            return 'application/json'

.. note::
    This handler requires the `ujson <https://pypi.org/project/ujson/>`_
    package, which must be installed in addition to ``graceful`` from PyPI:

    .. code::

        $ pip install ujson

Media handlers management
~~~~~~~~~~~~~~~~~~~~~~~~~

The purpose of :class:`MediaHandlers` class is to be a single handler that
manages internet media type handlers.


Here is an example of how this can be used:

.. code-block:: python

    from graceful.media.handlers import MediaHandlers


    class CatListResource(BaseCatListResource):
        media_handler = MediaHandlers(
            default_media_type='application/json',
            handlers = {
                'application/json': UltraJSONHandler(),
                'application/yaml': YAMLHandler()
            }
        )


    api = falcon.API()
    api.add_route('/v1/cats/', CatListResource())

Adding a new cat named `misty` through YAML document:

.. code-block:: console

    $ http POST localhost:8888/v1/cats name="misty" breed="siamese" Content-Type:application/yaml
    HTTP/1.1 201 Created
    Content-Length: 84
    Content-Type: application/json
    Date: Fri, 01 Feb 2019 12:37:59 GMT
    Server: waitress

    {
        "content": {
            "breed": "siamese",
            "id": 3,
            "name": "misty"
        },
        "meta": {
            "params": {
                "indent": 0
            }
        }
    }

Adding a new cat named `daisy` through JSON document:

.. code-block:: console

    $ http POST localhost:8888/v1/cats name="daisy" breed="sphynx"
    HTTP/1.1 201 Created
    Content-Length: 84
    Content-Type: application/json
    Date: Fri, 01 Feb 2019 12:38:35 GMT
    Server: waitress

    {
        "content": {
            "breed": "sphynx",
            "id": 4,
            "name": "daisy"
        },
        "meta": {
            "params": {
                "indent": 0
            }
        }
    }

By default, a responder always use the default internet media type
which is ``application/json`` in our example:

.. code-block:: console

    $ http localhost:8888/v1/cats?breed=siamese Content-Type:application/yaml
    HTTP/1.1 200 OK
    Content-Length: 104
    Content-Type: application/json
    Date: Sat, 02 Feb 2019 16:49:38 GMT
    Server: waitress

    {
        "content": [
            {
                "breed": "siamese",
                "id": 0,
                "name": "kitty"
            }
        ],
        "meta": {
            "params": {
                "breed": "siamese",
                "indent": 0
            }
        }
    }

    $ http localhost:8888/v1/cats?breed=siamese
    HTTP/1.1 200 OK
    Content-Length: 104
    Content-Type: application/json
    Date: Sat, 02 Feb 2019 16:49:47 GMT
    Server: waitress

    {
        "content": [
            {
                "breed": "siamese",
                "id": 0,
                "name": "kitty"
            }
        ],
        "meta": {
            "params": {
                "breed": "siamese",
                "indent": 0
            }
        }
    }

If you do need full negotiation, it is very easy to do it by using middleware.

Here is an example of how this can be done:

.. code-block:: python

    class NegotiationMiddleware(object):
        def process_request(self, req, resp):
            resp.content_type = req.content_type


    api = falcon.API(middleware=NegotiationMiddleware())
    api.add_route('/v1/cats/', CatListResource())

Querying through YAML:

.. code-block:: yaml

    $ http localhost:8888/v1/cats?breed=siamese Content-Type:application/yaml
    HTTP/1.1 200 OK
    Content-Length: 92
    Content-Type: application/yaml
    Date: Sat, 02 Feb 2019 17:00:01 GMT
    Server: waitress

    content:
    - {breed: siamese, id: 0, name: kitty}
    meta:
      params: {breed: siamese, indent: 0}

Querying through JSON:

.. code-block:: console

    $ http localhost:8888/v1/cats?breed=siamese
    HTTP/1.1 200 OK
    Content-Length: 104
    Content-Type: application/json
    Date: Sat, 02 Feb 2019 17:00:10 GMT
    Server: waitress

    {
        "content": [
            {
                "breed": "siamese",
                "id": 0,
                "name": "kitty"
            }
        ],
        "meta": {
            "params": {
                "breed": "siamese",
                "indent": 0
            }
        }
    }
