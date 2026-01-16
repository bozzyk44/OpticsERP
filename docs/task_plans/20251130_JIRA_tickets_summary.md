# JIRA Tickets Summary - Post-MVP Tasks

**Created**: 2025-11-30
**Status**: Ready for creation in JIRA
**Epic**: Post-MVP Deployment Preparation

---

## Overview

These three tasks represent critical post-MVP work required before production deployment:

1. **Russian UI Translation** - Localization for Russian-speaking users
2. **Installation User Guide** - Documentation for deployment
3. **CI/CD Deployment Plan** - Automated deployment pipeline

All task plans have been created in `docs/task_plans/` directory.

---

## JIRA Ticket 1: Перевод UI Odoo на русский язык (Russian UI Translation)

**Summary:** Перевод UI Odoo на русский язык (Russian UI Translation)

**Project:** OpticsERP (OPTERP)

**Issue Type:** Task

**Priority:** High

**Labels:** `post-mvp`, `localization`, `ui`, `pilot-prep`

**Description:**

```
## Objective

Translate all Odoo UI elements to Russian for better user experience in Russian-speaking optical retail locations.

## Acceptance Criteria

- [ ] All custom modules fully translated to Russian (optics_core, optics_pos_ru54fz, connector_b, ru_accounting_extras)
- [ ] Standard Odoo modules configured for Russian locale
- [ ] Date/time formats match Russian standards (dd.mm.yyyy, 24-hour time)
- [ ] Currency and number formatting configured for Russia (₽, space thousands separator, comma decimal)
- [ ] User testing confirms 100% Russian UI coverage
- [ ] POS interface fully operational in Russian
- [ ] All fiscal receipts and reports in Russian

## Task Plan

📄 `docs/task_plans/20251130_russian_ui_translation.md`

## Implementation Phases

**Phase 1: Setup and Base Translation (Week 1)**
- Install Russian language pack
- Configure regional settings (date/time/currency formats)
- Set up translation glossary

**Phase 2: Custom Modules Translation (Week 2)**
- Translate optics_core (prescription, lens, manufacturing terms)
- Translate optics_pos_ru54fz (POS, fiscal, 54-ФЗ terms)
- Translate connector_b (import/export terms)
- Translate ru_accounting_extras (accounting terms)

**Phase 3: POS Interface Translation (Week 2)**
- Translate all POS buttons and labels
- Translate payment flow
- Translate customer-facing receipts

**Phase 4: Reports Translation (Week 3)**
- Translate receipt templates
- Translate X/Z reports
- Translate manufacturing order labels

**Phase 5: Testing and Validation (Week 3)**
- UI walkthrough testing
- Format validation (dates, numbers, currency)
- User acceptance testing with cashiers

## Complexity

Medium (2-3 weeks effort)

## Dependencies

- ✅ MVP completion (all modules installed)
- ⏳ Native Russian speaker for translation
- ⏳ Optical retail terminology knowledge

## Deliverables

- [ ] All .po translation files created (`addons/*/i18n/ru_RU.po`)
- [ ] Translation glossary document
- [ ] Russian UI training materials
- [ ] User acceptance sign-off

## Success Metrics

- 100% of custom module strings translated
- 0 encoding errors
- ≥90% user satisfaction with Russian UI
- Training time reduced for Russian-only speakers

## Links

- Task Plan: docs/task_plans/20251130_russian_ui_translation.md
- Related Epic: Post-MVP Deployment Preparation
```

---

## JIRA Ticket 2: Installation User Guide

**Summary:** Create Installation User Guide

**Project:** OpticsERP (OPTERP)

**Issue Type:** Task

**Priority:** High

**Labels:** `post-mvp`, `documentation`, `deployment`, `pilot-prep`

**Description:**

```
## Objective

Create comprehensive installation and deployment documentation for OpticsERP system suitable for both technical staff and system administrators.

## Acceptance Criteria

- [ ] Complete installation guide for fresh deployment
- [ ] Upgrade guide for existing installations
- [ ] Troubleshooting section covers common issues
- [ ] Step-by-step instructions with screenshots
- [ ] Non-technical users can follow deployment process
- [ ] Technical validation by DevOps team

## Task Plan

📄 `docs/task_plans/20251130_installation_user_guide.md`

## Document Structure

### Main Sections (10 + 2 appendices):
1. Introduction (system overview, architecture, target audience)
2. System Requirements (hardware, software, network)
3. Pre-Installation (server prep, Docker install, firewall)
4. Installation Steps (clone repo, configure, deploy)
5. Post-Installation (health checks, smoke tests, security)
6. Configuration (Odoo, KKT Adapter, Redis, PostgreSQL)
7. Verification (service status, functional testing)
8. Troubleshooting (common issues, log locations, debug mode)
9. Upgrade Guide (backup, upgrade steps, rollback)
10. Appendices (ports, env vars, commands, SQL queries)

## Implementation Phases

**Phase 1: Requirements and Prerequisites (Week 1, Days 1-2)**
- Document system requirements (hardware, software, network)
- Create prerequisites checklist
- Write server preparation script

**Phase 2: Installation Steps Documentation (Week 1, Days 3-5)**
- Write step-by-step installation guide
- Create screenshot list and capture screenshots
- Write installation walkthrough

**Phase 3: Configuration Documentation (Week 2, Days 1-2)**
- Create .env file template with all variables
- Write configuration validation script
- Document all service configurations

**Phase 4: Troubleshooting Guide (Week 2, Days 3-4)**
- Create common issues table with solutions
- Document log locations
- Write debug mode guide

**Phase 5: Upgrade and Backup Procedures (Week 2, Day 5)**
- Write backup script
- Write restore script
- Write upgrade procedure

## Complexity

Medium (1-2 weeks effort)

## Dependencies

- ✅ MVP deployment complete (system running)
- ✅ All modules installed and working
- ⏳ Test environment for documentation validation
- ⏳ Screenshot tool

## Deliverables

### Documentation Files:
- [ ] docs/installation/00_README.md (overview)
- [ ] docs/installation/01_system_requirements.md
- [ ] docs/installation/02_installation_steps.md
- [ ] docs/installation/03_configuration.md
- [ ] docs/installation/04_verification.md
- [ ] docs/installation/05_troubleshooting.md
- [ ] docs/installation/06_upgrade_guide.md
- [ ] docs/installation/07_backup_restore.md
- [ ] docs/installation/appendix_a_ports.md
- [ ] docs/installation/appendix_b_env_vars.md

### Scripts:
- [ ] scripts/prep_server.sh (server preparation)
- [ ] scripts/validate_config.py (configuration validation)
- [ ] scripts/backup.sh (backup automation)
- [ ] scripts/restore.sh (restore automation)
- [ ] scripts/upgrade.sh (upgrade automation)
- [ ] scripts/health_check.sh (health verification)

### Templates:
- [ ] .env.example (environment configuration template)
- [ ] docker-compose.production.yml (production config)

## Success Metrics

- Non-technical user can deploy with guide only (<2 hours)
- Troubleshooting guide resolves ≥80% of common issues
- Backup/restore tested successfully
- Technical review passed (DevOps team)

## User Personas

**Primary:** System Administrator (5+ years Linux, familiar with Docker)
**Secondary:** IT Manager (2-3 years IT, basic Docker knowledge)
**Tertiary:** Business Owner (non-technical, single location deployment)

## Links

- Task Plan: docs/task_plans/20251130_installation_user_guide.md
- Related Epic: Post-MVP Deployment Preparation
```

---

## JIRA Ticket 3: CI/CD Deployment Plan

**Summary:** Implement CI/CD Deployment Pipeline

**Project:** OpticsERP (OPTERP)

**Issue Type:** Task

**Priority:** High

**Labels:** `post-mvp`, `cicd`, `devops`, `automation`, `production-prep`

**Description:**

```
## Objective

Design and implement CI/CD pipeline for OpticsERP to automate testing, building, and deployment across development, staging, and production environments.

## Acceptance Criteria

- [ ] Automated testing on every commit (unit, integration, UAT)
- [ ] Automated Docker image builds
- [ ] Deployment to staging on merge to main
- [ ] One-click production deployment with approval gates
- [ ] Rollback capability <5 minutes
- [ ] Zero-downtime deployments to production

## Task Plan

📄 `docs/task_plans/20251130_cicd_deployment_plan.md`

## Pipeline Architecture

### Stage 1: CI (Continuous Integration)
- Lint & style checks (flake8, black, isort)
- Unit tests (pytest with coverage ≥95%)
- Integration tests (Docker Compose test environment)
- UAT tests (full stack validation)

### Stage 2: Build & Push
- Build Docker images (Odoo, KKT Adapter)
- Tag images (version, SHA, branch)
- Push to container registry (GitHub Container Registry)
- Security scan (Trivy for vulnerabilities)

### Stage 3: Deploy to Staging
- Pull latest images
- Run database migrations
- Deploy with health checks
- Run smoke tests
- Slack/email notification

### Stage 4: Deploy to Production
- Manual approval required
- Backup database before deployment
- Zero-downtime deployment
- Health verification
- Automatic rollback on failure

## Implementation Phases

**Phase 1: CI Pipeline (Week 1)**
- Create GitHub Actions workflow for CI (lint, tests)
- Set up test Docker Compose environment
- Configure code coverage reporting (Codecov)
- Test CI pipeline with sample PRs

**Phase 2: Build & Push Pipeline (Week 1-2)**
- Create Docker build workflow
- Configure container registry (GitHub Container Registry)
- Add security scanning (Trivy)
- Tag and version images

**Phase 3: Staging Deployment (Week 2)**
- Create staging deployment workflow
- Configure SSH access to staging server
- Implement health checks and smoke tests
- Set up Slack notifications

**Phase 4: Production Deployment (Week 3)**
- Create production deployment workflow with approval gates
- Implement backup automation
- Write rollback script
- Test end-to-end deployment flow

## Complexity

High (2-3 weeks effort)

## Dependencies

- ✅ MVP deployment complete
- ✅ All tests automated (unit, integration, UAT)
- ⏳ Staging environment provisioned
- ⏳ Production environment provisioned
- ⏳ GitHub Actions enabled
- ⏳ Container registry configured

## Deliverables

### GitHub Actions Workflows:
- [ ] .github/workflows/ci.yml (lint, tests)
- [ ] .github/workflows/build.yml (Docker build & push)
- [ ] .github/workflows/deploy-staging.yml (staging auto-deploy)
- [ ] .github/workflows/deploy-production.yml (production manual deploy)

### Scripts:
- [ ] scripts/rollback.sh (production rollback)
- [ ] scripts/health_check.sh (post-deployment verification)
- [ ] scripts/db_migrate.sh (database migration)

### Configuration:
- [ ] docker-compose.test.yml (test environment)
- [ ] docker-compose.staging.yml (staging config)
- [ ] docker-compose.production.yml (production config)
- [ ] .github/CODEOWNERS (code ownership rules)

### Documentation:
- [ ] docs/cicd/00_README.md (CI/CD overview)
- [ ] docs/cicd/01_pipeline_design.md (architecture)
- [ ] docs/cicd/02_deployment_process.md (procedures)
- [ ] docs/cicd/03_rollback_procedures.md (rollback guide)
- [ ] docs/cicd/04_secrets_management.md (GitHub secrets)

## GitHub Secrets Required

### Repository Secrets:
- STAGING_SSH_KEY, STAGING_HOST, STAGING_USER, STAGING_URL
- PRODUCTION_SSH_KEY, PRODUCTION_HOST, PRODUCTION_USER, PRODUCTION_URL
- SLACK_WEBHOOK_URL, CODECOV_TOKEN

### Environment Secrets:
- Staging: DATABASE_URL, REDIS_URL, KKT_OFD_API_TOKEN (test)
- Production: DATABASE_URL, REDIS_URL, KKT_OFD_API_TOKEN (production)

## Success Metrics

**Performance:**
- CI pipeline completes in <10 minutes
- Build pipeline completes in <15 minutes
- Staging deployment completes in <10 minutes
- Production deployment completes in <15 minutes

**Reliability:**
- Deployment success rate ≥95%
- Zero failed rollbacks
- Mean time to deploy (MTTD) <30 minutes
- Mean time to recovery (MTTR) <5 minutes

**Quality:**
- Zero production incidents caused by deployment
- Test coverage maintained ≥95%
- Zero security vulnerabilities in production images
- 100% deployment documentation completeness

## Deployment Gates

**Staging:**
- ✅ All tests passed
- ✅ Docker image built successfully
- ✅ No critical security vulnerabilities
- ✅ Database migrations validated

**Production:**
- ✅ Staging successful for ≥24 hours
- ✅ Smoke tests passed in staging
- ✅ Manual approval from tech lead
- ✅ Backup completed successfully
- ✅ Rollback plan documented

## Links

- Task Plan: docs/task_plans/20251130_cicd_deployment_plan.md
- Related Epic: Post-MVP Deployment Preparation
```

---

## Creating Tickets in JIRA

### Manual Creation Instructions

1. **Navigate to JIRA:** https://bozzyk44.atlassian.net
2. **Click "Create"** button (+ icon in top navigation)
3. **Select Project:** OpticsERP (OPTERP)
4. **Issue Type:** Task
5. **Copy the description** from each ticket above
6. **Set Priority:** High
7. **Add Labels:** As specified for each ticket
8. **Create**

### Recommended Epic Structure

**Epic Name:** Post-MVP Deployment Preparation

**Epic Description:**
```
Prepare OpticsERP system for production deployment after MVP completion.

Includes:
- Russian UI localization (OPTERP-XX)
- Installation documentation (OPTERP-XX)
- CI/CD pipeline (OPTERP-XX)

Goal: Make system production-ready for pilot phase (20 locations, 40 POS terminals).
```

### Task Organization

**Sprint Planning:**
- Sprint 1 (Week 1-2): Russian UI Translation
- Sprint 2 (Week 2-3): Installation User Guide + CI/CD (parallel)
- Sprint 3 (Week 3-4): CI/CD completion + Integration testing

**Dependencies:**
```
MVP (OPTERP-62) → Post-MVP Epic
  ├── Russian UI Translation (2-3 weeks)
  ├── Installation User Guide (1-2 weeks)
  └── CI/CD Pipeline (2-3 weeks)
```

---

## API Creation Alternative (If Permissions Fixed)

If JIRA API permissions are granted, use the script:

```bash
# File: scripts/create_jira_tickets.sh
#!/bin/bash

source .env

# Ticket 1: Russian UI Translation
curl -X POST "https://bozzyk44.atlassian.net/rest/api/3/issue" \
  -H "Content-Type: application/json" \
  -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
  -d @jira_payloads/ticket1_russian_ui.json

# Ticket 2: Installation User Guide
curl -X POST "https://bozzyk44.atlassian.net/rest/api/3/issue" \
  -H "Content-Type: application/json" \
  -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
  -d @jira_payloads/ticket2_installation_guide.json

# Ticket 3: CI/CD Deployment Plan
curl -X POST "https://bozzyk44.atlassian.net/rest/api/3/issue" \
  -H "Content-Type: application/json" \
  -u "${JIRA_EMAIL}:${JIRA_API_TOKEN}" \
  -d @jira_payloads/ticket3_cicd_pipeline.json
```

---

## Next Actions

**Immediate:**
1. ✅ Task plans created (3/3)
2. ⏳ Create JIRA tickets manually (use descriptions above)
3. ⏳ Link tickets to Post-MVP Epic
4. ⏳ Assign priorities and sprint allocation

**After Ticket Creation:**
1. Update this document with JIRA ticket IDs (OPTERP-XX)
2. Commit all task plans to repository
3. Begin work on highest priority task

---

**Document Created**: 2025-11-30
**Status**: Ready for JIRA ticket creation
**Total Tasks**: 3
**Total Estimated Effort**: 5-8 weeks (if sequential), 3-4 weeks (if parallel)

---

🎯 **Recommendation:** Start with Russian UI Translation and Installation User Guide in parallel, then proceed with CI/CD pipeline once infrastructure is prepared.
