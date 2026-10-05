import itertools

from django.conf import settings

from rest_framework.test import APIClient, APITestCase

from app.accounts.models import User
from app.accounts.services.auth_service import login_user
from app.organizations.models import Organization, OrganizationMembership
from app.projects.models import Project, ProjectMembership
from app.projects.services.project_team_service import assign_team
from app.teams.models import Team, TeamMembership

API = "/api/v1"

_counter = itertools.count(1)


class BaseAPITestCase(APITestCase):
    """
    Base class for every API test in the project.

    * Each test starts with an empty (fake) Redis, so OTPs, tokens and rate
      limit counters never leak between tests.
    * `client_for(user)` returns a client authenticated with a *real* JWT that
      is registered in the token registry, so requests go through the same
      ValidatedJWTAuthentication path as production.
    * The `make_*` / `add_*` helpers build data straight through the ORM (not
      the API), so a test exercising one endpoint is not coupled to another.
    """

    PASSWORD = "Str0ng-Pass!234"

    def setUp(self):
        super().setUp()
        settings.REDIS_CLIENT.flushall()

    # ------------------------------------------------------------------
    # users & clients
    # ------------------------------------------------------------------
    def make_user(self, email=None, *, verified=True, **extra):
        n = next(_counter)
        email = email or f"user{n}@example.com"
        extra.setdefault("first_name", "User")
        extra.setdefault("last_name", str(n))
        user = User.objects.create_user(email=email, password=self.PASSWORD, **extra)
        if verified:
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
        return user

    def client_for(self, user):
        """An APIClient authenticated as `user` with a registered JWT."""
        _refresh, access = login_user(user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        return client

    def anon(self):
        return APIClient()

    # ------------------------------------------------------------------
    # containers
    # ------------------------------------------------------------------
    @staticmethod
    def set_settings(entity, **fields):
        """Update an Organization/Team/Project settings row in place."""
        cfg = entity.settings
        for key, value in fields.items():
            setattr(cfg, key, value)
        cfg.save()
        return cfg

    def make_org(self, owner, name=None, **settings_fields):
        org = Organization.objects.create(name=name or f"Org {next(_counter)}", owner=owner)
        OrganizationMembership.objects.create(user=owner, organization=org, role="OWNER")
        if settings_fields:
            self.set_settings(org, **settings_fields)
        return org

    def make_team(self, owner, org=None, name=None, **settings_fields):
        team = Team.objects.create(name=name or f"Team {next(_counter)}", created_by=owner, organization=org)
        TeamMembership.objects.create(user=owner, team=team, role="OWNER")
        if settings_fields:
            self.set_settings(team, **settings_fields)
        return team

    def make_project(self, owner, org=None, team=None, team_role="CONTRIBUTOR", name=None, **settings_fields):
        project = Project.objects.create(name=name or f"Project {next(_counter)}", created_by=owner, organization=org)
        ProjectMembership.objects.create(user=owner, project=project, role="OWNER")
        if team is not None:
            assign_team(project=project, team=team, role=team_role, is_owning=True, assigned_by=owner)
        if settings_fields:
            self.set_settings(project, **settings_fields)
        return project

    # ------------------------------------------------------------------
    # memberships
    # ------------------------------------------------------------------
    @staticmethod
    def add_org_member(org, user, role="MEMBER"):
        return OrganizationMembership.objects.create(user=user, organization=org, role=role)

    @staticmethod
    def add_team_member(team, user, role="MEMBER"):
        return TeamMembership.objects.create(user=user, team=team, role=role)

    @staticmethod
    def add_project_member(project, user, role="CONTRIBUTOR"):
        return ProjectMembership.objects.create(user=user, project=project, role=role)

    # ------------------------------------------------------------------
    # convenience
    # ------------------------------------------------------------------
    @staticmethod
    def redis():
        return settings.REDIS_CLIENT

    def assertOK(self, response, code=200):
        self.assertEqual(
            response.status_code, code,
            f"expected {code}, got {response.status_code}: {getattr(response, 'data', response.content)}",
        )
        return response

    def assertDenied(self, response, code=403):
        return self.assertOK(response, code)
