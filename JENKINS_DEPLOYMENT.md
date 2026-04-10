# Jenkins Deployment Guide - ZEROHUM-CHAOS

## 📋 Table of Contents
1. [Prerequisites](#prerequisites)
2. [Jenkins Setup](#jenkins-setup)
3. [Step-by-Step Configuration](#step-by-step-configuration)
4. [Pipeline Stages Explained](#pipeline-stages-explained)
5. [Troubleshooting](#troubleshooting)
6. [Post-Deployment Verification](#post-deployment-verification)

---

## Prerequisites

### Jenkins Server Requirements
- **OS**: Linux (Ubuntu 20.04+), macOS, or Windows with Docker
- **Jenkins Version**: 2.300+ 
- **Ram**: 4GB minimum, 8GB recommended
- **Disk Space**: 30GB minimum
- **Docker**: Version 20.10+
- **Docker Compose**: Version 1.29+

### Required Jenkins Plugins
Install these plugins in Jenkins (Manage Jenkins > Plugin Manager):

```
1. Pipeline
2. Docker Pipeline
3. Git
4. GitHub Integration
5. Slack Notification (optional, for alerts)
6. AnsiColor (for colored logs)
7. Blue Ocean (optional, for better UI)
```

**Installation Steps:**
1. Go to **Manage Jenkins** → **Manage Plugins**
2. Search for each plugin
3. Click "Install without restart"
4. Restart Jenkins after all plugins are installed

### System Configuration

**Ensure Jenkins user can run Docker:**

```bash
# On the Jenkins server/agent machine:
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
```

---

## Jenkins Setup

### Step 1: Configure Docker Credentials (Optional, if using registry)

1. Go to **Manage Jenkins** → **Manage Credentials**
2. Click **global** under Credentials
3. Click **Add Credentials**
4. Fill in:
   - **Kind**: Username with password
   - **Username**: Your Docker Hub username
   - **Password**: Your Docker Hub access token
   - **ID**: `docker-hub-credentials`
   - Click **Create**

### Step 2: Create a New Pipeline Job

1. **Click** "New Item" in Jenkins Dashboard
2. **Enter name**: `zerohum-chaos-pipeline`
3. **Select**: "Pipeline"
4. **Click** "OK"

### Step 3: Configure Git Repository

In the Pipeline job configuration:

1. **Go to** "Pipeline" section
2. **Definition**: Select "Pipeline script from SCM"
3. **SCM**: Select "Git"
4. **Repository URL**: `https://github.com/YOUR-USERNAME/DevOpsInProgress.git`
5. **Credentials**: Select your Git credentials
6. **Branch**: `*/main` (or your default branch)
7. **Script Path**: `Jenkinsfile`
8. Click **Save**

### Step 4: Configure Multibranch Pipeline (Advanced)

For automatic builds on multiple branches:

1. **Click** "New Item"
2. **Select**: "Multibranch Pipeline"
3. **Name**: `zerohum-chaos-multibranch`
4. **Branch Sources** → **Add source** → **Git**
5. **Project Repository**: `https://github.com/YOUR-USERNAME/DevOpsInProgress.git`
6. **Credentials**: Your Git credentials
7. Under **Discover branches**:
   - Select "All branches"
8. Click **Save**

This will automatically create separate pipelines for `main`, `develop`, and `staging` branches!

---

## Step-by-Step Configuration

### Complete Jenkins Job Setup

#### **Environment Variables Configuration**

In your Pipeline job, add global environment variables:

1. **Manage Jenkins** → **Configure System** → **Global properties**
2. Add:
   - `DOCKER_HOST`: `unix:///var/run/docker.sock` (if using Docker socket)
   - `PROJECT_PATH`: `/var/jenkins_home/workspace/zerohum-chaos-pipeline`

#### **Webhook Configuration** (Auto-trigger on Git Push)

For GitHub:

1. Go to your GitHub repository
2. **Settings** → **Webhooks** → **Add webhook**
3. **Payload URL**: `http://YOUR-JENKINS-URL/github-webhook/`
4. **Content type**: `application/json`
5. **Events**: Push events
6. Click **Add webhook**

Now every push to GitHub automatically triggers the pipeline!

#### **Build Triggers Configuration**

In your Jenkins Pipeline job:

1. **Configure** → Scroll to **Build Triggers**
2. Options:
   - ✅ **Poll SCM**: `H/15 * * * *` (check every 15 min)
   - ✅ **GitHub hook trigger**: (with webhook configured)
   - ✅ **Build periodically**: `H H * * *` (daily builds)

---

## Pipeline Stages Explained

### **Stage 1: Checkout**
- Clones latest code from Git
- Captures commit hash and branch name
- **Runs on**: All branches

### **Stage 2: Build**
- Builds Docker images from Dockerfile
- Tags them with commit hash
- **Output**: Local Docker images ready for deployment

### **Stage 3: Unit Tests**
- Runs Python tests on all services
- **Artifacts**: Test reports

### **Stage 4-6: Environment-Specific Deployments**
- **Dev (develop branch)**: Deploys immediately
- **Staging (staging branch)**: Requires manual approval
- **Production (main branch)**: Requires manual input approval

### **Stage 7: Health Checks**
- Verifies all containers are running
- Tests API endpoints
- Validates monitoring stack

### **Stage 8: Smoke Tests**
- Tests Prometheus metrics collection
- Verifies Docker networking
- Checks volume mounts

### **Stage 9: Cleanup**
- Runs only if deployment fails
- Saves logs for debugging
- Archives error artifacts

---

## Troubleshooting

### Issue 1: Jenkins can't connect to Docker

**Solution:**
```bash
# On Jenkins server/agent:
sudo usermod -aG docker jenkins
sudo chmod 666 /var/run/docker.sock
sudo systemctl restart jenkins
```

### Issue 2: Docker Compose not found

**Solution:**
```bash
# Verify Docker Compose is installed:
docker-compose --version

# If missing:
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### Issue 3: Port 5001, 5002, 8000 already in use

**Solution:**
```bash
# Kill existing containers:
docker-compose down

# Or change ports in docker-compose.yml:
# app-stable: "5011:5000" instead of "5001:5000"
```

### Issue 4: Pipeline fails at health checks

**Solution:**
```bash
# Check container logs:
docker-compose logs app-stable
docker-compose logs controller

# Verify networking:
docker network ls
docker network inspect zerohum-network
```

### Issue 5: Git authentication fails

**Solution:**
1. **Use SSH keys** instead of HTTP credentials:
   - Generate: `ssh-keygen -t ed25519 -C "jenkins"`
   - Add public key to GitHub Settings → Deploy Keys
   - Use SSH URL: `git@github.com:username/repo.git`

---

## Post-Deployment Verification

### Manual Verification Checklist

After deployment, verify everything:

```bash
# 1. Check container status
docker-compose ps

# 2. Test API endpoints
curl http://localhost:5001/health          # Stable app
curl http://localhost:5002/health          # Buggy app
curl http://localhost:8000                 # Dashboard

# 3. Check logs
docker-compose logs controller
docker-compose logs app-stable

# 4. Verify metrics
curl http://localhost:9090/api/v1/targets  # Prometheus targets

# 5. Check Docker network
docker network inspect zerohum-network
```

### Access Points After Deployment

| Service | URL | Purpose |
|---------|-----|---------|
| Dashboard | http://YOUR-SERVER:8000 | Main UI for testing |
| Prometheus | http://YOUR-SERVER:9090 | Metrics database |
| Grafana | http://YOUR-SERVER:3000 | Visualization (admin/admin) |
| Stable App | http://YOUR-SERVER:5001 | Production-like app |
| Buggy App | http://YOUR-SERVER:5002 | Test application |

---

## Advanced Configuration

### Multi-Agent Setup (Distributed Builds)

For large deployments across multiple servers:

1. **Manage Jenkins** → **Manage Nodes**
2. **New Node** → Configure SSH connection to deployment servers
3. In Jenkinsfile, specify:
   ```groovy
   agent {
       node {
           label 'docker-capable'
       }
   }
   ```

### Automated Rollback on Failure

Add to post-failure section in Jenkinsfile:

```groovy
failure {
    steps {
        sh '''
            echo "Rolling back to previous version..."
            docker-compose pull @previous
            docker-compose up -d
        '''
    }
}
```

### Slack Notifications

Add to Jenkinsfile post section:

```groovy
post {
    success {
        slackSend(
            color: 'good',
            message: "✅ Deployment successful: ${env.BUILD_URL}"
        )
    }
    failure {
        slackSend(
            color: 'danger',
            message: "❌ Deployment failed: ${env.BUILD_URL}"
        )
    }
}
```

---

## Quick Deploy Commands

Once Jenkins is configured, you can trigger deployments:

**Via CLI:**
```bash
# Trigger pipeline
curl -X POST http://JENKINS-URL/job/zerohum-chaos-pipeline/build \
  -u username:token

# Trigger with parameters
curl -X POST http://JENKINS-URL/job/zerohum-chaos-pipeline/buildWithParameters \
  -u username:token \
  -F ENVIRONMENT=production
```

**Via Web UI:**
1. Click job → Click "Build Now"
2. View build progress in real-time
3. Check console output for logs

---

## Success Criteria

Your deployment is successful when:

- ✅ All 7 containers are running
- ✅ All health checks pass
- ✅ Dashboard is accessible
- ✅ Prometheus collecting metrics
- ✅ Zero deployment errors in logs
- ✅ Smoke tests all pass

---

## Support & Debugging

**Enable debug mode in Jenkinsfile:**

```groovy
options {
    timestamps()
    ansiColor('xterm')  // For colored output
}
```

**View detailed logs:**
1. Jenkins UI → Click job → Click latest build
2. Click "Console Output"
3. Search for errors

**Collect diagnostic data:**
```bash
# On Jenkins server
docker ps -a
docker logs <container-id>
docker-compose logs --tail=100
```

---

**Next Steps:**
1. ✅ Install required Jenkins plugins
2. ✅ Create new Pipeline job
3. ✅ Configure Git repository
4. ✅ Run first build
5. ✅ Monitor deployment
6. ✅ Access dashboard at http://localhost:8000
