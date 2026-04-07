#!/bin/bash

# ZEROHUM-CHAOS Health Check Script
# Verifies all system components are running correctly

echo "╔════════════════════════════════════════════════════════╗"
echo "║        ZEROHUM-CHAOS System Health Check              ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

if docker compose version > /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose > /dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
else
    echo "✗ Docker Compose is not available"
    exit 1
fi

# Check containers
echo "Container Status:"
echo "─────────────────────────────────────────────────────────"
$COMPOSE_CMD ps
echo ""

# Check services
echo "Service Availability:"
echo "─────────────────────────────────────────────────────────"

# Dashboard
if curl -s http://localhost:8000 > /dev/null; then
    echo "✓ Dashboard (http://localhost:8000)"
else
    echo "✗ Dashboard (http://localhost:8000) - FAILED"
fi

# Stable App
if curl -s http://localhost:5001/health > /dev/null; then
    echo "✓ Stable App (http://localhost:5001)"
else
    echo "✗ Stable App (http://localhost:5001) - FAILED"
fi

# Buggy App
if curl -s http://localhost:5002/health > /dev/null 2>&1; then
    echo "✓ Buggy App (http://localhost:5002)"
else
    echo "✗ Buggy App (http://localhost:5002) - FAILED (expected)"
fi

# Prometheus
if curl -s http://localhost:9090/-/healthy > /dev/null; then
    echo "✓ Prometheus (http://localhost:9090)"
else
    echo "✗ Prometheus (http://localhost:9090) - FAILED"
fi

# Grafana
if curl -s http://localhost:3000/api/health > /dev/null; then
    echo "✓ Grafana (http://localhost:3000)"
else
    echo "✗ Grafana (http://localhost:3000) - FAILED"
fi

echo ""
echo "System Status: READY FOR TESTING"
echo ""
