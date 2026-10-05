"""
The `sprints` app is registered but has no models or endpoints yet.

These tests pin that state so it cannot change silently: the moment a model or
a route appears, one of them fails and reminds you to replace this file with
real tests (model, API and permission cases - see app/tasks/tests for the
pattern).
"""
from django.apps import apps
from django.test import SimpleTestCase

from core.testing.base import API


class SprintsAppPlaceholderTests(SimpleTestCase):
    def test_app_is_installed(self):
        self.assertEqual(apps.get_app_config("sprints").name, "app.sprints")

    def test_app_has_no_models_yet(self):
        self.assertEqual(list(apps.get_app_config("sprints").get_models()), [],
                         "sprints now has models - add tests for them in app/sprints/tests/")

    def test_no_routes_are_mounted_yet(self):
        from django.urls import Resolver404, resolve
        for path in (f"{API}/sprints/", f"{API}/sprints/create-sprint/"):
            with self.assertRaises(Resolver404, msg=f"{path} is now routed - add API tests"):
                resolve(path)
