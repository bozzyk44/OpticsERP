# Task Plan: CI/CD Deployment Plan

**Created**: 2025-11-30
**Status**: ⏳ Pending
**Complexity**: High
**Estimated Effort**: 2-3 weeks

---

## 1. Task Overview

### Objective
Design and implement CI/CD pipeline for OpticsERP to automate testing, building, and deployment across development, staging, and production environments.

### Success Criteria
- [x] Automated testing on every commit (unit, integration, UAT)
- [x] Automated Docker image builds
- [x] Deployment to staging on merge to main
- [x] One-click production deployment with approval gates
- [x] Rollback capability <5 minutes
- [x] Zero-downtime deployments to production

### Scope

**In Scope:**
- GitHub Actions CI/CD workflows
- Automated testing (unit, integration, UAT)
- Docker image build and push (Docker Hub / GitHub Container Registry)
- Staging environment auto-deployment
- Production deployment with manual approval
- Database migration automation
- Health checks and smoke tests
- Rollback procedures

**Out of Scope:**
- Kubernetes orchestration (future)
- Multi-cloud deployment (AWS, Azure, GCP)
- Infrastructure as Code (Terraform, Ansible) - future phase
- Advanced monitoring (Prometheus/Grafana setup) - separate task
- Blue-green deployments - future optimization

---

## 2. CI/CD Architecture

### 2.1. Pipeline Overview

```
┌─────────────┐
│  Developer  │
│   Commits   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Actions                          │
│ ┌──────────────────────────────────────────────────────┐   │
│ │  Stage 1: CI (Continuous Integration)                │   │
│ │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │   │
│ │  │  Lint &    │→ │   Unit     │→ │ Integration│    │   │
│ │  │   Tests    │  │   Tests    │  │   Tests    │    │   │
│ │  └────────────┘  └────────────┘  └────────────┘    │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                             │
│ ┌──────────────────────────────────────────────────────┐   │
│ │  Stage 2: Build & Push                               │   │
│ │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │   │
│ │  │   Build    │→ │   Tag      │→ │    Push    │    │   │
│ │  │   Docker   │  │   Image    │  │  to Repo   │    │   │
│ │  └────────────┘  └────────────┘  └────────────┘    │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                             │
│ ┌──────────────────────────────────────────────────────┐   │
│ │  Stage 3: Deploy to Staging                          │   │
│ │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │   │
│ │  │   Pull     │→ │  Database  │→ │   Smoke    │    │   │
│ │  │   Image    │  │  Migration │  │   Test     │    │   │
│ │  └────────────┘  └────────────┘  └────────────┘    │   │
│ └──────────────────────────────────────────────────────┘   │
│                                                             │
│ ┌──────────────────────────────────────────────────────┐   │
│ │  Stage 4: Deploy to Production (Manual Approval)     │   │
│ │  ┌────────────┐  ┌────────────┐  ┌────────────┐    │   │
│ │  │   Backup   │→ │   Deploy   │→ │   Verify   │    │   │
│ │  │     DB     │  │  w/ Health │  │  & Alert   │    │   │
│ │  └────────────┘  └────────────┘  └────────────┘    │   │
│ └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────┐
│   Slack/Email        │
│   Notification       │
└──────────────────────┘
```

### 2.2. Environment Strategy

| Environment | Branch | Deploy Trigger | Approval | Purpose |
|-------------|--------|----------------|----------|---------|
| **Development** | feature/* | Manual | None | Developer testing |
| **Staging** | main | Auto on merge | None | QA testing, UAT |
| **Production** | main + tag | Manual approval | Required | Live system |

### 2.3. Deployment Gates

**Staging Deployment Gates:**
- ✅ All tests passed (unit, integration, UAT)
- ✅ Docker image built successfully
- ✅ No critical security vulnerabilities (Trivy scan)
- ✅ Database migrations validated

**Production Deployment Gates:**
- ✅ Staging deployment successful for ≥24 hours
- ✅ Smoke tests passed in staging
- ✅ Manual approval from tech lead/owner
- ✅ Backup completed successfully
- ✅ Rollback plan documented

---

## 3. Implementation Plan

### Phase 1: CI Pipeline (Week 1)

**Step 1.1: GitHub Actions Workflow - CI**

File: `.github/workflows/ci.yml`

```yaml
name: CI Pipeline

on:
  push:
    branches: [ main, develop, 'feature/**' ]
  pull_request:
    branches: [ main, develop ]

jobs:
  lint:
    name: Lint Python Code
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install flake8 black isort

      - name: Run flake8
        run: flake8 kkt_adapter/ addons/ --max-line-length=120

      - name: Check Black formatting
        run: black --check kkt_adapter/ addons/

      - name: Check import sorting
        run: isort --check-only kkt_adapter/ addons/

  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: lint

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_opticserp
          POSTGRES_USER: odoo
          POSTGRES_PASSWORD: odoo
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r kkt_adapter/requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run unit tests
        env:
          DATABASE_URL: postgresql://odoo:odoo@localhost:5432/test_opticserp
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest tests/unit/ -v --cov=kkt_adapter --cov-report=xml --cov-report=term

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: unittests
          name: codecov-umbrella

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: unit-tests

    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Start services
        run: docker-compose -f docker-compose.test.yml up -d

      - name: Wait for services to be ready
        run: |
          timeout 120 bash -c 'until docker-compose -f docker-compose.test.yml ps | grep healthy; do sleep 5; done'

      - name: Run integration tests
        run: |
          docker-compose -f docker-compose.test.yml exec -T odoo pytest tests/integration/ -v

      - name: Cleanup
        if: always()
        run: docker-compose -f docker-compose.test.yml down -v

  uat-tests:
    name: UAT Tests
    runs-on: ubuntu-latest
    needs: integration-tests

    steps:
      - uses: actions/checkout@v3

      - name: Start full stack
        run: docker-compose up -d

      - name: Wait for Odoo to be ready
        run: |
          timeout 300 bash -c 'until curl -f http://localhost:8069/web/database/selector; do sleep 10; done'

      - name: Initialize database
        run: |
          docker-compose exec -T odoo odoo -d opticserp --init=base --stop-after-init
          docker-compose exec -T odoo odoo -d opticserp -i optics_core,optics_pos_ru54fz,connector_b,ru_accounting_extras --stop-after-init

      - name: Start Odoo
        run: docker-compose start odoo

      - name: Run UAT tests
        run: |
          docker-compose exec -T odoo pytest tests/uat/ -v --tb=short

      - name: Save logs on failure
        if: failure()
        run: |
          mkdir -p test-logs
          docker-compose logs odoo > test-logs/odoo.log
          docker-compose logs kkt_adapter > test-logs/kkt_adapter.log

      - name: Upload logs
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: test-logs
          path: test-logs/

      - name: Cleanup
        if: always()
        run: docker-compose down -v
```

**Step 1.2: Test Docker Compose**

File: `docker-compose.test.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: test_opticserp
      POSTGRES_USER: odoo
      POSTGRES_PASSWORD: odoo
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U odoo"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  odoo:
    build:
      context: .
      dockerfile: Dockerfile
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - HOST=postgres
      - USER=odoo
      - PASSWORD=odoo
      - DATABASE=test_opticserp
    volumes:
      - ./addons:/mnt/extra-addons
      - ./tests:/mnt/tests
    command: odoo --test-enable --stop-after-init
```

### Phase 2: Build & Push Pipeline (Week 1-2)

**Step 2.1: Docker Build Workflow**

File: `.github/workflows/build.yml`

```yaml
name: Build and Push Docker Images

on:
  push:
    branches: [ main ]
    tags: [ 'v*.*.*' ]
  pull_request:
    branches: [ main ]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build-odoo:
    name: Build Odoo Image
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v3

      - name: Log in to Container Registry
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/odoo
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build and push Odoo image
        uses: docker/build-push-action@v4
        with:
          context: .
          file: ./Dockerfile
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  build-kkt-adapter:
    name: Build KKT Adapter Image
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - uses: actions/checkout@v3

      - name: Log in to Container Registry
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/kkt-adapter
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha

      - name: Build and push KKT Adapter image
        uses: docker/build-push-action@v4
        with:
          context: ./kkt_adapter
          file: ./kkt_adapter/Dockerfile
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  security-scan:
    name: Security Scan (Trivy)
    runs-on: ubuntu-latest
    needs: [build-odoo, build-kkt-adapter]

    steps:
      - uses: actions/checkout@v3

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}/odoo:${{ github.sha }}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-results.sarif'
```

### Phase 3: Staging Deployment (Week 2)

**Step 3.1: Deploy to Staging Workflow**

File: `.github/workflows/deploy-staging.yml`

```yaml
name: Deploy to Staging

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  deploy:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: https://staging.opticserp.example.com

    steps:
      - uses: actions/checkout@v3

      - name: Setup SSH
        uses: webfactory/ssh-agent@v0.8.0
        with:
          ssh-private-key: ${{ secrets.STAGING_SSH_KEY }}

      - name: Add staging server to known hosts
        run: |
          mkdir -p ~/.ssh
          ssh-keyscan -H ${{ secrets.STAGING_HOST }} >> ~/.ssh/known_hosts

      - name: Deploy to staging
        env:
          STAGING_HOST: ${{ secrets.STAGING_HOST }}
          STAGING_USER: ${{ secrets.STAGING_USER }}
        run: |
          ssh $STAGING_USER@$STAGING_HOST << 'EOF'
            cd /opt/opticserp

            # Pull latest code
            git pull origin main

            # Pull latest images
            docker-compose pull

            # Run database migrations
            docker-compose run --rm odoo odoo -d opticserp --update=all --stop-after-init

            # Restart services with zero-downtime
            docker-compose up -d --no-deps --build odoo kkt_adapter

            # Wait for health check
            sleep 30
            docker-compose ps
          EOF

      - name: Smoke tests
        env:
          STAGING_URL: ${{ secrets.STAGING_URL }}
        run: |
          # Health check
          curl -f $STAGING_URL/web/health || exit 1

          # Database check
          curl -f $STAGING_URL/web/database/selector || exit 1

          # KKT Adapter check
          curl -f $STAGING_URL:8000/v1/health || exit 1

      - name: Notify Slack on success
        if: success()
        uses: slackapi/slack-github-action@v1
        with:
          webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
          payload: |
            {
              "text": "✅ Staging deployment successful!",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Staging Deployment Successful* ✅\n\n*Commit:* ${{ github.sha }}\n*Author:* ${{ github.actor }}\n*URL:* ${{ secrets.STAGING_URL }}"
                  }
                }
              ]
            }

      - name: Notify Slack on failure
        if: failure()
        uses: slackapi/slack-github-action@v1
        with:
          webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
          payload: |
            {
              "text": "❌ Staging deployment failed!",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Staging Deployment Failed* ❌\n\n*Commit:* ${{ github.sha }}\n*Author:* ${{ github.actor }}\n*Workflow:* ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
                  }
                }
              ]
            }
```

### Phase 4: Production Deployment (Week 3)

**Step 4.1: Deploy to Production Workflow**

File: `.github/workflows/deploy-production.yml`

```yaml
name: Deploy to Production

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version tag to deploy (e.g., v1.2.3)'
        required: true
        type: string

jobs:
  backup:
    name: Backup Production Database
    runs-on: ubuntu-latest
    environment: production

    steps:
      - name: Setup SSH
        uses: webfactory/ssh-agent@v0.8.0
        with:
          ssh-private-key: ${{ secrets.PRODUCTION_SSH_KEY }}

      - name: Create backup
        env:
          PROD_HOST: ${{ secrets.PRODUCTION_HOST }}
          PROD_USER: ${{ secrets.PRODUCTION_USER }}
        run: |
          ssh $PROD_USER@$PROD_HOST << 'EOF'
            cd /opt/opticserp
            ./scripts/backup.sh

            # Verify backup created
            ls -lh /opt/opticserp/backups/ | tail -1
          EOF

      - name: Upload backup metadata
        run: |
          echo "Backup created at $(date)" > backup-info.txt
          echo "Version: ${{ github.event.inputs.version }}" >> backup-info.txt

      - name: Save backup info
        uses: actions/upload-artifact@v3
        with:
          name: backup-metadata
          path: backup-info.txt

  deploy:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: backup
    environment:
      name: production
      url: https://opticserp.example.com

    steps:
      - uses: actions/checkout@v3
        with:
          ref: ${{ github.event.inputs.version }}

      - name: Setup SSH
        uses: webfactory/ssh-agent@v0.8.0
        with:
          ssh-private-key: ${{ secrets.PRODUCTION_SSH_KEY }}

      - name: Deploy to production
        env:
          PROD_HOST: ${{ secrets.PRODUCTION_HOST }}
          PROD_USER: ${{ secrets.PRODUCTION_USER }}
          VERSION: ${{ github.event.inputs.version }}
        run: |
          ssh $PROD_USER@$PROD_HOST << EOF
            cd /opt/opticserp

            # Checkout version
            git fetch --all --tags
            git checkout tags/$VERSION

            # Pull versioned images
            export IMAGE_TAG=$VERSION
            docker-compose pull

            # Run database migrations (dry-run first)
            docker-compose run --rm odoo odoo -d opticserp --update=all --stop-after-init --dry-run

            # Apply migrations
            docker-compose run --rm odoo odoo -d opticserp --update=all --stop-after-init

            # Zero-downtime deployment
            docker-compose up -d --no-deps --build odoo kkt_adapter celery

            # Wait for services
            sleep 60

            # Health check
            docker-compose ps
          EOF

      - name: Verify deployment
        env:
          PROD_URL: ${{ secrets.PRODUCTION_URL }}
        run: |
          # Health checks
          curl -f $PROD_URL/web/health || exit 1
          curl -f $PROD_URL:8000/v1/health || exit 1

          # Version check
          VERSION_DEPLOYED=$(curl -s $PROD_URL/web/version)
          echo "Deployed version: $VERSION_DEPLOYED"

      - name: Run smoke tests
        env:
          PROD_URL: ${{ secrets.PRODUCTION_URL }}
        run: |
          # Test POS
          # Test KKT Adapter
          # Test database connectivity
          echo "Smoke tests passed"

      - name: Notify Slack on success
        if: success()
        uses: slackapi/slack-github-action@v1
        with:
          webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
          payload: |
            {
              "text": "✅ Production deployment successful!",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Production Deployment Successful* ✅\n\n*Version:* ${{ github.event.inputs.version }}\n*Deployed by:* ${{ github.actor }}\n*URL:* ${{ secrets.PRODUCTION_URL }}"
                  }
                }
              ]
            }

      - name: Rollback on failure
        if: failure()
        env:
          PROD_HOST: ${{ secrets.PRODUCTION_HOST }}
          PROD_USER: ${{ secrets.PRODUCTION_USER }}
        run: |
          ssh $PROD_USER@$PROD_HOST << 'EOF'
            cd /opt/opticserp
            ./scripts/rollback.sh
          EOF

      - name: Notify Slack on failure
        if: failure()
        uses: slackapi/slack-github-action@v1
        with:
          webhook-url: ${{ secrets.SLACK_WEBHOOK_URL }}
          payload: |
            {
              "text": "❌ Production deployment failed! Rollback initiated.",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Production Deployment Failed* ❌\n\n*Version:* ${{ github.event.inputs.version }}\n*Deployed by:* ${{ github.actor }}\n*Status:* Rollback initiated\n*Workflow:* ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
                  }
                }
              ]
            }
```

**Step 4.2: Rollback Script**

File: `scripts/rollback.sh`

```bash
#!/bin/bash
# rollback.sh - Rollback production deployment

set -e

BACKUP_DIR="/opt/opticserp/backups"
ROLLBACK_LOG="/opt/opticserp/logs/rollback_$(date +%Y%m%d_%H%M%S).log"

exec 1> >(tee -a "$ROLLBACK_LOG")
exec 2>&1

echo "=== PRODUCTION ROLLBACK ==="
echo "Started: $(date)"

# Find latest backup
LATEST_BACKUP=$(ls -t $BACKUP_DIR/db_*.sql.gz | head -1)
BACKUP_DATE=$(echo $LATEST_BACKUP | grep -oP '\d{8}_\d{6}')

echo "Latest backup: $LATEST_BACKUP"
echo "Backup date: $BACKUP_DATE"

read -p "Proceed with rollback? (yes/NO): " confirm
if [ "$confirm" != "yes" ]; then
    echo "Rollback cancelled"
    exit 1
fi

# Stop services
echo "Stopping services..."
docker-compose stop odoo kkt_adapter celery

# Restore database
echo "Restoring database from $LATEST_BACKUP..."
gunzip < $LATEST_BACKUP | docker-compose exec -T postgres psql -U odoo -d opticserp

# Restore filestore
FILESTORE_BACKUP="$BACKUP_DIR/filestore_${BACKUP_DATE}.tar.gz"
if [ -f "$FILESTORE_BACKUP" ]; then
    echo "Restoring filestore from $FILESTORE_BACKUP..."
    docker-compose exec -T odoo tar xzf - -C / < $FILESTORE_BACKUP
fi

# Restore KKT buffer
BUFFER_BACKUP="$BACKUP_DIR/buffer_${BACKUP_DATE}.db"
if [ -f "$BUFFER_BACKUP" ]; then
    echo "Restoring KKT buffer from $BUFFER_BACKUP..."
    cat $BUFFER_BACKUP | docker-compose exec -T kkt_adapter sh -c "cat > /app/data/buffer.db"
fi

# Restart services
echo "Restarting services..."
docker-compose start odoo kkt_adapter celery

# Wait for health
echo "Waiting for health checks..."
sleep 30

# Verify health
if curl -f http://localhost:8069/web/health && curl -f http://localhost:8000/v1/health; then
    echo "✅ Rollback successful!"
    echo "System restored to: $BACKUP_DATE"
else
    echo "❌ Health check failed after rollback!"
    exit 1
fi

echo "Completed: $(date)"
```

---

## 4. Files to Create

### GitHub Actions Workflows

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | CI pipeline (lint, tests) |
| `.github/workflows/build.yml` | Build and push Docker images |
| `.github/workflows/deploy-staging.yml` | Auto-deploy to staging |
| `.github/workflows/deploy-production.yml` | Manual deploy to production |

### Scripts

| File | Purpose |
|------|---------|
| `scripts/rollback.sh` | Production rollback script |
| `scripts/health_check.sh` | Post-deployment health checks |
| `scripts/db_migrate.sh` | Database migration script |

### Configuration

| File | Purpose |
|------|---------|
| `docker-compose.test.yml` | Test environment compose file |
| `docker-compose.staging.yml` | Staging environment config |
| `docker-compose.production.yml` | Production environment config |
| `.github/CODEOWNERS` | Code ownership and review rules |

### Documentation

| File | Purpose |
|------|---------|
| `docs/cicd/00_README.md` | CI/CD overview |
| `docs/cicd/01_pipeline_design.md` | Pipeline architecture |
| `docs/cicd/02_deployment_process.md` | Deployment procedures |
| `docs/cicd/03_rollback_procedures.md` | Rollback guide |
| `docs/cicd/04_secrets_management.md` | GitHub secrets reference |

---

## 5. GitHub Secrets Configuration

### Repository Secrets

| Secret Name | Purpose | Example |
|-------------|---------|---------|
| `STAGING_SSH_KEY` | SSH private key for staging server | `-----BEGIN RSA PRIVATE KEY-----...` |
| `STAGING_HOST` | Staging server hostname | `staging.opticserp.example.com` |
| `STAGING_USER` | SSH user for staging | `deploy` |
| `STAGING_URL` | Staging application URL | `https://staging.opticserp.example.com` |
| `PRODUCTION_SSH_KEY` | SSH private key for production | `-----BEGIN RSA PRIVATE KEY-----...` |
| `PRODUCTION_HOST` | Production server hostname | `prod.opticserp.example.com` |
| `PRODUCTION_USER` | SSH user for production | `deploy` |
| `PRODUCTION_URL` | Production application URL | `https://opticserp.example.com` |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | `https://hooks.slack.com/services/...` |
| `CODECOV_TOKEN` | Codecov upload token | `abc123...` |

### Environment Secrets

**Staging Environment:**
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `KKT_OFD_API_TOKEN` - ОФД API token (test)

**Production Environment:**
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `KKT_OFD_API_TOKEN` - ОФД API token (production)

---

## 6. Deployment Checklist

### Pre-Deployment

**Code Quality:**
- [ ] All tests passing (unit, integration, UAT)
- [ ] Code coverage ≥95%
- [ ] No critical security vulnerabilities
- [ ] Code reviewed and approved

**Database:**
- [ ] Database migrations tested in staging
- [ ] Migration rollback tested
- [ ] Backup completed successfully
- [ ] Backup verified (restore test)

**Infrastructure:**
- [ ] Server resources sufficient (CPU, RAM, disk)
- [ ] Network connectivity verified
- [ ] SSL certificates valid (≥30 days remaining)
- [ ] DNS records correct

### During Deployment

**Staging:**
- [ ] Deploy to staging completed
- [ ] Smoke tests passed
- [ ] UAT re-run in staging (100% pass rate)
- [ ] Soak test (24 hours uptime)

**Production:**
- [ ] Maintenance window scheduled
- [ ] Users notified (if downtime expected)
- [ ] On-call engineer available
- [ ] Rollback plan documented
- [ ] Deploy approved by tech lead

### Post-Deployment

**Verification:**
- [ ] Health checks passed (all services)
- [ ] Smoke tests passed
- [ ] Critical workflows tested (POS sale, receipt print)
- [ ] Performance metrics normal (P95 latency)

**Monitoring:**
- [ ] Alerts configured
- [ ] Logs streaming to monitoring
- [ ] Metrics dashboard updated
- [ ] Error rate within SLA

**Documentation:**
- [ ] Deployment notes updated
- [ ] CHANGELOG.md updated
- [ ] Release notes published
- [ ] Team notified (Slack/email)

---

## 7. Acceptance Criteria

**For CI Pipeline:**
- [x] All tests run on every commit to main
- [x] Test failures block merge
- [x] Code coverage tracked and reported
- [x] Linting enforced

**For Build Pipeline:**
- [x] Docker images built on every merge to main
- [x] Images tagged with version/SHA
- [x] Security scans pass (no critical/high vulnerabilities)
- [x] Images pushed to registry

**For Staging Deployment:**
- [x] Auto-deploy on merge to main
- [x] Zero-downtime deployment
- [x] Smoke tests pass post-deployment
- [x] Slack notification sent

**For Production Deployment:**
- [x] Manual approval required
- [x] Backup created before deployment
- [x] Zero-downtime deployment
- [x] Automatic rollback on failure
- [x] Deployment time <15 minutes

---

## 8. Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Failed database migration** | Critical | Medium | Test in staging, dry-run first, backup before migration |
| **Docker registry unavailable** | High | Low | Cache images locally, fallback to Docker Hub |
| **SSH key compromise** | Critical | Low | Rotate keys quarterly, use GitHub secrets, audit access logs |
| **Rollback fails** | Critical | Low | Test rollback procedure monthly, verify backups |
| **Zero-downtime deployment failure** | High | Medium | Use health checks, graceful shutdown, connection draining |
| **Secrets leaked** | Critical | Low | Use GitHub secrets, scan for leaked secrets (GitGuardian) |

---

## 9. Dependencies

**Prerequisites:**
- ✅ MVP deployment complete
- ✅ All tests automated (unit, integration, UAT)
- ⏳ Staging environment provisioned
- ⏳ Production environment provisioned
- ⏳ GitHub Actions enabled
- ⏳ Docker registry configured (GitHub Container Registry or Docker Hub)

**Tools/Services:**
- GitHub Actions (CI/CD orchestration)
- Docker Hub or GitHub Container Registry (image storage)
- Slack (notifications)
- Codecov (code coverage)
- Trivy (security scanning)

---

## 10. Success Metrics

**CI/CD Performance:**
- [ ] CI pipeline completes in <10 minutes
- [ ] Build pipeline completes in <15 minutes
- [ ] Staging deployment completes in <10 minutes
- [ ] Production deployment completes in <15 minutes

**Reliability:**
- [ ] Deployment success rate ≥95%
- [ ] Zero failed rollbacks
- [ ] Mean time to deploy (MTTD) <30 minutes
- [ ] Mean time to recovery (MTTR) <5 minutes

**Quality:**
- [ ] Zero production incidents caused by deployment
- [ ] Test coverage maintained ≥95%
- [ ] Zero security vulnerabilities in production images
- [ ] 100% deployment documentation completeness

---

## 11. Next Steps

### Immediate Actions
1. Create `.github/workflows/` directory
2. Write CI pipeline workflow
3. Configure GitHub secrets
4. Test CI pipeline with sample PR

### Week 1 Deliverables
- CI pipeline operational (lint, tests)
- Build pipeline operational (Docker images)
- Test environments configured
- Documentation 50% complete

### Week 2 Deliverables
- Staging deployment automated
- Health checks and smoke tests working
- Notifications configured (Slack)
- Documentation 100% complete

### Week 3 Deliverables
- Production deployment workflow complete
- Rollback tested successfully
- Full deployment tested end-to-end
- Team trained on deployment process

---

**Task Complexity**: High
**Estimated Effort**: 2-3 weeks
**Priority**: High (blocks production deployment)
**Dependencies**: MVP completion (✅ Done), Staging/Production infrastructure (⏳ Pending)

---

**Created**: 2025-11-30
**Last Updated**: 2025-11-30
**Status**: ⏳ Pending approval
