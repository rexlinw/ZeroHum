#!/bin/bash

# ZEROHUM-CHAOS Project Validation Script
# Verifies complete project structure and readiness

echo "========================================================"
echo " ZEROHUM-CHAOS Project Validation Script"
echo " Verifying Complete System Implementation"
echo "========================================================"
echo ""

PASSED=0
FAILED=0

# Function to check file existence
check_file() {
    if [ -f "$1" ]; then
        echo " $1"
        ((PASSED++))
    else
        echo " MISSING: $1"
        ((FAILED++))
    fi
}

# Function to check directory existence
check_dir() {
    if [ -d "$1" ]; then
        echo " $1 (directory)"
        ((PASSED++))
    else
        echo " MISSING DIRECTORY: $1"
        ((FAILED++))
    fi
}

echo "Validating Documentation..."
echo "---------------------------------------------------------"
check_file "docs/README.md"
check_file "docs/ARCHITECTURE.md"
check_file "docs/QUICKSTART.md"
check_file "docs/JENKINS_QUICKSTART.md"
check_file "docs/JENKINS_DEPLOYMENT.md"
echo ""

echo "Validating Configuration..."
echo "---------------------------------------------------------"
check_file "docker-compose.yml"
check_file ".gitignore"
check_file "setup.sh"
check_file "check-health.sh"
echo ""

echo "Validating Application Services..."
echo "---------------------------------------------------------"
check_dir "app/stable"
check_file "app/stable/app.py"
check_file "app/stable/Dockerfile"
check_file "app/stable/requirements.txt"

check_dir "app/buggy"
check_file "app/buggy/app.py"
check_file "app/buggy/Dockerfile"
check_file "app/buggy/requirements.txt"
echo ""

echo "Validating Chaos Engine..."
echo "---------------------------------------------------------"
check_dir "chaos_engine"
check_file "chaos_engine/chaos.py"
check_file "chaos_engine/__init__.py"
echo ""

echo "Validating Controller..."
echo "---------------------------------------------------------"
check_dir "controller"
check_file "controller/decision_engine.py"
check_file "controller/controller.py"
check_file "controller/__init__.py"
echo ""

echo "Validating Executor..."
echo "---------------------------------------------------------"
check_dir "executor"
check_file "executor/recovery.py"
check_file "executor/__init__.py"
echo ""

echo "Validating Dashboard..."
echo "---------------------------------------------------------"
check_dir "dashboard"
check_file "dashboard/ui.py"
check_file "dashboard/Dockerfile"
check_file "dashboard/requirements.txt"
check_dir "dashboard/templates"
check_file "dashboard/templates/dashboard.html"
check_dir "dashboard/static"
check_file "dashboard/static/style.css"
check_file "dashboard/static/script.js"
echo ""

echo "Validating Monitoring Stack..."
echo "─────────────────────────────────────────────────────────"
check_dir "monitoring"
check_file "monitoring/prometheus.yml"
check_dir "monitoring/grafana"
check_file "monitoring/grafana/provisioning-datasources.yml"
check_file "monitoring/grafana/provisioning-dashboards.yml"
echo ""

echo "Validating Data Directory..."
echo "─────────────────────────────────────────────────────────"
check_dir "data"
echo ""

echo "╔════════════════════════════════════════════════════════╗"
echo "║                 Validation Results                    ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo " Passed:  $PASSED"
echo " Failed:  $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║   All components validated successfully!             ║"
    echo "║   Project ready for deployment and testing!          ║"
    echo "╚════════════════════════════════════════════════════════╝"
    exit 0
else
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║   Some components are missing!                       ║"
    echo "║  Please verify the project structure.                 ║"
    echo "╚════════════════════════════════════════════════════════╝"
    exit 1
fi
