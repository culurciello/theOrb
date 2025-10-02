from flask import render_template, request, jsonify, send_file, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from werkzeug.utils import secure_filename
import os
import uuid
import logging
from datetime import datetime

from flask import Blueprint

# Set up logger
logger = logging.getLogger('orb')

# Create a blueprint instead of importing app directly
bp = Blueprint('main', __name__)

# We'll register this blueprint with the app in app.py
from database import db
from models import Collection, Document, DocumentChunk, Conversation, Message, UserProfile, ApiKey, User
from document_processor import DocumentProcessor
from vector_store import VectorStore
from ai_agents import AgentManager
from ai_agents.verification_agent import VerificationAgent
from auth import login_required, get_current_user, get_user_collections_query, get_user_conversations_query, UserVectorStore, get_user_collection_or_404, get_user_conversation_or_404

# Initialize services
base_vector_store = VectorStore()
vector_store = UserVectorStore(base_vector_store)
document_processor = DocumentProcessor()
verification_agent = VerificationAgent()
agent_manager = AgentManager()

# Authentication routes
@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user, remember=request.form.get('remember-me'))
            user.last_login = datetime.utcnow()
            db.session.commit()

            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page."""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validation
        if password != confirm_password:
            flash('Passwords do not match')
            return render_template('register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return render_template('register.html')

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
            name=full_name.split()[0] if full_name else '',
            lastname=' '.join(full_name.split()[1:]) if full_name and len(full_name.split()) > 1 else '',
            email=email
        )
        db.session.add(profile)
        db.session.commit()

        flash('Registration successful! Please log in.')
        return redirect(url_for('main.login'))

    return render_template('register.html')

@bp.route('/logout')
def logout():
    """User logout."""
    logout_user()
    return redirect(url_for('main.login'))

@bp.route('/bypass-login')
def bypass_login():
    """Bypass login for testing (only works if BYPASS_AUTH is enabled)."""
    from flask import current_app
    if not current_app.config.get('BYPASS_AUTH', False):
        flash('Authentication bypass is disabled')
        return redirect(url_for('main.login'))

    # Get or create test user
    user = get_current_user()
    if user:
        login_user(user)
        flash('Logged in as test user')
        return redirect(url_for('main.index'))
    else:
        flash('Could not create test user')
        return redirect(url_for('main.login'))

@bp.route('/')
@login_required
def index():
    """Serve the main application page."""
    return render_template('index.html')

@bp.route('/api/agents', methods=['GET'])
def get_available_agents():
    """Get all available AI agents."""
    try:
        agents = agent_manager.get_available_agents()
        return jsonify(agents)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/collections', methods=['GET'])
@login_required
def get_collections():
    """Get all document collections for the current user."""
    collections = get_user_collections_query().all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'created_at': c.created_at.isoformat(),
        'document_count': len(c.documents)
    } for c in collections])

@bp.route('/api/collections', methods=['POST'])
@login_required
def create_collection():
    """Create a new document collection for the current user."""
    from auth import create_user_collection

    data = request.get_json()
    name = data.get('name', '').strip()

    if not name:
        return jsonify({'error': 'Collection name is required'}), 400

    # Check if collection name exists for this user
    user = get_current_user()
    existing = Collection.query.filter_by(name=name, user_id=user.id).first()
    if existing:
        return jsonify({'error': 'Collection name already exists'}), 400

    try:
        collection = create_user_collection(name)
        return jsonify({
            'id': collection.id,
            'name': collection.name,
            'created_at': collection.created_at.isoformat(),
            'document_count': 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/collections/<int:collection_id>', methods=['PUT'])
@login_required
def update_collection(collection_id):
    """Update collection name."""
    collection = get_user_collection_or_404(collection_id)
    data = request.get_json()
    name = data.get('name', '').strip()

    if not name:
        return jsonify({'error': 'Collection name is required'}), 400

    # Check if name exists for this user (exclude current collection)
    user = get_current_user()
    existing = Collection.query.filter_by(name=name, user_id=user.id).filter(Collection.id != collection_id).first()
    if existing:
        return jsonify({'error': 'Collection name already exists'}), 400

    collection.name = name
    collection.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        'id': collection.id,
        'name': collection.name,
        'updated_at': collection.updated_at.isoformat(),
        'document_count': len(collection.documents)
    })

@bp.route('/api/collections/<int:collection_id>', methods=['DELETE'])
@login_required
def delete_collection(collection_id):
    """Delete a collection and all its documents."""
    collection = get_user_collection_or_404(collection_id)

    # Delete from vector store
    vector_store.delete_collection(collection.name)

    # Delete from database (cascade will handle documents and chunks)
    db.session.delete(collection)
    db.session.commit()

    return jsonify({'success': True})

def _process_uploaded_file(file, collection_id, relative_path=None):
    """Helper function to process a single uploaded file."""
    filename = secure_filename(file.filename)
    temp_path = os.path.join('temp', f"{uuid.uuid4()}_{filename}")
    os.makedirs('temp', exist_ok=True)
    file.save(temp_path)
    
    try:
        # Process the file
        doc_data = document_processor.process_single_file(temp_path)
        if not doc_data:
            return None, "Unsupported file type or processing failed"
        
        # Create permanent storage
        collection_upload_dir = os.path.join('uploads', f'collection_{collection_id}')
        os.makedirs(collection_upload_dir, exist_ok=True)
        stored_filename = f"{uuid.uuid4()}_{filename}"
        stored_file_path = os.path.join(collection_upload_dir, stored_filename)
        
        import shutil
        shutil.copy2(temp_path, stored_file_path)
        
        # Generate access URL
        original_file_url = f"/api/files/collection_{collection_id}/{stored_filename}"
        
        # Create document record
        document = Document(
            filename=filename,
            file_path=relative_path or filename,
            stored_file_path=stored_file_path,
            original_file_url=original_file_url,
            content=doc_data['content'],
            summary=doc_data.get('summary', ''),
            file_type=doc_data['file_type'],
            file_size=doc_data['metadata'].get('file_size', 0),
            mime_type=doc_data.get('mime_type'),
            collection_id=collection_id
        )
        
        if doc_data.get('categories'):
            document.set_categories(doc_data['categories'])
        if doc_data.get('metadata'):
            document.set_metadata(doc_data['metadata'])
        
        db.session.add(document)
        db.session.flush()
        
        # Create chunks
        chunks = doc_data['chunks']
        chunk_records = []
        chunk_ids = []
        metadata = []
        
        for i, chunk_content in enumerate(chunks):
            chunk_id = f"doc_{document.id}_chunk_{i}"
            chunk = DocumentChunk(
                document_id=document.id,
                content=chunk_content,
                chunk_index=i,
                embedding_id=chunk_id
            )
            chunk_records.append(chunk)
            chunk_ids.append(chunk_id)
            metadata.append({
                'document_id': document.id,
                'filename': filename,
                'chunk_index': i,
                'file_type': doc_data['file_type'],
                'categories': ','.join(doc_data.get('categories', [])),
                'summary': doc_data.get('summary', ''),
                'original_file_url': original_file_url,
                'stored_file_path': stored_file_path,
                'file_path': relative_path or filename
            })
        
        db.session.add_all(chunk_records)
        return document, chunks, chunk_ids, metadata
        
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@bp.route('/api/collections/<int:collection_id>/upload', methods=['POST'])
@login_required
def upload_files(collection_id):
    """Upload files or directory to a collection."""
    collection = get_user_collection_or_404(collection_id)
    
    # Handle both single files and multiple files from directory selection
    files = []
    if 'file' in request.files:
        files = [request.files['file']]
    elif 'files' in request.files:
        files = request.files.getlist('files')
    
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No files provided'}), 400
    
    try:
        processed_docs = []
        all_chunks = []
        all_chunk_ids = []
        all_metadata = []
        
        for i, file in enumerate(files):
            if file.filename == '':
                continue
            
            # Get relative path for directory uploads
            relative_path = request.form.get(f'relativePath_{i}', file.filename)
            
            result = _process_uploaded_file(file, collection_id, relative_path)
            if result[0] is None:
                continue
                
            document, chunks, chunk_ids, metadata = result
            processed_docs.append(document)
            all_chunks.extend(chunks)
            all_chunk_ids.extend(chunk_ids)
            all_metadata.extend(metadata)
        
        if not processed_docs:
            return jsonify({'error': 'No supported files could be processed'}), 400
        
        # Add to vector store
        vector_store.add_document_chunks(collection.name, all_chunks, all_chunk_ids, all_metadata)
        
        # Update collection timestamp
        collection.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'processed_documents': len(processed_docs),
            'collection_id': collection_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/conversations', methods=['GET'])
@login_required
def get_conversations():
    """Get all conversations for the current user."""
    conversations = get_user_conversations_query().order_by(Conversation.updated_at.desc()).all()
    return jsonify([{
        'id': c.id,
        'title': c.title or f'Conversation {c.id}',
        'created_at': c.created_at.isoformat(),
        'updated_at': c.updated_at.isoformat(),
        'message_count': len(c.messages)
    } for c in conversations])

@bp.route('/api/conversations', methods=['POST'])
@login_required
def create_conversation():
    """Create a new conversation for the current user."""
    from auth import create_user_conversation

    data = request.get_json() or {}
    title = data.get('title', f'New Conversation')

    try:
        conversation = create_user_conversation(title)
        return jsonify({
            'id': conversation.id,
            'title': conversation.title,
            'created_at': conversation.created_at.isoformat(),
            'updated_at': conversation.updated_at.isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/conversations/<int:conversation_id>', methods=['GET'])
@login_required
def get_conversation(conversation_id):
    """Get a specific conversation with its messages."""
    conversation = get_user_conversation_or_404(conversation_id)
    messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.created_at).all()
    
    return jsonify({
        'id': conversation.id,
        'title': conversation.title,
        'created_at': conversation.created_at.isoformat(),
        'updated_at': conversation.updated_at.isoformat(),
        'messages': [{
            'id': m.id,
            'role': m.role,
            'content': m.content,
            'collection_used': m.collection_used,
            'verified': m.verified,
            'images': m.get_images(),
            'created_at': m.created_at.isoformat()
        } for m in messages]
    })

@bp.route('/api/conversations/<int:conversation_id>', methods=['DELETE'])
@login_required
def delete_conversation(conversation_id):
    """Delete a conversation."""
    conversation = get_user_conversation_or_404(conversation_id)
    db.session.delete(conversation)
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/api/chat', methods=['POST'])
@login_required
def chat():
    """Handle chat messages with AI agent."""
    # Support both JSON and multipart/form-data
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        user_message = request.form.get('message', '').strip()
        conversation_id = request.form.get('conversation_id')
        collection_id = request.form.get('collection_id')
        agent_id = request.form.get('agent_id')
        uploaded_image = request.files.get('image')
        image_action = request.form.get('image_action', 'similarity')
    else:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id')
        collection_id = data.get('collection_id')
        agent_id = data.get('agent_id')
        uploaded_image = None
        image_action = None

    if not user_message and not uploaded_image:
        return jsonify({'error': 'Message or image is required'}), 400

    # Log incoming message
    user = get_current_user()
    logger.info(f"📨 USER MESSAGE | User: {user.username} | Collection: {collection_id or 'None'} | Agent: {agent_id or 'auto'} | Message: {user_message[:100] if user_message else '[Image]'}...")

    try:
        # Get conversation
        if conversation_id:
            conversation = get_user_conversation_or_404(conversation_id)
        else:
            # Create new conversation
            current_user_obj = get_current_user()
            title = user_message[:50] + '...' if user_message and len(user_message) > 50 else (user_message or 'Image Query')
            conversation = Conversation(title=title, user_id=current_user_obj.id)
            db.session.add(conversation)
            db.session.flush()
        
        # Get collection name if specified
        collection_name = None
        if collection_id:
            collection = get_user_collection_or_404(collection_id)
            collection_name = collection.name
        
        # Get conversation history
        history_messages = Message.query.filter_by(conversation_id=conversation.id).order_by(Message.created_at).all()
        conversation_history = [{
            'role': msg.role,
            'content': msg.content
        } for msg in history_messages[-10:]]  # Last 10 messages

        response_text = None
        images_result = []
        verified = None

        # If image uploaded, process with CLIP
        if uploaded_image:
            # Save image temporarily
            import tempfile
            import shutil
            temp_dir = tempfile.mkdtemp()
            image_path = os.path.join(temp_dir, secure_filename(uploaded_image.filename))
            uploaded_image.save(image_path)

            try:
                if image_action == 'similarity':
                    # Find similar images in collection using CLIP
                    if collection_name:
                        similar_images = verification_agent.search_similar_images_by_upload(
                            collection_name, image_path, n_results=10
                        )
                        if similar_images:
                            response_text = f"Found {len(similar_images)} similar images:"
                            images_result = similar_images
                            verified = True
                        else:
                            response_text = "No similar images found in the selected collection."
                            verified = False
                    else:
                        response_text = "Please select a collection to search for similar images."
                        verified = False
                        
                elif image_action == 'describe':
                    # Generate description using CLIP
                    image_embedding = document_processor.get_image_embedding(image_path)
                    if image_embedding is not None:
                        # Process the image to get description
                        processed_image = document_processor.process_single_file(image_path)
                        if processed_image:
                            response_text = f"Image description: {processed_image['content']}"
                            verified = True
                        else:
                            response_text = "Could not process the uploaded image."
                            verified = False
                    else:
                        response_text = "Failed to analyze the image."
                        verified = False
                else:
                    response_text = 'Image uploaded successfully. What would you like to know about it?'
                    verified = True

            finally:
                # Clean up temp image
                shutil.rmtree(temp_dir)

        else:
            # Normal chat message - use agent manager
            # Get context from collection if specified
            context = ""
            document_references = []
            if collection_name:
                relevant_chunks = vector_store.search_similar_chunks(
                    collection_name, user_message, n_results=3
                )
                if relevant_chunks:
                    context = "\n\n--- Relevant Information ---\n"
                    for i, chunk in enumerate(relevant_chunks):
                        # Get document info for this chunk
                        try:
                            # Find document by file path in metadata
                            file_path = chunk['metadata'].get('file_path', '')
                            # Get user's collection by name to ensure isolation
                            user = get_current_user()
                            collection = Collection.query.filter_by(name=collection_name, user_id=user.id).first()
                            if collection:
                                document = Document.query.filter_by(
                                    collection_id=collection.id,
                                    file_path=file_path
                                ).first()

                                if document:
                                    chunk_order = chunk['metadata'].get('chunk_order', 0)
                                    document_references.append({
                                        'document_id': document.id,
                                        'filename': document.filename,
                                        'chunk_order': chunk_order,
                                        'file_path': file_path
                                    })
                                    context += f"Document {i+1} ({document.filename}, paragraph {chunk_order + 1}):\n{chunk['content']}\n\n"
                                else:
                                    context += f"Document {i+1}:\n{chunk['content']}\n\n"
                            else:
                                context += f"Document {i+1}:\n{chunk['content']}\n\n"
                        except Exception:
                            context += f"Document {i+1}:\n{chunk['content']}\n\n"

            # Auto-detect agent if not specified
            if not agent_id:
                agent_id = agent_manager.detect_agent_from_message(user_message)
                logger.info(f"🤖 AGENT DETECTED | Agent: {agent_id}")
            else:
                logger.info(f"🤖 AGENT SELECTED | Agent: {agent_id}")

            # Log context retrieval
            if context:
                logger.info(f"📚 CONTEXT RETRIEVED | Collection: {collection_name} | Chunks: {len(document_references)}")

            # Process with agent manager
            logger.info(f"⚙️ AGENT PROCESSING | Agent: {agent_id} | Collection: {collection_name or 'None'}")
            response_data = agent_manager.process_request(
                user_message=user_message,
                agent_name=agent_id,
                context=context,
                conversation_history=conversation_history,
                collection_name=collection_name,
                document_references=document_references
            )
            response_text = response_data['response']
            verified = response_data.get('verified')
            images_result = response_data.get('images', [])

            # Log response
            logger.info(f"✅ AGENT RESPONSE | Agent: {agent_id} | Length: {len(response_text)} chars | Verified: {verified}")

        # Save user message
        user_msg = Message(
            conversation_id=conversation.id,
            role='user',
            content=user_message or '[Image uploaded]',
            collection_used=collection_name
        )
        db.session.add(user_msg)
        
        # Save AI response
        ai_msg = Message(
            conversation_id=conversation.id,
            role='assistant',
            content=response_text,
            collection_used=collection_name,
            agent_used=response_data.get('agent_used', agent_id),
            verified=verified
        )
        
        # Store images data if present
        if images_result:
            ai_msg.set_images(images_result)
        db.session.add(ai_msg)
        
        # Update conversation timestamp
        conversation.updated_at = datetime.utcnow()
        
        db.session.commit()

        return jsonify({
            'conversation_id': conversation.id,
            'response': response_text,
            'verified': verified,
            'images': images_result,
            'document_references': response_data.get('document_references', [])
        })

    except Exception as e:
        logger.error(f"❌ CHAT ERROR | User: {user.username} | Error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/collections/<int:collection_id>/files', methods=['GET'])
@login_required
def get_collection_files(collection_id):
    """Get all files in a collection with proper count."""
    collection = get_user_collection_or_404(collection_id)
    documents = Document.query.filter_by(collection_id=collection_id).all()
    
    files = []
    for doc in documents:
        files.append({
            'id': doc.id,
            'filename': doc.filename,
            'file_path': doc.file_path,
            'file_type': doc.file_type,
            'file_size': doc.file_size,
            'mime_type': doc.mime_type,
            'categories': doc.get_categories(),
            'summary': doc.summary,
            'created_at': doc.created_at.isoformat(),
            'download_url': doc.original_file_url,
            'content_preview': doc.content[:200] + '...' if len(doc.content) > 200 else doc.content,
            'content_length': len(doc.content),
            'chunk_count': len(doc.chunks)
        })
    
    return jsonify({
        'collection_id': collection_id,
        'collection_name': collection.name,
        'files': files,
        'file_count': len(files)
    })

@bp.route('/api/collections/<int:collection_id>/file-links', methods=['GET'])
@login_required
def get_collection_file_links(collection_id):
    """Get all file links in a collection for easy access."""
    collection = get_user_collection_or_404(collection_id)
    documents = Document.query.filter_by(collection_id=collection_id).all()
    
    file_links = []
    for doc in documents:
        # Determine the best URL for accessing the file
        file_url = None
        if doc.original_file_url:
            file_url = doc.original_file_url
        elif doc.stored_file_path:
            # Create URL path for stored files
            if 'uploads/' in doc.stored_file_path:
                relative_path = doc.stored_file_path.split('uploads/', 1)[1]
                file_url = f'/api/files/{relative_path}'
            else:
                file_url = f'/api/files/collection_{collection_id}/{doc.filename}'
        
        if file_url:
            file_links.append({
                'id': doc.id,
                'filename': doc.filename,
                'file_type': doc.file_type,
                'file_size': doc.file_size,
                'mime_type': doc.mime_type,
                'url': file_url,
                'created_at': doc.created_at.isoformat(),
                'categories': doc.get_categories(),
                'summary': doc.summary[:100] + '...' if doc.summary and len(doc.summary) > 100 else doc.summary
            })
    
    return jsonify({
        'collection_id': collection_id,
        'collection_name': collection.name,
        'file_links': file_links,
        'total_files': len(file_links)
    })

@bp.route('/api/collections/<int:collection_id>/files/<int:document_id>', methods=['DELETE'])
@login_required
def remove_file_from_collection(collection_id, document_id):
    """Remove a specific file from collection."""
    collection = get_user_collection_or_404(collection_id)
    document = Document.query.filter_by(id=document_id, collection_id=collection_id).first_or_404()
    
    # Delete from vector store
    chunk_ids = [chunk.embedding_id for chunk in document.chunks]
    if chunk_ids:
        vector_store.delete_document_chunks(collection.name, chunk_ids)
    
    # Delete stored file if exists
    if document.stored_file_path and os.path.exists(document.stored_file_path):
        os.remove(document.stored_file_path)
    
    # Delete from database
    db.session.delete(document)
    collection.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True})

@bp.route('/api/documents/<int:document_id>', methods=['GET'])
@login_required
def get_document(document_id):
    """Get a specific document with full content and optional paragraph highlighting."""
    # Get document and verify it belongs to user's collection
    document = Document.query.get_or_404(document_id)
    collection = get_user_collection_or_404(document.collection_id)
    highlight_chunk = request.args.get('highlight_chunk', type=int)

    # Get chunks for this document
    chunks = DocumentChunk.query.filter_by(document_id=document_id).order_by(DocumentChunk.chunk_index).all()

    response_data = {
        'id': document.id,
        'filename': document.filename,
        'file_type': document.file_type,
        'created_at': document.created_at.isoformat(),
        'content': document.content,
        'collection_id': document.collection_id,
        'chunk_count': len(document.chunks),
        'chunks': [{'id': chunk.id, 'index': chunk.chunk_index, 'content': chunk.content} for chunk in chunks],
        'highlight_chunk': highlight_chunk
    }

    return jsonify(response_data)

@bp.route('/document-viewer')
def document_viewer():
    """Document viewer page."""
    return render_template('document_viewer.html')


# Log Routes
@bp.route('/api/logs', methods=['GET'])
@login_required
def get_logs():
    """Get recent application logs."""
    try:
        import sys
        from io import StringIO

        # Try to get logs from different sources
        logs = []

        # Option 1: Read from a log file if it exists
        log_file_paths = ['logs/app.log', 'app.log', 'theOrb.log']
        for log_path in log_file_paths:
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8') as f:
                    # Get last 1000 lines
                    all_lines = f.readlines()
                    logs = all_lines[-1000:] if len(all_lines) > 1000 else all_lines
                break

        # Option 2: If no log file, return a message
        if not logs:
            logs = [
                "🔧 VectorStore using device: mps",
                "✓ FAISS available for accelerated vector indexing",
                "📊 Application running successfully",
                "ℹ️ No log file configured. Configure logging to see more details here.",
                "",
                "To enable logging, add this to your app.py:",
                "import logging",
                "logging.basicConfig(filename='app.log', level=logging.INFO)",
            ]

        # Clean up logs - remove ANSI codes if any
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        cleaned_logs = [ansi_escape.sub('', log.rstrip()) for log in logs]

        return jsonify({
            'logs': cleaned_logs,
            'count': len(cleaned_logs)
        })

    except Exception as e:
        return jsonify({
            'error': str(e),
            'logs': [f'Error fetching logs: {str(e)}']
        }), 500

# Settings Routes
@bp.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    """Get user settings."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Split full_name into first and last name
    name_parts = user.full_name.split() if user.full_name else []
    first_name = name_parts[0] if len(name_parts) > 0 else ''
    last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

    # Get user profile for additional fields
    profile = user.user_profile

    return jsonify({
        'profile': {
            'firstName': first_name,
            'lastName': last_name,
            'email': user.email,
            'username': user.username,
            'full_name': user.full_name
        },
        'apiKeys': {
            'openai': '',
            'anthropic': ''
        },
        'defaultModel': 'gpt-4',
        'maxTokens': 4000,
        'temperature': 0.7
    })

@bp.route('/api/settings', methods=['POST'])
@login_required
def save_settings():
    """Save user settings."""
    try:
        settings = request.get_json()
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Update user profile information if provided
        if 'profile' in settings:
            profile_data = settings['profile']

            # Update full_name if firstName or lastName changed
            if 'firstName' in profile_data or 'lastName' in profile_data:
                first_name = profile_data.get('firstName', '').strip()
                last_name = profile_data.get('lastName', '').strip()
                if first_name or last_name:
                    user.full_name = f"{first_name} {last_name}".strip()

            # Update email if changed
            if 'email' in profile_data and profile_data['email'] != user.email:
                new_email = profile_data['email'].strip()
                if new_email:
                    # Check if email already exists for another user
                    existing_user = User.query.filter(
                        User.email == new_email,
                        User.id != user.id
                    ).first()
                    if existing_user:
                        return jsonify({'error': 'Email already exists'}), 400
                    user.email = new_email

            db.session.commit()

        return jsonify({'success': True, 'message': 'Settings saved successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# User Info Routes
@bp.route('/api/user/current', methods=['GET'])
@login_required
def get_current_user_info():
    """Get current authenticated user information."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'full_name': user.full_name,
        'theme_preference': user.theme_preference or 'light',
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'last_login': user.last_login.isoformat() if user.last_login else None
    })

# Theme Preference Routes
@bp.route('/api/user/theme', methods=['PUT'])
@login_required
def update_user_theme():
    """Update user theme preference."""
    try:
        data = request.get_json()
        theme = data.get('theme', '').strip().lower()

        # Validate theme
        valid_themes = ['light', 'dark']
        if theme not in valid_themes:
            return jsonify({'error': f'Invalid theme. Must be one of: {", ".join(valid_themes)}'}), 400

        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Update theme preference
        user.theme_preference = theme
        db.session.commit()

        return jsonify({
            'success': True,
            'theme': theme,
            'message': f'Theme updated to {theme}'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# User Profile Routes
@bp.route('/api/user/profile', methods=['GET'])
@login_required
def get_user_profile():
    """Get user profile information."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    profile = user.user_profile

    if not profile:
        # Create default profile for this user
        profile = UserProfile(
            user_id=user.id,
            name=user.full_name.split()[0] if user.full_name else user.username,
            lastname=' '.join(user.full_name.split()[1:]) if user.full_name and len(user.full_name.split()) > 1 else '',
            email=user.email
        )
        db.session.add(profile)
        db.session.commit()
    
    return jsonify({
        'id': profile.id,
        'name': profile.name,
        'lastname': profile.lastname,
        'email': profile.email,
        'phone': profile.phone,
        'address': profile.address,
        'created_at': profile.created_at.isoformat(),
        'updated_at': profile.updated_at.isoformat()
    })

@bp.route('/api/user/profile', methods=['PUT'])
@login_required
def update_user_profile():
    """Update user profile information."""
    data = request.get_json()

    # Get current user's profile
    user = get_current_user()
    profile = user.user_profile
    if not profile:
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
    
    # Update fields
    if 'name' in data:
        profile.name = data['name'].strip()
    if 'lastname' in data:
        profile.lastname = data['lastname'].strip()
    if 'email' in data:
        email = data['email'].strip()
        # Check if email already exists for another user
        existing_user = UserProfile.query.filter(
            UserProfile.email == email,
            UserProfile.id != profile.id
        ).first()
        if existing_user:
            return jsonify({'error': 'Email already exists'}), 400
        profile.email = email
    if 'phone' in data:
        profile.phone = data['phone'].strip() if data['phone'] else None
    if 'address' in data:
        profile.address = data['address'].strip() if data['address'] else None
    
    try:
        db.session.commit()
        return jsonify({
            'id': profile.id,
            'name': profile.name,
            'lastname': profile.lastname,
            'email': profile.email,
            'phone': profile.phone,
            'address': profile.address,
            'updated_at': profile.updated_at.isoformat()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# API Key Routes
@bp.route('/api/user/api-keys', methods=['GET'])
@login_required
def get_api_keys():
    """Get all API keys for the user."""
    user = get_current_user()
    profile = user.user_profile
    if not profile:
        return jsonify([])
    
    api_keys = ApiKey.query.filter_by(user_profile_id=profile.id).all()
    return jsonify([{
        'id': key.id,
        'service_name': key.service_name,
        'key_value': '***' + key.key_value[-4:] if len(key.key_value) > 4 else '***',  # Masked
        'is_active': key.is_active,
        'created_at': key.created_at.isoformat(),
        'updated_at': key.updated_at.isoformat()
    } for key in api_keys])

@bp.route('/api/user/api-keys', methods=['POST'])
@login_required
def create_api_key():
    """Create a new API key."""
    data = request.get_json()
    service_name = data.get('service_name', '').strip()
    key_value = data.get('key_value', '').strip()

    if not service_name or not key_value:
        return jsonify({'error': 'Service name and key value are required'}), 400

    # Get or create user's profile
    user = get_current_user()
    profile = user.user_profile
    if not profile:
        profile = UserProfile(
            user_id=user.id,
            name=user.full_name.split()[0] if user.full_name else user.username,
            lastname=' '.join(user.full_name.split()[1:]) if user.full_name and len(user.full_name.split()) > 1 else '',
            email=user.email
        )
        db.session.add(profile)
        db.session.flush()
    
    # Check if service already exists
    existing_key = ApiKey.query.filter_by(
        user_profile_id=profile.id,
        service_name=service_name
    ).first()
    
    if existing_key:
        return jsonify({'error': f'API key for {service_name} already exists. Use update instead.'}), 400
    
    api_key = ApiKey(
        user_profile_id=profile.id,
        service_name=service_name,
        key_value=key_value,
        is_active=True
    )
    
    try:
        db.session.add(api_key)
        db.session.commit()
        
        return jsonify({
            'id': api_key.id,
            'service_name': api_key.service_name,
            'key_value': '***' + api_key.key_value[-4:] if len(api_key.key_value) > 4 else '***',
            'is_active': api_key.is_active,
            'created_at': api_key.created_at.isoformat()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/user/api-keys/<int:key_id>', methods=['PUT'])
@login_required
def update_api_key(key_id):
    """Update an API key."""
    data = request.get_json()
    user = get_current_user()
    # Ensure the API key belongs to the current user
    api_key = ApiKey.query.join(UserProfile).filter(
        ApiKey.id == key_id,
        UserProfile.user_id == user.id
    ).first_or_404()
    
    if 'service_name' in data:
        api_key.service_name = data['service_name'].strip()
    if 'key_value' in data:
        api_key.key_value = data['key_value'].strip()
    if 'is_active' in data:
        api_key.is_active = data['is_active']
    
    try:
        db.session.commit()
        return jsonify({
            'id': api_key.id,
            'service_name': api_key.service_name,
            'key_value': '***' + api_key.key_value[-4:] if len(api_key.key_value) > 4 else '***',
            'is_active': api_key.is_active,
            'updated_at': api_key.updated_at.isoformat()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/user/api-keys/<int:key_id>', methods=['DELETE'])
@login_required
def delete_api_key(key_id):
    """Delete an API key."""
    user = get_current_user()
    # Ensure the API key belongs to the current user
    api_key = ApiKey.query.join(UserProfile).filter(
        ApiKey.id == key_id,
        UserProfile.user_id == user.id
    ).first_or_404()
    
    try:
        db.session.delete(api_key)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



@bp.route('/api/collections/<int:collection_id>/search', methods=['POST'])
@login_required
def search_collection(collection_id):
    """Search within a collection with filters."""
    collection = get_user_collection_or_404(collection_id)
    data = request.get_json()
    query = data.get('query', '').strip()
    search_type = data.get('search_type', 'text')  # 'text', 'category', 'file_type'
    filters = data.get('filters', {})
    n_results = data.get('n_results', 10)
    
    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    
    try:
        if search_type == 'category':
            results = vector_store.search_by_category(collection.name, query, n_results)
        elif search_type == 'file_type':
            results = vector_store.search_by_file_type(collection.name, query, n_results)
        else:
            results = vector_store.search_similar_chunks(collection.name, query, n_results, filters)
        
        return jsonify({
            'query': query,
            'search_type': search_type,
            'results': results,
            'total_results': len(results)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/collections/<int:collection_id>/stats', methods=['GET'])
@login_required
def get_collection_stats(collection_id):
    """Get detailed statistics about a collection."""
    collection = get_user_collection_or_404(collection_id)
    
    try:
        # Get vector store stats
        vector_stats = vector_store.get_collection_stats(collection.name)
        
        # Get database stats
        db_stats = {
            'total_documents': Document.query.filter_by(collection_id=collection_id).count(),
            'total_chunks': db.session.query(DocumentChunk).join(Document).filter(Document.collection_id == collection_id).count()
        }
        
        # Get processing stats from collection
        processing_stats = collection.get_processing_stats()
        
        return jsonify({
            'collection_id': collection_id,
            'collection_name': collection.name,
            'source_type': collection.source_type,
            'source_path': collection.source_path,
            'created_at': collection.created_at.isoformat(),
            'updated_at': collection.updated_at.isoformat(),
            'vector_store_stats': vector_stats,
            'database_stats': db_stats,
            'processing_stats': processing_stats
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/collections/<int:collection_id>/summary', methods=['GET'])
@login_required
def get_collection_summary(collection_id):
    """Get a summary of all documents in a collection."""
    collection = get_user_collection_or_404(collection_id)
    
    try:
        summary_data = vector_store.get_collection_summary(collection.name)
        
        return jsonify(summary_data)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/files/<path:file_path>')
def serve_file(file_path):
    """Serve original files from the uploads directory."""
    try:
        # Security check: only allow serving files from uploads directory
        if not file_path or '..' in file_path or '/' not in file_path:
            return jsonify({'error': 'Invalid file path'}), 400
        
        # Extract collection and filename
        path_parts = file_path.split('/', 1)
        if len(path_parts) != 2:
            return jsonify({'error': 'Invalid file path format'}), 400
        
        collection_dir, filename = path_parts
        
        # Validate collection directory format
        if not collection_dir.startswith('collection_'):
            return jsonify({'error': 'Invalid collection directory'}), 400
        
        # Construct full file path
        full_file_path = os.path.join('uploads', collection_dir, filename)
        
        # Check if file exists
        if not os.path.exists(full_file_path):
            return jsonify({'error': 'File not found'}), 404
        
        # Security check: make sure the resolved path is still within uploads
        resolved_path = os.path.abspath(full_file_path)
        uploads_path = os.path.abspath('uploads')
        
        if not resolved_path.startswith(uploads_path):
            return jsonify({'error': 'Access denied'}), 403
        
        # Get MIME type for proper content type
        import mimetypes
        mime_type, _ = mimetypes.guess_type(full_file_path)
        
        return send_file(full_file_path, mimetype=mime_type)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/images/<path:file_path>')
def serve_image(file_path):
    """Serve images from the file system."""
    try:
        # Security check: only allow serving files from collections
        if not file_path or '..' in file_path:
            return jsonify({'error': 'Invalid file path'}), 400
        
        # Decode URL-encoded file path
        from urllib.parse import unquote
        decoded_file_path = unquote(file_path)
        
        # Check if file exists
        if not os.path.exists(decoded_file_path):
            return jsonify({'error': 'Image not found'}), 404
        
        # Check if it's actually an image
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}
        file_ext = os.path.splitext(decoded_file_path)[1].lower()
        
        if file_ext not in allowed_extensions:
            return jsonify({'error': 'Not an image file'}), 400
        
        return send_file(decoded_file_path)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/collections/<int:collection_id>/images', methods=['GET'])
@login_required
def get_collection_images(collection_id):
    """Get all images in a collection."""
    collection = get_user_collection_or_404(collection_id)
    
    try:
        images = vector_store.get_collection_images(collection.name)
        return jsonify({
            'collection_name': collection.name,
            'images': images,
            'total_images': len(images)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/collections/<int:collection_id>/images/search', methods=['POST'])
@login_required
def search_similar_images(collection_id):
    """Search for similar images by uploading an image."""
    collection = get_user_collection_or_404(collection_id)
    
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    if file.filename == '':
        return jsonify({'error': 'No image file selected'}), 400
    
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif'}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        return jsonify({'error': 'File must be an image'}), 400
    
    try:
        temp_filename = f"temp_query_{uuid.uuid4()}{file_ext}"
        temp_path = os.path.join('temp', temp_filename)
        os.makedirs('temp', exist_ok=True)
        file.save(temp_path)
        
        n_results = request.form.get('n_results', 10, type=int)
        similar_images = verification_agent.search_similar_images_by_upload(
            collection.name, temp_path, n_results=n_results
        )
        
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return jsonify({
            'query_image': file.filename,
            'similar_images': similar_images,
            'total_results': len(similar_images)
        })
        
    except Exception as e:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        return jsonify({'error': str(e)}), 500



@bp.route('/api/search/files', methods=['POST'])
@login_required
def search_files_across_collections():
    """Search for files across all collections."""
    data = request.get_json()
    query = data.get('query', '').strip()
    file_type_filter = data.get('file_type', '').strip()
    n_results = data.get('n_results', 20)
    
    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    
    try:
        # Search across user's collections only
        all_results = []
        collections = get_user_collections_query().all()
        
        for collection in collections:
            # Build filters
            filters = {}
            if file_type_filter:
                filters['file_type'] = file_type_filter
            
            # Search in this collection
            results = vector_store.search_similar_chunks(
                collection_name=collection.name,
                query=query,
                n_results=n_results,
                filters=filters
            )
            
            # Add collection info and download URLs to results
            for result in results:
                result['collection_id'] = collection.id
                result['collection_name'] = collection.name
                
                # Ensure download URL is available
                if 'original_file_url' in result['metadata']:
                    result['download_url'] = result['metadata']['original_file_url']
                
                all_results.append(result)
        
        # Sort by relevance (distance/similarity)
        all_results.sort(key=lambda x: x.get('distance', float('inf')))
        
        return jsonify({
            'query': query,
            'file_type_filter': file_type_filter,
            'results': all_results[:n_results],
            'total_results': len(all_results),
            'collections_searched': len(collections)
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/image-caption', methods=['POST'])
def image_caption():
    """Convert uploaded image to text caption using CLIP."""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
            
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
            
        # Validate file type
        if not file.content_type.startswith('image/'):
            return jsonify({'error': 'File must be an image'}), 400
            
        # Save temporary file
        temp_filename = f"{uuid.uuid4()}.{file.filename.split('.')[-1]}"
        temp_path = os.path.join('uploads', temp_filename)
        
        # Create uploads directory if it doesn't exist
        os.makedirs('uploads', exist_ok=True)
        
        file.save(temp_path)
        
        try:
            # Use CLIP to generate caption
            caption = verification_agent.generate_image_caption(temp_path)
            
            return jsonify({'caption': caption})
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# LLM Management Routes
@bp.route('/api/llm/configs', methods=['GET'])
def get_llm_configs():
    """Get all available LLM configurations."""
    try:
        from llm_config import llm_config_manager
        configs = llm_config_manager.get_available_configs()
        return jsonify(configs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/llm/current', methods=['GET'])
def get_current_llm():
    """Get current LLM configuration."""
    try:
        from llm_providers import llm_manager
        current_info = llm_manager.get_current_provider_info()
        return jsonify(current_info)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/llm/current', methods=['POST'])
def set_current_llm():
    """Set the current LLM configuration."""
    try:
        data = request.get_json()
        config_id = data.get('config_id')
        
        if not config_id:
            return jsonify({'error': 'config_id is required'}), 400
        
        from llm_providers import llm_manager
        if llm_manager.switch_provider(config_id):
            return jsonify({'success': True, 'config_id': config_id})
        else:
            return jsonify({'error': 'Invalid config_id or provider not available'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/llm/configs/<config_id>', methods=['PUT'])
def update_llm_config(config_id):
    """Update a specific LLM configuration."""
    try:
        data = request.get_json()
        
        from llm_config import llm_config_manager
        if llm_config_manager.update_config(config_id, data):
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Invalid config_id'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/llm/status', methods=['GET'])
def get_llm_status():
    """Get status of all LLM providers."""
    try:
        from llm_providers import llm_manager
        status = llm_manager.get_provider_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/llm/test/<config_id>', methods=['POST'])
def test_llm_config(config_id):
    """Test a specific LLM configuration."""
    try:
        from llm_config import llm_config_manager
        from llm_providers import LLMProviderFactory
        
        if config_id not in llm_config_manager.configs:
            return jsonify({'error': 'Invalid config_id'}), 404
        
        config = llm_config_manager.configs[config_id]
        provider = LLMProviderFactory.create_provider(config)
        
        # Test with a simple message
        test_messages = [{"role": "user", "content": "Say 'Hello, I am working!' and nothing else."}]
        
        if not provider.is_available():
            return jsonify({
                'success': False,
                'error': f'Provider {config.display_name} is not available'
            })
        
        response = provider.generate_response(test_messages, "You are a helpful assistant.")
        
        return jsonify({
            'success': True,
            'response': response,
            'config_name': config.display_name
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/api/conversations/<int:conversation_id>/save-to-collection', methods=['POST'])
@login_required
def save_conversation_to_collection(conversation_id):
    """Save an entire conversation to a collection as a document."""
    try:
        data = request.get_json()
        collection_id = data.get('collection_id')
        collection_name = data.get('collection_name')
        
        # Get the conversation
        conversation = get_user_conversation_or_404(conversation_id)
        messages = Message.query.filter_by(conversation_id=conversation_id).order_by(Message.created_at).all()
        
        if not messages:
            return jsonify({'error': 'No messages found in conversation'}), 400
        
        # Create or get collection
        collection = None
        if collection_id:
            collection = get_user_collection_or_404(collection_id)
        elif collection_name:
            # Check if collection exists for this user
            user = get_current_user()
            collection = Collection.query.filter_by(name=collection_name.strip(), user_id=user.id).first()
            if not collection:
                # Create new collection for this user
                from auth import create_user_collection
                collection = create_user_collection(collection_name.strip())
                # No need to flush since create_user_collection already commits
        else:
            return jsonify({'error': 'Either collection_id or collection_name must be provided'}), 400
        
        # Prepare the conversation content
        conversation_content = f"# Chat Conversation: {conversation.title or 'Untitled'}\n\n"
        conversation_content += f"**Date:** {conversation.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for message in messages:
            role = "**User:**" if message.role == "user" else "**Assistant:**"
            conversation_content += f"{role}\n{message.content}\n\n"
            
            # Add verification status for assistant messages
            if message.role == "assistant" and message.verified is not None:
                status = "✅ Verified" if message.verified else "❌ Not Verified"
                conversation_content += f"*({status})*\n\n"
        
        # Create document record
        filename = f"chat_{conversation_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
        document = Document(
            filename=filename,
            file_path=f"conversations/{filename}",
            stored_file_path=None,  # This is text content, not a file
            original_file_url=None,
            content=conversation_content,
            summary=f"Chat conversation from {conversation.created_at.strftime('%Y-%m-%d')} with {len(messages)} messages",
            file_type='text',
            file_size=len(conversation_content.encode('utf-8')),
            mime_type='text/markdown',
            collection_id=collection.id
        )
        
        # Set categories
        categories = ['chat', 'conversation']
        if any(msg.agent_used for msg in messages):
            categories.append('ai-assisted')
        document.set_categories(categories)
        
        # Set metadata
        metadata = {
            'conversation_id': conversation_id,
            'message_count': len(messages),
            'agents_used': list(set(msg.agent_used for msg in messages if msg.agent_used)),
            'collections_used': list(set(msg.collection_used for msg in messages if msg.collection_used)),
            'created_date': conversation.created_at.isoformat(),
            'type': 'chat_conversation'
        }
        document.set_metadata(metadata)
        
        db.session.add(document)
        
        # Add to vector store for searchability
        try:
            # Create chunks for the conversation
            chunk_size = 2000  # Reasonable chunk size for conversations
            content_chunks = []
            current_chunk = ""
            
            for i, message in enumerate(messages):
                message_text = f"Message {i+1} ({message.role}): {message.content}\n\n"
                
                if len(current_chunk + message_text) <= chunk_size:
                    current_chunk += message_text
                else:
                    if current_chunk:
                        content_chunks.append(current_chunk.strip())
                    current_chunk = message_text
            
            if current_chunk:
                content_chunks.append(current_chunk.strip())
            
            # Add chunks to vector store
            for chunk_index, chunk_content in enumerate(content_chunks):
                embedding_id = f"doc_{document.id}_chunk_{chunk_index}"
                vector_store.add_document(
                    collection_name=collection.name,
                    document_id=document.id,
                    content=chunk_content,
                    metadata={
                        'filename': filename,
                        'chunk_index': chunk_index,
                        'conversation_id': conversation_id,
                        'type': 'chat_conversation'
                    },
                    embedding_id=embedding_id
                )
                
                # Create chunk record
                chunk = DocumentChunk(
                    document_id=document.id,
                    content=chunk_content,
                    chunk_index=chunk_index,
                    embedding_id=embedding_id
                )
                chunk.set_vector_metadata({
                    'collection_name': collection.name,
                    'added_at': datetime.utcnow().isoformat()
                })
                db.session.add(chunk)
        
        except Exception as vector_error:
            # Vector store operation failed, but we can still save to database
            print(f"Warning: Vector store operation failed: {vector_error}")
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Conversation saved to collection successfully',
            'collection': {
                'id': collection.id,
                'name': collection.name
            },
            'document': {
                'id': document.id,
                'filename': document.filename
            }
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500