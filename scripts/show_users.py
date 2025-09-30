#!/usr/bin/env python3
"""
Simple User List Script - Shows all registered users
Directly queries the SQLite database to show user accounts
"""

import sqlite3
import sys
import os
from datetime import datetime

def format_datetime(dt_str):
    """Format datetime string for display."""
    if not dt_str:
        return "Never"
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return dt_str

def show_all_users():
    """Show all users from the database."""
    db_path = 'instance/orb.db'

    if not os.path.exists(db_path):
        print("❌ Database file 'theorb.db' not found!")
        print("   Make sure you're running this from the correct directory.")
        return

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        cursor = conn.cursor()

        print("🔍 TheOrb User Management - User List")
        print("=" * 80)

        # Get all users
        cursor.execute("""
            SELECT id, username, email, full_name, is_active, is_admin,
                   created_at, last_login
            FROM user
            ORDER BY created_at DESC
        """)

        users = cursor.fetchall()

        if not users:
            print("📭 No users found in the database.")
            conn.close()
            return

        print(f"👥 Found {len(users)} registered user(s):\n")

        for i, user in enumerate(users, 1):
            print(f"🔢 User #{i}")
            print(f"   ID: {user['id']}")
            print(f"   Username: {user['username']}")
            print(f"   Email: {user['email']}")
            print(f"   Full Name: {user['full_name']}")
            print(f"   Password: [PROTECTED]")
            print(f"   Active: {'Yes' if user['is_active'] else 'No'}")
            print(f"   Admin: {'Yes' if user['is_admin'] else 'No'}")
            print(f"   Created: {format_datetime(user['created_at'])}")
            print(f"   Last Login: {format_datetime(user['last_login'])}")

            # Get collection count
            cursor.execute("SELECT COUNT(*) as count FROM collection WHERE user_id = ?", (user['id'],))
            collection_count = cursor.fetchone()['count']

            # Get conversation count
            cursor.execute("SELECT COUNT(*) as count FROM conversation WHERE user_id = ?", (user['id'],))
            conversation_count = cursor.fetchone()['count']

            print(f"   Collections: {collection_count}")
            print(f"   Conversations: {conversation_count}")

            # Get user profile if exists
            cursor.execute("SELECT * FROM user_profile WHERE user_id = ?", (user['id'],))
            profile = cursor.fetchone()

            if profile:
                print(f"   Profile: {profile['name']} {profile['lastname']}".strip())
                print(f"   Profile Email: {profile['email']}")
                print(f"   Profile Phone: {profile['phone'] or 'Not provided'}")
            else:
                print(f"   Profile: Not created")

            # Vector store prefix
            print(f"   Vector Store Prefix: 'user_{user['id']}_'")
            print("-" * 60)

        # Summary
        cursor.execute("SELECT COUNT(*) as count FROM user")
        total_users = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM collection")
        total_collections = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM conversation")
        total_conversations = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM user_profile")
        total_profiles = cursor.fetchone()['count']

        print(f"\n📊 Summary:")
        print(f"   Total Users: {total_users}")
        print(f"   Total Collections: {total_collections}")
        print(f"   Total Conversations: {total_conversations}")
        print(f"   Total Profiles: {total_profiles}")

        conn.close()

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def show_user_details(username_or_id):
    """Show detailed information for a specific user."""
    db_path = 'instance/orb.db'

    if not os.path.exists(db_path):
        print("❌ Database file 'theorb.db' not found!")
        return

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Try to find user by username or ID
        if username_or_id.isdigit():
            cursor.execute("SELECT * FROM user WHERE id = ?", (int(username_or_id),))
        else:
            cursor.execute("SELECT * FROM user WHERE username = ?", (username_or_id,))

        user = cursor.fetchone()

        if not user:
            print(f"❌ User '{username_or_id}' not found.")
            conn.close()
            return

        print(f"👤 Detailed User Information: {user['username']}")
        print("=" * 80)

        # Basic info
        print("📋 Basic Information:")
        print(f"   ID: {user['id']}")
        print(f"   Username: {user['username']}")
        print(f"   Email: {user['email']}")
        print(f"   Full Name: {user['full_name']}")
        print(f"   Active: {'Yes' if user['is_active'] else 'No'}")
        print(f"   Admin: {'Yes' if user['is_admin'] else 'No'}")
        print(f"   Created: {format_datetime(user['created_at'])}")
        print(f"   Last Login: {format_datetime(user['last_login'])}")
        print()

        # Profile
        cursor.execute("SELECT * FROM user_profile WHERE user_id = ?", (user['id'],))
        profile = cursor.fetchone()

        print("👤 Profile Information:")
        if profile:
            print(f"   Name: {profile['name']}")
            print(f"   Last Name: {profile['lastname']}")
            print(f"   Email: {profile['email']}")
            print(f"   Phone: {profile['phone'] or 'Not provided'}")
            print(f"   Address: {profile['address'] or 'Not provided'}")
            print(f"   Created: {format_datetime(profile['created_at'])}")
            print(f"   Updated: {format_datetime(profile['updated_at'])}")
        else:
            print("   No profile created")
        print()

        # Collections
        cursor.execute("SELECT * FROM collection WHERE user_id = ?", (user['id'],))
        collections = cursor.fetchall()

        print(f"📚 Collections ({len(collections)}):")
        if collections:
            for collection in collections:
                # Count documents
                cursor.execute("SELECT COUNT(*) as count FROM document WHERE collection_id = ?", (collection['id'],))
                doc_count = cursor.fetchone()['count']

                print(f"   • {collection['name']} (ID: {collection['id']}) - {doc_count} documents")
                print(f"     Created: {format_datetime(collection['created_at'])}")
                print(f"     Updated: {format_datetime(collection['updated_at'])}")
        else:
            print("   No collections")
        print()

        # Conversations
        cursor.execute("SELECT * FROM conversation WHERE user_id = ? ORDER BY created_at DESC LIMIT 10", (user['id'],))
        conversations = cursor.fetchall()

        cursor.execute("SELECT COUNT(*) as count FROM conversation WHERE user_id = ?", (user['id'],))
        total_conversations = cursor.fetchone()['count']

        print(f"💬 Conversations ({total_conversations}):")
        if conversations:
            for conv in conversations:
                # Count messages
                cursor.execute("SELECT COUNT(*) as count FROM message WHERE conversation_id = ?", (conv['id'],))
                msg_count = cursor.fetchone()['count']

                print(f"   • {conv['title']} (ID: {conv['id']}) - {msg_count} messages")
                print(f"     Created: {format_datetime(conv['created_at'])}")
                print(f"     Updated: {format_datetime(conv['updated_at'])}")

            if total_conversations > 10:
                print(f"   ... and {total_conversations - 10} more conversations")
        else:
            print("   No conversations")
        print()

        print(f"🔗 Vector Store:")
        print(f"   Prefix: 'user_{user['id']}_'")

        conn.close()

    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Show details for specific user
        show_user_details(sys.argv[1])
    else:
        # List all users
        show_all_users()

    print("\n💡 Usage:")
    print("   python3 show_users.py              # List all users")
    print("   python3 show_users.py <username>   # Show details for specific user")
    print("   python3 show_users.py <user_id>    # Show details for user by ID")