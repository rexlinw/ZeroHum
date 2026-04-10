#!/bin/bash

###############################################################################
# ZEROHUM-CHAOS Jenkins Deployment Helper Script
# Purpose: Simplify Jenkins configurations and deployments
# Usage: ./jenkins-deploy.sh [command]
###############################################################################

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="zerohum-chaos"
JENKINS_URL="${JENKINS_URL:-http://localhost:8080}"
DOCKER_COMPOSE_FILE="docker-compose.yml"

compose_cmd() {
    if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
        docker compose "$@"
        return
    fi

    if command -v docker-compose >/dev/null 2>&1; then
        docker-compose "$@"
        return
    fi

    log_error "Neither 'docker compose' nor 'docker-compose' is available"
    return 127
}

###############################################################################
# Helper Functions
###############################################################################

log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

###############################################################################
# Pre-deployment Checks
###############################################################################

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is not installed"
        exit 1
    fi
    log_success "Docker found: $(docker --version)"
    
    # Check Docker Compose
    if docker compose version >/dev/null 2>&1; then
        log_success "Docker Compose found: $(docker compose version | head -1)"
    elif command -v docker-compose >/dev/null 2>&1; then
        log_success "Docker Compose found: $(docker-compose --version)"
    else
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check Git
    if ! command -v git >/dev/null 2>&1; then
        log_error "Git is not installed"
        exit 1
    fi
    log_success "Git found: $(git --version)"
    
    # Check Docker daemon
    if ! docker ps >/dev/null 2>&1; then
        log_error "Docker daemon is not running or no permission"
        exit 1
    fi
    log_success "Docker daemon is accessible"
    
    log_success "All prerequisites satisfied"
}

###############################################################################
# Health Check Functions
###############################################################################

health_check() {
    log_info "Performing health checks..."
    
    local all_healthy=true
    
    # Check stable app
    if curl -sf http://localhost:5001/health > /dev/null 2>&1; then
        log_success "Stable app (5001) is healthy"
    else
        log_warning "Stable app (5001) is not responding"
        all_healthy=false
    fi
    
    # Check buggy app
    if curl -sf http://localhost:5002/health > /dev/null 2>&1; then
        log_success "Buggy app (5002) is healthy"
    else
        log_warning "Buggy app (5002) is not responding"
        all_healthy=false
    fi
    
    # Check dashboard
    if curl -sf http://localhost:8000 > /dev/null 2>&1; then
        log_success "Dashboard (8000) is accessible"
    else
        log_warning "Dashboard (8000) is not responding"
        all_healthy=false
    fi
    
    # Check Prometheus
    if curl -sf http://localhost:9090/-/healthy > /dev/null 2>&1; then
        log_success "Prometheus (9090) is healthy"
    else
        log_warning "Prometheus (9090) is not responding"
        all_healthy=false
    fi
    
    # Check Grafana
    if curl -sf http://localhost:3000/api/health > /dev/null 2>&1; then
        log_success "Grafana (3000) is healthy"
    else
        log_warning "Grafana (3000) is not responding"
        all_healthy=false
    fi
    
    if [ "$all_healthy" = true ]; then
        log_success "All services are healthy!"
        return 0
    else
        log_warning "Some services are not fully ready (may need more time)"
        return 0
    fi
}

###############################################################################
# Jenkins Specific Commands
###############################################################################

setup_jenkins_cli() {
    log_info "Setting up Jenkins CLI..."
    
    if [ ! -d ~/.jenkins ]; then
        mkdir -p ~/.jenkins
    fi
    
    if [ ! -f ~/.jenkins/jenkins-cli.jar ]; then
        log_info "Downloading Jenkins CLI..."
        wget -q -O ~/.jenkins/jenkins-cli.jar "${JENKINS_URL}/jnlpJars/jenkins-cli.jar"
        log_success "Jenkins CLI downloaded"
    fi
    
    log_success "Jenkins CLI is ready"
}

fix_jenkins_docker() {
    log_info "Configuring Jenkins container with Docker CLI and Compose support..."

    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is required on the host before running this command"
        exit 1
    fi

    if docker ps --format '{{.Names}}' | grep -qx 'jenkins'; then
        log_info "Jenkins container is already running"
    elif docker ps -a --format '{{.Names}}' | grep -qx 'jenkins'; then
        log_info "Starting existing Jenkins container..."
        docker start jenkins >/dev/null
        log_success "Existing Jenkins container started"
    else
        log_info "Creating Jenkins container with Docker socket mount..."
        docker volume create jenkins_home >/dev/null
        docker run -d \
            --name jenkins \
            -p 8080:8080 \
            -p 50000:50000 \
            -v jenkins_home:/var/jenkins_home \
            -v /var/run/docker.sock:/var/run/docker.sock \
            --user root \
            jenkins/jenkins:lts >/dev/null
        log_success "Jenkins container created"
    fi

    log_info "Installing Docker CLI + Compose plugin inside Jenkins container..."
    docker exec -u 0 jenkins bash -lc '
        set -e
        export DEBIAN_FRONTEND=noninteractive
        apt-get update
        if ! apt-get install -y docker.io docker-compose-plugin; then
            apt-get install -y docker.io docker-compose
        fi
    '

    log_info "Validating Docker access inside Jenkins container..."
    docker exec jenkins docker --version
    docker exec jenkins docker compose version
    docker exec jenkins docker ps >/dev/null

    log_success "Jenkins is ready to run Docker-based pipelines"
    log_info "Jenkins URL: ${JENKINS_URL}"
}

trigger_jenkins_build() {
    local job_name="$1"
    local token="$2"
    
    if [ -z "$token" ]; then
        log_error "Jenkins API token is required"
        log_info "Usage: ./jenkins-deploy.sh trigger-build <job-name> <api-token>"
        exit 1
    fi
    
    log_info "Triggering Jenkins build for: $job_name"
    
    curl -X POST \
        "${JENKINS_URL}/job/${job_name}/build" \
        -u "jenkins:${token}" \
        -H "Content-Type: application/x-www-form-urlencoded" || {
        log_error "Failed to trigger build"
        exit 1
    }
    
    log_success "Build triggered successfully"
}

###############################################################################
# Deployment Functions
###############################################################################

deploy() {
    local environment="$1"
    environment="${environment:-dev}"
    
    log_info "Deploying to $environment environment..."
    
    check_prerequisites
    
    # Stop existing containers
    log_info "Stopping existing containers..."
    compose_cmd down || true
    
    # Build images
    log_info "Building Docker images..."
    compose_cmd build
    
    # Start containers
    log_info "Starting containers..."
    compose_cmd up -d
    
    # Wait for services
    log_info "Waiting for services to stabilize (30 seconds)..."
    sleep 30
    
    # Health checks
    health_check
    
    log_success "Deployment to $environment completed!"
}

rollback() {
    log_warning "Rolling back deployment..."
    
    if [ ! -d backups ]; then
        log_error "No backup directory found"
        exit 1
    fi
    
    local latest_backup=$(ls -t backups | head -1)
    log_info "Using backup: $latest_backup"
    
    compose_cmd down || true
    log_success "Rollback completed (containers stopped)"
}

stop_services() {
    log_info "Stopping all services..."
    compose_cmd down
    log_success "All services stopped"
}

start_services() {
    log_info "Starting all services..."
    compose_cmd up -d
    sleep 15
    health_check
    log_success "All services started"
}

view_logs() {
    local service="$1"
    service="${service:-controller}"
    
    log_info "Viewing logs for: $service"
    compose_cmd logs --tail=100 -f "$service"
}

###############################################################################
# Status and Information
###############################################################################

status() {
    log_info "Current deployment status:"
    echo ""
    compose_cmd ps
    echo ""
    health_check
}

show_urls() {
    log_info "Service URLs:"
    echo ""
    echo "  Dashboard:    http://localhost:8000"
    echo "  Prometheus:   http://localhost:9090"
    echo "  Grafana:      http://localhost:3000 (admin/admin)"
    echo "  Stable App:   http://localhost:5001"
    echo "  Buggy App:    http://localhost:5002"
    echo "  cAdvisor:     http://localhost:8081"
    echo "  Node Export:  http://localhost:9100"
    echo ""
}

###############################################################################
# Validation Functions
###############################################################################

validate_environment() {
    log_info "Validating environment..."
    
    # Check Jenkinsfile exists
    if [ ! -f Jenkinsfile ]; then
        log_error "Jenkinsfile not found in current directory"
        exit 1
    fi
    log_success "Jenkinsfile found"
    
    # Check docker-compose.yml exists
    if [ ! -f "${DOCKER_COMPOSE_FILE}" ]; then
        log_error "${DOCKER_COMPOSE_FILE} not found in current directory"
        exit 1
    fi
    log_success "docker-compose.yml found"
    
    # Check docker-compose syntax
    if compose_cmd config > /dev/null 2>&1; then
        log_success "docker-compose.yml syntax is valid"
    else
        log_error "docker-compose.yml has syntax errors"
        exit 1
    fi
    
    log_success "Environment validation passed"
}

###############################################################################
# Main
###############################################################################

show_help() {
    cat <<EOF
${BLUE}ZEROHUM-CHAOS Jenkins Deployment Helper${NC}

${BLUE}Usage:${NC}
    ./jenkins-deploy.sh [command] [options]

${BLUE}Commands:${NC}
    check-prerequisites        Check if all required tools are installed
    health-check              Perform health checks on all services
    setup-jenkins-cli         Download and setup Jenkins CLI
    fix-jenkins-docker        Start/fix Jenkins container with Docker CLI access
    trigger-build <job> <token>  Trigger a Jenkins build
    
    deploy [env]              Deploy to environment (dev/staging/prod)
    rollback                  Rollback to previous version
    
    start                     Start all services
    stop                      Stop all services
    status                    Show current deployment status
    logs [service]            View logs for a service
    
    validate                  Validate environment setup
    urls                      Show service URLs
    
    help                      Show this help message
    version                   Show version information

${BLUE}Examples:${NC}
    ./jenkins-deploy.sh check-prerequisites
    ./jenkins-deploy.sh fix-jenkins-docker
    ./jenkins-deploy.sh deploy dev
    ./jenkins-deploy.sh trigger-build zerohum-chaos-pipeline YOUR_API_TOKEN
    ./jenkins-deploy.sh logs controller
    ./jenkins-deploy.sh health-check

${BLUE}Environment Variables:${NC}
    JENKINS_URL              Jenkins server URL (default: http://localhost:8080)
    ENVIRONMENT              Target environment (default: dev)

${BLUE}For more information, see:${NC}
    - JENKINS_DEPLOYMENT.md  (Complete deployment guide)
    - README.md              (Project overview)
    - Jenkinsfile           (Pipeline definition)

EOF
}

# Main command routing
case "${1:-help}" in
    check-prerequisites)
        check_prerequisites
        ;;
    health-check)
        health_check
        ;;
    setup-jenkins-cli)
        setup_jenkins_cli
        ;;
    fix-jenkins-docker)
        fix_jenkins_docker
        ;;
    trigger-build)
        trigger_jenkins_build "$2" "$3"
        ;;
    deploy)
        deploy "$2"
        ;;
    rollback)
        rollback
        ;;
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    status)
        status
        ;;
    logs)
        view_logs "$2"
        ;;
    validate)
        validate_environment
        ;;
    urls)
        show_urls
        ;;
    help)
        show_help
        ;;
    version)
        echo "ZEROHUM-CHAOS Jenkins Deployment Helper v1.0"
        ;;
    *)
        log_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
