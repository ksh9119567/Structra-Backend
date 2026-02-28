TEAM_ROLES = [
    ("OWNER", "Owner"),             # Root-level access
    ("MANAGER", "Manager"),        # Manages team, invites members
    ("LEAD", "Lead"),              # Can assign tasks, manage team workflows
    ("MEMBER", "Member"),          # Normal team member
    ("VIEWER", "Viewer"),          # Read-only
]

TEAM_ROLE_HIERARCHY = {
    "OWNER": 5,
    "MANAGER": 4,
    "LEAD": 3,
    "MEMBER": 2,
    "VIEWER": 1,
}

TEAM_ACTION_POLICIES = {
    "invite_member": {
        "system_min_role": "MANAGER",
        "system_max_role": "MANAGER",
        "configurable": True,
        "default": "MANAGER",
    },
    "remove_member": {
        "system_min_role": "MANAGER",
        "system_max_role": "MANAGER",
        "configurable": True,
        "default": "MANAGER",
    },
    "update_member": {
        "system_min_role": "MANAGER",
        "system_max_role": "MANAGER",
        "configurable": True,
        "default": "MANAGER",
    },
}
