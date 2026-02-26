# Authentication Flow Documentation

## Overview

This document describes the authentication and authorization flow in the Task App. The system uses JWT (JSON Web Tokens) for stateless authentication combined with role-based access control (RBAC).

---

## 🔐 Authentication Methods

### 1. User Registration

**Endpoint**: `POST /api/v1/accounts/register/`

**Flow**:
1. User submits email, password, and optional name
2. System validates email uniqueness
3. Password is hashed securely
4. User account is created
5. JWT tokens (access + refresh) are generated and returned

---

### 2. User Login

**Endpoint**: `POST /api/v1/accounts/login/`

**Flow**:
1. User submits email and password
2. System validates credentials
3. If valid, JWT tokens are generated
4. Refresh token is stored for blacklist checking
5. Access token is returned to client

---

### 3. Token Refresh

**Endpoint**: `POST /api/v1/accounts/token/refresh/`

**Flow**:
1. Client sends refresh token
2. System validates token signature and expiry
3. Checks if token is blacklisted
4. If valid, new access token is generated
5. New access token is returned

---

### 4. User Logout

**Endpoint**: `POST /api/v1/accounts/logout/`

**Flow**:
1. Client sends refresh token
2. System validates token
3. Refresh token is added to blacklist
4. Session is terminated

---

## 🔑 JWT Token Structure

### Access Token
- **Expiry**: 15 minutes (configurable)
- **Purpose**: API request authentication
- **Header**: `Authorization: Bearer <access_token>`

### Refresh Token
- **Expiry**: 7 days (configurable)
- **Purpose**: Obtaining new access tokens
- **Storage**: Stored securely for blacklist checking

---

## 🔐 OTP-Based Authentication

### Generate OTP

**Endpoint**: `POST /api/v1/accounts/get-otp/`

**Flow**:
1. User requests OTP for email or phone
2. System generates OTP
3. OTP is sent via email or SMS
4. Response confirms OTP was sent

### Verify OTP

**Endpoint**: `POST /api/v1/accounts/verify-otp/`

**Flow**:
1. User submits OTP
2. System validates OTP
3. Marks email/phone as verified
4. Returns success message

---

## 🔄 Password Reset Flow

### Step 1: Request Password Reset

**Endpoint**: `POST /api/v1/accounts/forgot-password/request/`

**Flow**:
1. User submits email
2. System generates OTP
3. OTP is sent to email
4. Response confirms OTP was sent

### Step 2: Verify OTP for Password Reset

**Endpoint**: `POST /api/v1/accounts/forgot-password/verify/`

**Flow**:
1. User submits email and OTP
2. System validates OTP
3. Generates temporary reset token
4. Returns reset token to client

### Step 3: Reset Password

**Endpoint**: `PUT /api/v1/accounts/forgot-password/reset/`

**Flow**:
1. User submits reset token and new password
2. System validates reset token
3. Password is updated securely
4. Reset token is invalidated
5. User can now login with new password

---

## 🛡️ Authorization & Role-Based Access Control (RBAC)

### Role Hierarchy

**Organization Roles** (highest to lowest):
- OWNER
- ADMIN
- MANAGER
- MEMBER
- VIEWER

**Team Roles** (highest to lowest):
- OWNER
- MANAGER
- LEAD
- MEMBER
- VIEWER

**Project Roles** (highest to lowest):
- OWNER
- MANAGER
- LEAD
- CONTRIBUTOR
- VIEWER

### Permission Checking

**Flow**:
1. User makes API request with JWT token
2. System extracts user ID from token
3. Checks if user has required role in the resource
4. Compares role hierarchy against minimum required role
5. Grants or denies access

---

## � Membership & Invitation Flow

### Invite User to Organization

**Endpoint**: `POST /api/v1/organizations/sent-invite/`

**Flow**:
1. Authorized user sends invite
2. System generates invite token
3. Invite link is sent to user's email
4. User clicks link and accepts invite
5. User is added to organization with specified role

### Accept Invitation

**Endpoint**: `POST /api/v1/organizations/accept-org-invite/`

**Flow**:
1. User clicks invite link with token
2. System validates token
3. Adds user to organization membership
4. Invalidates token
5. User now has access to organization

---

## 🔒 Security Features

### Password Security
- Passwords hashed using secure algorithms
- Minimum password requirements enforced
- Password reset requires OTP verification

### Token Security
- JWT tokens signed with secure key
- Refresh tokens stored securely
- Tokens have expiry times
- Blacklist checking prevents token reuse after logout

### OTP Security
- OTP generated using secure random
- OTP expires after 5 minutes
- OTP can only be used once
- Rate limiting on OTP requests

### Soft Delete
- Deleted users cannot login
- Deleted users are filtered from all queries
- User data is preserved for audit purposes

### Activity Logging
- All authentication events logged
- Failed login attempts tracked
- Account deletion attempts logged
- Sensitive data redacted from logs

---

## � Error Handling

### Common Authentication Errors

| Status | Error | Cause |
|--------|-------|-------|
| 400 | Invalid credentials | Wrong email/password |
| 400 | User not found | Email doesn't exist |
| 400 | Account deleted | User is soft-deleted |
| 400 | Account inactive | User is inactive |
| 401 | Invalid token | Token expired or invalid |
| 401 | Token blacklisted | Token was logged out |
| 403 | Permission denied | User lacks required role |
| 429 | Too many requests | Rate limit exceeded |

---

## 📊 Authentication Flow Overview

```
Registration → Login → Token Generation → API Requests → Token Refresh → Logout
```

**Registration Flow**:
- Email validation → Password hashing → User creation → Token generation

**Login Flow**:
- Credential validation → Token generation → Token storage

**API Request Flow**:
- Token validation → User verification → Role checking → Request processing

**Logout Flow**:
- Token blacklisting → Session termination

---

## 📝 Configuration

### JWT Settings
- Access token lifetime: 15 minutes
- Refresh token lifetime: 7 days
- Algorithm: HS256

### OTP Settings
- OTP expiry: 5 minutes
- OTP length: 6 digits
- Max OTP attempts: 3

### Password Reset Settings
- Reset token expiry: 15 minutes
- Max reset attempts: 5

---

## 📚 Related Documentation

- [API Reference](API_REFERENCE.md) - Complete API endpoints
- [Activity Tracking](ACTIVITY_TRACKING.md) - Authentication event logging
- [Developer Guide](DEVELOPER_GUIDE.md) - Development setup and practices
