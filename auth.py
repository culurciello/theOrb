"""
Authentication utilities and decorators for multi-user support.
"""

from functools import wraps
from flask import current_app, request, session
from flask_login import current_user, login_required as flask_login_required
from models import User


def get_current_user():
    """Get the current user, with bypass support for testing."""
    if current_app.config.get('BYPASS_AUTH', False):
        # In bypass mode, try to get user by ID first
        test_user_id = current_app.config.get('DEFAULT_TEST_USER_ID')
        if test_user_id:
            user = User.query.get(test_user_id)
            if user:
                return user

        # Fallback to username lookup
        test_username = current_app.config.get('DEFAULT_TEST_USER', 'testuser')
        user = User.query.filter_by(username=test_username).first()
        if user:
            return user

        # If test user doesn't exist, create one
        from database import db
        user = User(
            username=test_username,
            email=f'{test_username}@example.com',
            full_name=test_username.replace('_', ' ').title()
        )
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        return user

    # Normal authentication mode
    if current_user and current_user.is_authenticated:
        return current_user

    return None


def login_required(f):
    """Custom login required decorator that supports auth bypass."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return flask_login_required(f)(*args, **kwargs)
        return f(*args, **kwargs)
    return decorated_function


def get_user_collections_query():
    """Get query for collections belonging to current user."""
    from models import Collection
    user = get_current_user()
    if user:
        return Collection.query.filter_by(user_id=user.id)
    return Collection.query.filter(False)  # Return empty query


def get_user_conversations_query():
    """Get query for conversations belonging to current user."""
    from models import Conversation
    user = get_current_user()
    if user:
        return Conversation.query.filter_by(user_id=user.id)
    return Conversation.query.filter(False)  # Return empty query


def create_user_collection(name, **kwargs):
    """Create a new collection for the current user."""
    from models import Collection
    from database import db

    user = get_current_user()
    if not user:
        raise ValueError("No authenticated user")

    collection = Collection(
        name=name,
        user_id=user.id,
        **kwargs
    )
    db.session.add(collection)
    db.session.commit()
    return collection


def create_user_conversation(title=None, **kwargs):
    """Create a new conversation for the current user."""
    from models import Conversation
    from database import db

    user = get_current_user()
    if not user:
        raise ValueError("No authenticated user")

    conversation = Conversation(
        title=title,
        user_id=user.id,
        **kwargs
    )
    db.session.add(conversation)
    db.session.commit()
    return conversation


def get_user_vector_store_collection_name(collection_name):
    """Get the vector store collection name with user prefix."""
    user = get_current_user()
    if user:
        return f"{user.get_vector_store_prefix()}{collection_name}"
    return collection_name


def get_user_collection_or_404(collection_id):
    """Get a collection that belongs to the current user or return 404."""
    from models import Collection
    from flask import abort

    user = get_current_user()
    if not user:
        abort(401)

    collection = Collection.query.filter_by(id=collection_id, user_id=user.id).first()
    if not collection:
        abort(404)

    return collection


def get_user_conversation_or_404(conversation_id):
    """Get a conversation that belongs to the current user or return 404."""
    from models import Conversation
    from flask import abort

    user = get_current_user()
    if not user:
        abort(401)

    conversation = Conversation.query.filter_by(id=conversation_id, user_id=user.id).first()
    if not conversation:
        abort(404)

    return conversation


class UserVectorStore:
    """Wrapper for VectorStore that handles user isolation."""

    def __init__(self, vector_store):
        self.vector_store = vector_store

    def _get_user_collection_name(self, collection_name):
        """Get user-specific collection name."""
        return get_user_vector_store_collection_name(collection_name)

    def add_chunks(self, collection_name, chunks, **kwargs):
        """Add chunks to user-specific collection."""
        user_collection = self._get_user_collection_name(collection_name)
        return self.vector_store.add_chunks(user_collection, chunks, **kwargs)

    def search_similar_chunks(self, collection_name, query, **kwargs):
        """Search in user-specific collection."""
        user_collection = self._get_user_collection_name(collection_name)
        return self.vector_store.search_similar_chunks(user_collection, query, **kwargs)

    def search_images_by_keywords(self, collection_name, query, **kwargs):
        """Search images in user-specific collection."""
        user_collection = self._get_user_collection_name(collection_name)
        return self.vector_store.search_images_by_keywords(user_collection, query, **kwargs)

    def search_similar_images_by_embedding(self, collection_name, embedding, **kwargs):
        """Search similar images in user-specific collection."""
        user_collection = self._get_user_collection_name(collection_name)
        return self.vector_store.search_similar_images_by_embedding(user_collection, embedding, **kwargs)

    def delete_collection(self, collection_name):
        """Delete user-specific collection."""
        user_collection = self._get_user_collection_name(collection_name)
        return self.vector_store.delete_collection(user_collection)

    def get_collection_stats(self, collection_name):
        """Get stats for user-specific collection."""
        user_collection = self._get_user_collection_name(collection_name)
        return self.vector_store.get_collection_stats(user_collection)

    def list_collections(self):
        """List all collections for current user."""
        user = get_current_user()
        if not user:
            return []

        all_collections = self.vector_store.list_collections()
        user_prefix = user.get_vector_store_prefix()

        # Filter and remove user prefix from collection names
        user_collections = []
        for collection in all_collections:
            if collection.startswith(user_prefix):
                clean_name = collection[len(user_prefix):]
                user_collections.append(clean_name)

        return user_collections

    def add_document_chunks(self, collection_name, chunks, chunk_ids, metadata):
        """Add document chunks to user-specific collection."""
        user_collection = self._get_user_collection_name(collection_name)
        return self.vector_store.add_document_chunks(user_collection, chunks, chunk_ids, metadata)

    def delete_document_chunks(self, collection_name, chunk_ids):
        """Delete document chunks from user-specific collection."""
        user_collection = self._get_user_collection_name(collection_name)
        return self.vector_store.delete_document_chunks(user_collection, chunk_ids)

    def search_by_category(self, collection_name, query, n_results):
        """Search by category in user-specific collection."""
        user_collection = self._get_user_collection_name(collection_name)
        return self.vector_store.search_by_category(user_collection, query, n_results)

    def search_by_file_type(self, collection_name, query, n_results):
        """Search by file type in user-specific collection."""
        user_collection = self._get_user_collection_name(collection_name)
        return self.vector_store.search_by_file_type(user_collection, query, n_results)

    def get_collection_summary(self, collection_name):
        """Get collection summary for user-specific collection."""
        user_collection = self._get_user_collection_name(collection_name)
        return self.vector_store.get_collection_summary(user_collection)

    def get_collection_images(self, collection_name):
        """Get collection images for user-specific collection."""
        user_collection = self._get_user_collection_name(collection_name)
        return self.vector_store.get_collection_images(user_collection)

    def add_document(self, collection_name, document_id, content, metadata, embedding_id):
        """Add document to user-specific collection."""
        user_collection = self._get_user_collection_name(collection_name)
        return self.vector_store.add_document(user_collection, document_id, content, metadata, embedding_id)