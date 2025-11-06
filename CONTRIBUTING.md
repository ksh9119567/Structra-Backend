# Contributing Guidelines

Thank you for your interest in contributing to this project!  
This document outlines the workflow, branching strategy, pull request rules, code review standards, and commit conventions we follow to maintain a clean and professional codebase.

---

## 🧠 Branching Strategy (Git Workflow)

We follow a **Git Feature-Branch Workflow** with `main` and `develop` as primary branches:

| Branch | Purpose |
|--------|-----------|
| `main` | Production-ready code only. Contains stable releases. |
| `develop` | Active development branch. All features merge here before release. |

### 📌 Rules
- Do **NOT** push directly to `main` or `develop`
- All work must happen in feature branches created from `develop`
- Every merge into `develop` or `main` must happen via a Pull Request (PR)

---

## 🌿 Branch Types & Naming Convention

Use lowercase + hyphens. Prefix branch names to indicate purpose.

| Type | Prefix | Example |
|--------|-----------|----------|
| Feature | `feature/` | `feature/user-auth-api` |
| Bug Fix | `fix/` | `fix/login-token-expiry` |
| Hotfix (urgent prod fix) | `hotfix/` | `hotfix/admin-crash` |
| Release | `release/` | `release/v0.2.0` |
| Documentation | `docs/` | `docs/api-reference` |
| DevOps | `chore/` | `chore/docker-optimizations` |

### ✅ How to create a feature branch
```bash
git checkout develop
git pull
git checkout -b feature/<short-description>
```

---

## ✅ Development Workflow

### 1. Create a feature/bug branch from `develop`
```bash
git checkout develop
git pull
git checkout -b feature/task-crud-api
```

### 2. Commit frequently with clear messages
Follow commit rules (below).

### 3. Push to remote
```bash
git push -u origin feature/task-crud-api
```

### 4. Create Pull Request (PR)
Target branch must be `develop`.

### 5. Review Process
- Assign at least **1 reviewer** (peer review required)
- Reviewer requests changes or approves
- Once approved, squash and merge into `develop`
- Delete branch after merge

### 6. Release Process
- When features are tested and ready for deployment:
  1. Create release branch from `develop`
  2. Test & UAT on release branch
  3. Merge `release/...` into `main` and tag version
  4. Merge back into `develop` to sync

```bash
git checkout develop
git checkout -b release/v0.3.0
```

---

## 🧪 Code Quality Standards

Before creating a PR, ensure:

- Code is formatted (Black/Prettier if enabled)
- No commented-out code left behind
- No console/debug prints
- Tests written (if applicable)
- Code documentation updated

### Python standards:
- Follow PEP8
- Use docstrings for functions, classes, and APIs

---

## ✍️ Commit Message Guidelines

We use a structured commit format (Conventional Commits):

```
<type>(optional-scope): <short summary>

[optional body]
```

| Type | Use For |
|--------|----------|
| feat | New feature |
| fix | Bug fix |
| docs | Documentation updates |
| refactor | Code restructuring (no behavior change) |
| style | Formatting, missing semicolons, etc. |
| test | Adding or updating tests |
| chore | CI/CD, tooling, minor tasks |

Examples:
```
feat(tasks): add task assignment API
fix(auth): refresh token not stored in redis
docs: update setup instructions for windows users
chore: upgrade dependencies
```

---

## 🔒 GitHub Branch Protection Rules (Setup)

To enforce workflow:
1. Go to GitHub Repo → **Settings → Branches**
2. Add rule for `main`:
   - ✅ Require Pull Request before merging
   - ✅ Require at least 1 reviewer approval
   - ✅ Require status checks to pass (enable once tests exist)
   - ✅ Prevent direct pushes
   - ✅ Prevent branch deletion
3. Add rule for `develop`:
   - ✅ Require PR before merging
   - ✅ Require at least 1 reviewer approval
   - 🚫 Direct push not allowed

Optional (Recommended as project grows):
- Enable CI workflow checks (tests + lint)

---

## 🤝 Code Review Expectations

Reviewer should verify:
- Code quality & readability
- Architecture & folder structure standards
- No secrets committed
- Unit tests included (if required)
- No breaking changes without discussion

Reviewer can request changes. Author must address comments before approval.

---

## 📦 After Merge

- Delete feature branch after merge (GitHub button)
- Pull latest `develop` frequently to avoid conflicts

```bash
git checkout develop
git pull
```

---

## 🐞 Reporting Issues

Use GitHub Issues and include:
- Summary
- Steps to reproduce
- Expected vs actual behavior
- Screenshots / logs if useful

---

## 🙌 Contributions Philosophy

- Small PRs are better than large ones
- Keep scope focused—1 feature per PR
- Communicate early to avoid duplicated work

---

Thank you for helping maintain a clean and professional codebase!
