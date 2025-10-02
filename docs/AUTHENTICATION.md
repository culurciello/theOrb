# TheOrb Multi-User Authentication Guide

This document explains how to use TheOrb's multi-user authentication system, including the bypass options for development and testing.

## Quick Start

### 🚀 For Development/Testing (Bypass Authentication)

Use these commands to start TheOrb without needing to login:

```bash
# Start with culurciello user (recommended)
python3 app.py --bypass-auth --user culurciello

# Start with culurciello user in debug mode
python3 app.py --bypass-auth --user culurciello --debug

# Start with any username
python3 app.py --bypass-auth --user your_username

# Start on different port
python3 app.py --bypass-auth --user culurciello --port 8080
```

### 🔐 For Production (Full Authentication)

```bash
# Start with full authentication system
python3 app.py

# Then visit http://localhost:3000/login to sign in or register
```

## Convenience Script

For even easier usage, use the `start_app.py` convenience script:

```bash
# Quick start with culurciello user
python3 start_app.py culurciello

# Start with any user
python3 start_app.py your_username

# Start with full authentication
python3 start_app.py auth

# Start with debug mode
python3 start_app.py culurciello --debug

# Start on custom port
python3 start_app.py culurciello --port 8080
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--bypass-auth` | Skip login, use specified user directly | false |
| `--user USERNAME` | Username for bypass mode | culurciello |
| `--port PORT` | Port to run on | 3000 |
| `--debug` | Enable debug mode | false |

## User Data Isolation

Each user has completely isolated data:

- **Collections**: User-specific document collections
- **Conversations**: Private chat histories
- **Vector Store**: Isolated embeddings and search (`user_5_collection_name`)
- **Settings**: Individual user preferences and API keys

## Authentication Features

### ✅ Implemented Features

- **User Registration**: Create new accounts with username/email/password
- **Secure Login**: Password hashing with Werkzeug
- **Session Management**: Flask-Login integration with "Remember Me"
- **User Profiles**: Automatic profile creation with user data
- **Password Security**: Secure password hashing and validation

### 🚀 Bypass Mode Features

- **Automatic User Creation**: Creates user if it doesn't exist
- **Direct Access**: Skip login entirely for development
- **Flexible Users**: Use any username with `--user` parameter
- **Debug Integration**: Works seamlessly with Flask debug mode

## Environment Variables

You can also use environment variables instead of command line arguments:

```bash
# Set bypass mode
export BYPASS_AUTH=true
export DEFAULT_TEST_USER=culurciello

# Start the app
python3 app.py
```

## Database Management

### User Data Structure

```
User (culurciello)
├── Collections (user_5_*)
│   ├── Documents
│   └── Vector Embeddings
├── Conversations
│   └── Messages
└── User Profile
    └── API Keys
```

### Database Reset

If you need to reset the database:

```bash
# Remove database files
rm -f orb.db
rm -rf instance/

# Restart app (will recreate database)
python3 app.py --bypass-auth --user culurciello
```

## Development Workflow

### Recommended Development Setup

1. **Start in bypass mode**:
   ```bash
   python3 app.py --bypass-auth --user culurciello --debug
   ```

2. **Access the application**:
   - Go to `http://localhost:3000/`
   - No login required - automatically logged in as culurciello

3. **Test different users**:
   ```bash
   python3 app.py --bypass-auth --user testuser --debug
   ```

### Testing Authentication

1. **Test full auth system**:
   ```bash
   python3 app.py
   # Visit http://localhost:3000/login
   ```

2. **Create test account**:
   - Username: `testuser`
   - Email: `test@example.com`
   - Password: `password123`

3. **Test login/logout flow**

## Troubleshooting

### Common Issues

**Problem**: Can't login / create account
**Solution**: Use bypass mode for development:
```bash
python3 app.py --bypass-auth --user culurciello
```

**Problem**: Database errors
**Solution**: Reset database:
```bash
rm -f orb.db && python3 app.py --bypass-auth --user culurciello
```

**Problem**: User not found
**Solution**: App automatically creates users in bypass mode

**Problem**: Permission errors
**Solution**: Check file permissions and database access

### Debug Mode

Enable debug mode for detailed error messages:

```bash
python3 app.py --bypass-auth --user culurciello --debug
```

## Security Notes

### Development vs Production

- **Development**: Use `--bypass-auth` for convenience
- **Production**: Always use full authentication (`python3 app.py`)

### Password Security

- Passwords are hashed using Werkzeug's secure methods
- No passwords are stored in plain text
- Session cookies are signed with Flask's secret key

### Data Isolation

- Users cannot access each other's data
- Vector store collections are prefixed by user ID
- Database queries are filtered by user ownership

## API Integration

When using the bypass mode, the authentication system automatically:

1. Creates the specified user if it doesn't exist
2. Sets up user profile and relationships
3. Configures vector store isolation
4. Enables all user-specific features

The API endpoints work the same way - they automatically get the current user context from the bypass system.

---

## Summary

**For quick development with culurciello user**:
```bash
python3 app.py --bypass-auth --user culurciello --debug
```

**For production with full authentication**:
```bash
python3 app.py
```

The bypass system solves the "can't login / make account" problem by allowing direct user specification via command line parameters.