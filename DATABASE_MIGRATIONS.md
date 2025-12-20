# Database Migrations Guide

## Overview

Database migrations are **automatically applied** during deployment. The deployment script runs `alembic upgrade head` before starting the new container.

## Automatic Migrations (Production)

When you push to GitHub:
1. ✅ Code is built into Docker image
2. ✅ Image is pushed to GHCR
3. ✅ Deployment script pulls new image
4. ✅ **Migrations run automatically** (`alembic upgrade head`)
5. ✅ New container starts with updated schema

**No manual action needed!**

## Manual Migration (If Needed)

### On EC2 Instance

```bash
# SSH to EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# Run migrations manually
sudo /opt/ai-data-capture-api/scripts/run-migrations.sh

# Or specify a specific image
sudo /opt/ai-data-capture-api/scripts/run-migrations.sh ghcr.io/demola07/ai-data-capture-portal-api:latest
```

### Check Current Migration Version

```bash
# SSH to EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# Check current database version
docker run --rm \
  --env-file /opt/ai-data-capture-api/.env \
  ghcr.io/demola07/ai-data-capture-portal-api:latest \
  alembic current

# View migration history
docker run --rm \
  --env-file /opt/ai-data-capture-api/.env \
  ghcr.io/demola07/ai-data-capture-portal-api:latest \
  alembic history
```

## Creating New Migrations

### On Your Local Machine

```bash
# 1. Make changes to models in app/models.py

# 2. Generate migration
alembic revision --autogenerate -m "add password and role to counsellors"

# 3. Review generated migration in alembic/versions/
# Edit if needed

# 4. Test locally
alembic upgrade head

# 5. Commit and push
git add alembic/versions/*.py
git commit -m "feat: add counsellor authentication fields"
git push origin main
```

**The migration will automatically run on EC2 during deployment!**

## Migration Workflow

```
Local Development:
  1. Update models (app/models.py)
  2. Generate migration (alembic revision --autogenerate)
  3. Review/edit migration file
  4. Test locally (alembic upgrade head)
  5. Commit migration file
  6. Push to GitHub

GitHub Actions:
  1. Build Docker image (includes migration files)
  2. Push to GHCR
  3. Deploy to EC2

EC2 Deployment:
  1. Pull new image
  2. Run migrations (alembic upgrade head) ← AUTOMATIC
  3. Start new container
  4. Health check
  5. Swap containers
```

## Rollback Migrations

### Rollback One Version

```bash
# SSH to EC2
ssh -i your-key.pem ubuntu@your-ec2-ip

# Rollback one migration
docker run --rm \
  --env-file /opt/ai-data-capture-api/.env \
  ghcr.io/demola07/ai-data-capture-portal-api:latest \
  alembic downgrade -1
```

### Rollback to Specific Version

```bash
# Rollback to specific revision
docker run --rm \
  --env-file /opt/ai-data-capture-api/.env \
  ghcr.io/demola07/ai-data-capture-portal-api:latest \
  alembic downgrade <revision_id>
```

## Troubleshooting

### Migration Fails During Deployment

If migration fails, deployment stops automatically:

```bash
# Check deployment logs
ssh -i your-key.pem ubuntu@your-ec2-ip
sudo journalctl -u ai-data-capture-api -n 100

# Check migration error
docker logs ai-data-capture-api-app --tail 100
```

**Fix:**
1. Fix the migration locally
2. Test: `alembic upgrade head`
3. Commit and push
4. Deployment will retry with fixed migration

### Check Migration Status

```bash
# Current version
docker run --rm \
  --env-file /opt/ai-data-capture-api/.env \
  ghcr.io/demola07/ai-data-capture-portal-api:latest \
  alembic current

# Pending migrations
docker run --rm \
  --env-file /opt/ai-data-capture-api/.env \
  ghcr.io/demola07/ai-data-capture-portal-api:latest \
  alembic heads

# Show all migrations
docker run --rm \
  --env-file /opt/ai-data-capture-api/.env \
  ghcr.io/demola07/ai-data-capture-portal-api:latest \
  alembic history --verbose
```

### Database Connection Issues

```bash
# Test database connection
docker run --rm \
  --env-file /opt/ai-data-capture-api/.env \
  ghcr.io/demola07/ai-data-capture-portal-api:latest \
  python -c "from app.database import engine; engine.connect(); print('✅ Database connected')"
```

## Best Practices

### 1. Always Review Auto-Generated Migrations

```bash
# After generating migration
cat alembic/versions/XXXXX_your_migration.py

# Check for:
# - Correct table/column names
# - Proper data types
# - Missing indexes
# - Foreign key constraints
```

### 2. Test Migrations Locally First

```bash
# Test upgrade
alembic upgrade head

# Test downgrade
alembic downgrade -1

# Test upgrade again
alembic upgrade head
```

### 3. Backup Before Major Migrations

```bash
# On EC2, backup database before deployment
pg_dump -h $DB_HOST -U $DB_USER $DB_NAME > backup_$(date +%Y%m%d).sql

# Upload to S3
aws s3 cp backup_$(date +%Y%m%d).sql s3://your-backup-bucket/
```

### 4. Use Descriptive Migration Messages

```bash
# Good
alembic revision --autogenerate -m "add email verification fields to users"

# Bad
alembic revision --autogenerate -m "update db"
```

### 5. One Change Per Migration

Don't mix unrelated changes:
- ✅ One migration: Add user email verification
- ✅ Another migration: Add counsellor ratings
- ❌ One migration: Add email + ratings + delete old table

## Example: Adding New Field

### 1. Update Model

```python
# app/models.py
class Counsellor(Base):
    __tablename__ = "counsellors"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    # New field
    bio = Column(Text, nullable=True)  # ← Add this
```

### 2. Generate Migration

```bash
alembic revision --autogenerate -m "add bio field to counsellors"
```

### 3. Review Migration

```python
# alembic/versions/xxxxx_add_bio_field_to_counsellors.py
def upgrade():
    op.add_column('counsellors', sa.Column('bio', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('counsellors', 'bio')
```

### 4. Test Locally

```bash
# Apply migration
alembic upgrade head

# Check it worked
alembic current

# Test rollback
alembic downgrade -1

# Re-apply
alembic upgrade head
```

### 5. Deploy

```bash
git add alembic/versions/xxxxx_add_bio_field_to_counsellors.py
git commit -m "feat: add bio field to counsellor profiles"
git push origin main
```

**Migration runs automatically on EC2!**

## Current Migrations

Your existing migrations:
- ✅ `0578ecab030b_add_password_and_role_to_counsellors.py`

These will run automatically on first deployment.

## Safety Features

The deployment script:
1. ✅ Runs migrations **before** starting new container
2. ✅ Stops deployment if migration fails
3. ✅ Keeps old container running if migration fails
4. ✅ Only swaps to new container after successful migration
5. ✅ Logs all migration output

**Your database is safe!**
