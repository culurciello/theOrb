#!/usr/bin/env python3
"""
Convenience script to start TheOrb with different user configurations.
This provides easy shortcuts for common usage patterns.
"""

import subprocess
import sys
import os

def show_usage():
    """Show usage instructions."""
    print("🚀 TheOrb Application Starter")
    print("=" * 40)
    print()
    print("Quick start options:")
    print()
    print("1. 👤 Start with culurciello user (bypass auth):")
    print("   python3 start_app.py culurciello")
    print()
    print("2. 👤 Start with any user (bypass auth):")
    print("   python3 start_app.py <username>")
    print()
    print("3. 🔐 Start with full authentication:")
    print("   python3 start_app.py auth")
    print()
    print("4. 🐛 Start with debug mode:")
    print("   python3 start_app.py culurciello --debug")
    print()
    print("5. 🌐 Start on custom port:")
    print("   python3 start_app.py culurciello --port 8000")
    print()
    print("Advanced usage (direct app.py):")
    print("   python3 app.py --bypass-auth --user culurciello")
    print("   python3 app.py --bypass-auth --user culurciello --debug")
    print("   python3 app.py --bypass-auth --user culurciello --port 8080")
    print("   python3 app.py  # Full authentication mode")

def start_with_user(username, extra_args=None):
    """Start the app with a specific user."""
    cmd = ['python3', 'app.py', '--bypass-auth', '--user', username]

    if extra_args:
        cmd.extend(extra_args)

    print(f"🚀 Starting TheOrb with user: {username}")
    if extra_args:
        print(f"🔧 Extra arguments: {' '.join(extra_args)}")

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 TheOrb stopped")

def start_with_auth():
    """Start the app with full authentication."""
    cmd = ['python3', 'app.py']

    print("🔐 Starting TheOrb with full authentication")
    print("🌐 Go to http://localhost:3000/login to sign in")

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n👋 TheOrb stopped")

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        show_usage()
        return

    command = sys.argv[1].lower()
    extra_args = sys.argv[2:] if len(sys.argv) > 2 else None

    if command == 'help' or command == '--help' or command == '-h':
        show_usage()
    elif command == 'auth':
        start_with_auth()
    elif command in ['culurciello', 'testuser', 'admin'] or not command.startswith('-'):
        # Treat as username
        start_with_user(command, extra_args)
    else:
        print(f"❌ Unknown command: {command}")
        show_usage()

if __name__ == '__main__':
    main()