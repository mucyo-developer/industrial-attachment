# AI Chatbot Deployment Guide

This guide covers multiple deployment options for the AI Chatbot application.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Deployment Options](#deployment-options)
4. [Docker Deployment](#docker-deployment)
5. [Systemd Service Deployment](#systemd-service-deployment)
6. [Manual Deployment](#manual-deployment)
7. [Security Considerations](#security-considerations)
8. [Monitoring and Maintenance](#monitoring-and-maintenance)

## Prerequisites

### System Requirements
- **OS**: Linux (Ubuntu 20.04+), macOS, or Windows 10+
- **Python**: 3.11 or higher
- **RAM**: Minimum 2GB, Recommended 4GB+
- **Storage**: Minimum 5GB free space
- **Network**: Internet connection for Ollama model downloads

### Required Software
- Python 3.11+
- pip (Python package manager)
- Ollama (for AI model serving)
- Git (for cloning repository)

## Environment Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd chat3
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements-prod.txt
```

### 4. Configure Environment
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 5. Start Ollama
```bash
# Install Ollama (if not already installed)
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama service
ollama serve

# Pull the required model
ollama pull qwen2.5:0.5b
```

## Deployment Options

### Option 1: Docker Deployment (Recommended)
Easiest and most portable deployment method.

### Option 2: Systemd Service
For Linux servers with systemd.

### Option 3: Manual Deployment
For development or custom setups.

## Docker Deployment

### Quick Start
```bash
# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f chatbot
```

### Production Docker Setup
```bash
# Create production environment file
cp .env.example .env.production

# Edit with production values
nano .env.production

# Deploy with production settings
docker-compose --env-file .env.production up -d
```

### Docker with HTTPS
```bash
# Deploy with Nginx reverse proxy
docker-compose --profile https up -d

# You'll need to provide SSL certificates in ./ssl/
```

### Docker Commands
```bash
# Stop services
docker-compose down

# Update and rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Access container shell
docker-compose exec chatbot bash

# View resource usage
docker stats
```

## Systemd Service Deployment

### 1. Create Service User
```bash
sudo useradd -m -s /bin/bash chatbot
sudo usermod -aG sudo chatbot
```

### 2. Deploy Application
```bash
# Copy files to deployment directory
sudo cp -r . /opt/chatbot
sudo chown -R chatbot:chatbot /opt/chatbot

# Switch to chatbot user
sudo su - chatbot
cd /opt/chatbot

# Setup virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-prod.txt

# Configure environment
cp .env.example .env
nano .env  # Edit configuration
```

### 3. Install Service
```bash
# Copy service file
sudo cp chatbot.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable and start service
sudo systemctl enable chatbot
sudo systemctl start chatbot

# Check status
sudo systemctl status chatbot
```

### 4. Service Management
```bash
# View logs
sudo journalctl -u chatbot -f

# Restart service
sudo systemctl restart chatbot

# Stop service
sudo systemctl stop chatbot

# Check service status
sudo systemctl status chatbot
```

## Manual Deployment

### Development Server
```bash
# Start development server
python production_chatbot.py
```

### Production with Gunicorn
```bash
# Make startup script executable
chmod +x start.sh

# Start production server
./start.sh
```

### Manual Gunicorn
```bash
# Activate virtual environment
source venv/bin/activate

# Start with Gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 60 production_chatbot:app
```

## Security Considerations

### 1. Environment Variables
- Never commit `.env` files to version control
- Use strong, unique `SECRET_KEY`
- Change default passwords and keys

### 2. Network Security
- Use HTTPS in production
- Configure firewall rules
- Limit access to Ollama API

### 3. File System Security
- Run as non-root user
- Set appropriate file permissions
- Use read-only filesystem where possible

### 4. Rate Limiting
- Configure Nginx rate limiting
- Implement API rate limiting
- Monitor for abuse

### 5. SSL/TLS Configuration
```bash
# Generate self-signed certificate (for testing)
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes

# Or use Let's Encrypt for production
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

## Monitoring and Maintenance

### 1. Health Checks
```bash
# Check application health
curl http://localhost:5000/health

# Check Ollama status
curl http://localhost:11434/api/tags
```

### 2. Log Management
```bash
# View application logs
tail -f logs/chatbot.log

# Rotate logs (add to logrotate)
sudo nano /etc/logrotate.d/chatbot
```

### 3. Performance Monitoring
```bash
# Monitor resource usage
htop
df -h
free -h

# Monitor network connections
netstat -tulpn | grep :5000
```

### 4. Backup Strategy
```bash
# Backup application data
tar -czf backup-$(date +%Y%m%d).tar.gz data/ logs/ .env

# Backup to remote location
rsync -avz backup-$(date +%Y%m%d).tar.gz user@backup-server:/backups/
```

### 5. Updates and Maintenance
```bash
# Update dependencies
pip install --upgrade -r requirements-prod.txt

# Update Ollama models
ollama pull qwen2.5:0.5b

# Restart service after updates
sudo systemctl restart chatbot
```

## Troubleshooting

### Common Issues

#### 1. Ollama Connection Failed
```bash
# Check if Ollama is running
ps aux | grep ollama

# Restart Ollama
sudo systemctl restart ollama  # If installed as service
# or
ollama serve  # If running manually
```

#### 2. Permission Denied Errors
```bash
# Check file permissions
ls -la /opt/chatbot

# Fix permissions
sudo chown -R chatbot:chatbot /opt/chatbot
sudo chmod +x /opt/chatbot/start.sh
```

#### 3. Port Already in Use
```bash
# Find process using port 5000
sudo lsof -i :5000

# Kill process
sudo kill -9 <PID>

# Or change port in .env
echo "PORT=5001" >> .env
```

#### 4. Memory Issues
```bash
# Check memory usage
free -h

# Reduce Gunicorn workers
# Edit gunicorn command to use --workers 1
```

### Debug Mode
```bash
# Enable debug logging
echo "LOG_LEVEL=DEBUG" >> .env

# Restart service
sudo systemctl restart chatbot

# View detailed logs
sudo journalctl -u chatbot -f --no-pager
```

## Performance Tuning

### 1. Gunicorn Configuration
```bash
# Optimize for your system
gunicorn --workers 4 --worker-class gthread --threads 2 --timeout 120 production_chatbot:app
```

### 2. Nginx Optimization
```bash
# Add to nginx.conf
worker_processes auto;
worker_connections 2048;

# Enable gzip compression
gzip on;
gzip_types text/plain text/css application/json application/javascript;
```

### 3. Database Optimization (if using database)
- Configure connection pooling
- Add indexes for frequent queries
- Regular maintenance and cleanup

## Support

For issues and support:
1. Check logs for error messages
2. Review troubleshooting section
3. Check GitHub issues
4. Contact support team

---

**Note**: This deployment guide assumes you have administrative access to the deployment environment. Adjust commands and paths as needed for your specific setup.
