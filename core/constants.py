ORG_ROLES = [
    ("OWNER", "Owner"),            # Root-level access, created the org
    ("ADMIN", "Admin"),            # Full control except deleting org
    ("MANAGER", "Manager"),        # Manage teams/projects but not billing
    ("MEMBER", "Member"),          # Normal user
    ("VIEWER", "Viewer"),          # Read-only access
]

TEAM_ROLES = [
    ("MANAGER", "Manager"),        # Manages team, invites members
    ("LEAD", "Lead"),              # Can assign tasks, manage team workflows
    ("MEMBER", "Member"),          # Normal team member
    ("VIEWER", "Viewer"),          # Read-only
]

PROJECT_ROLES = [
    ("OWNER", "Owner"),            # Full control of project
    ("MANAGER", "Manager"),        # Can manage tasks and members
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

TASK_STATUS = [
    ("TO_DO", "To Do"),
    ("IN_PROGRESS", "In Progress"),
    ("REVIEW", "In Review"),
    ("DONE", "Done"),
    ("BLOCKED", "Blocked"),
]

ORG_ROLE_HIERARCHY = {
    "OWNER": 5,
    "ADMIN": 4,
    "MANAGER": 3,
    "MEMBER": 2,
    "VIEWER": 1,
}

TEAM_ROLE_HIERARCHY = {
    "MANAGER": 4,
    "LEAD": 3,
    "MEMBER": 2,
    "VIEWER": 1,
}

PROJECT_ROLE_HIERARCHY = {
    "OWNER": 4,
    "MANAGER": 3,
    "CONTRIBUTOR": 2,
    "VIEWER": 1,
}

TASK_PRIORITY = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "URGENT": 4,
}

TASK_TYPE = [
    ("BUG", "Bug"),
    ("FEATURE", "Feature"),
    ("IMPROVEMENT", "Improvement"),
    ("DOCUMENTATION", "Documentation"),
]

