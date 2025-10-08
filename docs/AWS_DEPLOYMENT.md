# AWS Deployment Guide with Gunicorn

## Prerequisites

- AWS EC2 instance (Ubuntu 20.04/22.04 or Amazon Linux 2)
- MySQL installed and running
- Python 3.8+ installed
- Domain name (optional, for SSL)

## Step 1: Prepare EC2 Instance

### Update system packages
```bash
sudo apt update && sudo apt upgrade -y  # Ubuntu
# OR
sudo yum update -y  # Amazon Linux
```

### Install required system packages
```bash
# Ubuntu
sudo apt install python3-pip python3-venv nginx git mysql-server -y

# Amazon Linux
sudo yum install python3-pip python3-venv nginx git mysql-server -y
```

### Install Python development tools
```bash
# Ubuntu
sudo apt install python3-dev build-essential libmysqlclient-dev -y

# Amazon Linux
sudo yum install python3-devel gcc gcc-c++ mysql-devel -y
```

## Step 2: Clone and Setup Application

### Clone repository
```bash
cd /home/ubuntu
git clone <your-repo-url> theOrb-web
cd theOrb-web
```

### Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Python dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 3: Setup MySQL Database

### Secure MySQL installation
```bash
sudo mysql_secure_installation
```

### Create database and user
```bash
sudo mysql -u root -p
```

```sql
CREATE DATABASE appdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'orvin'@'localhost' IDENTIFIED BY 'your_secure_password';
GRANT ALL PRIVILEGES ON appdb.* TO 'orvin'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## Step 4: Configure Environment Variables

### Create .env file
```bash
cd /home/ubuntu/theOrb-web
nano .env
```

Add the following:
```bash
# Database
MYSQL_USER=orvin
MYSQL_PASSWORD=your_secure_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=appdb

# Flask
SECRET_KEY=your-very-long-random-secret-key-here
FLASK_ENV=production

# Authentication (set to false for production)
BYPASS_AUTH=false
DEFAULT_TEST_USER=admin

# Optional: API Keys
# ANTHROPIC_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
```

### Generate a secure secret key
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## Step 5: Create Logs Directory

```bash
mkdir -p /home/ubuntu/theOrb-web/logs
```

## Step 6: Setup Systemd Service

### Copy service file
```bash
sudo cp theorb.service /etc/systemd/system/
```

### Edit service file with your paths
```bash
sudo nano /etc/systemd/system/theorb.service
```

Update these lines if needed:
- `User=ubuntu` (change to your username)
- `WorkingDirectory=/home/ubuntu/theOrb-web`
- `Environment` variables
- Path to gunicorn binary

### Reload systemd and enable service
```bash
sudo systemctl daemon-reload
sudo systemctl enable theorb.service
sudo systemctl start theorb.service
```

### Check service status
```bash
sudo systemctl status theorb.service
```

### View logs
```bash
# Service logs
sudo journalctl -u theorb.service -f

# Application logs
tail -f /home/ubuntu/theOrb-web/logs/gunicorn-error.log
tail -f /home/ubuntu/theOrb-web/logs/gunicorn-access.log
```

## Step 7: Configure Nginx

### Create Nginx configuration
```bash
sudo nano /etc/nginx/sites-available/theorb
```

Add the following:
```nginx
upstream theorb_app {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://theorb_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;

        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeout settings
        proxy_connect_timeout 120;
        proxy_send_timeout 120;
        proxy_read_timeout 120;
    }

    location /static {
        alias /home/ubuntu/theOrb-web/static;
        expires 30d;
    }

    location /uploads {
        alias /home/ubuntu/theOrb-web/uploads;
        expires 7d;
    }
}
```

### Enable the site
```bash
sudo ln -s /etc/nginx/sites-available/theorb /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Step 8: Setup SSL with Let's Encrypt (Optional)

### Install Certbot
```bash
# Ubuntu
sudo apt install certbot python3-certbot-nginx -y

# Amazon Linux
sudo yum install certbot python3-certbot-nginx -y
```

### Obtain SSL certificate
```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Follow the prompts and certbot will automatically configure SSL.

## Step 9: Configure Firewall

### Ubuntu (UFW)
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### AWS Security Group
In AWS Console, add these inbound rules:
- SSH (22) - Your IP
- HTTP (80) - Anywhere
- HTTPS (443) - Anywhere

## Step 10: Initialize Database

### Test database connection
```bash
cd /home/ubuntu/theOrb-web
source venv/bin/activate
python3 -c "from app import app, db; app.app_context().push(); db.create_all(); print('Database initialized!')"
```

## Management Commands

### Restart application
```bash
sudo systemctl restart theorb.service
```

### Stop application
```bash
sudo systemctl stop theorb.service
```

### View logs
```bash
# Real-time logs
sudo journalctl -u theorb.service -f

# Application logs
tail -f logs/gunicorn-error.log
tail -f logs/app.log
```

### Update application
```bash
cd /home/ubuntu/theOrb-web
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart theorb.service
```

## Monitoring

### Check if application is running
```bash
curl http://localhost:3000/
```

### Monitor system resources
```bash
htop
# or
top
```

### Check Gunicorn workers
```bash
ps aux | grep gunicorn
```

## Troubleshooting

### Service won't start
```bash
# Check service status
sudo systemctl status theorb.service

# Check logs
sudo journalctl -u theorb.service -n 50

# Check Gunicorn logs
tail -100 logs/gunicorn-error.log
```

### Database connection issues
```bash
# Test MySQL connection
mysql -u orvin -p appdb

# Check if MySQL is running
sudo systemctl status mysql
```

### Permission issues
```bash
# Fix ownership
sudo chown -R ubuntu:ubuntu /home/ubuntu/theOrb-web

# Fix permissions
chmod -R 755 /home/ubuntu/theOrb-web
```

### Nginx issues
```bash
# Test Nginx config
sudo nginx -t

# Check Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

## Performance Tuning

### Adjust Gunicorn workers
Edit `gunicorn_config.py`:
```python
# Recommended: (2 x $num_cores) + 1
workers = 5  # for 2-core machine

# For CPU-bound tasks
worker_class = 'sync'

# For I/O-bound tasks (more concurrent requests)
worker_class = 'gevent'
workers = 20
```

### Increase timeout for long-running requests
Edit `gunicorn_config.py`:
```python
timeout = 300  # 5 minutes
```

### MySQL tuning
Edit `/etc/mysql/mysql.conf.d/mysqld.cnf`:
```ini
[mysqld]
max_connections = 200
innodb_buffer_pool_size = 1G  # Adjust based on RAM
```

## Backup Strategy

### Backup MySQL database
```bash
# Create backup
mysqldump -u orvin -p appdb > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
mysql -u orvin -p appdb < backup_20250101_120000.sql
```

### Backup uploaded files
```bash
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz uploads/
```

### Automated backups (crontab)
```bash
crontab -e
```

Add:
```bash
# Daily database backup at 2 AM
0 2 * * * mysqldump -u orvin -p'password' appdb > /home/ubuntu/backups/db_$(date +\%Y\%m\%d).sql

# Weekly files backup on Sunday at 3 AM
0 3 * * 0 tar -czf /home/ubuntu/backups/uploads_$(date +\%Y\%m\%d).tar.gz /home/ubuntu/theOrb-web/uploads/
```

## Quick Start Commands

```bash
# Start everything
sudo systemctl start mysql
sudo systemctl start theorb
sudo systemctl start nginx

# Stop everything
sudo systemctl stop nginx
sudo systemctl stop theorb

# Restart application
sudo systemctl restart theorb

# View logs
sudo journalctl -u theorb -f
```
