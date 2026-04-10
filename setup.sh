#!/bin/bash

# ZEROHUM-CHAOS Setup Script
# Initializes and starts the complete system

set -e

echo "╔════════════════════════════════════════════════════════╗"
echo "║     ZEROHUM-CHAOS System Initialization              ║"
echo "║  Chaos-Aware Autonomous DevOps System                ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""

# Check prerequisites
echo "[1/5] Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo " Docker is not installed"
    exit 1
fi

if docker compose version > /dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose > /dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
else
    echo " Docker Compose is not installed"
    exit 1
fi

echo " Docker found: $(docker --version)"
echo " Docker Compose found: $($COMPOSE_CMD version)"
echo ""

# Create data directory
echo "[2/5] Creating data directory..."
mkdir -p data
chmod 777 data
echo " Data directory ready"
echo ""

# Build images
echo "[3/5] Building Docker images..."
$COMPOSE_CMD build --no-cache

if [ $? -eq 0 ]; then
    echo " Images built successfully"
else
    echo " Build failed"
    exit 1
fi
echo ""

# Start services
echo "[4/5] Starting services..."
$COMPOSE_CMD up -d

if [ $? -eq 0 ]; then
    echo " Services started"
else
    echo " Failed to start services"
    exit 1
fi
echo ""

# Wait for services to be ready
echo "[5/5] Waiting for services to be ready..."
sleep 30

echo "╔════════════════════════════════════════════════════════╗"
echo "║          ZEROHUM-CHAOS System Ready                  ║"
echo "╚════════════════════════════════════════════════════════╝"
echo ""
echo "Access the system at:"
echo "  Dashboard:    http://localhost:8000"
echo "  Grafana:      http://localhost:3000 (admin/admin)"
echo "  Prometheus:   http://localhost:9090"
echo "  Stable App:   http://localhost:5001"
echo "  Buggy App:    http://localhost:5002"
echo ""
echo "To view logs:"
echo "  $COMPOSE_CMD logs -f"
echo ""
echo "To stop the system:"
echo "  $COMPOSE_CMD down"
echo ""
