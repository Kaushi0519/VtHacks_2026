INSTRUCTIONS FOR CLAUDE

## Git Workflow

4-person team, trunk-based with short-lived feature branches. No PRs, no branch protection.

**Branch off main, merge back same day:**
```bash
git checkout main && git pull
git checkout -b feat/your-feature
# ... work ...
git checkout main && git pull --rebase
git merge feat/your-feature
git push origin main
git branch -d feat/your-feature
```

**Rules:**
- Always `git pull --rebase` on main before merging
- Claim files/areas with teammates before starting to avoid conflicts
- Merge branches same-day, don't let them diverge
- Near demo time: freeze main, only team lead merges

## STACK

## PROJECT DETAILS/ARCHITECTURE