# Git Workflow

```powershell
git checkout main
git pull origin main
git status
git checkout -b feature/task-name
```

After implementation:

```powershell
pytest
ruff check .
black --check .
git add .
git commit -m "feat: describe completed task"
git push -u origin feature/task-name
```
