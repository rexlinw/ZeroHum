# ZEROHUM-CHAOS
## A Chaos-Aware Autonomous DevOps System for Self-Healing Applications

**A College Final-Year DevOps Project**

---

## Project Overview

ZEROHUM-CHAOS is an autonomous, self-healing DevOps system that validates application reliability through **controlled chaos engineering**. The system intentionally injects controlled failures, detects issues in real-time, and automatically executes recovery actions—**all without human intervention**.

### Key Principle
> This project does NOT fix buggy application code. Instead, it demonstrates **DevOps and SRE best practices** by proving that infrastructure can detect and recover from failures autonomously.

---

## Core Features

 **Autonomous Failure Detection** - Monitors application health using Prometheus metrics  
 **Intelligent Decision Making** - Python-based controller that analyzes system state and recommends actions  
 **Automatic Recovery** - Executes restart, rollback, and remediation without approval  
 **Controlled Chaos Injection** - Simulates real-world failures (container stops, process kills, CPU stress)  
 **Live Dashboard** - One-click test execution with real-time log streaming  
 **Complete Observability** - Prometheus + Grafana for metrics and visualization  
 **Comprehensive Logging** - All decisions and actions logged to JSON/CSV for analysis  

---

## System Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    ZEROHUM-CHAOS System                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │              CONTROL PLANE (Dashboard/Controller)        │ │
│  │                   (Port 8000)                             │ │
│  │  • Web UI with one-click test button                    │ │
│  │  • Decision Engine (analyzes metrics)                   │ │
│  │  • Recovery Executor (executes actions)                 │ │
│  └──────────────────────────────────────────────────────────┘ │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │         CHAOS ENGINE (Failure Injection)                │ │
│  │  • Container stop/start                                 │ │
│  │  • Process termination                                  │ │
│  │  • CPU/Memory stress                                    │ │
│  └──────────────────────────────────────────────────────────┘ │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │            APPLICATION SERVICES                         │ │
│  │  • Stable App (Port 5001) ← Production Ready           │ │
│  │  • Buggy App (Port 5002)  ← For Testing                │ │
│  │  • Health Endpoints (/health, /metrics)                │ │
│  └──────────────────────────────────────────────────────────┘ │
│                          ↓                                      │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │        MONITORING STACK                                 │ │
│  │  • Prometheus (Port 9090) - Metrics Collection         │ │
│  │  • Grafana (Port 3000) - Visualization                 │ │
│  │  • cAdvisor (Port 8080) - Container Metrics            │ │
│  │  • Node Exporter (Port 9100) - System Metrics          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Application Running
        ↓
   Health Check Endpoint
        ↓
   Prometheus Scrapes Metrics (every 15s)
        ↓
   Controller Analyzes Metrics
        ↓
   Decision Engine Evaluates State
        ↓
   Action Recommended (restart/rollback/isolate)
        ↓
   Recovery Executor Performs Action
        ↓
   System Recovers to Healthy State
        ↓
   Metrics Update → Loop Continues
```

---

## Project Structure

```
zerohum-chaos/
│
├── app/
│   ├── stable/
│   │   ├── app.py              # Production-ready Flask app
│   │   ├── Dockerfile          # Container image
│   │   └── requirements.txt     # Python dependencies
│   │
│   └── buggy/
│       ├── app.py              # Intentionally unstable app
│       ├── Dockerfile          # Container image
│       └── requirements.txt     # Python dependencies
│
├── chaos_engine/
│   └── chaos.py                # Failure injection engine
│
├── controller/
│   ├── decision_engine.py       # Autonomous decision maker
│   └── controller.py            # Main orchestrator
│
├── executor/
│   └── recovery.py              # Recovery action executor
│
├── monitoring/
│   ├── prometheus.yml           # Prometheus configuration
│   └── grafana/
│       ├── provisioning-datasources.yml
│       └── provisioning-dashboards.yml
│
├── dashboard/
│   ├── ui.py                   # Flask dashboard server
│   ├── Dockerfile              # Dashboard container
│   ├── requirements.txt         # Dependencies
│   ├── templates/
│   │   └── dashboard.html       # Web interface
│   └── static/
│       ├── style.css            # Dashboard styling
│       └── script.js            # Dashboard interactivity
│
├── data/
│   ├── test_results.json       # Test output
│   └── recovery_log.csv        # Recovery actions
│
├── docker-compose.yml           # Container orchestration
├── README.md                    # This file
└── ARCHITECTURE.md              # Detailed architecture
```

---

## Quick Start

### Prerequisites

- Docker & Docker Compose installed
- Python 3.11+ (for local development)
- 4GB RAM minimum recommended

### Installation & Setup

1. **Clone the repository**
   ```bash
   cd zerohum-chaos
   ```

2. **Build Docker images**
   ```bash
   docker-compose build
   ```

3. **Start the system**
   ```bash
   docker-compose up -d
   ```

4. **Wait for services to start** (30 seconds)
   ```bash
   docker-compose ps
   ```

### Access the Dashboard

Open your browser and navigate to:
- **Dashboard**: http://localhost:8000
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Stable App**: http://localhost:5001
- **Buggy App**: http://localhost:5002

---

## Running a Test

### Simple Test (Recommended)

1. Open the Dashboard: http://localhost:8000
2. Select a test scenario from the dropdown:
   - **Default**: Container Crash & Recovery
   - **Container Crash**: Detect and restart stopped container
   - **Crash Loop**: Detect repeated failures and rollback
   - **Degradation**: Handle resource exhaustion

3. Click **"Run Reliability Test"**

4. Watch the real-time logs showing:
   - Chaos injection
   - Failure detection
   - Recovery decisions
   - System stabilization

5. View results and metrics in the dashboard

### Test Scenarios Explained

#### Scenario 1: Container Crash & Recovery (Default)
```
Timeline:
0s    → Baseline health check passes
5s    → Chaos injected: Container stopped
8s    → Failure detected
12s   → Recovery action: Container restart
15s   → System healthy again
```

**What it demonstrates:**
- Container down detection
- Automatic recovery without alerts
- Zero manual intervention

#### Scenario 2: Crash Loop & Rollback
```
Timeline:
0s    → Stable version running
5s    → Deploy buggy version
8s    → Multiple failures detected
12s   → Trigger rollback to stable version
15s   → Back to healthy state
```

**What it demonstrates:**
- Repeated failure detection
- Automatic version rollback
- Version management without human approval

#### Scenario 3: Resource Degradation
```
Timeline:
0s    → Normal operation
5s    → CPU stress applied
8s    → Performance degradation detected
12s   → Recovery action triggered
15s   → Resource pressure relieved
```

**What it demonstrates:**
- Performance metric monitoring
- Resource-based decision making
- Proactive recovery

---

## Configuration

### Decision Engine Thresholds
Edit `controller/decision_engine.py`:
```python
self.thresholds = {
    'health_check_failure_rate': 0.3,      # 30% failures
    'error_rate_threshold': 0.25,          # 25% errors
    'response_time_threshold': 5000,       # 5 seconds
    'container_down_threshold': 3,         # 3 checks
    'rollback_threshold': 5,               # 5 consecutive failures
}
```

### Prometheus Scrape Interval
Edit `monitoring/prometheus.yml`:
```yaml
global:
  scrape_interval: 15s    # How often to collect metrics
  evaluation_interval: 15s
```

### Monitoring Interval
Edit `dashboard/ui.py`:
```python
self.polling_interval = 30  # Check metrics every 30 seconds
```

---

## Test Results Interpretation

### Results File: `data/test_results.json`

```json
{
  "status": "completed",
  "start_time": "2026-01-06T10:30:00.000000",
  "end_time": "2026-01-06T10:35:30.000000",
  "chaos_injected": "container_stop",
  "failures_detected": 3,
  "recovery_actions": 2,
  "final_status": "passed"
}
```

**Interpretation:**
- `failures_detected`: How many anomalies were found
- `recovery_actions`: How many recovery steps were executed
- `final_status`: "passed" = system recovered successfully

### Recovery Log: `data/recovery_log.csv`

```csv
timestamp,action,container,success,duration_seconds
2026-01-06T10:30:15.123456,restart_container,app-stable,true,2.34
2026-01-06T10:30:20.456789,health_check,app-stable,true,0.50
```

---

## Key Concepts

### What is Autonomous Recovery?

```
Traditional Approach (Manual):
Failure → Alert → On-call Engineer → Investigation → Execution → Recovery
         (Minutes to Hours)

ZEROHUM-CHAOS Approach (Autonomous):
Failure → Detection → Decision → Execution → Recovery
         (Seconds)
```

### What Can It Detect?

✅ Container crashes
✅ Repeated failures
✅ Health check failures
✅ High error rates
✅ Slow responses
✅ Resource exhaustion
✅ Service unavailability

### What Can It Do?

✅ Restart containers
✅ Rollback to previous versions
✅ Scale services
✅ Isolate problematic services
✅ Log all actions
✅ Report metrics

---

## Limitations & Design Decisions

### What It Does NOT Do

❌ Fix application code bugs
❌ Detect network failures external to containers
❌ Optimize application performance
❌ Handle data corruption
❌ Manage persistent storage failover
❌ Require internet connectivity
❌ Use machine learning or complex algorithms

### Why These Limitations?

1. **Application bugs are code issues** - DevOps cannot fix code, only manage infrastructure
2. **Focus on reliability, not performance** - Goals is proving autonomous recovery
3. **Demo-friendly approach** - Simple, understandable logic for college project

---

## Architecture Deep Dive

### Decision Engine Rules

```python
IF container_down:
    ACTION = restart_container
ELIF high_error_rate:
    IF error_rate > 50%:
        ACTION = rollback_to_stable
    ELSE:
        ACTION = restart_container
ELIF response_time_slow:
    ACTION = scale_service
ELSE:
    ACTION = none (continue monitoring)
```

### Recovery Executor Priority

```
Priority 1: Container Restart (fastest, least disruptive)
Priority 2: Service Rollback (restores stable version)
Priority 3: Service Isolation (prevents cascade failure)
Priority 4: Manual Intervention (should never reach this)
```

### Monitoring Loop

```python
while system_running:
    metrics = prometheus.query()
    analysis = decision_engine.analyze(metrics)
    decision = decision_engine.decide(analysis)
    
    if should_execute(decision):
        result = executor.execute(decision)
        log_action(result)
    
    sleep(polling_interval)
```

---

## Testing the System

### Test Scenarios Included

1. **Default Test** (Recommended for demos)
   - Demonstrates the full cycle
   - Takes ~3 minutes

2. **Container Crash Test**
   - Tests container restart logic
   - Takes ~2 minutes

3. **Crash Loop Test**
   - Tests rollback logic
   - Takes ~3 minutes

4. **Degradation Test**
   - Tests performance monitoring
   - Takes ~3 minutes

### How to Interpret Test Logs

```
=== ZEROHUM-CHAOS Test Started ===                    # Test begins
--- Phase 1: Baseline Health Check ---                # Healthy state confirmed
--- Phase 2: Injecting Chaos ---                      # Failure simulation starts
Chaos injected: Container stopped                      # Failure injection complete
--- Phase 3: Failure Detection ---                    # Monitoring begins
Detection result - Status: degraded, Severity: high   # Anomaly detected
--- Phase 4: Autonomous Decision Making ---           # Analysis happens
Controller decision: RESTART                          # Action chosen
--- Phase 5: Autonomous Recovery ---                  # Recovery starts
Recovery result: Container restart successful         # Action executed
--- Phase 6: Verification ---                         # Validation
Final status: healthy                                 # System recovered
=== Test Completed: PASSED ===                        # Success confirmed
```

---

## Common Issues & Troubleshooting

### Issue: Dashboard not loading (Port 8000)

**Solution:**
```bash
docker-compose logs controller
docker-compose restart controller
```

### Issue: Prometheus not collecting metrics

**Solution:**
```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Verify scrape configs
docker-compose logs prometheus
```

### Issue: Containers failing to restart

**Solution:**
```bash
# Check Docker socket permission
docker ps
# Verify docker-compose.yml mount

# Try manual restart
docker restart app-stable
```

### Issue: Tests not showing results

**Solution:**
```bash
# Check data directory permissions
ls -la data/

# Verify controller logs
docker-compose logs controller

# Restart controller
docker-compose restart controller
```

---

## Performance Characteristics

### Typical Response Times

| Operation | Time | Notes |
|-----------|------|-------|
| Failure Detection | 15-30s | Next Prometheus scrape |
| Decision Making | < 1s | Python analysis |
| Container Restart | 2-5s | Docker command |
| Version Rollback | 5-10s | Stop + Start new image |
| Full Recovery Cycle | 30-60s | End-to-end |

### Resource Usage

- **Prometheus**: ~200MB RAM
- **Grafana**: ~150MB RAM
- **Controller**: ~100MB RAM
- **Each App**: ~50MB RAM
- **Total**: ~700MB RAM

---

## Future Enhancements

### Phase 2 Features
- [ ] Machine learning for anomaly detection
- [ ] Multi-region failover
- [ ] Database backup & recovery
- [ ] Network simulation (packet loss, latency)
- [ ] Custom metric thresholds via UI
- [ ] Action rate limiting (prevent flapping)

### Phase 3 Features
- [ ] Kubernetes integration
- [ ] Helm chart deployment
- [ ] Incident webhook notifications (read-only)
- [ ] Historical trend analysis
- [ ] Predictive failure detection
- [ ] Cost optimization recommendations

---

## GitHub Repository

```bash
# Initialize Git
git init
git add .
git commit -m "Initial commit: ZEROHUM-CHAOS system"

# Meaningful commit messages
git commit -m "feat: Add decision engine for autonomous recovery"
git commit -m "fix: Improve health check logic"
git commit -m "docs: Add comprehensive architecture guide"
```

### Commit History Best Practices

```
feat: Add feature
fix: Fix bug
docs: Documentation
test: Add tests
refactor: Code cleanup
perf: Performance improvement
```

---

## Demo Walkthrough (5 minutes)

**For Viva/Presentation:**

1. **Show System Running** (30s)
   - Open dashboard
   - Show all services healthy

2. **Run Default Test** (2 min 30s)
   - Click "Run Test"
   - Watch logs in real-time
   - Point out each phase

3. **Analyze Results** (1 min)
   - Show test results
   - Show Prometheus graphs
   - Show recovery log

4. **Answer Questions** (1 min)
   - Explain decision logic
   - Discuss limitations
   - Highlight DevOps principles

---

## Technical Stack

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11 | Controller & orchestration |
| Flask | 2.3.0 | Web dashboard |
| Docker | Latest | Containerization |
| Docker Compose | 2.0+ | Orchestration |
| Prometheus | Latest | Metrics collection |
| Grafana | Latest | Visualization |
| cAdvisor | Latest | Container metrics |

---

## License & Attribution

This project is created as a College Final-Year Project in DevOps & SRE.

---

## References & Learning Resources

- [Chaos Engineering Principles](https://principlesofchaos.org)
- [SRE Best Practices](https://sre.google)
- [Prometheus Documentation](https://prometheus.io)
- [Docker Best Practices](https://docs.docker.com)

---

## Support & Questions

For implementation details, see [ARCHITECTURE.md](ARCHITECTURE.md)

For code walkthrough, check comments in:
- `chaos_engine/chaos.py`
- `controller/decision_engine.py`
- `executor/recovery.py`

---

**Last Updated**: January 6, 2026
**Project Status**: Complete & Ready for Demo
**Maintainer**: DevOps Student
