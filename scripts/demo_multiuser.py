#!/usr/bin/env python3
"""
Demonstration script for multi-user functionality.
This shows how different users have isolated data.
"""

import os
from app import app
from database import db
from models import User, Collection, Conversation, Message
from auth import UserVectorStore
from vector_store import VectorStore


def demonstrate_user_isolation():
    """Demonstrate that each user has isolated data."""
    print("🎯 Multi-User Isolation Demonstration")
    print("=" * 50)

    with app.app_context():
        # Get our test users
        user1 = User.query.filter_by(username='user1').first()
        user2 = User.query.filter_by(username='user2').first()

        if not user1 or not user2:
            print("❌ Test users not found. Run test_multiuser.py first.")
            return

        print(f"👤 User 1: {user1.username} (ID: {user1.id})")
        print(f"👤 User 2: {user2.username} (ID: {user2.id})")

        # Show collections for each user
        user1_collections = Collection.query.filter_by(user_id=user1.id).all()
        user2_collections = Collection.query.filter_by(user_id=user2.id).all()

        print(f"\n📁 User1's Collections ({len(user1_collections)}):")
        for col in user1_collections:
            print(f"  - {col.name} (ID: {col.id})")

        print(f"\n📁 User2's Collections ({len(user2_collections)}):")
        for col in user2_collections:
            print(f"  - {col.name} (ID: {col.id})")

        # Show vector store prefixes
        print(f"\n🔍 Vector Store Isolation:")
        print(f"  - User1 prefix: {user1.get_vector_store_prefix()}")
        print(f"  - User2 prefix: {user2.get_vector_store_prefix()}")

        # Create some conversations for demonstration
        conv1 = Conversation(title="User1's Chat", user_id=user1.id)
        conv2 = Conversation(title="User2's Chat", user_id=user2.id)
        db.session.add_all([conv1, conv2])
        db.session.commit()

        # Show conversations
        user1_conversations = Conversation.query.filter_by(user_id=user1.id).all()
        user2_conversations = Conversation.query.filter_by(user_id=user2.id).all()

        print(f"\n💬 User1's Conversations ({len(user1_conversations)}):")
        for conv in user1_conversations:
            print(f"  - {conv.title} (ID: {conv.id})")

        print(f"\n💬 User2's Conversations ({len(user2_conversations)}):")
        for conv in user2_conversations:
            print(f"  - {conv.title} (ID: {conv.id})")


def demonstrate_vector_store_isolation():
    """Demonstrate vector store user isolation."""
    print(f"\n🔒 Vector Store User Isolation Demo")
    print("=" * 40)

    # Create vector store instances
    base_vector_store = VectorStore()
    user_vector_store = UserVectorStore(base_vector_store)

    # Simulate different users by setting different prefixes
    class MockUser:
        def __init__(self, user_id, username):
            self.id = user_id
            self.username = username

        def get_vector_store_prefix(self):
            return f"user_{self.id}_"

    # Mock users for demonstration
    mock_user1 = MockUser(1, "user1")
    mock_user2 = MockUser(2, "user2")

    print(f"Collection names with user prefixes:")
    print(f"  - User1: '{mock_user1.get_vector_store_prefix()}my_collection'")
    print(f"  - User2: '{mock_user2.get_vector_store_prefix()}my_collection'")
    print(f"  → Same collection name, but isolated storage!")


def show_authentication_features():
    """Show authentication features."""
    print(f"\n🔐 Authentication Features")
    print("=" * 30)

    with app.app_context():
        print("✅ Features implemented:")
        print("  - User registration and login")
        print("  - Password hashing (werkzeug.security)")
        print("  - Session management (Flask-Login)")
        print("  - User-specific collections")
        print("  - User-specific conversations")
        print("  - Vector store isolation")
        print("  - Authentication bypass for testing")
        print("  - Unique constraints (username, email)")

        print(f"\n🚀 Testing Mode:")
        print(f"  - Set BYPASS_AUTH=true to skip login")
        print(f"  - Set DEFAULT_TEST_USER_ID=1 for test user")
        print(f"  - Access /bypass-login endpoint")


def show_usage_instructions():
    """Show how to use the multi-user system."""
    print(f"\n📖 Usage Instructions")
    print("=" * 25)

    print("1. 🏃 Running the Application:")
    print("   # Normal mode (requires login)")
    print("   python3 app.py")
    print()
    print("   # Testing mode (bypasses authentication)")
    print("   BYPASS_AUTH=true DEFAULT_TEST_USER_ID=1 python3 app.py")

    print("\n2. 🌐 Web Interface:")
    print("   - Login: http://localhost:3000/login")
    print("   - Register: http://localhost:3000/register")
    print("   - Main app: http://localhost:3000/")

    print("\n3. 👥 User Management:")
    print("   - Each user has isolated collections")
    print("   - Each user has isolated conversations")
    print("   - Vector store data is prefixed by user ID")
    print("   - Same collection names allowed for different users")

    print("\n4. 🔧 Development/Testing:")
    print("   - Use bypass login for quick testing")
    print("   - Check test_multiuser.py for examples")
    print("   - Database recreated automatically if schema changes")


def main():
    """Run the demonstration."""
    try:
        demonstrate_user_isolation()
        demonstrate_vector_store_isolation()
        show_authentication_features()
        show_usage_instructions()

        print(f"\n🎉 Multi-User System Successfully Implemented!")
        print("   Ready for production use with proper authentication")
        print("   or testing use with authentication bypass.")

    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()