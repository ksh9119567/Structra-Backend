ORG_ROLES = [
    ("OWNER", "Owner"),            # Root-level access, created the org
    ("ADMIN", "Admin"),            # Full control except deleting org
    ("MANAGER", "Manager"),        # Manage teams/projects but not billing
    ("MEMBER", "Member"),          # Normal user
    ("VIEWER", "Viewer"),          # Read-only access
]

ORG_ROLE_HIERARCHY = {
    "OWNER": 5,
    "ADMIN": 4,
    "MANAGER": 3,
    "MEMBER": 2,
    "VIEWER": 1,
}

ORG_ACTION_POLICIES = {
    "invite_member": {
        "system_min_role": "MANAGER",
        "system_max_role": "ADMIN",
        "configurable": True,
        "default": "ADMIN",
    },
    "remove_member": {
        "system_min_role": "ADMIN",
        "system_max_role": "ADMIN",
        "configurable": True,
        "default": "ADMIN",
    },
    "update_member": {
        "system_min_role": "ADMIN",
        "system_max_role": "ADMIN",
        "configurable": True,
        "default": "ADMIN",
    },
    "create_team": {
        "system_min_role": "MANAGER",
        "system_max_role": "ADMIN",
        "configurable": True,
        "default": "ADMIN",
    },
    "create_project": {
        "system_min_role": "MANAGER",
        "system_max_role": "ADMIN",
        "configurable": True,
        "default": "ADMIN",
    }
}
