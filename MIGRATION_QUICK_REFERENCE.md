# Flask-Migrate Quick Reference

## 🚀 Quick Start (For Existing Database)

```bash
# One-time setup for existing database
python migrate_to_alembic.py
```

## 📝 Common Commands

### Make Changes & Generate Migration
```bash
# 1. Edit your models in models/*.py
# 2. Generate migration
flask db migrate -m "Add user preferences table"

# 3. Review the generated file in migrations/versions/
# 4. Apply the migration
flask db upgrade
```

### Check Status
```bash
flask db current    # Show current version
flask db history    # Show all migrations
```

### Rollback
```bash
flask db downgrade  # Go back one version
```

## 🔧 Helper Scripts

```bash
# Interactive migration manager
python manage_migrations.py create   # Create new migration
python manage_migrations.py apply    # Apply migrations
python manage_migrations.py history  # View history
```

## ⚠️ Important Notes

1. **Always review generated migrations** before applying
2. **PostgreSQL enums** may need manual tweaking
3. **Test on development first**
4. **Migrations run automatically on startup**

## 🆘 Troubleshooting

### "Target database is not up to date"
```bash
flask db stamp head  # Mark as current
flask db upgrade     # Apply pending
```

### Migration conflicts after git pull
```bash
flask db merge -m "Merge migrations"  # Resolve conflicts
```

## 📁 Structure
```
migrations/
├── versions/        # Your migration files
├── alembic.ini     # Config (don't edit)
└── README.md       # Detailed docs
```

## 🔄 Workflow

1. `git pull` → `flask db upgrade` → Make changes
2. `flask db migrate -m "..."` → Review → Test
3. `git add migrations/versions/*.py` → Commit → Push

---
See `FLASK_MIGRATE_GUIDE.md` for detailed documentation.