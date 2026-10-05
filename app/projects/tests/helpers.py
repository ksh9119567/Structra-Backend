from urllib.parse import urlencode

from core.testing.base import API, BaseAPITestCase


def purl(name, **query):
    """/api/v1/projects/<name>/?k=v"""
    url = f"{API}/projects/{name}/"
    return f"{url}?{urlencode(query)}" if query else url


def results(response):
    """The list payload of a paginated response."""
    return response.data["results"]["data"]


def ids(response):
    return {str(item["id"]) for item in results(response)}


class ProjectAPITestCase(BaseAPITestCase):
    """Adds small request shortcuts shared by the project test modules."""

    def get(self, user, name, **query):
        return self.client_for(user).get(purl(name, **query))

    def post(self, user, name, data=None, **query):
        return self.client_for(user).post(purl(name, **query), data or {}, format="json")

    def put(self, user, name, data=None, **query):
        return self.client_for(user).put(purl(name, **query), data or {}, format="json")

    def delete(self, user, name, data=None, **query):
        return self.client_for(user).delete(purl(name, **query), data or {}, format="json")
