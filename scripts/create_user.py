#!/usr/bin/env python3
"""
Script to create a new user in TheOrb system.
"""

import sys
from app import app
from models import User, UserProfile
from database import db


def create_user(username, email, full_name, password):
    """Create a new user with the specified details."""
    with app.app_context():
        # Check if user already exists
        existing = User.query.filter_by(username=username).first()
        if existing:
            print(f"❌ User '{username}' already exists!")
            return False

        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            print(f"❌ Email '{email}' already registered!")
            return False

        # Create new user
        user = User(
            username=username,
            email=email,
            full_name=full_name
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Create user profile
        profile = UserProfile(
            user_id=user.id,
            name=full_name.split()[0] if full_name else username,
            lastname=' '.join(full_name.split()[1:]) if full_name and len(full_name.split()) > 1 else '',
            email=email
        )
        db.session.add(profile)
        db.session.commit()

        print(f"✅ User created successfully!")
        print(f"   Username: {username}")
        print(f"   Email: {email}")
        print(f"   Full Name: {full_name}")
        print(f"   User ID: {user.id}")
        print(f"   Vector Store Prefix: {user.get_vector_store_prefix()}")

        return True


def main():
    """Main function to handle user input."""
    print("👤 Create New TheOrb User")
    print("=" * 30)

    if len(sys.argv) == 5:
        # Command line arguments provided
        username, email, full_name, password = sys.argv[1:]
        create_user(username, email, full_name, password)
    else:
        # Interactive mode
        print("Enter user details (or press Ctrl+C to cancel):")
        try:
            username = input("Username: ").strip()
            email = input("Email: ").strip()
            full_name = input("Full Name: ").strip()
            password = input("Password: ").strip()

            if not all([username, email, password]):
                print("❌ Username, email, and password are required!")
                return

            create_user(username, email, full_name, password)

            print("\n🚀 Ready to use! Start the app with:")
            print(f"   python3 app.py --bypass-auth --user {username} --debug")
            print("   OR")
            print("   python3 app.py  # Then login normally")

        except KeyboardInterrupt:
            print("\n👋 Cancelled")


if __name__ == "__main__":
    main()