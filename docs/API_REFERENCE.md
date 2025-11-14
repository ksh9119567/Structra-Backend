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
| POST | `otp/login/` | Generate & Send Login OTP on email or phone |
| POST | `otp/email/` | Generate & Send Email Verification OTP |
| POST | `otp/phone/` | Generate & Send Phone Verification OTP |
| POST | `otp/verify/login/` | Verify Login OTP |
| POST | `otp/verify/email/` | Verify Email Verification OTP |
| POST | `otp/verify/phone/` | Verify Phone Verification OTP |
| POST | `forgot-password/request/` | Generate & Send OTP on email or phone |
| POST | `forgot-password/verify/` | Verify OTP and generate reset token |
| PUT  | `forgot-password/reset/` | Verify reset token and update the password |


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
