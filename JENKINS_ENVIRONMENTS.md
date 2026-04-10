# Jenkins Environment-Specific Deployment Configuration

## Overview

This guide explains how to configure Jenkins for different deployment environments (Dev, Staging, Production) with the ZEROHUM-CHAOS project.

---

## Three-Environment Setup

```
Development  →  Staging  →  Production
(develop)      (staging)    (main)
Auto Deploy    Manual Approval  Gated Approval
```

---

## Environment Configuration

### Development Environment

**Branch**: `develop`
**Behavior**: Auto-deploys on every commit
**Approval**: None required

**Configuration in Jenkins**:

```groovy
// In Jenkinsfile, this stage runs automatically:
stage('Deploy - Dev') {
    when {
        branch 'develop'
    }
    steps {
        sh 'docker-compose down || true'
        sh 'docker-compose up -d'
        sh 'sleep 30'
        sh './jenkins-deploy.sh health-check'
    }
}
```

**To test**:
```bash
git checkout develop
git commit --allow-empty -m "Test dev deployment"
git push origin develop
# Pipeline automatically triggers and deploys
```

### Staging Environment

**Branch**: `staging`
**Behavior**: Deploys but requires manual input
**Approval**: Manual approval via Jenkins UI

**Configuration in Jenkins**:

```groovy
stage('Deploy - Staging') {
    when {
        branch 'staging'
    }
    input 'Deploy to Staging? (Click Proceed to continue)'
    steps {
        sh '''
            echo "Deploying to staging..."
            docker-compose down || true
            docker-compose up -d
        '''
    }
}
```

**To deploy to staging**:

1. Create staging branch:
   ```bash
   git checkout -b staging
   git push origin staging
   ```

2. In Jenkins:
   - Pipeline detects staging branch
   - Builds and tests
   - Waits at "Deploy - Staging" stage
   - Click **Proceed** in browser to deploy

### Production Environment

**Branch**: `main`
**Behavior**: Requires explicit approval + input
**Approval**: GitHub branch protection + Jenkins input

**Configuration in Jenkins**:

```groovy
stage('Deploy - Production') {
    when {
        branch 'main'
    }
    input 'PRODUCTION DEPLOYMENT: Are you absolutely sure? (Irreversible)'
    steps {
        sh '''
            BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
            mkdir -p $BACKUP_DIR
            docker-compose logs > $BACKUP_DIR/docker-compose.log || true
            
            docker-compose down || true
            docker-compose up -d
            sleep 30
        '''
    }
}
```

**To deploy to production**:

1. Merge to main (via Pull Request):
   ```bash
   git checkout main
   git pull origin main
   git merge develop
   git push origin main
   ```

2. GitHub branch protection rules prevent direct push
3. In Jenkins:
   - Build & test runs
   - Waits at production approval gate
   - **REQUIRES EXPLICIT APPROVAL** (high barrier)

---

## Environment-Specific Variables

### Set Environment Variables Per Job

In Jenkins Pipeline job configuration:

```groovy
withEnv([
    'ENVIRONMENT=development',
    'LOG_LEVEL=DEBUG',
    'METRICS_RETENTION=30d'
]) {
    // Stage execution here
}
```

### Alternative: Jenkins Credentials

Store environment-specific secrets:

1. **Manage Jenkins** → **Manage Credentials** → **global** → **Add Credentials**
2. Fill in for each environment:
   - **Kind**: Secret text
   - **Secret**: Your secret value
   - **ID**: `prod-db-password` (for example)
3. In Jenkinsfile:
   ```groovy
   environment {
       DB_PASSWORD = credentials('prod-db-password')
   }
   ```

---

## Deployment Workflow Example

### Development Workflow (Continuous)

```
Developer pushes code → Jenkins detects change → 
Build & Test autorun → Deploy to Dev automatically → 
Tests run → Feedback in <2 minutes
```

**Time to feedback**: ~2 minutes

### Staging Workflow (Gated)

```
Release manager merges to staging → Jenkins builds & tests →
Pipeline waits at approval → Manual review of test results →
Click "Proceed" in Jenkins → Deploy to staging → 
Full integration tests → Ready for QA
```

**Time to staging**: ~5 minutes + human review

### Production Workflow (Highly Gated)

```
Staging validated → PR created from staging → 
Code review & approval needed → Merged to main →
Jenkins builds & tests → Double confirmation required →
Manual prod approval + timestamp → Deploy to production →
Post-deployment monitoring
```

**Time to production**: ~30 minutes + approvals (safety first!)

---

## Scheduled Deployments

### Daily Production Deployment Window

```groovy
// Only allow production deployments during business hours
stage('Deploy - Production') {
    when {
        branch 'main'
        allOf {
            expression { Calendar.getInstance().get(Calendar.HOUR_OF_DAY) >= 9 }
            expression { Calendar.getInstance().get(Calendar.HOUR_OF_DAY) < 17 }
            expression { Calendar.getInstance().get(Calendar.DAY_OF_WEEK) != Calendar.SUNDAY }
            expression { Calendar.getInstance().get(Calendar.DAY_OF_WEEK) != Calendar.SATURDAY }
        }
    }
    // Deploy steps
}
```

### Weekly Release Schedule

```bash
# Schedule via Jenkins UI:
# Manage Jenkins → Configure System → Global properties
# Or use cron: H H(9-17) * * 1 (Mondays 9am-5pm)
```

---

## Health Checks Per Environment

### Development Health Checks

```bash
# Quick checks, fail fast
curl http://localhost:5001/health
curl http://localhost:5002/health
```

### Staging Health Checks

```bash
# More thorough checks
curl -f http://localhost:5001/health
curl -f http://localhost:5002/health
curl -f http://localhost:8000

# Check metrics collection
curl http://localhost:9090/api/v1/query?query=up

# Run synthetic tests
docker-compose exec app-stable python tests/smoke_test.py
```

### Production Health Checks

```bash
# Extensive validation
curl -f http://localhost:5001/health || rollback
curl -f http://localhost:5002/health || rollback
curl -f http://localhost:8000 || rollback
curl -f http://localhost:9090/-/healthy || rollback

# Check database connectivity
docker-compose exec controller python tests/db_connectivity.py || rollback

# Validate data integrity
docker-compose exec controller python tests/data_validation.py || rollback

# Performance baseline checks
docker-compose exec cAdvisor curl http://localhost:8080/metrics || rollback
```

---

## Rollback Procedures

### Automatic Rollback on Failure

```groovy
post {
    failure {
        stage('Rollback') {
            when { branch 'main' }
            steps {
                sh '''
                    echo "DEPLOYMENT FAILED - ROLLING BACK"
                    docker-compose down
                    
                    # Use the backup from before deployment
                    LATEST_BACKUP=$(ls -t backups | head -1)
                    docker load < backups/$LATEST_BACKUP/images.tar
                    
                    docker-compose up -d
                '''
                slackSend(
                    color: 'danger',
                    message: "⚠️ Production deployment failed and rolled back"
                )
            }
        }
    }
}
```

### Manual Rollback via CLI

```bash
# List available backups
ls -la backups/

# Restore specific backup
docker-compose down
docker load < backups/20260410_120000/images.tar
docker-compose up -d

# Verify rollback
./jenkins-deploy.sh health-check
```

---

## Monitoring Deployments

### Real-Time Deployment Monitoring

**During deployment**, monitor in Jenkins:

1. Click build → **Console Output**
2. Search for progress (Ctrl+F):
   - "Building" = images being built
   - "Deploying" = containers starting
   - "Health checks" = validation in progress
   - "SUCCESS" = deployment complete

### Post-Deployment Monitoring

Monitor in real-time:

```bash
# Terminal 1: Watch logs
docker-compose logs -f controller

# Terminal 2: Monitor metrics
watch -n 1 'curl -s http://localhost:9090/api/v1/query?query=up | jq'

# Terminal 3: Dashboard
open http://localhost:8000
```

---

## Approval Gates Configuration

### Manual Approval in Jenkins

Configure in Jenkinsfile:

```groovy
stage('Approval') {
    when { branch 'main' }
    steps {
        script {
            def userInput = input(
                id: 'UserInput',
                message: 'Deploy to Production?',
                parameters: [
                    [$class: 'BooleanParameterDefinition',
                     defaultValue: false,
                     description: 'Check to proceed',
                     name: 'APPROVE']
                ]
            )
            if (!userInput) {
                error("Deployment cancelled by user")
            }
        }
    }
}
```

### Slack-Based Approval

```groovy
// Requires Slack plugin
stage('Slack Approval') {
    steps {
        slackSend(
            channel: '#devops-approvals',
            message: 'Production deployment ready. Approve: http://jenkins.example.com/job/...',
            attachments: [[
                text: 'Click button to approve',
                actions: [[
                    type: 'button',
                    text: 'APPROVE PRODUCTION',
                    url: 'http://jenkins.example.com/...'
                ]]
            ]]
        )
    }
}
```

---

## Email Notifications

### Deployment Success

```groovy
post {
    success {
        emailext(
            subject: "✅ Deployment Successful: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            body: """
                Project: ${env.JOB_NAME}
                Build Number: ${env.BUILD_NUMBER}
                Build Status: SUCCESS
                Environment: main (Production)
                
                View details: ${env.BUILD_URL}
            """,
            to: 'devops-team@example.com'
        )
    }
}
```

### Deployment Failure

```groovy
post {
    failure {
        emailext(
            subject: "❌ Deployment Failed: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
            body: """
                Project: ${env.JOB_NAME}
                Build Number: ${env.BUILD_NUMBER}
                Build Status: FAILURE
                
                Error Details: ${env.BUILD_LOG_EXCERPT}
                
                View logs: ${env.BUILD_URL}console
            """,
            to: 'devops-team@example.com',
            attachmentPattern: 'build_logs.txt'
        )
    }
}
```

---

## Summary: Branch-Based Deployment

| Branch | Environment | Trigger | Approval | Risk Level |
|--------|-------------|---------|----------|-----------|
| develop | Development | Auto on commit | ❌ None | 🟢 Low |
| staging | Staging | Auto on commit | ✅ Manual | 🟡 Medium |
| main | Production | Auto on commit | ✅✅ Explicit + Input | 🔴 High |

---

## Quick Reference Commands

```bash
# Trigger specific branch deployment
git checkout develop && git push  # Auto-deploys to dev

git checkout staging && git push  # Auto-builds, manual approval to deploy

git checkout main && git push     # Auto-builds, high-barrier production approval
```

---

Next: See [JENKINS_DEPLOYMENT.md](JENKINS_DEPLOYMENT.md) for complete deployment guide.
