from urllib.parse import urlencode

from core.testing.base import API, BaseAPITestCase


def ourl(name, **query):
    """/api/v1/organizations/<name>/?k=v"""
    url = f"{API}/organizations/{name}/"
    return f"{url}?{urlencode(query)}" if query else url


def results(response):
    return response.data["results"]["data"]


def ids(response):
    return {str(item["id"]) for item in results(response)}


class OrgAPITestCase(BaseAPITestCase):
    def get(self, user, name, **query):
        return self.client_for(user).get(ourl(name, **query))

    def post(self, user, name, data=None, **query):
        return self.client_for(user).post(ourl(name, **query), data or {}, format="json")

    def put(self, user, name, data=None, **query):
        return self.client_for(user).put(ourl(name, **query), data or {}, format="json")

    def delete(self, user, name, data=None, **query):
        return self.client_for(user).delete(ourl(name, **query), data or {}, format="json")
