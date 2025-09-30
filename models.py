from datetime import datetime
import json
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from database import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    theme_preference = db.Column(db.String(10), default='light')

    # Relationships
    collections = db.relationship('Collection', backref='user', lazy=True, cascade='all, delete-orphan')
    conversations = db.relationship('Conversation', backref='user', lazy=True, cascade='all, delete-orphan')
    user_profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')

    def set_password(self, password):
        """Set password hash."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check password against hash."""
        return check_password_hash(self.password_hash, password)

    def get_vector_store_prefix(self):
        """Get unique prefix for this user's vector store collections."""
        return f"user_{self.id}_"

class Collection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    source_type = db.Column(db.String(50), default='file')  # 'file', 'directory', 'url'
    source_path = db.Column(db.Text)  # Path to source directory or file
    processing_stats = db.Column(db.Text)  # JSON string of processing statistics
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    documents = db.relationship('Document', backref='collection', lazy=True, cascade='all, delete-orphan')

    # Ensure collection names are unique per user
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='unique_user_collection_name'),)
    
    def get_processing_stats(self):
        """Parse processing stats from JSON string."""
        if self.processing_stats:
            try:
                return json.loads(self.processing_stats)
            except:
                return {}
        return {}
    
    def set_processing_stats(self, stats_dict):
        """Set processing stats as JSON string."""
        self.processing_stats = json.dumps(stats_dict) if stats_dict else None

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.Text, nullable=False)  # Original file path/relative path
    stored_file_path = db.Column(db.Text)  # Path to stored copy of original file
    original_file_url = db.Column(db.Text)  # URL to access original file
    content = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text)
    file_type = db.Column(db.String(50), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))  # MIME type for serving files
    categories = db.Column(db.Text)  # JSON string of categories
    metadata_json = db.Column(db.Text)  # JSON string of additional metadata
    collection_id = db.Column(db.Integer, db.ForeignKey('collection.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    chunks = db.relationship('DocumentChunk', backref='document', lazy=True, cascade='all, delete-orphan')
    
    def get_categories(self):
        """Parse categories from JSON string."""
        if self.categories:
            try:
                return json.loads(self.categories)
            except:
                return []
        return []
    
    def set_categories(self, categories_list):
        """Set categories as JSON string."""
        self.categories = json.dumps(categories_list) if categories_list else None
    
    def get_metadata(self):
        """Parse metadata from JSON string."""
        if self.metadata_json:
            try:
                return json.loads(self.metadata_json)
            except:
                return {}
        return {}
    
    def set_metadata(self, metadata_dict):
        """Set metadata as JSON string."""
        self.metadata_json = json.dumps(metadata_dict) if metadata_dict else None

class DocumentChunk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    chunk_index = db.Column(db.Integer, nullable=False)
    embedding_id = db.Column(db.String(255), unique=True)
    vector_metadata = db.Column(db.Text)  # JSON string of vector store metadata
    
    def get_vector_metadata(self):
        """Parse vector metadata from JSON string."""
        if self.vector_metadata:
            try:
                return json.loads(self.vector_metadata)
            except:
                return {}
        return {}
    
    def set_vector_metadata(self, metadata_dict):
        """Set vector metadata as JSON string."""
        self.vector_metadata = json.dumps(metadata_dict) if metadata_dict else None

class Conversation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan')

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user', 'assistant'
    content = db.Column(db.Text, nullable=False)
    collection_used = db.Column(db.String(100))
    agent_used = db.Column(db.String(100))  # Which AI agent was used
    verified = db.Column(db.Boolean, default=False)
    images = db.Column(db.Text)  # JSON string of images data
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_images(self, images_data):
        """Set images data as JSON string."""
        if images_data:
            self.images = json.dumps(images_data)
        else:
            self.images = None
    
    def get_images(self):
        """Get images data from JSON string."""
        if self.images:
            try:
                return json.loads(self.images)
            except json.JSONDecodeError:
                return []
        return []

class UserProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    api_keys = db.relationship('ApiKey', backref='user_profile', lazy=True, cascade='all, delete-orphan')

class ApiKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_profile_id = db.Column(db.Integer, db.ForeignKey('user_profile.id'), nullable=False)
    service_name = db.Column(db.String(100), nullable=False)  # 'openai', 'anthropic', etc.
    key_value = db.Column(db.Text, nullable=False)  # Encrypted in production
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)