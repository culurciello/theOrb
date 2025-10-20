#!/bin/bash

# Security Setup Script for theOrb-web
# This script helps set up security configurations

echo "========================================="
echo "  theOrb-web Security Setup"
echo "========================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  No .env file found. Creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "📝 IMPORTANT: Edit .env file and update the following:"
    echo "   - SECRET_KEY (generate a strong key)"
    echo "   - Database credentials"
    echo "   - API keys"
    echo "   - ALLOWED_ORIGINS for your domain"
    echo ""
else
    echo "✅ .env file exists"
fi

# Generate a strong SECRET_KEY
echo "🔑 Generating a strong SECRET_KEY..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo ""
echo "Generated SECRET_KEY:"
echo "$SECRET_KEY"
echo ""
echo "📝 Add this to your .env file as:"
echo "SECRET_KEY=$SECRET_KEY"
echo ""

# Check Python version
echo "🐍 Checking Python version..."
python3 --version
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install --upgrade pip
pip3 install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Check for vulnerabilities
echo "🔍 Checking for known vulnerabilities..."
if command -v safety &> /dev/null; then
    safety check --json || echo "⚠️  Some vulnerabilities found. Review and update."
else
    echo "ℹ️  Install 'safety' to check for vulnerabilities: pip install safety"
fi
echo ""

# Create logs directory
echo "📁 Creating logs directory..."
mkdir -p logs
chmod 755 logs
echo "✅ Logs directory created"
echo ""

# Summary
echo "========================================="
echo "  Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your configuration"
echo "2. Update SECRET_KEY with the generated key above"
echo "3. Configure ALLOWED_ORIGINS for your domain"
echo "4. Run the application: python3 app.py"
echo ""
echo "For production deployment:"
echo "- Set FLASK_ENV=production"
echo "- Use a production-grade secret key"
echo "- Enable HTTPS"
echo "- Review SECURITY.md for best practices"
echo ""
echo "📖 Read SECURITY.md for complete security documentation"
echo ""
