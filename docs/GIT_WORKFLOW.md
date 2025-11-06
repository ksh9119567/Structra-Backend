# Git Workflow & Branching Model

This repository uses a **feature-branch workflow** with protected `main` and `develop` branches and PR-based merging. This guide defines how branches are created, how code moves through environments, and how releases are cut.

## Branches

- `main` — production-ready, tagged releases only.
- `develop` — integration branch for ongoing work (next release).

### Rules
- ❌ No direct pushes to `main` or `develop`.
- ✅ All work must be done in short-lived branches from `develop`.
- ✅ Every change lands via Pull Request (PR) with at least **1 reviewer**.

## Branch Types & Naming

Use lowercase, hyphen-separated names.

| Type | Prefix | Examples |
|------|--------|----------|
| Feature | `feature/` | `feature/task-crud-api`, `feature/jwt-blacklist` |
| Bug fix | `fix/` | `fix/login-refresh-expiry` |
| Hotfix (prod) | `hotfix/` | `hotfix/critical-auth-bug` |
| Release | `release/` | `release/v0.3.0` |
| Docs | `docs/` | `docs/update-readme` |
| Chore/DevOps | `chore/` | `chore/upgrade-deps` |

## Standard Flow

1. **Create**: `git checkout develop && git pull && git checkout -b feature/<name>`  
2. **Commit** using Conventional Commits (see CONTRIBUTING.md).  
3. **Push**: `git push -u origin feature/<name>`  
4. **Open PR** → base: `develop` → assign reviewer → fill checklist.  
5. **Review**: address comments → reviewer approves.  
6. **Merge**: **Squash merge** into `develop`. Delete branch.  
7. **Release**: when ready, cut a release branch:  
   ```bash
   git checkout develop
   git pull
   git checkout -b release/vX.Y.Z
   # stabilize (tests, docs)
   git checkout main && git merge --no-ff release/vX.Y.Z
   git tag vX.Y.Z
   git push --tags
   git checkout develop && git merge --no-ff release/vX.Y.Z
   ```

> CI should run tests/linters on PRs to `develop` and `main`.

## PR Quality Checklist (quick)
- [ ] Scope is focused (one feature/fix).
- [ ] Tests added/updated.
- [ ] Docs updated (README/SETUP/API docs).
- [ ] No commented debug code / prints.
- [ ] Secrets are not committed.
- [ ] Branch is up to date with `develop`.

## GitHub Branch Protection (recommended)

**Settings → Branches → Add rule**

- For `main` and `develop`:
  - Require PR before merging ✔
  - Require at least 1 reviewer ✔
  - Require status checks to pass (enable once CI exists) ✔
  - Restrict who can push ✔
  - (Optional) Require signed commits

## Versioning & Tags

Use semantic versioning: `vMAJOR.MINOR.PATCH` (e.g., `v0.3.0`).  
Tag only after merging release into `main`.

## Backports / Hotfixes

Urgent production fixes:
1. Create `hotfix/...` from `main`.
2. PR → base `main` → review → merge → tag patch release.
3. Merge `main` back into `develop` to keep history consistent.

## Helpful Commands

```bash
# Update local branches
git fetch --all --prune

# Rebase your feature branch to latest develop
git checkout feature/<name>
git fetch origin
git rebase origin/develop

# Resolve conflicts then push with --force-with-lease
git push --force-with-lease
```

See also: `CONTRIBUTING.md` for commit style and review expectations.
