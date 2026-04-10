# Jenkins Deployment - Quick Start Guide

## 🚀 5-Minute Setup

This guide gets your ZEROHUM-CHAOS project deployed in Jenkins in 5 minutes.

---

## Step 1: Verify Prerequisites (1 minute)

```bash
cd /Users/DELL/Documents/Projects/Zerohum/DevOpsInProgress

# Run prerequisite check
./jenkins-deploy.sh check-prerequisites
```

Expected output: All tools installed ✅

---

## Step 2: Install Jenkins (If not already installed)

### Option A: Docker (Fastest)

```bash
# Pull Jenkins image
docker pull jenkins/jenkins:lts-jdk11

# Run Jenkins container
docker run -d \
  --name jenkins \
  -p 8080:8080 \
  -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  jenkins/jenkins:lts-jdk11

# Get initial admin password
docker logs jenkins 2>&1 | grep -A 5 "Jenkins initial setup is required"
```

### Option B: Direct Installation (macOS)

```bash
# Install Jenkins via Homebrew
brew install jenkins-lts

# Start Jenkins
brew services start jenkins-lts

# Jenkins will be available at http://localhost:8080
```

### Option C: Linux (Ubuntu)

```bash
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io.key | sudo tee /usr/share/keyrings/jenkins-keyring.asc > /dev/null
echo deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/ | sudo tee /etc/apt/sources.list.d/jenkins.list > /dev/null
sudo apt-get update
sudo apt-get install jenkins
sudo systemctl start jenkins
```

---

## Step 3: Configure Jenkins (2 minutes)

### 3.1 Access Jenkins Dashboard

1. Open: **http://localhost:8080**
2. Enter the initial admin password from logs
3. **Skip plugin suggestions** or use default plugins

### 3.2 Create Admin User

1. Click **Create First Admin User**
2. Fill in credentials:
   - **Username**: `admin`
   - **Password**: Your strong password
   - **Full name**: Jenkins Admin
3. Click **Save and Continue**
4. Click **Save and Finish**

### 3.3 Install Required Plugins

1. Click **Manage Jenkins** → **Manage Plugins**
2. Go to **Available** tab
3. Search and install:
   - `Pipeline`
   - `Docker Pipeline`
   - `Git`
   - `GitHub Integration`
   - `AnsiColor`
4. Click **Install without restart**
5. Wait for installation
6. Check **Restart Jenkins when installation is complete**

### 3.4 Configure Docker Socket Access

```bash
# If running Jenkins as Docker container:
docker exec jenkins sudo usermod -aG docker jenkins

# If running Jenkins locally:
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins
```

---

## Step 4: Create Jenkins Pipeline Job (1 minute)

### Method A: Using Web UI (Recommended for First Time)

1. **Jenkins Dashboard** → Click **New Item**
2. **Item name**: `zerohum-chaos-pipeline`
3. **Select**: `Pipeline`
4. Click **OK**
5. Scroll to **Pipeline** section
6. **Definition**: Select `Pipeline script from SCM`
7. **SCM**: Select `Git`
8. **Repository URL**: 
   ```
   https://github.com/YOUR-USERNAME/DevOpsInProgress.git
   ```
9. **Credentials**: Add your GitHub credentials
10. **Branch**: `*/main`
11. **Script Path**: `Jenkinsfile`
12. Click **Save**

### Method B: Using Pipeline Script (Inline)

1. **Jenkins Dashboard** → Click **New Item**
2. **Item name**: `zerohum-chaos-local`
3. **Select**: `Pipeline`
4. Click **OK**
5. **Pipeline** section:
   - **Definition**: `Pipeline script`
   - **Script**: Paste contents of your Jenkinsfile
6. Click **Save**

### Method C: Multibranch Pipeline (Advanced)

Auto-creates jobs for each branch:

1. **New Item** → `Multibranch Pipeline`
2. **Name**: `zerohum-chaos-multibranch`
3. **Branch Sources** → **Add source** → **Git**
4. **Repository**: `https://github.com/YOUR-USERNAME/...`
5. Under **Discover branches**: Select `All branches`
6. Click **Save**

---

## Step 5: Run Your First Deployment (1 minute)

### Via Web UI

1. Go to your pipeline job: `zerohum-chaos-pipeline`
2. Click **Build Now**
3. Check the progress:
   - Click on the build number (e.g., #1)
   - Click **Console Output**
   - Watch the build progress in real-time

### Via Command Line

```bash
# Trigger build (requires API token)
curl -X POST http://localhost:8080/job/zerohum-chaos-pipeline/build \
  -u admin:YOUR_API_TOKEN

# Get API token:
# Jenkins → Your User Profile → Configure → API Token
```

### Using Our Helper Script

```bash
# Check current deployment status
./jenkins-deploy.sh status

# Perform health checks
./jenkins-deploy.sh health-check

# View service URLs
./jenkins-deploy.sh urls
```

---

## 📊 What Happens During Pipeline Execution

The Jenkinsfile will execute these stages:

| Stage | Duration | What it Does |
|-------|----------|-------------|
| **Checkout** | 5s | Pulls latest code from Git |
| **Build** | 30s | Builds Docker images |
| **Unit Tests** | 20s | Runs tests on all services |
| **Deploy** | 10s | Starts containers (branch-specific) |
| **Health Checks** | 10s | Verifies all services are running |
| **Smoke Tests** | 5s | Tests critical functionality |

**Total Time**: ~80 seconds for first run, ~60 seconds for subsequent runs

---

## 🔍 Monitoring Your Deployment

After deployment, access these services:

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| Dashboard | http://localhost:8000 | No login |
| Prometheus | http://localhost:9090 | No login |
| Grafana | http://localhost:3000 | admin / admin |
| Stable App | http://localhost:5001 | N/A |
| Buggy App | http://localhost:5002 | N/A |

---

## ✅ Success Checklist

After running the pipeline, verify:

- [ ] Pipeline completed successfully (green build)
- [ ] All 7 containers are running: `./jenkins-deploy.sh status`
- [ ] Dashboard is accessible: http://localhost:8000
- [ ] Prometheus has metrics: http://localhost:9090
- [ ] No errors in console output
- [ ] Health checks all pass: `./jenkins-deploy.sh health-check`

---

## 🐛 Troubleshooting

### Pipeline fails at "Build" stage

**Problem**: Docker images won't build

**Solution**:
```bash
# Check Docker daemon
docker ps

# Check Jenkins Docker access
docker exec jenkins docker ps

# Give Jenkins permission
docker exec jenkins sudo usermod -aG docker jenkins
docker restart jenkins
```

### Port already in use

**Error**: `bind: address already in use`

**Solution**:
```bash
# Stop existing containers
./jenkins-deploy.sh stop

# Or change ports in docker-compose.yml
```

### Git connection fails

**Error**: `Failed to connect to repository`

**Solution**:
1. Use SSH instead of HTTPS for Git
2. Add Jenkins SSH key to GitHub:
   - Generate: `ssh-keygen -t ed25519`
   - Add to GitHub → Settings → Deploy Keys
3. Use SSH URL: `git@github.com:username/repo.git`

### Services not responding to health checks

**Error**: `curl: (7) Failed to connect; Connection refused`

**Solution**:
```bash
# Wait longer for services to start
sleep 30

# Check logs
./jenkins-deploy.sh logs controller

# Restart services
./jenkins-deploy.sh restart
```

---

## 🔐 Security Recommendations

1. **Change default Grafana password**:
   ```
   Grafana (3000) → Admin → Change Password
   ```

2. **Set up Jenkins security**:
   - Manage Jenkins → Configure Global Security
   - Enable CSRF protection
   - Set authorization strategy

3. **Use secrets for credentials**:
   - Store Docker Hub tokens in Jenkins Credentials store
   - Never commit secrets to Git

4. **Set up HTTPS**:
   - Use reverse proxy (nginx) to add SSL/TLS
   - Or use Jenkins behind a load balancer

---

## 📚 Next Steps

1. **Enable Git webhook** for automatic builds on push:
   - GitHub → Settings → Webhooks
   - Add: `http://YOUR-JENKINS-URL/github-webhook/`

2. **Set up email notifications**:
   - Manage Jenkins → Configure System
   - Set email configuration

3. **Configure multibranch pipeline**:
   - Separate pipelines for `main`, `develop`, `staging`

4. **Add build approval gates**:
   - Manual approval before production deployment

5. **Integrate with monitoring/alerting**:
   - Send alerts to Slack
   - Create Grafana dashboards

---

## 📖 Complete Documentation

For detailed information, see:
- **[JENKINS_DEPLOYMENT.md](JENKINS_DEPLOYMENT.md)** - Complete setup guide
- **[Jenkinsfile](Jenkinsfile)** - Pipeline definition
- **[README.md](README.md)** - Project overview
- **[QUICKSTART.md](QUICKSTART.md)** - Basic project usage

---

## 🆘 Need Help?

### Check logs

```bash
# Jenkins logs
docker logs jenkins  # if using Docker
journalctl -u jenkins  # if using systemd
tail -f ~/.jenkins/jobs/zerohum-chaos-pipeline/builds/1/log  # Build logs

# Application logs
./jenkins-deploy.sh logs controller
./jenkins-deploy.sh logs app-stable
./jenkins-deploy.sh logs app-buggy
```

### Run diagnostic commands

```bash
./jenkins-deploy.sh validate        # Validate environment
./jenkins-deploy.sh health-check    # Check all services
./jenkins-deploy.sh status          # Show deployment status
```

### Check Docker connectivity

```bash
docker ps                           # Verify Docker works
docker-compose ps                   # Check containers
docker network inspect zerohum-network  # Check networking
```

---

**Ready to deploy? Start with Step 1 above and you'll have a working CI/CD pipeline in minutes! 🚀**
