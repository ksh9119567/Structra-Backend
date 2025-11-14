from .models import User


def get_user(identifier, kind="email"):
    """
    Returns a user instance by email or phone number.
    """
    if kind == "email":
        return User.objects.filter(email__iexact=identifier).first()
    elif kind == "phone":
        # model field is `phone_no`; keep lookup case-insensitive-ish if needed
        return User.objects.filter(phone_no=identifier).first()
    return None

