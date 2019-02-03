import copy
import io
import json

import pytest

import falcon
from falcon.testing import create_environ

from graceful.media.base import BaseMediaHandler
from graceful.media.json import JSONHandler
from graceful.media.handlers import MediaHandlers


class SimpleMediaHandler(BaseMediaHandler):
    def deserialize(self, stream, content_type, content_length):
        try:
            s = stream.read(content_length or 0)
            fp = io.StringIO(s.decode('utf-8') if isinstance(s, bytes) else s)
            return json.load(fp)
        except ValueError as err:
            raise falcon.HTTPBadRequest(
                title='Invalid JSON',
                description='Could not parse JSON body - {}'.format(err))

    def serialize(self, media, content_type, **kwargs):
        fp = io.StringIO()
        json.dump(media, fp)
        return fp.getvalue()

    @property
    def media_type(self):
        return 'application/json'


class SimpleJSONHandler(JSONHandler):
    """A simple tested media handler."""
    @classmethod
    def dumps(cls, obj, *args, indent=0, **kwargs):
        fp = io.StringIO()
        json.dump(obj, fp, indent=indent or None)
        return fp.getvalue()

    @classmethod
    def loads(cls, s, *args, **kwargs):
        fp = io.StringIO(s.decode('utf-8'))
        return json.load(fp)


@pytest.fixture(scope='module')
def media():
    return {
        'content': {
            'breed': 'siamese',
            'id': 0,
            'name': 'kitty'
        },
        'meta': {
            'params': {
                'indent': 0
            }
        }
    }


@pytest.fixture
def media_json():
    return 'application/json'


@pytest.fixture
def req(media, media_json):
    headers = {'Content-Type': media_json}
    env = create_environ(body=json.dumps(media), headers=headers)
    return falcon.Request(env)


@pytest.fixture(params=[
    JSONHandler(),
    SimpleJSONHandler(),
    SimpleMediaHandler(),
    MediaHandlers()
])
def media_handler(request):
    return request.param


@pytest.fixture
def json_handler():
    return JSONHandler()


@pytest.fixture
def subclass_json_handler():
    return SimpleJSONHandler()


@pytest.fixture
def media_handlers():
    return MediaHandlers()


def test_abstract_media_handler():
    with pytest.raises(TypeError):
        BaseMediaHandler()


def test_allowed_media_types():
    handler = SimpleMediaHandler(extra_media_types=['application/yaml'])
    assert isinstance(handler.allowed_media_types, set)
    assert len(handler.allowed_media_types) == 2
    assert 'application/json' in handler.allowed_media_types
    assert 'application/yaml' in handler.allowed_media_types


def test_json_handler_media_type(json_handler, media_json):
    assert json_handler.media_type == media_json


def test_json_handler_deserialize(json_handler, media, media_json):
    body = json.dumps(media)
    stream = io.BytesIO(body.encode('utf-8'))
    assert json_handler.deserialize(stream, media_json, len(body)) == media


def test_json_handler_deserialize_invalid_stream(json_handler, media_json):
    with pytest.raises(falcon.HTTPBadRequest):
        json_handler.deserialize(io.BytesIO(b'{'), media_json, 1)


def test_json_handler_serialize(json_handler, media, media_json):
    expected = json.dumps(media)
    assert json_handler.serialize(media, media_json) == expected


@pytest.mark.parametrize('indent', [2, 4])
def test_json_handler_serialize_indent(
        json_handler, mocker, media, media_json, indent):
    mocker.patch.object(json, 'dumps', autospec=True)
    json_handler.serialize(media, media_json, indent=indent)
    json.dumps.assert_called_once_with(media, indent=indent)


def test_json_handler_serialize_indent_none(
        json_handler, mocker, media, media_json):
    mocker.patch.object(json, 'dumps', autospec=True)
    json_handler.serialize(media, media_json, indent=0)
    json.dumps.assert_called_once_with(media, indent=None)
    with pytest.raises(AssertionError):
        json.dumps.assert_called_once_with(media, indent=0)


def test_subclass_json_handler_media_type(subclass_json_handler, media_json):
    assert subclass_json_handler.media_type == media_json


def test_subclass_json_dumps(subclass_json_handler):
    obj = {'testing': True}
    expected = json.dumps(obj)
    assert subclass_json_handler.dumps(obj) == expected


def test_subclass_json_loads(subclass_json_handler):
    s = b'{"testing": true}'
    expected = json.loads(s.decode('utf-8'))
    assert subclass_json_handler.loads(s) == expected


def test_handle_request(media_handler, req, media, media_json):
    assert media_handler.handle_request(req, content_type=media_json) == media


def test_handle_request_unsupported_media_type(media_handler, req):
    with pytest.raises(falcon.HTTPUnsupportedMediaType):
        media_handler.handle_request(req, content_type='nope/json')


def test_handle_response(media_handler, resp, media):
    data = media_handler.handle_response(resp, media=media)
    assert (resp.data or resp.body) == data
    assert resp.data or isinstance(resp.body, str)
    assert resp.body or isinstance(resp.data, bytes)


def test_handle_response_content_type(media_handler, resp, media):
    media_handler.handle_response(resp, media=media)
    assert resp.content_type == media_handler.media_type


def test_handle_response_serialized_string(media_handler, resp, mocker):
    serialized = '{"testing": true}'
    mocker.patch.object(media_handler, 'serialize', return_value=serialized)
    media_handler.handle_response(resp, media={'testing': True})
    assert resp.body == serialized
    assert resp.data is None


def test_handle_response_serialized_bytes(media_handler, resp, mocker):
    serialized = b'{"testing": true}'
    mocker.patch.object(media_handler, 'serialize', return_value=serialized)
    media_handler.handle_response(resp, media={'testing': True})
    assert resp.data == serialized
    assert resp.body is None


def test_serialization_process(media_handler, media):
    content_type = media_handler.media_type
    s = media_handler.serialize(media, content_type)
    stream = io.BytesIO(s.encode('utf-8') if isinstance(s, str) else s)
    assert media_handler.deserialize(stream, content_type, len(s)) == media


def test_media_handlers_default_media_type(media_handlers):
    assert media_handlers.media_type == 'application/json'


def test_media_handlers_unknown_default_media_type():
    with pytest.raises(ValueError):
        handlers = {'application/json': JSONHandler()}
        MediaHandlers(default_media_type='nope/json', handlers=handlers)


def test_media_handlers_allowed_media_types(media_handlers):
    assert isinstance(media_handlers.allowed_media_types, set)
    assert len(media_handlers.allowed_media_types) == 2
    expected = {'application/json', 'application/json; charset=UTF-8'}
    assert media_handlers.allowed_media_types == expected


@pytest.mark.parametrize('media_type', [
    'application/json',
    'application/json; charset=UTF-8'
])
def test_media_handlers_lookup(media_handlers, media_type):
    handler = media_handlers.lookup_handler(media_type)
    assert isinstance(handler, JSONHandler)


@pytest.mark.parametrize('media_type', [
    'application/json',
    'application/json; charset=UTF-8'
])
def test_media_handlers_lookup_by_default_media_type(
        media_handlers, media_type):
    handler = media_handlers.lookup_handler('*/*', media_type)
    assert isinstance(handler, JSONHandler)
    handler = media_handlers.lookup_handler(None, media_type)
    assert isinstance(handler, JSONHandler)


def test_media_handlers_lookup_unknown_media_type(media_handlers):
    with pytest.raises(falcon.HTTPUnsupportedMediaType):
        media_handlers.lookup_handler('nope/json')
    with pytest.raises(falcon.HTTPUnsupportedMediaType):
        media_handlers.lookup_handler('*/*', 'nope/json')
    with pytest.raises(falcon.HTTPUnsupportedMediaType):
        media_handlers.lookup_handler(None, 'nope/json')


@pytest.mark.parametrize('default_media_type', [
    'application/json',
    'application/yaml'
])
def test_custom_media_handlers(default_media_type, req, resp, media, mocker):
    class FakeYAMLHandler(BaseMediaHandler):
        def deserialize(self, stream, content_type, content_length, **kwargs):
            try:
                return json.loads(stream.read(content_length or 0), **kwargs)
            except ValueError as err:
                raise falcon.HTTPBadRequest(
                    title='Invalid YAML',
                    description='Could not parse YAML body - {}'.format(err))

        def serialize(self, media, content_type, indent=0, **kwargs):
            return json.dumps(media, indent=indent, **kwargs)

        @property
        def media_type(self):
            return 'application/yaml'

    json_handler = JSONHandler()
    yaml_handler = FakeYAMLHandler()

    media_handlers = MediaHandlers(
        default_media_type=default_media_type,
        handlers={
            'application/json': json_handler,
            'application/yaml': yaml_handler
        }
    )
    request_stream = copy.copy(req.stream)

    # testing YAML request handler
    assert media_handlers.media_type == default_media_type
    assert media_handlers.lookup_handler('application/yaml') is yaml_handler
    mocker.patch.object(yaml_handler, 'deserialize')
    req.stream = request_stream
    req.content_type = 'application/yaml'
    media_handlers.handle_request(req)
    yaml_handler.deserialize.assert_called_once()

    # testing JSON request handler
    assert media_handlers.lookup_handler('application/json') is json_handler
    mocker.patch.object(json_handler, 'deserialize')
    req.stream = request_stream
    req.content_type = 'application/json'
    media_handlers.handle_request(req)
    json_handler.deserialize.assert_called_once()

    # testing response handler
    default_handler = media_handlers.handlers[default_media_type]
    mocker.patch.object(default_handler, 'serialize')
    media_handlers.handle_response(resp, media=media)
    assert resp.content_type == media_handlers.media_type
    default_handler.serialize.assert_called_once()


def test_custom_extra_media_handlers():
    extra_media_types = ['application/json; charset=UTF-8']
    json_handler = JSONHandler(extra_media_types=extra_media_types)
    media_handlers = MediaHandlers(
        default_media_type='application/json',
        handlers={'application/json': json_handler}
    )
    assert media_handlers.lookup_handler('application/json') is json_handler
    for extra_media_type in extra_media_types:
        media_handler = media_handlers.lookup_handler(extra_media_type)
        assert media_handler is media_handlers.handlers[extra_media_type]
        assert media_handler is json_handler

    media_handlers = MediaHandlers(
        default_media_type='application/json',
        handlers={
            'application/json': json_handler,
            'application/json; charset=UTF-8': JSONHandler()
        }
    )

    assert media_handlers.lookup_handler('application/json') is json_handler
    for extra_media_type in extra_media_types:
        media_handler = media_handlers.lookup_handler(extra_media_type)
        assert media_handler is media_handlers.handlers[extra_media_type]
        assert media_handler is not json_handler
