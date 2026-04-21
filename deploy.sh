#!/bin/bash

# Automated deployment script for AI Chatbot
# Usage: ./deploy.sh [docker|systemd|manual]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default deployment method
DEPLOYMENT_METHOD=${1:-docker}

echo -e "${BLUE}AI Chatbot Deployment Script${NC}"
echo -e "${BLUE}================================${NC}"

# Function to print status
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Docker is installed (for Docker deployment)
    if [ "$DEPLOYMENT_METHOD" = "docker" ]; then
        if ! command -v docker &> /dev/null; then
            print_error "Docker is not installed. Please install Docker first."
            exit 1
        fi
        
        if ! command -v docker-compose &> /dev/null; then
            print_error "Docker Compose is not installed. Please install Docker Compose first."
            exit 1
        fi
    fi
    
    # Check if Python is installed
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.11 or higher."
        exit 1
    fi
    
    # Check if Ollama is installed
    if ! command -v ollama &> /dev/null; then
        print_warning "Ollama is not installed. The deployment will include Ollama."
    fi
    
    print_status "Prerequisites check completed."
}

# Setup environment
setup_environment() {
    print_status "Setting up environment..."
    
    # Create .env file if it doesn't exist
    if [ ! -f .env ]; then
        print_status "Creating .env file from template..."
        cp .env.example .env
        
        # Generate random secret key
        SECRET_KEY=$(openssl rand -hex 32)
        sed -i "s/your-secret-key-here-change-this-in-production/$SECRET_KEY/" .env
        
        print_warning "Please review and update .env file with your configuration."
    fi
    
    # Create necessary directories
    mkdir -p logs data ssl
    
    print_status "Environment setup completed."
}

# Docker deployment
deploy_docker() {
    print_status "Starting Docker deployment..."
    
    # Build and start services
    docker-compose down 2>/dev/null || true
    docker-compose build --no-cache
    docker-compose up -d
    
    # Wait for services to start
    print_status "Waiting for services to start..."
    sleep 10
    
    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        print_status "Docker deployment completed successfully!"
        print_status "Application is running at: http://localhost:5000"
        print_status "Health check: http://localhost:5000/health"
    else
        print_error "Docker deployment failed. Check logs with: docker-compose logs"
        exit 1
    fi
}

# Systemd deployment
deploy_systemd() {
    print_status "Starting Systemd deployment..."
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        print_error "Systemd deployment requires root privileges. Please run with sudo."
        exit 1
    fi
    
    # Create chatbot user
    if ! id "chatbot" &>/dev/null; then
        print_status "Creating chatbot user..."
        useradd -m -s /bin/bash chatbot
    fi
    
    # Deploy application
    DEPLOY_DIR="/opt/chatbot"
    print_status "Deploying application to $DEPLOY_DIR..."
    
    mkdir -p $DEPLOY_DIR
    cp -r . $DEPLOY_DIR/
    chown -R chatbot:chatbot $DEPLOY_DIR
    
    # Setup virtual environment
    cd $DEPLOY_DIR
    sudo -u chatbot python3 -m venv venv
    sudo -u chatbot bash -c "source venv/bin/activate && pip install -r requirements-prod.txt"
    
    # Install systemd service
    cp chatbot.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable chatbot
    systemctl start chatbot
    
    # Check service status
    if systemctl is-active --quiet chatbot; then
        print_status "Systemd deployment completed successfully!"
        print_status "Application is running at: http://localhost:5000"
        print_status "Service status: systemctl status chatbot"
    else
        print_error "Systemd deployment failed. Check logs with: journalctl -u chatbot"
        exit 1
    fi
}

# Manual deployment
deploy_manual() {
    print_status "Starting manual deployment..."
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Install dependencies
    print_status "Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements-prod.txt
    
    # Start with Gunicorn
    print_status "Starting production server..."
    export FLASK_ENV=production
    gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 60 --access-logfile logs/access.log --error-logfile logs/error.log production_chatbot:app &
    
    PID=$!
    echo $PID > chatbot.pid
    
    print_status "Manual deployment completed!"
    print_status "Application is running at: http://localhost:5000"
    print_status "Process ID: $PID"
    print_status "Stop with: kill $PID"
}

# Post-deployment checks
post_deployment_checks() {
    print_status "Running post-deployment checks..."
    
    # Wait for application to start
    sleep 5
    
    # Health check
    if curl -f http://localhost:5000/health > /dev/null 2>&1; then
        print_status "Health check passed!"
    else
        print_warning "Health check failed. Application may still be starting..."
    fi
    
    # Check Ollama connection
    if curl -f http://localhost:11434/api/tags > /dev/null 2>&1; then
        print_status "Ollama connection verified!"
    else
        print_warning "Ollama connection failed. Please ensure Ollama is running."
    fi
    
    print_status "Post-deployment checks completed."
}

# Main deployment logic
main() {
    print_status "Starting deployment with method: $DEPLOYMENT_METHOD"
    
    check_prerequisites
    setup_environment
    
    case $DEPLOYMENT_METHOD in
        docker)
            deploy_docker
            ;;
        systemd)
            deploy_systemd
            ;;
        manual)
            deploy_manual
            ;;
        *)
            print_error "Unknown deployment method: $DEPLOYMENT_METHOD"
            echo "Usage: $0 [docker|systemd|manual]"
            exit 1
            ;;
    esac
    
    post_deployment_checks
    
    print_status "Deployment completed successfully!"
    echo ""
    echo -e "${GREEN}Next steps:${NC}"
    echo "1. Test the application at http://localhost:5000"
    echo "2. Check logs if needed"
    echo "3. Review security settings"
    echo "4. Set up monitoring and backups"
    echo ""
    echo -e "${BLUE}For more information, see DEPLOYMENT.md${NC}"
}

# Run main function
main "$@"
