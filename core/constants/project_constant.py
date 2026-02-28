PROJECT_ROLES = [
    ("OWNER", "Owner"),            # Full control of project
    ("MANAGER", "Manager"),        # Can manage tasks and members
    ('LEAD', 'Lead'),              # Can assign tasks
    ("CONTRIBUTOR", "Contributor"),# Can work on tasks
    ("VIEWER", "Viewer"),          # Can view everything
]

PROJECT_STATUS = [
    ("PLANNING", "Planning"),
    ("ACTIVE", "Active"),
    ("COMPLETED", "Completed"),
    ("ON_HOLD", "On Hold"),
    ("ARCHIVED", "Archived"),
]

PROJECT_ROLE_HIERARCHY = {
    "OWNER": 5,
    "MANAGER": 4,
    "LEAD": 3,
    "CONTRIBUTOR": 2,
    "VIEWER": 1,
}

PROJECT_ACTION_POLICIES = {
    "invite_member": {
        "system_min_role": "LEAD",
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
    "create_task": {
        "system_min_role": "MEMBER",
        "system_max_role": "MANAGER",
        "configurable": True,
        "default": "MANAGER",
    },
    "update_task": {
        "system_min_role": "MEMBER",
        "system_max_role": "MANAGER",
        "configurable": True,
        "default": "MANAGER",
    },
    "delete_task": {
        "system_min_role": "MANAGER",
        "system_max_role": "MANAGER",
        "configurable": True,
        "default": "MANAGER",
    }
}
