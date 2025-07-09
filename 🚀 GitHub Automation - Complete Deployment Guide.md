# 🚀 GitHub Automation - Complete Deployment Guide

## 📋 Overview

This guide covers the complete deployment of the GitHub Automation system, including:
- ✅ GitHub Webhook Integration
- ✅ OpenAI-powered Commit Analysis
- ✅ Automated PR Generation
- ✅ PostgreSQL Database
- ✅ Admin Dashboard with Logging
- ✅ Docker Containerization
- ✅ Production-ready Configuration

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub        │    │   Your Server   │    │   OpenAI API    │
│   Webhooks      │───▶│   Flask App     │───▶│   Analysis      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   PostgreSQL    │
                       │   Database      │
                       └─────────────────┘
```

## 🛠️ Prerequisites

### Required Software
- **Docker & Docker Compose** (recommended)
- **Python 3.11+** (for local development)
- **Node.js 18+** (for React frontend)
- **PostgreSQL 14+** (if not using Docker)

### Required API Keys
- **OpenAI API Key** - For commit analysis
- **GitHub Personal Access Token** - For repository access
- **GitHub Webhook Secret** (optional but recommended)

## 🚀 Quick Start (Docker - Recommended)

### 1. Environment Setup
```bash
# Clone/extract the project
cd github-automation-backend

# Copy environment template
cp .env.example .env

# Edit .env with your actual values
nano .env
```

### 2. Configure Environment Variables
```bash
# Required - OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here

# Required - GitHub Configuration  
GITHUB_TOKEN=ghp_your-github-token-here
GITHUB_WEBHOOK_SECRET=your-webhook-secret-here

# Optional - Change default passwords
SECRET_KEY=your-super-secret-key-here
DATABASE_URL=postgresql://github_automation:your-db-password@postgres:5432/github_automation
```

### 3. Deploy with Docker
```bash
# Build and start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f backend
```

### 4. Verify Deployment
```bash
# Check health endpoint
curl http://localhost:5000/health

# Access admin dashboard
open http://localhost:5000/admin

# Access main application
open http://localhost:5000
```

## 🔧 Manual Setup (Development)

### 1. Backend Setup
```bash
cd github-automation-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL database
sudo -u postgres createdb github_automation
sudo -u postgres createuser github_automation
sudo -u postgres psql -c "ALTER USER github_automation PASSWORD 'automation_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE github_automation TO github_automation;"

# Run database migrations
python src/main.py
```

### 2. Frontend Setup
```bash
cd my-github-automation/my-github-automation

# Install dependencies
npm install

# Build for production
npm run build

# Copy to Flask static directory
./github-automation-backend/build-and-deploy.sh
```

### 3. Start Services
```bash
# Start backend
cd github-automation-backend
source venv/bin/activate
python src/main.py

# Backend will be available at http://localhost:5000
```

## 🔗 GitHub Webhook Configuration

### 1. Create Webhook in GitHub Repository
1. Go to your repository → Settings → Webhooks
2. Click "Add webhook"
3. Configure:
   - **Payload URL**: `https://your-domain.com/webhook/github`
   - **Content type**: `application/json`
   - **Secret**: Your webhook secret from `.env`
   - **Events**: Select "Push" and "Pull requests"

### 2. Test Webhook
```bash
# Make a commit to your repository
git add .
git commit -m "Test webhook integration"
git push

# Check logs in admin dashboard
open http://localhost:5000/admin
```

## 📊 Admin Dashboard Features

### Access the Dashboard
- **URL**: `http://localhost:5000/admin`
- **Features**:
  - Real-time statistics
  - Webhook event monitoring
  - Commit analysis logs
  - Repository management
  - System health monitoring
  - Log export functionality

### Key Metrics
- Total repositories tracked
- Webhook events processed
- Commit analyses performed
- PRs automatically generated
- Error rates and system health

## 🔒 Security Configuration

### 1. Production Security
```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Use strong database passwords
# Enable SSL/TLS certificates
# Configure firewall rules
# Set up monitoring and alerting
```

### 2. Environment Variables
```bash
# Production .env example
SECRET_KEY=your-32-character-hex-secret
DATABASE_URL=postgresql://user:secure_password@localhost/github_automation
OPENAI_API_KEY=sk-your-production-api-key
GITHUB_TOKEN=ghp_your-production-token
FLASK_ENV=production
```

## 🌐 Cloud Deployment Options

### 1. Railway (Recommended for beginners)
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

### 2. DigitalOcean App Platform
1. Connect your GitHub repository
2. Configure environment variables
3. Deploy with one click

### 3. AWS/GCP/Azure
- Use Docker containers
- Configure load balancers
- Set up managed databases
- Configure monitoring

## 🔧 Automated Build Script

### Use the Build Script
```bash
# Make script executable
chmod +x github-automation-backend/build-and-deploy.sh

# Run build and deploy
./github-automation-backend/build-and-deploy.sh

# With options
./github-automation-backend/build-and-deploy.sh --restart
./github-automation-backend/build-and-deploy.sh --clean
```

### What the Script Does
1. ✅ Builds React frontend
2. ✅ Copies files to Flask static directory
3. ✅ Updates Flask routes
4. ✅ Creates backups
5. ✅ Provides deployment summary

## 📝 API Endpoints

### Webhook Endpoints
- `POST /webhook/github` - GitHub webhook receiver
- `GET /webhook/events` - List webhook events
- `GET /webhook/commits` - List commit analyses
- `GET /webhook/logs` - System logs

### Admin API
- `GET /admin/api/statistics` - Dashboard statistics
- `GET /admin/api/activity` - Activity charts data
- `GET /admin/api/log-levels` - Log level distribution
- `GET /admin/api/export-logs` - Export logs as CSV

### Repository API
- `GET /api/repositories` - List repositories
- `POST /api/repositories` - Add repository
- `GET /api/analyses` - List analyses
- `POST /api/analyses` - Create analysis

## 🐛 Troubleshooting

### Common Issues

#### 1. Database Connection Error
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Check connection
psql -h localhost -U github_automation -d github_automation
```

#### 2. Webhook Not Receiving Events
```bash
# Check webhook URL is accessible
curl -X POST https://your-domain.com/webhook/github

# Check GitHub webhook delivery logs
# Go to Repository → Settings → Webhooks → Recent Deliveries
```

#### 3. OpenAI API Errors
```bash
# Verify API key
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# Check rate limits and billing
```

#### 4. Frontend Not Loading
```bash
# Rebuild frontend
cd my-github-automation/my-github-automation
npm run build

# Copy to Flask
./github-automation-backend/build-and-deploy.sh
```

### Log Locations
- **Application logs**: `/app/logs/github_automation.log`
- **Docker logs**: `docker-compose logs backend`
- **Admin dashboard**: `http://localhost:5000/admin`

## 📈 Monitoring & Maintenance

### Health Checks
```bash
# Application health
curl http://localhost:5000/health

# Database health
curl http://localhost:5000/admin/api/system-health

# Docker health
docker-compose ps
```

### Backup Strategy
```bash
# Database backup
docker-compose exec postgres pg_dump -U github_automation github_automation > backup.sql

# Restore database
docker-compose exec -T postgres psql -U github_automation github_automation < backup.sql
```

### Updates
```bash
# Update application
git pull origin main
docker-compose build
docker-compose up -d

# Update dependencies
pip install -r requirements.txt --upgrade
npm update
```

## 🎯 Next Steps

### Enhancements
1. **Add more AI models** (Claude, Gemini)
2. **Implement task queues** (Celery, Redis)
3. **Add email notifications**
4. **Create mobile app**
5. **Add more integrations** (Slack, Discord)

### Scaling
1. **Load balancing** with multiple instances
2. **Database sharding** for large datasets
3. **CDN integration** for static assets
4. **Caching layers** (Redis, Memcached)

## 📞 Support

### Documentation
- **API Documentation**: `http://localhost:5000/docs`
- **Admin Guide**: `http://localhost:5000/admin`
- **GitHub Repository**: Your project repository

### Getting Help
1. Check the admin dashboard logs
2. Review the troubleshooting section
3. Check GitHub webhook delivery logs
4. Verify environment variables
5. Test API endpoints manually

---

## 🎉 Congratulations!

Your GitHub Automation system is now ready to:
- ✅ Receive webhook events from GitHub
- ✅ Analyze commits with OpenAI
- ✅ Generate improvement suggestions
- ✅ Create automated pull requests
- ✅ Track everything in a beautiful dashboard

**Happy automating! 🤖**

