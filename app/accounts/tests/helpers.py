import itertools

from rest_framework_simplejwt.tokens import RefreshToken

from app.accounts.models import User
from core.testing.base import API, BaseAPITestCase


_register_counter = itertools.count(1)


def aurl(name):
    return f"{API}/accounts/{name}/"


def lifetime_seconds(token):
    """Lifetime baked into a (refresh) JWT: exp - iat."""
    decoded = RefreshToken(token)
    return int(decoded["exp"] - decoded["iat"])


class AccountAPITestCase(BaseAPITestCase):
    def register_payload(self, **overrides):
        n = next(_register_counter)   # a counter, not the clock: two calls in one millisecond must differ
        payload = {
            "email": f"new{n}@example.com",
            "username": "newbie",
            "first_name": "New",
            "last_name": "Bie",
            "password": self.PASSWORD,
        }
        payload.update(overrides)
        return payload

    def login(self, email, password=None, **extra):
        return self.anon().post(aurl("login"), {"email": email, "password": password or self.PASSWORD, **extra},
                                format="json")

    def otp(self, purpose, kind, identifier):
        """The OTP currently stored for (purpose, kind, identifier), or None."""
        return self.redis().get(f"otp:{purpose}:{kind}:{identifier}")

    def fresh(self, user):
        return User.objects.get(pk=user.pk)
