from rest_framework.exceptions import PermissionDenied, ValidationError


def ensure_can_grant_role(*, role, granter_role, hierarchy):
    """
    Guards every path that hands someone a role they did not earn through the
    normal ladder (invites). Without it any member allowed to invite could
    invite an accomplice straight in as OWNER, or as a role above their own,
    and then be out-ranked by that account.

    - OWNER is never granted this way; ownership moves only through the
      dedicated transfer-ownership action.
    - Otherwise the granted role must rank strictly below the granter's own
      role, mirroring the rule update-member already enforces. A scope's
      OWNER (or a governance backstop acting as one) may grant any
      non-OWNER role.
    """
    if role == "OWNER":
        raise ValidationError("Ownership can only be transferred, not granted by invite.")

    granter_rank = hierarchy.get(granter_role)
    if granter_rank is None:
        raise PermissionDenied("You do not have permission to invite members.")

    if granter_role == "OWNER":
        return

    if hierarchy.get(role, -1) >= granter_rank:
        raise ValidationError("You cannot invite someone with a role equal to or higher than your own.")
