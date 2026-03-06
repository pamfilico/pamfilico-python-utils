"""Tests for collection pagination decorator."""

from marshmallow import Schema, fields

from pamfilico_python_utils.flask.pagination import collection


def test_collection_decorator_applies():
    class DummySchema(Schema):
        id = fields.Int()

    @collection(DummySchema)
    def dummy(auth):
        class Q:
            session = None

            def column_descriptions(self):
                return [{"type": type("M", (), {"id": 1})()}]

            def filter(self, *a):
                return self

            def order_by(self, *a):
                return self

            def limit(self, n):
                return self

            def offset(self, n):
                return self

            def count(self):
                return 0

            def all(self):
                return []

        return Q()

    assert callable(dummy)
