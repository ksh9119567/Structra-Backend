# API Reference (v1)

Base URL: `/api/v1/`

---

## 🔐 Authentication

| Method | Endpoint | Description |
|---------|-----------|-------------|
| POST | `/accounts/register/` | Register new user |
| GET  | `/accounts/get-user/` | Get current user details |
| POST | `/accounts/login/` | Login (JWT) |
| POST | `/accounts/logout/` | Logout and blacklist token |
| POST | `/accounts/token/refresh/` | Refresh access token |
| POST | `/accounts/otp/get/` | Generate & Send OTP on email or phone |
| POST | `/accounts/otp/verify/` | Verify OTP |
| POST | `/accounts/forgot-password/request/` | Generate & Send OTP for password reset |
| POST | `/accounts/forgot-password/verify/` | Verify OTP and generate reset token |
| PUT  | `/accounts/forgot-password/reset/` | Reset password with token |

**Register Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Register Response (201):**
```json
{
  "message": "User created successfully",
  "user": {
    "id": "user-uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_email_verified": false,
    "is_phone_verified": false,
    "date_joined": "2024-01-15T10:30:00Z"
  },
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

## 🧑‍💼 Organizations

| Method | Endpoint | Description |
|---------|-----------|-------------|
| GET  | `/organizations/` | List all organizations user is member of |
| POST | `/organizations/` | Create a new organization |
| GET  | `/organizations/{id}/` | Get organization details |
| PATCH | `/organizations/{id}/` | Update organization details |
| DELETE | `/organizations/{id}/` | Delete organization (owner only) |
| GET  | `/organizations/{id}/members/` | List all organization members |
| POST | `/organizations/{id}/send_invite/` | Send invite to user for organization |
| POST | `/organizations/{id}/add_member/` | Add user to organization (via invite token) |
| PATCH | `/organizations/{id}/update_member/` | Update member role in organization |
| DELETE | `/organizations/{id}/remove_member/` | Remove member from organization |
| DELETE | `/organizations/{id}/self_remove_member/` | Remove yourself from organization |
| PATCH | `/organizations/{id}/transfer_owner/` | Transfer organization ownership |

**Query Parameters:**
- `org_id` - Organization ID (required for most operations)
- `email` - User email (for member operations)
- `role` - Role to assign (OWNER, ADMIN, MANAGER, MEMBER, VIEWER)
- `search` - Search by name
- `ordering` - Order by field (-created_at)

**Create Organization Request Body:**
```json
{
  "name": "Acme Corporation",
  "is_self_remove_allowed": false
}
```

**Create Organization Response (201):**
```json
{
  "message": "Organization created successfully",
  "data": {
    "id": "org-uuid",
    "name": "Acme Corporation",
    "owner": "user-uuid",
    "is_self_remove_allowed": false,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

**Organization Roles:**
- `OWNER` - Root-level access, created the org
- `ADMIN` - Full control except deleting org
- `MANAGER` - Manage teams/projects but not billing
- `MEMBER` - Normal user
- `VIEWER` - Read-only access

---

## 🧑‍💼 Teams

| Method | Endpoint | Description |
|---------|-----------|-------------|
| GET  | `/teams/` | List all teams user is member of |
| POST | `/teams/` | Create a new team |
| GET  | `/teams/{id}/` | Get team details |
| PATCH | `/teams/{id}/` | Update team details |
| DELETE | `/teams/{id}/` | Delete team (creator only) |
| GET  | `/teams/{id}/members/` | List all team members |
| POST | `/teams/{id}/send_invite/` | Send invite to user for team |
| POST | `/teams/{id}/add_member/` | Add user to team (via invite token) |
| PATCH | `/teams/{id}/update_member/` | Update member role in team |
| DELETE | `/teams/{id}/remove_member/` | Remove member from team |
| DELETE | `/teams/{id}/self_remove_member/` | Remove yourself from team |
| PATCH | `/teams/{id}/transfer_manager/` | Transfer team manager role |

**Query Parameters:**
- `team_id` - Team ID (required for most operations)
- `email` - User email (for member operations)
- `role` - Role to assign (MANAGER, LEAD, MEMBER, VIEWER)
- `search` - Search by name or description
- `ordering` - Order by field (-created_at)

**Create Team Request Body:**
```json
{
  "name": "Development Team",
  "description": "Backend development team",
  "organization": "org-uuid",
  "is_self_remove_allowed": false
}
```

**Create Team Response (201):**
```json
{
  "message": "Team created successfully",
  "data": {
    "id": "team-uuid",
    "name": "Development Team",
    "description": "Backend development team",
    "organization": "org-uuid",
    "created_by": "user-uuid",
    "is_self_remove_allowed": false,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

**Team Roles:**
- `MANAGER` - Manages team, invites members
- `LEAD` - Can assign tasks, manage team workflows
- `MEMBER` - Normal team member
- `VIEWER` - Read-only access

---

## 🧑‍💼 Projects

| Method | Endpoint | Description |
|---------|-----------|-------------|
| GET  | `/projects/` | List all projects user is member of (paginated) |
| POST | `/projects/` | Create a new project |
| GET  | `/projects/{id}/` | Get project details |
| PATCH | `/projects/{id}/` | Update project details |
| DELETE | `/projects/{id}/` | Delete project (owner only) |
| GET  | `/projects/{id}/members/` | List all project members |
| POST | `/projects/{id}/send_invite/` | Send invite to user for project |
| POST | `/projects/{id}/add_member/` | Add user to project (via invite token) |
| PATCH | `/projects/{id}/update_member/` | Update member role in project |
| DELETE | `/projects/{id}/remove_member/` | Remove member from project |
| DELETE | `/projects/{id}/self_remove_member/` | Remove yourself from project |
| PATCH | `/projects/{id}/transfer_ownership/` | Transfer project ownership |

**Query Parameters:**
- `project_id` - Project ID (required for most operations)
- `email` - User email (for member operations)
- `role` - Role to assign (OWNER, MANAGER, CONTRIBUTOR, VIEWER)

**Create Project Request Body:**
```json
{
  "name": "My Project",
  "description": "Project description",
  "organization": "org-uuid",
  "team": "team-uuid",
  "status": "PLANNING"
}
```

**Create Project Response (201):**
```json
{
  "message": "Project created successfully",
  "data": {
    "id": "project-uuid",
    "name": "My Project",
    "description": "Project description",
    "organization": "org-uuid",
    "team": "team-uuid",
    "created_by": "user-uuid",
    "status": "PLANNING",
    "is_self_remove_allowed": false,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

**Project Roles:**
- `OWNER` - Full control of project
- `MANAGER` - Can manage tasks and members
- `CONTRIBUTOR` - Can work on tasks
- `VIEWER` - Can view everything

**Project Status Values:**
- `PLANNING` - Project in planning phase
- `ACTIVE` - Project is currently active
- `COMPLETED` - Project has been completed
- `ON_HOLD` - Project is on hold
- `ARCHIVED` - Project has been archived

---

## 📋 Tasks

| Method | Endpoint | Description |
|---------|-----------|-------------|
| GET  | `/tasks/` | List all tasks in a project (paginated) |
| POST | `/tasks/` | Create a new task |
| GET  | `/tasks/{id}/` | Get task details |
| PATCH | `/tasks/{id}/` | Update task details |
| DELETE | `/tasks/{id}/` | Delete task (creator/manager only) |

**Query Parameters:**
- `project_id` - Project ID (required)
- `status` - Filter by status (TO_DO, IN_PROGRESS, REVIEW, DONE, BLOCKED)
- `priority` - Filter by priority (LOW, MEDIUM, HIGH, URGENT)
- `assigned_to` - Filter by assignee UUID
- `parent` - Filter by parent task UUID (for subtasks)
- `search` - Search in title and description
- `ordering` - Order by field (-timestamp, due_date, priority)

**Create Task Request Body:**
```json
{
  "project": "project-uuid",
  "title": "Task Title",
  "description": "Task description",
  "start_date": "2024-01-15",
  "due_date": "2024-01-20",
  "status": "TO_DO",
  "priority": "HIGH",
  "task_type": "FEATURE",
  "assigned_to": "user-uuid",
  "parent": null
}
```

**Create Task Response:**
```json
{
  "id": "task-uuid",
  "project": "project-uuid",
  "parent": null,
  "title": "Task Title",
  "description": "Task description",
  "start_date": "2024-01-15",
  "due_date": "2024-01-20",
  "status": "TO_DO",
  "priority": "HIGH",
  "task_type": "FEATURE",
  "assigned_to": "user-uuid",
  "created_by": "user-uuid",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Task Status Values:**
- `TO_DO` - Not started
- `IN_PROGRESS` - Currently being worked on
- `REVIEW` - Waiting for review
- `DONE` - Completed
- `BLOCKED` - Blocked by dependencies

**Task Priority Values:**
- `LOW` - Low priority
- `MEDIUM` - Medium priority
- `HIGH` - High priority
- `URGENT` - Urgent/Critical

**Task Type Values:**
- `BUG` - Bug fix
- `FEATURE` - New feature
- `IMPROVEMENT` - Improvement
- `DOCUMENTATION` - Documentation

---

## � Activity Logs

| Method | Endpoint | Description |
|---------|-----------|-------------|
| GET  | `/activity-logs/` | List activity logs (user's own or all for admins) |
| GET  | `/activity-logs/{id}/` | Get specific activity log |
| GET  | `/activity-logs/my_activities/` | Get current user's recent activities |
| GET  | `/activity-logs/stats/` | Get activity statistics |

**Query Parameters:**
- `action` - Filter by action (CREATE, READ, UPDATE, DELETE, LOGIN, LOGOUT, ACCESS, FAILED)
- `resource_type` - Filter by resource type (Organization, Project, Team, Task, etc.)
- `method` - Filter by HTTP method (GET, POST, PUT, PATCH, DELETE)
- `status_code` - Filter by HTTP status code
- `status_code_gte` - Filter by status code >= value
- `status_code_lte` - Filter by status code <= value
- `timestamp_after` - Filter activities after date
- `timestamp_before` - Filter activities before date
- `username` - Search by username (admin only)
- `search` - Full-text search
- `ordering` - Order by field (-timestamp, response_time_ms, status_code)

**Response Example (List):**
```json
{
  "count": 150,
  "next": "http://localhost:8000/api/v1/activity-logs/?page=2",
  "previous": null,
  "results": [
    {
      "id": "log-uuid",
      "user_email": "user@example.com",
      "username": "user@example.com",
      "action": "CREATE",
      "resource_type": "Project",
      "resource_name": "My Project",
      "description": "CREATE Project: My Project",
      "method": "POST",
      "path": "/api/v1/projects/",
      "status_code": 201,
      "response_time_ms": 145.23,
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Response Example (Stats):**
```json
{
  "message": "Success",
  "data": {
    "total_activities": 1250,
    "by_action": {
      "CREATE": 350,
      "READ": 600,
      "UPDATE": 200,
      "DELETE": 50,
      "LOGIN": 50
    },
    "by_resource": {
      "Project": 400,
      "Task": 600,
      "Organization": 150,
      "Team": 100
    },
    "by_status": {
      "success_2xx": 1200,
      "redirect_3xx": 10,
      "client_error_4xx": 30,
      "server_error_5xx": 10
    }
  }
}
```

---

## 💬 Comments

| Method | Endpoint | Description |
|---------|-----------|-------------|


---


## 🧠 Notes
- All endpoints require JWT token (except register/login).
- Admin users have elevated access across org/projects.
- Pagination and filtering supported via DRF defaults.
- Activity logs are automatically tracked for all API requests.
- Sensitive data (passwords, tokens) is automatically redacted from logs.
- See [Activity Tracking Documentation](ACTIVITY_TRACKING.md) for detailed activity log information.
