from urllib.parse import urlencode

from app.tasks.models import Task
from core.testing.base import API, BaseAPITestCase


def kurl(name, **query):
    """/api/v1/tasks/<name>/?k=v"""
    url = f"{API}/tasks/{name}/"
    return f"{url}?{urlencode(query)}" if query else url


def results(response):
    return response.data["results"]["data"]


def ids(response):
    return {str(item["id"]) for item in results(response)}


class TaskAPITestCase(BaseAPITestCase):
    """
    Provides a ready-made project with one user per role:

        owner (OWNER, creator) / manager / lead / contributor / viewer / outsider
    """

    def setUp(self):
        super().setUp()
        self.owner = self.make_user()
        self.project = self.make_project(self.owner)
        self.manager, self.lead, self.contributor, self.viewer, self.outsider = (self.make_user() for _ in range(5))
        self.add_project_member(self.project, self.manager, "MANAGER")
        self.add_project_member(self.project, self.lead, "LEAD")
        self.add_project_member(self.project, self.contributor, "CONTRIBUTOR")
        self.add_project_member(self.project, self.viewer, "VIEWER")

    # requests
    def get(self, user, name, **query):
        return self.client_for(user).get(kurl(name, **query))

    def post(self, user, name, data=None, **query):
        return self.client_for(user).post(kurl(name, **query), data or {}, format="json")

    def put(self, user, name, data=None, **query):
        return self.client_for(user).put(kurl(name, **query), data or {}, format="json")

    def delete(self, user, name, data=None, **query):
        return self.client_for(user).delete(kurl(name, **query), data or {}, format="json")

    # data
    def make_task(self, created_by=None, project=None, **fields):
        fields.setdefault("title", "Task")
        return Task.objects.create(project=project or self.project, created_by=created_by or self.owner, **fields)

    def create(self, user, title="New task", project=None, **extra):
        data = {"title": title, "project_id": str((project or self.project).id), **extra}
        return self.post(user, "create-task", data)
