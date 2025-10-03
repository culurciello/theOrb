# Deployment Configuration for Subpages

This application can now be deployed on a subpage URL like `https://geocoolee.com/mynewpage/`.

## Environment Variables

Set these environment variables to configure the subpage deployment:

### Option 1: Using URL_PREFIX (Recommended)
```bash
export URL_PREFIX="/mynewpage"
export APPLICATION_ROOT="/mynewpage/"
```

### Option 2: Using APPLICATION_ROOT only
```bash
export APPLICATION_ROOT="/mynewpage/"
```

## Web Server Configuration

### For Nginx
```nginx
location /mynewpage/ {
    proxy_pass http://localhost:3000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

### For Apache (with mod_proxy)
```apache
ProxyPass /mynewpage/ http://localhost:3000/
ProxyPassReverse /mynewpage/ http://localhost:3000/
ProxyPreserveHost On
```

## Running the Application

### Development
```bash
export URL_PREFIX="/mynewpage"
export APPLICATION_ROOT="/mynewpage/"
python app.py
```

### Production (example with systemd)
```ini
# /etc/systemd/system/orb-web.service
[Unit]
Description=Orb Web Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/theOrb-web
Environment=URL_PREFIX=/mynewpage
Environment=APPLICATION_ROOT=/mynewpage/
Environment=DATABASE_URL=sqlite:///orb.db
ExecStart=/path/to/venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Testing the Configuration

1. Start the application with the environment variables set
2. Visit `http://localhost:3000/mynewpage/` (note the trailing slash)
3. All static files, API calls, and navigation should work correctly

## Notes

- **Static files**: Already configured with `url_for('static')` in templates
- **API calls**: Already using relative URLs (`/api/...`)
- **Internal navigation**: Uses relative paths and will work automatically
- **File serving**: Configured to work with the URL prefix

The application is now ready for subpage deployment!