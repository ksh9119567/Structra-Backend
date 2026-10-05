from urllib.parse import urlencode

from core.testing.base import API, BaseAPITestCase


def turl(name, **query):
    """/api/v1/teams/<name>/?k=v"""
    url = f"{API}/teams/{name}/"
    return f"{url}?{urlencode(query)}" if query else url


def results(response):
    return response.data["results"]["data"]


def ids(response):
    return {str(item["id"]) for item in results(response)}


class TeamAPITestCase(BaseAPITestCase):
    def get(self, user, name, **query):
        return self.client_for(user).get(turl(name, **query))

    def post(self, user, name, data=None, **query):
        return self.client_for(user).post(turl(name, **query), data or {}, format="json")

    def put(self, user, name, data=None, **query):
        return self.client_for(user).put(turl(name, **query), data or {}, format="json")

    def delete(self, user, name, data=None, **query):
        return self.client_for(user).delete(turl(name, **query), data or {}, format="json")
