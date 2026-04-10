# ZEROHUM-CHAOS Quick Start Guide

## What is ZEROHUM-CHAOS?

ZEROHUM-CHAOS is a **completely autonomous self-healing DevOps system** that:
-  Injects controlled failures (chaos engineering)
-  Detects failures automatically
-  Recovers without human intervention
-  Logs everything for analysis
-  Provides a web dashboard for testing

**The complete system is containerized and runs locally.**

---

## System Requirements

- **Docker** & **Docker Compose** installed
- **4GB RAM** minimum
- **20GB disk space** for images
- **Linux, macOS, or Windows (with WSL2)**

---

## Quick Start (3 Minutes)

### Step 1: Navigate to Project

```bash
cd zerohum-chaos
```

### Step 2: Start All Services

```bash
docker-compose up -d
```

This starts:
-  Stable & Buggy Applications
-  Prometheus (metrics collection)
-  Grafana (visualization)
-  cAdvisor (container metrics)
-  Dashboard (web UI)

### Step 3: Wait for Services (30 seconds)

```bash
# Check status
docker-compose ps

# All should show "Up"
```

### Step 4: Open Dashboard

Visit: **http://localhost:8000**

---

## Running Your First Test

### Option 1: Web Dashboard (Recommended)

1. Go to http://localhost:8000
2. Click "Run Reliability Test"
3. Select scenario: "Default: Container Crash & Recovery"
4. Click "Run Reliability Test"
5. Watch the test run in real-time!

### Option 2: Command Line

```bash
# Check all services are running
curl http://localhost:5001/health      # Should return 200 OK
curl http://localhost:3000/api/health  # Grafana ready

# View controller logs
docker-compose logs -f controller

# Manually trigger chaos
docker exec chaos python3 chaos_engine/chaos.py
```

---

## Understanding the Test Output

When you run a test, you'll see logs like:

```
=== ZEROHUM-CHAOS Test Started ===
Scenario: default
Timestamp: 2026-01-06T10:30:00

--- Phase 1: Baseline Health Check ---
Checking stable application health...
Stable app health: healthy

--- Phase 2: Injecting Chaos ---
Stopping app-stable container to simulate failure...
Chaos injected: Container stopped

--- Phase 3: Failure Detection ---
Monitoring system detects container is down...
Detection result - Status: degraded, Severity: high

--- Phase 4: Autonomous Decision Making ---
Controller decision: RESTART
Reason: Health check failure rate is 100%. Attempting restart.

--- Phase 5: Autonomous Recovery ---
Executing recovery action: restart...
Recovery result: Container restart successful
Duration: 2.34 seconds

--- Phase 6: Verification ---
Verifying system recovery...
Final status: healthy
 System successfully recovered!

=== Test Completed: PASSED ===
```

---

## Key Components Explained

###  Dashboard (Port 8000)

**What**: Web interface for running tests
**Access**: http://localhost:8000
**Features**:
- One-click test execution
- Real-time log streaming
- Results visualization
- System status monitoring

###  Stable App (Port 5001)

**What**: Production-ready Flask application
**Access**: http://localhost:5001
**Features**:
- Always responds to health checks
- 0% error rate
- Used as rollback target

###  Buggy App (Port 5002)

**What**: Intentionally unstable application
**Access**: http://localhost:5002
**Features**:
- Random failures (30% of requests fail)
- Simulates real-world problems
- Used for chaos testing

###  Prometheus (Port 9090)

**What**: Metrics collection system
**Access**: http://localhost:9090
**Queries**:
```promql
# Health check success rate
increase(http_requests_total{job="app-stable",status="200",path="/health"}[2m])

# Container uptime
time() - container_start_time{container_name="app-stable"}
```

###  Grafana (Port 3000)

**What**: Visualization dashboard
**Access**: http://localhost:3000
**Login**: admin / admin
**Features**:
- Real-time metrics graphs
- Historical analysis
- Read-only (for demo safety)

---

## Test Scenarios

### Scenario 1: Container Crash & Recovery (Default)

**What happens**:
1. Application running normally
2. Container is stopped (simulates crash)
3. System detects failure
4. System restarts container
5. Application recovered

**Expected result**:  PASSED

**What it proves**: The system can detect and recover from complete service failure

---

### Scenario 2: Container Crash Detection

**What happens**:
1. Baseline health check passes
2. Container is stopped
3. Multiple health checks fail
4. Container is restarted

**Expected result**:  PASSED

**What it proves**: Failure detection accuracy

---

### Scenario 3: Crash Loop & Rollback

**What happens**:
1. Buggy version deployed
2. Application crashes repeatedly
3. System detects crash loop
4. System rolls back to stable version

**Expected result**:  PASSED

**What it proves**: Intelligent version management and escalation

---

### Scenario 4: Resource Degradation

**What happens**:
1. Normal operation baseline
2. CPU stress applied
3. Performance degrades
4. Recovery action triggers
5. Normal operation restored

**Expected result**:  PASSED

**What it proves**: Resource-based monitoring and recovery

---

## Accessing Results

### Dashboard Results

After running a test, results are shown:
- Test status (PASSED/FAILED)
- Failures detected
- Recovery actions executed
- Total duration

### JSON Results File

```bash
cat data/test_results.json
```

Output:
```json
{
  "status": "completed",
  "start_time": "2026-01-06T10:30:00",
  "end_time": "2026-01-06T10:35:30",
  "chaos_injected": "container_stop",
  "failures_detected": 3,
  "recovery_actions": 2,
  "final_status": "passed"
}
```

### CSV Recovery Log

```bash
cat data/recovery_log.csv
```

Output:
```csv
timestamp,action,container,success,duration_seconds
2026-01-06T10:30:15.123456,restart_container,app-stable,true,2.34
2026-01-06T10:30:20.456789,health_check,app-stable,true,0.50
```

---

## Monitoring in Real-Time

### Watch Logs

```bash
# All services
docker-compose logs -f

# Just controller
docker-compose logs -f controller

# Just the app
docker-compose logs -f app-stable

# Follow last 50 lines
docker-compose logs -f --tail=50
```

### View Prometheus Metrics

Go to: http://localhost:9090

Search for:
- `up{job="app-stable"}`
- `container_cpu_usage_seconds`
- `http_requests_total`

### Grafana Dashboards

Go to: http://localhost:3000

Default dashboards are auto-provisioned for:
- Container metrics
- System metrics
- Application metrics

---

## Troubleshooting

### Services won't start

```bash
# Check Docker is running
docker ps

# Check for port conflicts
netstat -tulpn | grep -E '(5001|8000|9090|3000)'

# Rebuild images
docker-compose build --no-cache
```

### Dashboard not accessible

```bash
# Check controller service
docker-compose ps controller

# View controller logs
docker-compose logs controller

# Restart
docker-compose restart controller
```

### Test doesn't run

```bash
# Check controller logs
docker-compose logs -f controller

# Verify Prometheus is working
curl http://localhost:9090/-/healthy

# Check if apps are running
docker-compose ps app-stable
```

### Port already in use

If you need different ports, edit `docker-compose.yml`:

```yaml
app-stable:
  ports:
    - "5001:5000"  # Change 5001 to any free port
```

---

## Stopping the System

```bash
# Stop all services
docker-compose down

# Remove all data volumes
docker-compose down -v

# Remove images too
docker-compose down -v --rmi all
```

---

## Next Steps

1. **Run a test** - Click the button on dashboard
2. **View results** - Check JSON and CSV files
3. **Explore metrics** - Visit Prometheus and Grafana
4. **Read architecture** - See ARCHITECTURE.md
5. **Modify thresholds** - Tune decision engine
6. **Add scenarios** - Extend chaos engine

---

## Key Files

```
zerohum-chaos/
├── README.md              # Full documentation
├── ARCHITECTURE.md        # Technical deep dive
├── docker-compose.yml     # System configuration
├── setup.sh              # Automated setup
├── check-health.sh       # Health verification
└── [component folders]    # Source code
```

---

## Demo Talking Points

**"ZEROHUM-CHAOS demonstrates that infrastructure can be self-healing"**

- Traditional approach: Failure → Alert → Human → Fix → Recovery (minutes)
- Our approach: Failure → Detection → Autonomous Fix → Recovery (seconds)

**Key achievements**:
 Zero human intervention required
 Controlled failure injection
 Intelligent decision making
 Automatic recovery execution
 Complete observability
 Production-like architecture

---

## Questions?

For detailed information:
- Architecture: See `ARCHITECTURE.md`
- Component code: Check comments in Python files
- Configuration: Edit YAML files
- Debugging: Use `docker-compose logs`

---

**Happy Testing!** 
