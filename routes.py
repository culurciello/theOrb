from flask import render_template, request, jsonify, Response, send_file
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import datetime

from flask import Blueprint

# Create a blueprint instead of importing app directly
bp = Blueprint('main', __name__)

# We'll register this blueprint with the app in app.py
from database import db
from models import Collection, Document, DocumentChunk, Conversation, Message, UserProfile, ApiKey
from document_processor import DocumentProcessor
from vector_store import VectorStore
from ai_agents import AgentManager
from ai_agents.verification_agent import VerificationAgent

# Initialize services
vector_store = VectorStore()
document_processor = DocumentProcessor()
verification_agent = VerificationAgent()
agent_manager = AgentManager()

@bp.route('/')
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
def get_collections():
    """Get all document collections."""
    collections = Collection.query.all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'created_at': c.created_at.isoformat(),
        'document_count': len(c.documents)
    } for c in collections])

@bp.route('/api/collections', methods=['POST'])
def create_collection():
    """Create a new document collection."""
    data = request.get_json()
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'error': 'Collection name is required'}), 400
    
    if Collection.query.filter_by(name=name).first():
        return jsonify({'error': 'Collection name already exists'}), 400
    
    collection = Collection(name=name)
    db.session.add(collection)
    db.session.commit()
    
    return jsonify({
        'id': collection.id,
        'name': collection.name,
        'created_at': collection.created_at.isoformat(),
        'document_count': 0
    })

@bp.route('/api/collections/<int:collection_id>', methods=['PUT'])
def update_collection(collection_id):
    """Update collection name."""
    collection = Collection.query.get_or_404(collection_id)
    data = request.get_json()
    name = data.get('name', '').strip()
    
    if not name:
        return jsonify({'error': 'Collection name is required'}), 400
    
    if name != collection.name and Collection.query.filter_by(name=name).first():
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
def delete_collection(collection_id):
    """Delete a collection and all its documents."""
    collection = Collection.query.get_or_404(collection_id)
    
    # Delete from vector store
    vector_store.delete_collection(collection.name)
    
    # Delete from database
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
def upload_files(collection_id):
    """Upload files or directory to a collection."""
    collection = Collection.query.get_or_404(collection_id)
    
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
def get_conversations():
    """Get all conversations."""
    conversations = Conversation.query.order_by(Conversation.updated_at.desc()).all()
    return jsonify([{
        'id': c.id,
        'title': c.title or f'Conversation {c.id}',
        'created_at': c.created_at.isoformat(),
        'updated_at': c.updated_at.isoformat(),
        'message_count': len(c.messages)
    } for c in conversations])

@bp.route('/api/conversations', methods=['POST'])
def create_conversation():
    """Create a new conversation."""
    data = request.get_json() or {}
    title = data.get('title', f'New Conversation')
    
    conversation = Conversation(title=title)
    db.session.add(conversation)
    db.session.commit()
    
    return jsonify({
        'id': conversation.id,
        'title': conversation.title,
        'created_at': conversation.created_at.isoformat(),
        'updated_at': conversation.updated_at.isoformat(),
        'message_count': 0
    })

@bp.route('/api/conversations/<int:conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get a specific conversation with its messages."""
    conversation = Conversation.query.get_or_404(conversation_id)
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
def delete_conversation(conversation_id):
    """Delete a conversation."""
    conversation = Conversation.query.get_or_404(conversation_id)
    db.session.delete(conversation)
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/api/chat', methods=['POST'])
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

    try:
        # Get conversation
        if conversation_id:
            conversation = Conversation.query.get_or_404(conversation_id)
        else:
            # Create new conversation
            title = user_message[:50] + '...' if user_message and len(user_message) > 50 else (user_message or 'Image Query')
            conversation = Conversation(title=title)
            db.session.add(conversation)
            db.session.flush()
        
        # Get collection name if specified
        collection_name = None
        if collection_id:
            collection = Collection.query.get_or_404(collection_id)
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
            if collection_name:
                relevant_chunks = vector_store.search_similar_chunks(
                    collection_name, user_message, n_results=3
                )
                if relevant_chunks:
                    context = "\n\n--- Relevant Information ---\n"
                    for i, chunk in enumerate(relevant_chunks):
                        context += f"Document {i+1}:\n{chunk['content']}\n\n"

            # Auto-detect agent if not specified
            if not agent_id:
                agent_id = agent_manager.detect_agent_from_message(user_message)
            
            # Process with agent manager
            response_data = agent_manager.process_request(
                user_message=user_message,
                agent_name=agent_id,
                context=context,
                conversation_history=conversation_history,
                collection_name=collection_name
            )
            response_text = response_data['response']
            verified = response_data.get('verified')
            images_result = response_data.get('images', [])

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
            'images': images_result
        })
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/api/collections/<int:collection_id>/files', methods=['GET'])
def get_collection_files(collection_id):
    """Get all files in a collection with proper count."""
    collection = Collection.query.get_or_404(collection_id)
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
def get_collection_file_links(collection_id):
    """Get all file links in a collection for easy access."""
    collection = Collection.query.get_or_404(collection_id)
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
def remove_file_from_collection(collection_id, document_id):
    """Remove a specific file from collection."""
    collection = Collection.query.get_or_404(collection_id)
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
def get_document(document_id):
    """Get a specific document with full content."""
    document = Document.query.get_or_404(document_id)
    
    return jsonify({
        'id': document.id,
        'filename': document.filename,
        'file_type': document.file_type,
        'created_at': document.created_at.isoformat(),
        'content': document.content,
        'collection_id': document.collection_id,
        'chunk_count': len(document.chunks)
    })


# User Profile Routes
@bp.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    """Get user profile information."""
    # For now, get the first user profile or create a default one
    profile = UserProfile.query.first()
    
    if not profile:
        # Create default profile
        profile = UserProfile(
            name='User',
            lastname='Name',
            email='user@example.com'
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
def update_user_profile():
    """Update user profile information."""
    data = request.get_json()
    
    # Get or create profile
    profile = UserProfile.query.first()
    if not profile:
        profile = UserProfile()
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
def get_api_keys():
    """Get all API keys for the user."""
    profile = UserProfile.query.first()
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
def create_api_key():
    """Create a new API key."""
    data = request.get_json()
    service_name = data.get('service_name', '').strip()
    key_value = data.get('key_value', '').strip()
    
    if not service_name or not key_value:
        return jsonify({'error': 'Service name and key value are required'}), 400
    
    # Get or create profile
    profile = UserProfile.query.first()
    if not profile:
        profile = UserProfile(
            name='User',
            lastname='Name',
            email='user@example.com'
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
def update_api_key(key_id):
    """Update an API key."""
    data = request.get_json()
    api_key = ApiKey.query.get_or_404(key_id)
    
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
def delete_api_key(key_id):
    """Delete an API key."""
    api_key = ApiKey.query.get_or_404(key_id)
    
    try:
        db.session.delete(api_key)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500



@bp.route('/api/collections/<int:collection_id>/search', methods=['POST'])
def search_collection(collection_id):
    """Search within a collection with filters."""
    collection = Collection.query.get_or_404(collection_id)
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
def get_collection_stats(collection_id):
    """Get detailed statistics about a collection."""
    collection = Collection.query.get_or_404(collection_id)
    
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
def get_collection_summary(collection_id):
    """Get a summary of all documents in a collection."""
    collection = Collection.query.get_or_404(collection_id)
    
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
def get_collection_images(collection_id):
    """Get all images in a collection."""
    collection = Collection.query.get_or_404(collection_id)
    
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
def search_similar_images(collection_id):
    """Search for similar images by uploading an image."""
    collection = Collection.query.get_or_404(collection_id)
    
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
def search_files_across_collections():
    """Search for files across all collections."""
    data = request.get_json()
    query = data.get('query', '').strip()
    file_type_filter = data.get('file_type', '').strip()
    n_results = data.get('n_results', 20)
    
    if not query:
        return jsonify({'error': 'Search query is required'}), 400
    
    try:
        # Search across all collections
        all_results = []
        collections = Collection.query.all()
        
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