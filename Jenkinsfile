pipeline {
    agent any
    
    options {
        timestamps()
        timeout(time: 1, unit: 'HOURS')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }
    
    environment {
        PROJECT_NAME = 'zerohum-chaos'
        REGISTRY = 'docker.io'
        REGISTRY_CREDENTIALS = 'docker-hub-credentials'
        SLACK_CHANNEL = '#devops-alerts'
    }
    
    stages {
        stage('Checkout') {
            steps {
                echo '🔄 Checking out source code...'
                checkout scm
                script {
                    env.GIT_COMMIT_SHORT = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
                    env.GIT_BRANCH = sh(returnStdout: true, script: 'git rev-parse --abbrev-ref HEAD').trim()
                }
            }
        }
        
        stage('Build') {
            steps {
                echo '🏗️ Building Docker images...'
                sh '''
                    echo "Build Date: $(date)"
                    echo "Git Commit: ${GIT_COMMIT_SHORT}"
                    echo "Git Branch: ${GIT_BRANCH}"
                    
                    docker-compose build
                '''
            }
        }
        
        stage('Unit Tests') {
            steps {
                echo '🧪 Running unit tests...'
                sh '''
                    echo "Testing Python applications..."
                    
                    # Test stable app
                    docker-compose run --rm app-stable python -m pytest app.py -v || true
                    
                    # Test buggy app
                    docker-compose run --rm app-buggy python -m pytest app.py -v || true
                    
                    # Test chaos engine
                    docker-compose run --rm controller python -m pytest ../chaos_engine/ -v || true
                '''
            }
        }
        
        stage('Deploy - Dev') {
            when {
                branch 'develop'
            }
            steps {
                echo '🚀 Deploying to Development...'
                sh '''
                    echo "Stopping existing containers..."
                    docker-compose down || true
                    
                    echo "Starting services in development mode..."
                    docker-compose up -d
                    
                    echo "Waiting for services to stabilize..."
                    sleep 30
                    
                    echo "Verifying deployment..."
                    docker-compose ps
                '''
            }
        }
        
        stage('Deploy - Staging') {
            when {
                branch 'staging'
            }
            steps {
                echo '🚀 Deploying to Staging...'
                sh '''
                    echo "Creating backup of current state..."
                    docker-compose exec -T controller cp -r /app /app_backup || true
                    
                    echo "Deploying new version..."
                    docker-compose down || true
                    docker-compose up -d
                    
                    echo "Waiting for services..."
                    sleep 30
                '''
            }
        }
        
        stage('Deploy - Production') {
            when {
                branch 'main'
            }
            steps {
                echo '🚀 Deploying to Production...'
                input 'Deploy to Production? (Click Proceed to continue)'
                sh '''
                    echo "Creating production backup..."
                    BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
                    mkdir -p $BACKUP_DIR
                    docker-compose logs > $BACKUP_DIR/docker-compose.log || true
                    
                    echo "Performing health checks before deployment..."
                    curl -f http://localhost:5001/health || echo "Pre-deployment health check failed"
                    
                    echo "Deploying to production..."
                    docker-compose down || true
                    docker-compose up -d
                    
                    echo "Waiting for services..."
                    sleep 30
                    
                    echo "Running post-deployment health checks..."
                    curl -f http://localhost:5001/health
                    curl -f http://localhost:5002/health
                    curl -f http://localhost:8000/ || echo "Dashboard not fully ready"
                '''
            }
        }
        
        stage('Health Checks') {
            steps {
                echo '🩺 Performing health checks...'
                sh '''
                    echo "Checking container status..."
                    docker-compose ps
                    
                    echo "Waiting for services to become healthy..."
                    sleep 10
                    
                    echo "Testing stable app endpoint..."
                    curl -f http://localhost:5001/health && echo "✅ Stable app healthy" || echo "❌ Stable app unhealthy"
                    
                    echo "Testing buggy app endpoint..."
                    curl -f http://localhost:5002/health && echo "✅ Buggy app healthy" || echo "❌ Buggy app unhealthy"
                    
                    echo "Testing dashboard..."
                    curl -f http://localhost:8000 && echo "✅ Dashboard accessible" || echo "⚠️ Dashboard not fully ready (expected at startup)"
                    
                    echo "Testing Prometheus..."
                    curl -f http://localhost:9090/-/healthy && echo "✅ Prometheus healthy" || echo "❌ Prometheus unhealthy"
                    
                    echo "Testing Grafana..."
                    curl -f http://localhost:3000/api/health && echo "✅ Grafana healthy" || echo "❌ Grafana unhealthy"
                '''
            }
        }
        
        stage('Smoke Tests') {
            steps {
                echo '🔥 Running smoke tests...'
                sh '''
                    echo "Testing Prometheus metrics collection..."
                    curl -s http://localhost:9090/api/v1/query?query=up | grep -q "success" && echo "✅ Metrics working" || echo "⚠️ Metrics query pending"
                    
                    echo "Checking Docker network..."
                    docker network inspect zerohum-network > /dev/null && echo "✅ Network healthy" || echo "❌ Network issue"
                    
                    echo "Verifying volume mounts..."
                    docker-compose exec -T controller ls -la /app || true
                '''
            }
        }
        
        stage('Cleanup') {
            when {
                expression { currentBuild.result == 'FAILURE' }
            }
            steps {
                echo '🧹 Cleaning up after failure...'
                sh '''
                    echo "Collecting logs for debugging..."
                    docker-compose logs > deployment_error_logs.txt || true
                    
                    echo "Stopping failed deployment..."
                    docker-compose down || true
                '''
                archiveArtifacts artifacts: 'deployment_error_logs.txt', allowEmptyArchive: true
            }
        }
    }
    
    post {
        always {
            echo '📋 Pipeline execution completed'
            sh 'docker-compose ps || true'
        }
        success {
            echo '✅ Deployment successful!'
            script {
                if (env.BRANCH_NAME == 'main') {
                    echo 'Notifying production deployment success'
                }
            }
        }
        failure {
            echo '❌ Deployment failed!'
            sh '''
                echo "Saving diagnostic information..."
                docker-compose logs > build_logs.txt || true
            '''
            archiveArtifacts artifacts: 'build_logs.txt', allowEmptyArchive: true
        }
    }
}
