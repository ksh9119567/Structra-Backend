# API Reference (v1)

Base URL: `/api/v1/`

---

## 🔐 Authentication

| Method | Endpoint | Description |
|---------|-----------|-------------|
| POST | `/api/accounts/register/` | Register new user |
| GET  | `/api/accounts/get-user/` | Return a particular user |
| POST | `/api/accounts/login/` | Login (JWT) |
| POST | `/api/accounts/logout/` | Logout and blacklist token |
| POST | `/api/accounts/token/refresh/` | Refresh access token |
| POST | `/api/accounts/otp/login/` | Generate & Send Login OTP on email or phone |
| POST | `/api/accounts/otp/email/` | Generate & Send Email Verification OTP |
| POST | `/api/accounts/otp/phone/` | Generate & Send Phone Verification OTP |
| POST | `/api/accounts/otp/verify/login/` | Verify Login OTP |
| POST | `/api/accounts/otp/verify/email/` | Verify Email Verification OTP |
| POST | `/api/accounts/otp/verify/phone/` | Verify Phone Verification OTP |
| POST | `/api/accounts/forgot-password/request/` | Generate & Send OTP on email or phone |
| POST | `/api/accounts/forgot-password/verify/` | Verify OTP and generate reset token |
| PUT  | `/api/accounts/forgot-password/reset/` | Verify reset token and update the password |


---

## 🧑‍💼 Organizations

| Method | Endpoint | Description |
|---------|-----------|-------------|
| GET  | `/api/organizations/get-org/` | Get list of all organizations user is member in |
| POST | `/api/organizations/create-org/` | Create a new organization |
| GET  | `/api/organizations/get-org-details/` | Get details of the organization |
| GET  | `/api/organizations/get-org-members/` | Get list of all members of organization |
| DELETE | `/api/organizations/self-remove-member/` | Remove yourself from organization |
| PUT  | `/api/organizations/update-org/` | Update details of organization |
| POST | `/api/organizations/sent-invite/` | Generate & sent a invite to user email |
| POST | `/api/organizations/add-org-member/` | Verify and add user to organization |
| PUT  | `/api/organizations/update-member/` | Update member role in organization |
| PUT  | `/api/organizations/update-owner/` | Transfer ownership of the organization |
| DELETE | `/api/organizations/remove-member/` | Remove a particular member from organization |
| DELETE | `/api/organizations/delete-org/` | Delete organization |


---

## 🧑‍💼 Teams

| Method | Endpoint | Description |
|---------|-----------|-------------|
| GET  | `/api/teams/get-user-teams/` | Get list of all team user is member in |
| POST | `/api/teams/create-team/` | Create a new team |
| GET  | `/api/teams/get-team-details/` | Get details of the team |
| GET  | `/api/teams/get-team-members/` | Get list of all members of team |
| DELETE | `/api/teams/self-remove-member/` | Remove yourself from team |
| PUT  | `/api/teams/update-team/` | Update details of team |
| POST | `/api/teams/sent-invite/` | Generate & sent a invite to user email |
| POST | `/api/teams/add-team-member/` | Verify and add user to team |
| PUT  | `/api/teams/update-member/` | Update member role in team |
| DELETE | `/api/teams/remove-member/` | Remove a particular member from team |
| DELETE | `/api/teams/delete-team/` | Delete team |
| PUT  | `/api/teams/transfer-manager/` | Transfer ownership of the team |


---

## 🧑‍💼 Projects

| Method | Endpoint | Description |
|---------|-----------|-------------|

---

## 📋 Tasks

| Method | Endpoint | Description |
|---------|-----------|-------------|

---

## 💬 Comments

| Method | Endpoint | Description |
|---------|-----------|-------------|

---

## 🧠 Notes
- All endpoints require JWT token (except register/login).
- Admin users have elevated access across org/projects.
- Pagination and filtering supported via DRF defaults.
