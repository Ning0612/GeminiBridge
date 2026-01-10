# Deployment Guide

Production deployment guide for GeminiBridge v2.0.0

## Table of Contents

- [Prerequisites](#prerequisites)
- [Production Checklist](#production-checklist)
- [Deployment Methods](#deployment-methods)
  - [Standalone Server](#standalone-server)
  - [Docker Deployment](#docker-deployment)
  - [Docker Compose](#docker-compose)
  - [Kubernetes](#kubernetes)
  - [Cloud Platforms](#cloud-platforms)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Backup and Recovery](#backup-and-recovery)
- [Scaling](#scaling)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 2 cores
- RAM: 2 GB
- Disk: 10 GB available
- OS: Linux, Windows Server, or macOS

**Recommended (Production):**
- CPU: 4+ cores
- RAM: 4+ GB
- Disk: 50 GB SSD
- OS: Ubuntu 22.04 LTS or similar

### Required Software

1. **Python 3.12+**
   ```bash
   python --version
   # Should output: Python 3.12.0 or higher
   ```

2. **Docker** (for sandboxed CLI execution)
   ```bash
   docker --version
   # Should output: Docker version 24.0 or higher
   ```

3. **Gemini CLI**
   ```bash
   # Install via npm
   npm install -g @google/generative-ai-cli

   # Verify installation
   gemini --version
   ```

4. **Process Manager** (recommended: systemd, supervisord, or PM2)

## Production Checklist

Before deploying to production, complete this checklist:

### Security

- [ ] Generate strong bearer token (32+ characters)
- [ ] Enable `SECURITY_STRICT_MODE=true`
- [ ] Configure appropriate CORS origins
- [ ] Review and adjust rate limits
- [ ] Run security check: `python scripts/check_security.py`
- [ ] Set restrictive file permissions on `.env` (chmod 600)
- [ ] Disable DEBUG mode: `DEBUG=false`

### Configuration

- [ ] Set `LOG_LEVEL=INFO` (or WARNING for production)
- [ ] Configure log retention: `LOG_RETENTION_DAYS=30`
- [ ] Set appropriate `GEMINI_CLI_TIMEOUT`
- [ ] Configure `MAX_CONCURRENT_REQUESTS` based on capacity
- [ ] Set `QUEUE_TIMEOUT` appropriately

### Infrastructure

- [ ] Configure reverse proxy (nginx, Caddy, etc.)
- [ ] Enable HTTPS/TLS
- [ ] Set up firewall rules
- [ ] Configure log rotation
- [ ] Set up monitoring and alerting
- [ ] Plan backup strategy

### Testing

- [ ] Test health endpoint: `curl http://localhost:11434/health`
- [ ] Test chat completions with sample requests
- [ ] Load test with expected traffic
- [ ] Verify error handling and rate limiting
- [ ] Test Docker container cleanup

## Deployment Methods

### Standalone Server

Deploy GeminiBridge as a standalone Python application.

#### 1. Setup User and Directory

```bash
# Create dedicated user
sudo useradd -r -s /bin/false geminibridge

# Create application directory
sudo mkdir -p /opt/geminibridge
sudo chown geminibridge:geminibridge /opt/geminibridge
```

#### 2. Install Application

```bash
# Switch to application directory
cd /opt/geminibridge

# Clone repository
sudo -u geminibridge git clone https://github.com/yourusername/GeminiBridge.git .

# Create virtual environment
sudo -u geminibridge python3 -m venv .venv

# Install dependencies
sudo -u geminibridge .venv/bin/pip install -r requirements.txt
```

#### 3. Configure Environment

```bash
# Copy environment template
sudo -u geminibridge cp .env.example .env

# Generate secure token
sudo -u geminibridge .venv/bin/python scripts/generate_token.py

# Edit configuration
sudo -u geminibridge nano .env
```

**Production `.env` example:**

```bash
# Server
PORT=11434
HOST=127.0.0.1

# Security
BEARER_TOKEN=<generated-secure-token>
SECURITY_STRICT_MODE=true

# Gemini CLI
GEMINI_CLI_PATH=/usr/local/bin/gemini
GEMINI_CLI_TIMEOUT=60

# Performance
MAX_CONCURRENT_REQUESTS=10
MIN_REQUEST_GAP_MS=500
QUEUE_TIMEOUT=60
CLI_MAX_RETRIES=3
CLI_CLEANUP_WAIT_MS=200  # Increase to 500-800 for better stability

# Logging
LOG_LEVEL=INFO
LOG_RETENTION_DAYS=30

# CORS
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

#### 4. Set Permissions

```bash
# Restrict .env file
sudo chmod 600 /opt/geminibridge/.env
sudo chown geminibridge:geminibridge /opt/geminibridge/.env

# Create logs directory
sudo mkdir -p /opt/geminibridge/logs
sudo chown geminibridge:geminibridge /opt/geminibridge/logs
```

#### 5. Create systemd Service

Create `/etc/systemd/system/geminibridge.service`:

```ini
[Unit]
Description=GeminiBridge - OpenAI API Compatible Proxy for Gemini
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=geminibridge
Group=geminibridge
WorkingDirectory=/opt/geminibridge
Environment="PATH=/opt/geminibridge/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/geminibridge/.venv/bin/python main.py

# Restart policy
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=geminibridge

[Install]
WantedBy=multi-user.target
```

#### 6. Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable geminibridge

# Start service
sudo systemctl start geminibridge

# Check status
sudo systemctl status geminibridge

# View logs
sudo journalctl -u geminibridge -f
```

### Windows Deployment

Deploy GeminiBridge on Windows with automatic startup.

#### 1. Install Prerequisites

```powershell
# Install Python 3.12+ from https://www.python.org/
# Install Docker Desktop from https://www.docker.com/products/docker-desktop/
# Install Gemini CLI
npm install -g @google/generative-ai-cli
```

#### 2. Setup Project

```powershell
# Clone repository
git clone https://github.com/yourusername/GeminiBridge.git
cd GeminiBridge

# Create virtual environment
python -m venv .venv

# Activate virtual environment
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

#### 3. Configure Environment

```powershell
# Copy environment template
cp .env.example .env

# Generate secure token
python scripts/generate_token.py

# Edit .env file (use notepad or your preferred editor)
notepad .env
```

**Windows Production `.env` example:**

```bash
# Server
PORT=11434
HOST=127.0.0.1

# Security
BEARER_TOKEN=<generated-secure-token>

# Gemini CLI (Windows path)
GEMINI_CLI_PATH=C:\Users\YourName\AppData\Roaming\npm\gemini.cmd
GEMINI_CLI_TIMEOUT=60

# Performance (optimized for Windows)
MAX_CONCURRENT_REQUESTS=8
MIN_REQUEST_GAP_MS=500
QUEUE_TIMEOUT=60
CLI_MAX_RETRIES=3
CLI_CLEANUP_WAIT_MS=200  # Increase to 500-800 if experiencing conflicts

# Logging
LOG_LEVEL=INFO
LOG_RETENTION_DAYS=7
DEBUG=false
```

#### 4. Setup Auto-Start with Task Scheduler

**Option A: Automated Setup (Recommended)**

```powershell
# Run as Administrator
.\setup_task_scheduler.ps1
```

The script will:
- Validate Python virtual environment and project files
- Create a Windows Task Scheduler task named "GeminiBridge"
- Configure auto-start at system startup
- Set up automatic restart on failure (3 attempts, 1-minute interval)
- Start the application immediately
- Display task status and Python processes

**Option B: Manual Task Scheduler Setup**

1. Open Task Scheduler (`taskschd.msc`)
2. Create New Task:
   - **General Tab:**
     - Name: `GeminiBridge`
     - Run whether user is logged on or not: ☐ (unchecked for user-level)
     - Run with highest privileges: ☑
   - **Triggers Tab:**
     - New → Begin the task: `At startup`
     - Delay task for: `30 seconds` (give Docker time to start)
   - **Actions Tab:**
     - Action: `Start a program`
     - Program: `C:\path\to\GeminiBridge\.venv\Scripts\python.exe`
     - Arguments: `main.py`
     - Start in: `C:\path\to\GeminiBridge`
   - **Conditions Tab:**
     - Start only if computer is on AC power: ☐ (unchecked)
   - **Settings Tab:**
     - Allow task to be run on demand: ☑
     - If task fails, restart every: `1 minute` (max 3 attempts)

#### 5. Manage Windows Service

```powershell
# View task status
Get-ScheduledTask -TaskName "GeminiBridge"
Get-ScheduledTaskInfo -TaskName "GeminiBridge"

# Start task manually
Start-ScheduledTask -TaskName "GeminiBridge"

# Stop task
Stop-ScheduledTask -TaskName "GeminiBridge"

# Disable auto-start
Disable-ScheduledTask -TaskName "GeminiBridge"

# Enable auto-start
Enable-ScheduledTask -TaskName "GeminiBridge"

# Remove task
Unregister-ScheduledTask -TaskName "GeminiBridge" -Confirm:$false

# Check if application is running
Get-Process python* | Where-Object {$_.Path -like "*GeminiBridge*"}

# View application logs
Get-Content -Path ".\logs\gemini-bridge-$(Get-Date -Format 'yyyy-MM-dd').log" -Tail 50 -Wait
```

#### 6. Windows Firewall Configuration

```powershell
# Allow inbound connections (if needed for remote access)
New-NetFirewallRule -DisplayName "GeminiBridge" `
    -Direction Inbound `
    -LocalPort 11434 `
    -Protocol TCP `
    -Action Allow

# Remove firewall rule
Remove-NetFirewallRule -DisplayName "GeminiBridge"
```

#### 7. Troubleshooting Windows Deployment

**Task doesn't start:**
- Check Docker Desktop is running
- Verify Python virtual environment exists
- Check Task Scheduler event logs: Event Viewer → Task Scheduler History

**Application crashes:**
- Check logs in `logs/` directory
- Verify `.env` configuration is correct
- Test manual start: `.venv\Scripts\python main.py`

**Docker conflicts:**
- Ensure Docker Desktop is fully started before GeminiBridge
- Consider increasing `CLI_CLEANUP_WAIT_MS` to 800-1000ms
- Reduce `MAX_CONCURRENT_REQUESTS` to 5-8

### Docker Deployment

Deploy GeminiBridge in a Docker container.

#### 1. Create Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    docker.io \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Gemini CLI
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g @google/generative-ai-cli

# Create app directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 geminibridge && \
    chown -R geminibridge:geminibridge /app

# Switch to non-root user
USER geminibridge

# Expose port
EXPOSE 11434

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:11434/health || exit 1

# Run application
CMD ["python", "main.py"]
```

#### 2. Build Image

```bash
# Build image
docker build -t geminibridge:latest .

# Tag for registry
docker tag geminibridge:latest yourusername/geminibridge:v2.0.0
```

#### 3. Run Container

```bash
# Run with environment variables
docker run -d \
  --name geminibridge \
  -p 11434:11434 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/logs:/app/logs \
  -e BEARER_TOKEN="your-secure-token" \
  -e SECURITY_STRICT_MODE=true \
  -e LOG_LEVEL=INFO \
  --restart unless-stopped \
  geminibridge:latest

# View logs
docker logs -f geminibridge

# Check health
docker exec geminibridge curl http://localhost:11434/health
```

### Docker Compose

Deploy GeminiBridge with Docker Compose.

#### Create `docker-compose.yml`

```yaml
version: '3.8'

services:
  geminibridge:
    build: .
    container_name: geminibridge
    ports:
      - "11434:11434"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./logs:/app/logs
      - ./.env:/app/.env:ro
    environment:
      - PORT=11434
      - HOST=0.0.0.0
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
    networks:
      - geminibridge-net

networks:
  geminibridge-net:
    driver: bridge
```

#### Deploy with Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Scale (multiple instances)
docker-compose up -d --scale geminibridge=3
```

### Kubernetes

Deploy GeminiBridge on Kubernetes.

#### 1. Create Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: geminibridge
```

#### 2. Create Secret

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: geminibridge-secret
  namespace: geminibridge
type: Opaque
stringData:
  bearer-token: "your-secure-token-here"
```

#### 3. Create ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: geminibridge-config
  namespace: geminibridge
data:
  PORT: "11434"
  HOST: "0.0.0.0"
  LOG_LEVEL: "INFO"
  LOG_RETENTION_DAYS: "30"
  MAX_CONCURRENT_REQUESTS: "10"
  SECURITY_STRICT_MODE: "true"
```

#### 4. Create Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: geminibridge
  namespace: geminibridge
spec:
  replicas: 3
  selector:
    matchLabels:
      app: geminibridge
  template:
    metadata:
      labels:
        app: geminibridge
    spec:
      containers:
      - name: geminibridge
        image: yourusername/geminibridge:v2.0.0
        ports:
        - containerPort: 11434
          name: http
        env:
        - name: BEARER_TOKEN
          valueFrom:
            secretKeyRef:
              name: geminibridge-secret
              key: bearer-token
        envFrom:
        - configMapRef:
            name: geminibridge-config
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 11434
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 11434
          initialDelaySeconds: 10
          periodSeconds: 5
        volumeMounts:
        - name: docker-sock
          mountPath: /var/run/docker.sock
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: docker-sock
        hostPath:
          path: /var/run/docker.sock
      - name: logs
        emptyDir: {}
```

#### 5. Create Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: geminibridge
  namespace: geminibridge
spec:
  selector:
    app: geminibridge
  ports:
  - protocol: TCP
    port: 11434
    targetPort: 11434
  type: ClusterIP
```

#### 6. Create Ingress (Optional)

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: geminibridge
  namespace: geminibridge
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: geminibridge-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: geminibridge
            port:
              number: 11434
```

#### Deploy to Kubernetes

```bash
# Apply all resources
kubectl apply -f namespace.yaml
kubectl apply -f secret.yaml
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml

# Check deployment status
kubectl get pods -n geminibridge
kubectl get svc -n geminibridge

# View logs
kubectl logs -f deployment/geminibridge -n geminibridge

# Scale deployment
kubectl scale deployment geminibridge --replicas=5 -n geminibridge
```

### Cloud Platforms

#### AWS (Elastic Beanstalk)

```bash
# Install EB CLI
pip install awsebcli

# Initialize EB application
eb init -p python-3.12 geminibridge

# Create environment
eb create geminibridge-prod

# Deploy
eb deploy

# Set environment variables
eb setenv BEARER_TOKEN="your-token" SECURITY_STRICT_MODE=true

# Open application
eb open
```

#### Google Cloud (Cloud Run)

```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT_ID/geminibridge

# Deploy to Cloud Run
gcloud run deploy geminibridge \
  --image gcr.io/PROJECT_ID/geminibridge \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars BEARER_TOKEN=your-token,SECURITY_STRICT_MODE=true

# View service URL
gcloud run services describe geminibridge
```

#### Azure (Container Instances)

```bash
# Create resource group
az group create --name geminibridge-rg --location eastus

# Create container
az container create \
  --resource-group geminibridge-rg \
  --name geminibridge \
  --image yourusername/geminibridge:v2.0.0 \
  --dns-name-label geminibridge-unique \
  --ports 11434 \
  --environment-variables \
    BEARER_TOKEN=your-token \
    SECURITY_STRICT_MODE=true

# Get FQDN
az container show \
  --resource-group geminibridge-rg \
  --name geminibridge \
  --query ipAddress.fqdn
```

## Configuration

### Reverse Proxy (nginx)

Configure nginx as reverse proxy:

```nginx
# /etc/nginx/sites-available/geminibridge
upstream geminibridge {
    server 127.0.0.1:11434;
}

server {
    listen 80;
    listen [::]:80;
    server_name api.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.yourdomain.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    # Logging
    access_log /var/log/nginx/geminibridge_access.log;
    error_log /var/log/nginx/geminibridge_error.log;

    location / {
        proxy_pass http://geminibridge;
        proxy_http_version 1.1;

        # Headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Streaming support
        proxy_buffering off;
        proxy_cache off;
    }

    # Health check endpoint (no auth required)
    location /health {
        proxy_pass http://geminibridge/health;
        access_log off;
    }
}
```

Enable and restart nginx:

```bash
sudo ln -s /etc/nginx/sites-available/geminibridge /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Firewall Configuration

```bash
# Allow HTTPS
sudo ufw allow 443/tcp

# Allow SSH (for management)
sudo ufw allow 22/tcp

# Block direct access to application port
sudo ufw deny 11434/tcp

# Enable firewall
sudo ufw enable
```

## Monitoring

### Health Check Monitoring

```bash
# Simple health check script
#!/bin/bash
# /usr/local/bin/check-geminibridge.sh

HEALTH_URL="http://localhost:11434/health"
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_URL)

if [ "$RESPONSE" -eq 200 ]; then
    echo "GeminiBridge is healthy"
    exit 0
else
    echo "GeminiBridge is unhealthy (HTTP $RESPONSE)"
    exit 1
fi
```

### Prometheus Metrics (Future)

Example metrics endpoint structure:

```
# TYPE geminibridge_requests_total counter
geminibridge_requests_total{status="success"} 1523
geminibridge_requests_total{status="error"} 12

# TYPE geminibridge_queue_active gauge
geminibridge_queue_active 2

# TYPE geminibridge_queue_queued gauge
geminibridge_queue_queued 0

# TYPE geminibridge_execution_time_ms histogram
geminibridge_execution_time_ms_bucket{le="100"} 543
geminibridge_execution_time_ms_bucket{le="500"} 1421
geminibridge_execution_time_ms_bucket{le="1000"} 1523
```

### Log Aggregation

Configure centralized logging with ELK stack:

```yaml
# filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /opt/geminibridge/logs/*.log
  json.keys_under_root: true
  json.add_error_key: true

output.elasticsearch:
  hosts: ["localhost:9200"]
  index: "geminibridge-%{+yyyy.MM.dd}"
```

## Backup and Recovery

### Configuration Backup

```bash
# Backup script
#!/bin/bash
BACKUP_DIR="/backup/geminibridge"
DATE=$(date +%Y%m%d_%H%M%S)

# Backup .env
cp /opt/geminibridge/.env $BACKUP_DIR/.env.$DATE

# Backup model mappings
cp /opt/geminibridge/config/models.json $BACKUP_DIR/models.json.$DATE

# Backup logs (last 7 days)
tar -czf $BACKUP_DIR/logs.$DATE.tar.gz /opt/geminibridge/logs/*.log
```

### Disaster Recovery

1. **Backup Required Files:**
   - `.env` (configuration)
   - `config/models.json` (model mappings)
   - Recent logs (for audit)

2. **Recovery Steps:**
   ```bash
   # Restore configuration
   cp /backup/geminibridge/.env.latest /opt/geminibridge/.env
   cp /backup/geminibridge/models.json.latest /opt/geminibridge/config/models.json

   # Restart service
   sudo systemctl restart geminibridge
   ```

## Scaling

### Vertical Scaling

Increase resources for single instance:

```bash
# Update systemd service
# Increase MAX_CONCURRENT_REQUESTS
echo "MAX_CONCURRENT_REQUESTS=20" >> /opt/geminibridge/.env

# Restart service
sudo systemctl restart geminibridge
```

### Horizontal Scaling

Deploy multiple instances with load balancer:

```nginx
# nginx load balancer
upstream geminibridge_cluster {
    least_conn;
    server 10.0.1.10:11434 weight=1;
    server 10.0.1.11:11434 weight=1;
    server 10.0.1.12:11434 weight=1;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://geminibridge_cluster;
    }
}
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u geminibridge -n 50

# Verify Python version
/opt/geminibridge/.venv/bin/python --version

# Check file permissions
ls -la /opt/geminibridge/.env

# Verify Docker is running
sudo systemctl status docker
```

### High Memory Usage

```bash
# Check process memory
ps aux | grep python

# Reduce concurrent requests
echo "MAX_CONCURRENT_REQUESTS=3" >> /opt/geminibridge/.env
sudo systemctl restart geminibridge
```

### Docker Container Conflicts

```bash
# List conflicting containers
docker ps -a | grep sandbox

# Clean up all sandbox containers
docker ps -a | grep sandbox | awk '{print $1}' | xargs docker rm -f

# Restart service
sudo systemctl restart geminibridge
```

### SSL/TLS Issues

```bash
# Renew Let's Encrypt certificate
sudo certbot renew

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

---

For additional help:
- [Architecture Guide](ARCHITECTURE.md)
- [Security Guide](SECURITY.md)
- [API Documentation](API.md)
