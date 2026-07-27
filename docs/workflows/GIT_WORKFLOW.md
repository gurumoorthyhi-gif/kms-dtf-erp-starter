# Git Workflow

## Start

```powershell
git status -sb
git remote -v
git fetch origin
```

Create `agent/<description>` when starting from the default branch. Continue the
existing feature branch when work is already grouped in an open draft PR.

## Before staging

```powershell
git diff --check
git diff --stat
git status --short
```

Confirm that no `.env`, OAuth token, Backblaze key, database, cache, artwork,
preview, upload, backup, or customer file is present.

## Validate

```powershell
python -m pytest
python -m ruff check .
python -m black --check .
python -m compileall -q app
```

Schema changes also require blank-database migration tests.

## Publish

Stage only the confirmed scope, commit with a concise behavior description, then:

```powershell
git push -u origin (git branch --show-current)
```

Open or update a draft pull request. Its description must explain behavior,
architecture/data impact, migrations, security implications, validation, and
remaining external setup.

Do not merge until manual ERP testing and cloud integration testing succeed.
