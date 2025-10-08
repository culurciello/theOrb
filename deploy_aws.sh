#!/bin/bash
# Quick deployment script for AWS EC2

set -e

echo "🚀 TheOrb AWS Deployment Script"
echo "================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Please do not run as root${NC}"
    exit 1
fi

# Get current directory
APP_DIR=$(pwd)
echo "📁 Application directory: $APP_DIR"

# Step 1: Install system dependencies
echo -e "\n${YELLOW}📦 Installing system dependencies...${NC}"
if [ -f /etc/debian_version ]; then
    sudo apt update
    sudo apt install -y python3-pip python3-venv nginx mysql-server python3-dev build-essential libmysqlclient-dev
elif [ -f /etc/redhat-release ]; then
    sudo yum update -y
    sudo yum install -y python3-pip python3-venv nginx mysql-server python3-devel gcc gcc-c++ mysql-devel
else
    echo -e "${RED}❌ Unsupported OS${NC}"
    exit 1
fi

# Step 2: Create virtual environment
echo -e "\n${YELLOW}🐍 Setting up Python virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

# Step 3: Install Python packages
echo -e "\n${YELLOW}📚 Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Step 4: Create logs directory
echo -e "\n${YELLOW}📝 Creating logs directory...${NC}"
mkdir -p logs

# Step 5: Setup .env file
echo -e "\n${YELLOW}⚙️  Configuring environment...${NC}"
if [ ! -f .env ]; then
    echo "Creating .env file..."
    cat > .env << EOL
# Database
MYSQL_USER=orvin
MYSQL_PASSWORD=orvin
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=appdb

# Flask
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
FLASK_ENV=production

# Authentication
BYPASS_AUTH=false
DEFAULT_TEST_USER=admin
EOL
    echo -e "${GREEN}✅ Created .env file${NC}"
else
    echo -e "${GREEN}✅ .env file already exists${NC}"
fi

# Step 6: Setup MySQL
echo -e "\n${YELLOW}🗄️  Setting up MySQL database...${NC}"
read -p "Have you created the MySQL database and user? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Please create the database first:"
    echo "  sudo mysql -u root -p"
    echo "  CREATE DATABASE appdb;"
    echo "  CREATE USER 'orvin'@'localhost' IDENTIFIED BY 'orvin';"
    echo "  GRANT ALL PRIVILEGES ON appdb.* TO 'orvin'@'localhost';"
    echo "  FLUSH PRIVILEGES;"
    echo "  EXIT;"
    exit 1
fi

# Step 7: Initialize database
echo -e "\n${YELLOW}🔧 Initializing database tables...${NC}"
python3 << EOF
from app import app, db
with app.app_context():
    db.create_all()
    print("✅ Database tables created")
EOF

# Step 8: Setup systemd service
echo -e "\n${YELLOW}⚙️  Setting up systemd service...${NC}"
# Update service file with current user and path
CURRENT_USER=$(whoami)
SERVICE_FILE="theorb.service"
TEMP_SERVICE="/tmp/theorb.service"

sed -e "s|User=ubuntu|User=$CURRENT_USER|g" \
    -e "s|Group=ubuntu|Group=$CURRENT_USER|g" \
    -e "s|/home/ubuntu/theOrb-web|$APP_DIR|g" \
    "$SERVICE_FILE" > "$TEMP_SERVICE"

sudo cp "$TEMP_SERVICE" /etc/systemd/system/theorb.service
rm "$TEMP_SERVICE"

sudo systemctl daemon-reload
sudo systemctl enable theorb.service

echo -e "${GREEN}✅ Service configured${NC}"

# Step 9: Setup Nginx
echo -e "\n${YELLOW}🌐 Setting up Nginx...${NC}"
read -p "Enter your domain name (or press Enter to skip): " DOMAIN_NAME

if [ -n "$DOMAIN_NAME" ]; then
    sudo tee /etc/nginx/sites-available/theorb > /dev/null << EOL
upstream theorb_app {
    server 127.0.0.1:3000;
}

server {
    listen 80;
    server_name $DOMAIN_NAME www.$DOMAIN_NAME;

    client_max_body_size 100M;

    location / {
        proxy_pass http://theorb_app;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;

        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";

        proxy_connect_timeout 120;
        proxy_send_timeout 120;
        proxy_read_timeout 120;
    }

    location /static {
        alias $APP_DIR/static;
        expires 30d;
    }

    location /uploads {
        alias $APP_DIR/uploads;
        expires 7d;
    }
}
EOL

    sudo ln -sf /etc/nginx/sites-available/theorb /etc/nginx/sites-enabled/
    sudo nginx -t && sudo systemctl restart nginx
    echo -e "${GREEN}✅ Nginx configured for $DOMAIN_NAME${NC}"
else
    echo "⏭️  Skipping Nginx configuration"
fi

# Step 10: Start services
echo -e "\n${YELLOW}🚀 Starting services...${NC}"
sudo systemctl start theorb.service

# Check service status
sleep 2
if sudo systemctl is-active --quiet theorb.service; then
    echo -e "${GREEN}✅ TheOrb service is running!${NC}"
else
    echo -e "${RED}❌ TheOrb service failed to start${NC}"
    echo "Check logs with: sudo journalctl -u theorb.service -n 50"
    exit 1
fi

# Summary
echo -e "\n${GREEN}================================================${NC}"
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Service management commands:"
echo "  sudo systemctl status theorb   # Check status"
echo "  sudo systemctl restart theorb  # Restart"
echo "  sudo systemctl stop theorb     # Stop"
echo "  sudo systemctl start theorb    # Start"
echo ""
echo "View logs:"
echo "  sudo journalctl -u theorb -f           # Service logs"
echo "  tail -f logs/gunicorn-error.log        # Error logs"
echo "  tail -f logs/gunicorn-access.log       # Access logs"
echo ""
if [ -n "$DOMAIN_NAME" ]; then
    echo "🌐 Your application is available at:"
    echo "   http://$DOMAIN_NAME"
    echo ""
    echo "To enable HTTPS, run:"
    echo "   sudo certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME"
else
    echo "🌐 Your application is available at:"
    echo "   http://$(curl -s ifconfig.me):80"
fi
echo ""
