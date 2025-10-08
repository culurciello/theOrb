# Quick Start Guide - Running on AWS with Gunicorn

## Automatic Deployment (Recommended)

```bash
# Run the deployment script
./deploy_aws.sh
```

This script will:
- Install system dependencies
- Setup Python virtual environment
- Configure MySQL database
- Setup systemd service
- Configure Nginx
- Start the application

## Manual Deployment

### 1. Quick Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file with your MySQL credentials
cat > .env << EOL
MYSQL_USER=orvin
MYSQL_PASSWORD=orvin
MYSQL_HOST=localhost
MYSQL_DATABASE=appdb
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
EOL

# Create logs directory
mkdir -p logs

# Initialize database
python3 -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### 2. Run with Gunicorn

**Development (foreground)**:
```bash
gunicorn --config gunicorn_config.py wsgi:application
```

**Production (with systemd)**:
```bash
# Copy and edit service file
sudo cp theorb.service /etc/systemd/system/
sudo nano /etc/systemd/system/theorb.service  # Update paths and user

# Start service
sudo systemctl daemon-reload
sudo systemctl enable theorb
sudo systemctl start theorb
```

### 3. Test the Application

```bash
# Test locally
curl http://localhost:3000/login

# Check service status
sudo systemctl status theorb

# View logs
sudo journalctl -u theorb -f
```

## Common Commands

### Service Management
```bash
# Start
sudo systemctl start theorb

# Stop
sudo systemctl stop theorb

# Restart
sudo systemctl restart theorb

# Status
sudo systemctl status theorb

# Enable on boot
sudo systemctl enable theorb
```

### View Logs
```bash
# Live service logs
sudo journalctl -u theorb -f

# Last 100 lines
sudo journalctl -u theorb -n 100

# Gunicorn logs
tail -f logs/gunicorn-error.log
tail -f logs/gunicorn-access.log
tail -f logs/app.log
```

### Update Application
```bash
cd /home/ubuntu/theOrb-web
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart theorb
```

## Configuration Files

- **gunicorn_config.py** - Gunicorn settings (workers, timeout, logging)
- **wsgi.py** - WSGI entry point
- **theorb.service** - Systemd service definition
- **.env** - Environment variables (MySQL, secrets)

## Environment Variables

Set in `.env` file:
```bash
MYSQL_USER=orvin
MYSQL_PASSWORD=your_password
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=appdb
SECRET_KEY=your-secret-key
BYPASS_AUTH=false
```

## Running Without Systemd (Testing)

```bash
# Simple gunicorn
gunicorn wsgi:application

# With config file
gunicorn --config gunicorn_config.py wsgi:application

# Custom port
gunicorn --bind 0.0.0.0:8000 wsgi:application

# With auto-reload (development)
gunicorn --reload wsgi:application
```

## Nginx Configuration

Create `/etc/nginx/sites-available/theorb`:
```nginx
upstream theorb_app {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://theorb_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/theorb /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Troubleshooting

### Service won't start
```bash
sudo journalctl -u theorb -n 50
tail -100 logs/gunicorn-error.log
```

### Database connection error
```bash
# Test MySQL connection
mysql -u orvin -p appdb

# Check MySQL is running
sudo systemctl status mysql
```

### Port already in use
```bash
# Find process using port 3000
sudo lsof -i :3000
sudo kill <PID>
```

### Permission denied
```bash
sudo chown -R $USER:$USER /home/ubuntu/theOrb-web
```

## Performance Tuning

Edit `gunicorn_config.py`:
```python
# More workers for more traffic
workers = 8

# Longer timeout for slow requests
timeout = 300

# For I/O-bound tasks
worker_class = 'gevent'
```

## Security Checklist

- [ ] Change default MySQL password
- [ ] Set strong SECRET_KEY
- [ ] Set BYPASS_AUTH=false for production
- [ ] Enable firewall (ufw/iptables)
- [ ] Setup SSL with Let's Encrypt
- [ ] Regular backups of database
- [ ] Keep system packages updated

## Monitoring

```bash
# CPU and memory
htop

# Disk usage
df -h

# Active connections
netstat -plant | grep :3000

# Gunicorn workers
ps aux | grep gunicorn
```
