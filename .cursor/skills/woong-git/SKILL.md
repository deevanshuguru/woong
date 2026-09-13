---
name: woong-git
description: Run the Woong git and GitHub workflow. Use when creating an issue, branching, committing, opening a pull request, reviewing, or merging in this repository.
---

# Git and GitHub workflow

Full detail in [`docs/CONTRIBUTING.md`](../../../docs/CONTRIBUTING.md).

## Always first

```bash
git config user.name    # deevanshuguru
git config user.email   # deevanshu0@gmail.com
```

Never commit as any other account.

## The loop

```bash
gh issue create --title "..." --label ... --body "Why / Scope / Done when"
git checkout main && git pull origin main
git checkout -b feat/<short-description>
# one item only
pytest -q
git add <named files>
git commit -m "feat(scope): subject

Body: what changed and why it is safe.

Refs #<issue>

Co-authored-by: deevanshu-guru <deevanshuguru@gmail.com>"
git push -u origin feat/<short-description>
gh pr create --title "feat: ..." --body "Changed / Why / Verified / Closes #<issue>"
# review against the checklist, recorded as a pull request comment
gh pr merge <number> --squash --delete-branch
```

## Rules

- An issue exists before a branch. It states why, scope and done-when.
- Never commit to `main`.
- `git add` names files explicitly. Never `git add -A`.
- Conventional commit subjects under 72 characters. Scopes: `foundation`,
  `warehouse`, `ingest`, `metrics`, `engine`, `api`, `web`, `docs`, `ci`.
- Co-author trailer on every commit.
- Never commit `.env`, tokens, `data/` or logs.
- Never name a provider in a commit message or pull request body.
- Never attribute work to an assistant or a tool.
- Tests pass before the pull request is opened.
- The review checklist is applied in writing before merge.
