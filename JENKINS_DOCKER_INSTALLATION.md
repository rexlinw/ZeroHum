# Jenkins Docker Installation Guide

## Quick Fix: Install Docker on macOS

If your Jenkins pipeline fails at the **Prerequisites** stage with `docker: command not found`, follow these steps.

---

## Option 1: Docker Desktop (Recommended) ⭐

### Installation
```bash
# Using Homebrew (easiest)
brew install --cask docker

# Or visit: https://www.docker.com/products/docker-desktop
```

### First Run
1. Open **Applications** → double-click **Docker.app**
2. Enter your macOS password when prompted
3. Wait for Docker icon to appear in menu bar (top-right)

### Verify Installation
```bash
docker ps
docker --version
```

---

## Option 2: Lightweight Docker with Colima

For resource-constrained systems:

```bash
# Install Docker CLI + Colima VM
brew install docker colima

# Start Colima daemon
colima start

# Verify
docker ps
```

---

## Option 3: Jenkins in Docker Container (Best for CI/CD)

Run Jenkins itself as a container - no additional host setup needed:

```bash
# Create persistent volume
docker volume create jenkins_home

# Run Jenkins with Docker daemon access
docker run -d \
  --name jenkins \
  -p 8080:8080 \
  -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --user root \
  jenkins/jenkins:lts

# Watch startup logs
docker logs -f jenkins

# Get admin password (displayed in logs after ~30 seconds)
docker logs jenkins 2>&1 | grep -A 5 "Please use the following password"
```

Access Jenkins at: `http://localhost:8080`

---

## Verify Docker Works with Jenkins

### If Jenkins is running locally:
```bash
# Test Docker command directly
docker ps

# Test docker compose
docker compose --version
```

### If Jenkins is running in container:
```bash
# Test from inside Jenkins container
docker exec jenkins docker ps
docker exec jenkins docker compose --version
```

---

## After Installation: Re-run Pipeline

1. **Restart Jenkins** (if running locally):
   ```bash
   brew services restart jenkins-lts
   ```

2. **Go to Jenkins** → Click **ZeroHum-Pipeline** → **Build Now**

3. **Monitor Output** - should now see:
   ```
   ✅ Docker found: Docker version XX.X.X
   ✅ Docker daemon is accessible
   ```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `docker: command not found` | Install Docker (see options above) |
| `Cannot connect to Docker daemon` | Start Docker: `docker run hello-world` or open Docker Desktop |
| Permission denied | Linux only: `sudo usermod -aG docker $USER && newgrp docker` |
| Port 8080 already in use | Change Jenkins port: `-p 9090:8080` |

---

## Next Steps

Once Docker is installed and working:

1. ✅ Prerequisites stage passes
2. 🏗️ Build stage builds all Docker images
3. 🧪 Unit Tests run in containers
4. 🚀 Deploy stages start services
5. 🩺 Health checks verify everything
6. ✅ Pipeline completes successfully

Your Jenkins pipeline is now ready to build and deploy the ZeroHum chaos engineering platform!
