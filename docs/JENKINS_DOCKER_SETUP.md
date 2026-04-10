# Jenkins Docker Configuration Guide

## Problem
Jenkins pipeline fails with: `docker: command not found`

## Solution

The Jenkins process needs access to Docker. Follow these steps to configure Jenkins on macOS:

### 1. **Verify Docker Installation**
```bash
# Check if Docker is installed
docker --version

# Check if Docker daemon is running
docker info
```

### 2. **Add Jenkins User to Docker Group** (Linux only)
```bash
# For Linux systems:
sudo usermod -aG docker jenkins
sudo systemctl restart jenkins

# Verify Jenkins can access Docker:
sudo su - jenkins -s /bin/bash
docker ps
```

### 3. **On macOS Configuration**

#### Option A: Run Jenkins in Docker Container
This is recommended for macOS:

```bash
# Start Jenkins in Docker with Docker daemon access
docker run -d \
  --name jenkins \
  -p 8080:8080 \
  -p 50000:50000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v jenkins_home:/var/jenkins_home \
  --user root \
  jenkins/jenkins:latest
```

#### Option B: Install Docker CLI in Jenkins Container
If running Jenkins locally:

1. SSH into Jenkins host
2. Install Docker CLI:
```bash
# On macOS with Homebrew
brew install docker

# Or download Docker Desktop which includes Docker CLI
```

3. Ensure Docker daemon is accessible to Jenkins process

### 4. **Configure Jenkins Pipeline**

The updated Jenkinsfile now includes a `Prerequisites` stage that:
-  Checks if Docker command is available
-  Verifies Docker daemon is running
-  Provides clear error messages if either check fails

### 5. **Troubleshooting Checklist**

- [ ] Docker is installed (`docker --version` works)
- [ ] Docker daemon is running (`docker info` works)
- [ ] Jenkins process can access Docker socket/daemon
- [ ] Jenkins user is in docker group (Linux) or has proper permissions (macOS)
- [ ] Docker compose commands updated to use `docker compose` (v2.0+)

### 6. **Verify Setup**

Test Jenkins can run Docker:

```bash
# Manual test from Jenkins workspace
cd /Users/DELL/.jenkins/workspace/ZeroHum-Pipeline
docker ps
docker compose ps
```

### 7. **Common Issues**

| Issue | Solution |
|-------|----------|
| `docker: command not found` | Install Docker or add to PATH |
| `permission denied` | Add jenkins user to docker group and restart Jenkins |
| `Cannot connect to Docker daemon` | Start Docker daemon (`sudo systemctl start docker`) |
| `docker-compose: command not found` | Use `docker compose` instead (modern Docker v1.20+) |

## Docker Compose Version

The pipeline uses modern Docker Compose syntax:
- **Old**: `docker-compose build`
- **New**: `docker compose build`

Docker 1.20+ includes Compose as a native command. Both work identically, but the new syntax is preferred.

## Next Steps

1. Ensure Docker is properly configured on your Jenkins host
2. Run the pipeline again - the `Prerequisites` stage will verify everything
3. The pipeline will now fail fast with clear error messages if Docker is not available

## For More Information

- [Docker Installation Guide](https://docs.docker.com/get-docker/)
- [Jenkins Docker Plugin](https://plugins.jenkins.io/docker-plugin/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
