#!/usr/bin/env python3
"""
CLI Testing Interface for theOrb-web
=====================================

A comprehensive command-line interface for testing all functionality 
without the GUI, using the same database and backend components.

Usage:
    python3 cli_test.py [command] [options]
    
Commands:
    interactive     - Start interactive testing mode
    collections     - Test collection management
    documents       - Test document processing
    search         - Test search functionality
    images         - Test CLIP image similarity
    chat           - Test chat/conversation features
    files          - Test file linking and retrieval
    full-test      - Run comprehensive test suite
    
Examples:
    python3 cli_test.py interactive
    python3 cli_test.py collections --create "Test Collection"
    python3 cli_test.py search --query "meeting notes" --collection 1
"""

import sys
import os
import argparse
import json
from pathlib import Path
import tempfile
from datetime import datetime
from PIL import Image
import uuid

# Add the app directory to sys.path so we can import the modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app components
from app import app, db
from models import Collection, Document, DocumentChunk, Conversation, Message, UserProfile, ApiKey
from document_processor import DocumentProcessor
from vector_store import VectorStore
from ai_agent import OrbAIAgent

class OrbCLITester:
    """Command-line interface for testing theOrb-web functionality."""
    
    def __init__(self):
        """Initialize the CLI tester with app context."""
        self.app = app
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Initialize components
        self.doc_processor = DocumentProcessor()
        self.vector_store = VectorStore()
        self.ai_agent = OrbAIAgent()
        
        print("🔮 theOrb CLI Tester Initialized")
        print(f"📁 Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print(f"🗂️ Vector Store: ./chroma_db")
        print()
    
    def __del__(self):
        """Clean up app context."""
        if hasattr(self, 'app_context'):
            self.app_context.pop()
    
    def interactive_mode(self):
        """Start interactive testing mode with menu."""
        print("🎯 Interactive Testing Mode")
        print("=" * 50)
        
        while True:
            print("\nAvailable Commands:")
            print("1. Collection Management")
            print("2. Document Processing") 
            print("3. Search & Retrieval")
            print("4. CLIP Image Similarity")
            print("5. Chat & Conversations")
            print("6. File Linking & Access")
            print("7. Database Status")
            print("8. Run Full Test Suite")
            print("9. Create Test Data")
            print("0. Exit")
            
            try:
                choice = input("\nSelect option (0-9): ").strip()
                
                if choice == '0':
                    print("👋 Goodbye!")
                    break
                elif choice == '1':
                    self.collection_menu()
                elif choice == '2':
                    self.document_menu()
                elif choice == '3':
                    self.search_menu()
                elif choice == '4':
                    self.image_menu()
                elif choice == '5':
                    self.chat_menu()
                elif choice == '6':
                    self.files_menu()
                elif choice == '7':
                    self.show_database_status()
                elif choice == '8':
                    self.run_full_test_suite()
                elif choice == '9':
                    self.create_test_data()
                else:
                    print("❌ Invalid option")
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def collection_menu(self):
        """Collection management testing menu."""
        print("\n📚 Collection Management")
        print("-" * 30)
        
        while True:
            print("\n1. List Collections")
            print("2. Create Collection")
            print("3. View Collection Details")
            print("4. Delete Collection") 
            print("5. Collection Statistics")
            print("0. Back to Main Menu")
            
            choice = input("Select option: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.list_collections()
            elif choice == '2':
                name = input("Collection name: ").strip()
                if name:
                    self.create_collection(name)
            elif choice == '3':
                self.list_collections()
                try:
                    cid = int(input("Collection ID: "))
                    self.view_collection(cid)
                except ValueError:
                    print("❌ Invalid ID")
            elif choice == '4':
                self.list_collections()
                try:
                    cid = int(input("Collection ID to delete: "))
                    confirm = input("Are you sure? (y/N): ").strip().lower()
                    if confirm == 'y':
                        self.delete_collection(cid)
                except ValueError:
                    print("❌ Invalid ID")
            elif choice == '5':
                self.list_collections()
                try:
                    cid = int(input("Collection ID for stats: "))
                    self.collection_stats(cid)
                except ValueError:
                    print("❌ Invalid ID")
    
    def document_menu(self):
        """Document processing testing menu."""
        print("\n📄 Document Processing")
        print("-" * 30)
        
        while True:
            print("\n1. Upload Single File")
            print("2. Upload Multiple Files")  
            print("3. Process Directory")
            print("4. List Documents in Collection")
            print("5. View Document Details")
            print("6. Test File Processing")
            print("0. Back to Main Menu")
            
            choice = input("Select option: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.upload_single_file()
            elif choice == '2':
                self.upload_multiple_files()
            elif choice == '3':
                self.process_directory()
            elif choice == '4':
                self.list_collection_documents()
            elif choice == '5':
                self.view_document()
            elif choice == '6':
                self.test_file_processing()
    
    def search_menu(self):
        """Search and retrieval testing menu."""
        print("\n🔍 Search & Retrieval")
        print("-" * 30)
        
        while True:
            print("\n1. Search in Collection")
            print("2. Search Across All Collections")
            print("3. Search by Category")
            print("4. Search by File Type")
            print("5. Test Vector Similarity")
            print("6. Search Files with Download Links")
            print("0. Back to Main Menu")
            
            choice = input("Select option: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.search_in_collection()
            elif choice == '2':
                self.search_all_collections()
            elif choice == '3':
                self.search_by_category()
            elif choice == '4':
                self.search_by_file_type()
            elif choice == '5':
                self.test_vector_similarity()
            elif choice == '6':
                self.search_files_with_links()
    
    def image_menu(self):
        """CLIP image similarity testing menu."""
        print("\n🖼️ CLIP Image Similarity")
        print("-" * 30)
        
        while True:
            print("\n1. Search Images by Text")
            print("2. Upload Image for Similarity")
            print("3. Test Image Processing")
            print("4. List All Images")
            print("5. Test CLIP Embeddings")
            print("0. Back to Main Menu")
            
            choice = input("Select option: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.search_images_by_text()
            elif choice == '2':
                self.upload_image_similarity()
            elif choice == '3':
                self.test_image_processing()
            elif choice == '4':
                self.list_all_images()
            elif choice == '5':
                self.test_clip_embeddings()
    
    def chat_menu(self):
        """Chat and conversation testing menu."""
        print("\n💬 Chat & Conversations") 
        print("-" * 30)
        
        while True:
            print("\n1. List Conversations")
            print("2. Create New Conversation")
            print("3. Send Chat Message")
            print("4. Test AI Response")
            print("5. Image Search in Chat")
            print("0. Back to Main Menu")
            
            choice = input("Select option: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.list_conversations()
            elif choice == '2':
                self.create_conversation()
            elif choice == '3':
                self.send_chat_message()
            elif choice == '4':
                self.test_ai_response()
            elif choice == '5':
                self.test_image_search_chat()
    
    def files_menu(self):
        """File linking and access testing menu."""
        print("\n🔗 File Linking & Access")
        print("-" * 30)
        
        while True:
            print("\n1. List Files in Collection")
            print("2. Test File Download URLs")
            print("3. Verify File Storage")
            print("4. Test File Serving")
            print("5. Check File Linking")
            print("0. Back to Main Menu")
            
            choice = input("Select option: ").strip()
            
            if choice == '0':
                break
            elif choice == '1':
                self.list_files_in_collection()
            elif choice == '2':
                self.test_download_urls()
            elif choice == '3':
                self.verify_file_storage()
            elif choice == '4':
                self.test_file_serving()
            elif choice == '5':
                self.check_file_linking()
    
    # Collection Management Implementation
    def list_collections(self):
        """List all collections."""
        collections = Collection.query.all()
        if not collections:
            print("📭 No collections found")
            return
        
        print(f"\n📚 Collections ({len(collections)}):")
        print("-" * 60)
        for c in collections:
            print(f"ID: {c.id} | Name: {c.name} | Docs: {c.documents.__len__()}")
            print(f"  Created: {c.created_at.strftime('%Y-%m-%d %H:%M')}")
            if c.description:
                print(f"  Description: {c.description}")
            print()
    
    def create_collection(self, name):
        """Create a new collection."""
        try:
            collection = Collection(name=name)
            db.session.add(collection)
            db.session.commit()
            print(f"✅ Collection '{name}' created with ID: {collection.id}")
            return collection
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating collection: {e}")
            return None
    
    def view_collection(self, collection_id):
        """View collection details."""
        collection = Collection.query.get(collection_id)
        if not collection:
            print("❌ Collection not found")
            return
        
        print(f"\n📚 Collection Details: {collection.name}")
        print("-" * 50)
        print(f"ID: {collection.id}")
        print(f"Name: {collection.name}")
        print(f"Documents: {len(collection.documents)}")
        print(f"Created: {collection.created_at}")
        print(f"Updated: {collection.updated_at}")
        
        if collection.documents:
            print(f"\n📄 Documents:")
            for doc in collection.documents[:5]:  # Show first 5
                print(f"  • {doc.filename} ({doc.file_type})")
            if len(collection.documents) > 5:
                print(f"  ... and {len(collection.documents) - 5} more")
    
    def delete_collection(self, collection_id):
        """Delete a collection."""
        collection = Collection.query.get(collection_id)
        if not collection:
            print("❌ Collection not found")
            return
        
        try:
            # Delete from vector store first
            self.vector_store.delete_collection(collection.name)
            
            # Delete from database
            db.session.delete(collection)
            db.session.commit()
            print(f"✅ Collection '{collection.name}' deleted")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error deleting collection: {e}")
    
    def collection_stats(self, collection_id):
        """Show collection statistics."""
        collection = Collection.query.get(collection_id)
        if not collection:
            print("❌ Collection not found")
            return
        
        # Get vector store stats
        vector_stats = self.vector_store.get_collection_stats(collection.name)
        
        print(f"\n📊 Statistics for '{collection.name}'")
        print("-" * 40)
        print(f"Database Documents: {len(collection.documents)}")
        print(f"Vector Store Chunks: {vector_stats.get('document_count', 0)}")
        print(f"Unique Files: {vector_stats.get('unique_files', 0)}")
        
        if 'file_types' in vector_stats:
            print(f"\nFile Types:")
            for ftype, count in vector_stats['file_types'].items():
                print(f"  {ftype}: {count}")
        
        if 'categories' in vector_stats:
            print(f"\nCategories:")
            for category, count in vector_stats['categories'].items():
                print(f"  {category}: {count}")
    
    # Document Processing Implementation
    def upload_single_file(self):
        """Upload and process a single file."""
        self.list_collections()
        try:
            collection_id = int(input("Collection ID: "))
            collection = Collection.query.get(collection_id)
            if not collection:
                print("❌ Collection not found")
                return
        except ValueError:
            print("❌ Invalid collection ID")
            return
        
        file_path = input("File path: ").strip()
        if not os.path.exists(file_path):
            print("❌ File not found")
            return
        
        self.process_and_upload_file(file_path, collection)
    
    def process_and_upload_file(self, file_path, collection):
        """Process and upload a single file to collection."""
        try:
            print(f"🔄 Processing {file_path}...")
            
            # Process the file
            doc_data = self.doc_processor.process_single_file(file_path)
            if not doc_data:
                print("❌ Failed to process file")
                return
            
            # Create upload directory
            upload_dir = f"uploads/collection_{collection.id}"
            os.makedirs(upload_dir, exist_ok=True)
            
            # Copy file to storage
            filename = os.path.basename(file_path)
            stored_filename = f"{uuid.uuid4()}_{filename}"
            stored_path = os.path.join(upload_dir, stored_filename)
            
            import shutil
            shutil.copy2(file_path, stored_path)
            
            # Create document record
            document = Document(
                filename=filename,
                file_path=filename,
                stored_file_path=stored_path,
                original_file_url=f"/api/files/collection_{collection.id}/{stored_filename}",
                content=doc_data['content'],
                summary=doc_data.get('summary', ''),
                file_type=doc_data['file_type'],
                file_size=doc_data['metadata'].get('file_size', 0),
                mime_type=doc_data.get('mime_type'),
                collection_id=collection.id
            )
            
            if doc_data.get('categories'):
                document.set_categories(doc_data['categories'])
            
            if doc_data.get('metadata'):
                document.set_metadata(doc_data['metadata'])
            
            db.session.add(document)
            db.session.flush()
            
            # Process chunks
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
                    'original_file_url': f"/api/files/collection_{collection.id}/{stored_filename}",
                    'stored_file_path': stored_path,
                    'file_path': filename
                })
            
            # Save chunks to database
            db.session.add_all(chunk_records)
            
            # Add to vector store
            self.vector_store.add_document_chunks(collection.name, chunks, chunk_ids, metadata)
            
            db.session.commit()
            
            print(f"✅ Successfully processed '{filename}'")
            print(f"   File type: {doc_data['file_type']}")
            print(f"   Content length: {len(doc_data['content'])}")
            print(f"   Chunks: {len(chunks)}")
            print(f"   Categories: {doc_data.get('categories', [])}")
            print(f"   Download URL: /api/files/collection_{collection.id}/{stored_filename}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error processing file: {e}")
    
    def upload_multiple_files(self):
        """Upload multiple files."""
        self.list_collections()
        try:
            collection_id = int(input("Collection ID: "))
            collection = Collection.query.get(collection_id)
            if not collection:
                print("❌ Collection not found")
                return
        except ValueError:
            print("❌ Invalid collection ID")
            return
        
        file_paths = input("File paths (comma-separated): ").strip().split(',')
        file_paths = [p.strip() for p in file_paths if p.strip()]
        
        success_count = 0
        for file_path in file_paths:
            if os.path.exists(file_path):
                self.process_and_upload_file(file_path, collection)
                success_count += 1
            else:
                print(f"❌ File not found: {file_path}")
        
        print(f"\n✅ Processed {success_count}/{len(file_paths)} files")
    
    def process_directory(self):
        """Process an entire directory."""
        self.list_collections()
        try:
            collection_id = int(input("Collection ID: "))
            collection = Collection.query.get(collection_id)
            if not collection:
                print("❌ Collection not found")
                return
        except ValueError:
            print("❌ Invalid collection ID")
            return
        
        directory_path = input("Directory path: ").strip()
        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            print("❌ Directory not found")
            return
        
        try:
            print(f"🔄 Processing directory {directory_path}...")
            processed_docs = self.doc_processor.process_directory(directory_path)
            
            if not processed_docs:
                print("❌ No supported files found")
                return
            
            # Add file URLs
            upload_dir = f"uploads/collection_{collection.id}"
            os.makedirs(upload_dir, exist_ok=True)
            
            for doc in processed_docs:
                if doc and os.path.exists(doc['file_path']):
                    filename = os.path.basename(doc['file_path'])
                    stored_filename = f"{uuid.uuid4()}_{filename}"
                    stored_path = os.path.join(upload_dir, stored_filename)
                    
                    import shutil
                    shutil.copy2(doc['file_path'], stored_path)
                    
                    doc['stored_file_path'] = stored_path
                    doc['original_file_url'] = f"/api/files/collection_{collection.id}/{stored_filename}"
            
            # Add to vector store
            stats = self.vector_store.add_directory_documents(collection.name, processed_docs)
            
            # Save to database
            for doc_data in processed_docs:
                if not doc_data:
                    continue
                
                document = Document(
                    filename=os.path.basename(doc_data['file_path']),
                    file_path=doc_data['file_path'],
                    stored_file_path=doc_data.get('stored_file_path'),
                    original_file_url=doc_data.get('original_file_url'),
                    content=doc_data['content'],
                    summary=doc_data.get('summary', ''),
                    file_type=doc_data['file_type'],
                    file_size=doc_data['metadata'].get('file_size', 0),
                    mime_type=doc_data.get('mime_type'),
                    collection_id=collection.id
                )
                
                if doc_data.get('categories'):
                    document.set_categories(doc_data['categories'])
                if doc_data.get('metadata'):
                    document.set_metadata(doc_data['metadata'])
                
                db.session.add(document)
            
            db.session.commit()
            
            print(f"✅ Directory processed successfully")
            print(f"   Total documents: {stats['total_documents']}")
            print(f"   Total chunks: {stats['total_chunks']}")
            print(f"   File types: {list(stats['file_types'].keys())}")
            print(f"   Categories: {list(stats['categories'].keys())}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error processing directory: {e}")
    
    def list_collection_documents(self):
        """List documents in a collection."""
        self.list_collections()
        try:
            collection_id = int(input("Collection ID: "))
            collection = Collection.query.get(collection_id)
            if not collection:
                print("❌ Collection not found")
                return
        except ValueError:
            print("❌ Invalid collection ID")
            return
        
        if not collection.documents:
            print("📭 No documents in this collection")
            return
        
        print(f"\n📄 Documents in '{collection.name}' ({len(collection.documents)}):")
        print("-" * 80)
        for doc in collection.documents:
            print(f"ID: {doc.id} | {doc.filename} ({doc.file_type})")
            print(f"  Size: {doc.file_size or 0} bytes | Chunks: {len(doc.chunks)}")
            print(f"  Created: {doc.created_at.strftime('%Y-%m-%d %H:%M')}")
            if doc.original_file_url:
                print(f"  Download: {doc.original_file_url}")
            print()
    
    def view_document(self):
        """View document details."""
        doc_id = input("Document ID: ").strip()
        try:
            document = Document.query.get(int(doc_id))
            if not document:
                print("❌ Document not found")
                return
        except ValueError:
            print("❌ Invalid document ID")
            return
        
        print(f"\n📄 Document Details: {document.filename}")
        print("-" * 60)
        print(f"ID: {document.id}")
        print(f"Filename: {document.filename}")
        print(f"File Type: {document.file_type}")
        print(f"File Size: {document.file_size} bytes")
        print(f"MIME Type: {document.mime_type}")
        print(f"Collection: {document.collection.name}")
        print(f"Chunks: {len(document.chunks)}")
        print(f"Categories: {document.get_categories()}")
        print(f"Created: {document.created_at}")
        print(f"Download URL: {document.original_file_url}")
        
        if document.summary:
            print(f"\nSummary: {document.summary}")
        
        print(f"\nContent Preview:")
        print("-" * 40)
        print(document.content[:500] + "..." if len(document.content) > 500 else document.content)
    
    def test_file_processing(self):
        """Test file processing without uploading."""
        file_path = input("File path to test: ").strip()
        if not os.path.exists(file_path):
            print("❌ File not found")
            return
        
        try:
            print(f"🔄 Testing file processing...")
            doc_data = self.doc_processor.process_single_file(file_path)
            
            if doc_data:
                print(f"✅ File processed successfully")
                print(f"   File type: {doc_data['file_type']}")
                print(f"   Content length: {len(doc_data['content'])}")
                print(f"   Chunks: {len(doc_data['chunks'])}")
                print(f"   Categories: {doc_data.get('categories', [])}")
                print(f"   Summary: {doc_data.get('summary', 'N/A')}")
                
                if doc_data['file_type'] == 'image' and 'clip_embedding' in doc_data:
                    print(f"   CLIP embedding: {len(doc_data['clip_embedding'])} dimensions")
            else:
                print("❌ Failed to process file")
                
        except Exception as e:
            print(f"❌ Error testing file: {e}")
    
    # Search Implementation
    def search_in_collection(self):
        """Search within a specific collection."""
        self.list_collections()
        try:
            collection_id = int(input("Collection ID: "))
            collection = Collection.query.get(collection_id)
            if not collection:
                print("❌ Collection not found")
                return
        except ValueError:
            print("❌ Invalid collection ID")
            return
        
        query = input("Search query: ").strip()
        if not query:
            return
        
        n_results = input("Number of results (default 5): ").strip()
        n_results = int(n_results) if n_results.isdigit() else 5
        
        try:
            results = self.vector_store.search_similar_chunks(
                collection.name, query, n_results
            )
            
            if not results:
                print("🔍 No results found")
                return
            
            print(f"\n🔍 Search Results for '{query}' in '{collection.name}'")
            print("-" * 60)
            for i, result in enumerate(results, 1):
                print(f"{i}. Score: {1-result.get('distance', 0):.3f}")
                print(f"   File: {result['metadata'].get('filename', 'Unknown')}")
                print(f"   Type: {result['metadata'].get('file_type', 'Unknown')}")
                print(f"   Content: {result['content'][:200]}...")
                if result['metadata'].get('original_file_url'):
                    print(f"   Download: {result['metadata']['original_file_url']}")
                print()
                
        except Exception as e:
            print(f"❌ Search error: {e}")
    
    def search_all_collections(self):
        """Search across all collections."""
        query = input("Search query: ").strip()
        if not query:
            return
        
        n_results = input("Number of results (default 10): ").strip()
        n_results = int(n_results) if n_results.isdigit() else 10
        
        try:
            all_results = []
            collections = Collection.query.all()
            
            for collection in collections:
                results = self.vector_store.search_similar_chunks(
                    collection.name, query, n_results
                )
                for result in results:
                    result['collection_name'] = collection.name
                    result['collection_id'] = collection.id
                    all_results.append(result)
            
            # Sort by similarity
            all_results.sort(key=lambda x: x.get('distance', float('inf')))
            
            if not all_results:
                print("🔍 No results found")
                return
            
            print(f"\n🔍 Global Search Results for '{query}'")
            print("-" * 60)
            for i, result in enumerate(all_results[:n_results], 1):
                print(f"{i}. Score: {1-result.get('distance', 0):.3f}")
                print(f"   Collection: {result.get('collection_name', 'Unknown')}")
                print(f"   File: {result['metadata'].get('filename', 'Unknown')}")
                print(f"   Type: {result['metadata'].get('file_type', 'Unknown')}")
                print(f"   Content: {result['content'][:200]}...")
                if result['metadata'].get('original_file_url'):
                    print(f"   Download: {result['metadata']['original_file_url']}")
                print()
                
        except Exception as e:
            print(f"❌ Search error: {e}")
    
    def search_by_category(self):
        """Search documents by category."""
        self.list_collections()
        try:
            collection_id = int(input("Collection ID: "))
            collection = Collection.query.get(collection_id)
            if not collection:
                print("❌ Collection not found")
                return
        except ValueError:
            print("❌ Invalid collection ID")
            return
        
        category = input("Category to search: ").strip()
        if not category:
            return
        
        n_results = input("Number of results (default 10): ").strip()
        n_results = int(n_results) if n_results.isdigit() else 10
        
        try:
            results = self.vector_store.search_by_category(
                collection.name, category, n_results
            )
            
            if not results:
                print(f"🔍 No results found for category '{category}'")
                return
            
            print(f"\n🏷️ Category Search Results for '{category}'")
            print("-" * 60)
            for i, result in enumerate(results, 1):
                print(f"{i}. File: {result['metadata'].get('filename', 'Unknown')}")
                print(f"   Categories: {result['metadata'].get('categories', '')}")
                print(f"   Content: {result['content'][:200]}...")
                print()
                
        except Exception as e:
            print(f"❌ Search error: {e}")
    
    def search_by_file_type(self):
        """Search documents by file type."""
        self.list_collections()
        try:
            collection_id = int(input("Collection ID: "))
            collection = Collection.query.get(collection_id)
            if not collection:
                print("❌ Collection not found")
                return
        except ValueError:
            print("❌ Invalid collection ID")
            return
        
        file_type = input("File type (text, image, video, etc.): ").strip()
        if not file_type:
            return
        
        n_results = input("Number of results (default 10): ").strip()
        n_results = int(n_results) if n_results.isdigit() else 10
        
        try:
            results = self.vector_store.search_by_file_type(
                collection.name, file_type, n_results
            )
            
            if not results:
                print(f"🔍 No results found for file type '{file_type}'")
                return
            
            print(f"\n📁 File Type Search Results for '{file_type}'")
            print("-" * 60)
            for i, result in enumerate(results, 1):
                print(f"{i}. File: {result['metadata'].get('filename', 'Unknown')}")
                print(f"   Type: {result['metadata'].get('file_type', 'Unknown')}")
                print(f"   Content: {result['content'][:200]}...")
                if result['metadata'].get('original_file_url'):
                    print(f"   Download: {result['metadata']['original_file_url']}")
                print()
                
        except Exception as e:
            print(f"❌ Search error: {e}")
    
    def test_vector_similarity(self):
        """Test vector similarity calculations."""
        text1 = input("First text: ").strip()
        text2 = input("Second text: ").strip()
        
        if not text1 or not text2:
            return
        
        try:
            # Get embeddings
            embedding1 = self.vector_store.model.encode([text1])
            embedding2 = self.vector_store.model.encode([text2])
            
            # Calculate similarity
            from sklearn.metrics.pairwise import cosine_similarity
            similarity = cosine_similarity(embedding1, embedding2)[0][0]
            
            print(f"\n🔢 Vector Similarity Analysis")
            print("-" * 40)
            print(f"Text 1: {text1}")
            print(f"Text 2: {text2}")
            print(f"Cosine Similarity: {similarity:.4f}")
            
            if similarity > 0.8:
                print("📊 Very similar")
            elif similarity > 0.6:
                print("📊 Moderately similar")
            elif similarity > 0.4:
                print("📊 Somewhat similar")
            else:
                print("📊 Not very similar")
                
        except Exception as e:
            print(f"❌ Error calculating similarity: {e}")
    
    def search_files_with_links(self):
        """Test file search with download links."""
        query = input("Search query for files: ").strip()
        if not query:
            return
        
        try:
            # Search across all collections
            all_results = []
            collections = Collection.query.all()
            
            for collection in collections:
                results = self.vector_store.search_similar_chunks(
                    collection.name, query, 5
                )
                for result in results:
                    result['collection_name'] = collection.name
                    all_results.append(result)
            
            # Sort by similarity
            all_results.sort(key=lambda x: x.get('distance', float('inf')))
            
            if not all_results:
                print("🔍 No files found")
                return
            
            print(f"\n🔗 File Search Results with Download Links")
            print("-" * 70)
            for i, result in enumerate(all_results[:10], 1):
                print(f"{i}. File: {result['metadata'].get('filename', 'Unknown')}")
                print(f"   Collection: {result.get('collection_name', 'Unknown')}")
                print(f"   Score: {1-result.get('distance', 0):.3f}")
                if result['metadata'].get('original_file_url'):
                    print(f"   📎 Download: {result['metadata']['original_file_url']}")
                else:
                    print(f"   ❌ No download URL available")
                print()
                
        except Exception as e:
            print(f"❌ Search error: {e}")
    
    # Image Similarity Implementation
    def search_images_by_text(self):
        """Search for images using text descriptions."""
        self.list_collections()
        try:
            collection_id = int(input("Collection ID: "))
            collection = Collection.query.get(collection_id)
            if not collection:
                print("❌ Collection not found")
                return
        except ValueError:
            print("❌ Invalid collection ID")
            return
        
        text_query = input("Describe what you're looking for: ").strip()
        if not text_query:
            return
        
        try:
            # Search for images using text
            text_embedding = self.doc_processor.get_text_embedding_for_image_search(text_query)
            if text_embedding is None:
                print("❌ Failed to generate text embedding")
                return
            
            # Search for similar images
            results = self.vector_store.search_similar_images_by_embedding(
                collection.name, text_embedding, 5
            )
            
            if not results:
                print("🔍 No similar images found")
                return
            
            print(f"\n🖼️ Image Search Results for '{text_query}'")
            print("-" * 60)
            for i, result in enumerate(results, 1):
                print(f"{i}. Similarity: {result.get('similarity', 0):.3f}")
                print(f"   File: {result['metadata'].get('file_path', 'Unknown')}")
                print(f"   Description: {result['content']}")
                if result['metadata'].get('original_file_url'):
                    print(f"   View: {result['metadata']['original_file_url']}")
                print()
                
        except Exception as e:
            print(f"❌ Image search error: {e}")
    
    def upload_image_similarity(self):
        """Upload an image and find similar ones."""
        self.list_collections()
        try:
            collection_id = int(input("Collection ID: "))
            collection = Collection.query.get(collection_id)
            if not collection:
                print("❌ Collection not found")
                return
        except ValueError:
            print("❌ Invalid collection ID")
            return
        
        image_path = input("Image path: ").strip()
        if not os.path.exists(image_path):
            print("❌ Image not found")
            return
        
        try:
            # Get image embedding
            query_embedding = self.doc_processor.get_image_embedding(image_path)
            if query_embedding is None:
                print("❌ Failed to process image")
                return
            
            # Find similar images
            results = self.vector_store.search_similar_images_by_embedding(
                collection.name, query_embedding, 5
            )
            
            if not results:
                print("🔍 No similar images found")
                return
            
            print(f"\n🖼️ Similar Images to '{os.path.basename(image_path)}'")
            print("-" * 60)
            for i, result in enumerate(results, 1):
                print(f"{i}. Similarity: {result.get('similarity', 0):.3f}")
                print(f"   File: {result['metadata'].get('file_path', 'Unknown')}")
                print(f"   Description: {result['content']}")
                print()
                
        except Exception as e:
            print(f"❌ Image similarity error: {e}")
    
    def test_image_processing(self):
        """Test image processing with CLIP."""
        image_path = input("Image path: ").strip()
        if not os.path.exists(image_path):
            print("❌ Image not found")
            return
        
        try:
            print(f"🔄 Processing image...")
            
            # Process image
            doc_data = self.doc_processor.process_single_file(image_path)
            if not doc_data:
                print("❌ Failed to process image")
                return
            
            print(f"✅ Image processed successfully")
            print(f"   File type: {doc_data['file_type']}")
            print(f"   Description: {doc_data['content']}")
            print(f"   Categories: {doc_data.get('categories', [])}")
            
            if 'clip_embedding' in doc_data:
                print(f"   CLIP embedding: {len(doc_data['clip_embedding'])} dimensions")
                print(f"   Confidence: {doc_data['metadata'].get('clip_confidence', 0):.3f}")
            
        except Exception as e:
            print(f"❌ Error processing image: {e}")
    
    def list_all_images(self):
        """List all images in collections."""
        collections = Collection.query.all()
        total_images = 0
        
        print(f"\n🖼️ Images in Collections")
        print("-" * 50)
        
        for collection in collections:
            images = self.vector_store.search_by_file_type(collection.name, "image", 100)
            if images:
                print(f"\n📁 {collection.name} ({len(images)} images):")
                for img in images[:5]:  # Show first 5
                    print(f"   • {img['metadata'].get('filename', 'Unknown')}")
                    print(f"     {img['content']}")
                if len(images) > 5:
                    print(f"   ... and {len(images) - 5} more")
                total_images += len(images)
        
        print(f"\n📊 Total images across all collections: {total_images}")
    
    def test_clip_embeddings(self):
        """Test CLIP embedding generation."""
        print("CLIP Embedding Test")
        print("1. Test with text")
        print("2. Test with image")
        
        choice = input("Select option: ").strip()
        
        if choice == '1':
            text = input("Enter text: ").strip()
            if text:
                try:
                    embedding = self.doc_processor.get_text_embedding_for_image_search(text)
                    if embedding is not None:
                        print(f"✅ Text embedding generated")
                        print(f"   Dimensions: {len(embedding)}")
                        print(f"   Sample values: {embedding[:5].tolist()}")
                    else:
                        print("❌ Failed to generate embedding")
                except Exception as e:
                    print(f"❌ Error: {e}")
        
        elif choice == '2':
            image_path = input("Image path: ").strip()
            if os.path.exists(image_path):
                try:
                    embedding = self.doc_processor.get_image_embedding(image_path)
                    if embedding is not None:
                        print(f"✅ Image embedding generated")
                        print(f"   Dimensions: {len(embedding)}")
                        print(f"   Sample values: {embedding[:5].tolist()}")
                    else:
                        print("❌ Failed to generate embedding")
                except Exception as e:
                    print(f"❌ Error: {e}")
    
    # Chat Implementation
    def list_conversations(self):
        """List all conversations."""
        conversations = Conversation.query.all()
        if not conversations:
            print("💬 No conversations found")
            return
        
        print(f"\n💬 Conversations ({len(conversations)}):")
        print("-" * 60)
        for conv in conversations:
            print(f"ID: {conv.id} | Title: {conv.title}")
            print(f"  Messages: {len(conv.messages)}")
            print(f"  Created: {conv.created_at.strftime('%Y-%m-%d %H:%M')}")
            print()
    
    def create_conversation(self):
        """Create a new conversation."""
        title = input("Conversation title: ").strip()
        if not title:
            title = f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        try:
            conversation = Conversation(title=title)
            db.session.add(conversation)
            db.session.commit()
            print(f"✅ Conversation '{title}' created with ID: {conversation.id}")
            return conversation
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating conversation: {e}")
    
    def send_chat_message(self):
        """Send a chat message and get AI response."""
        self.list_conversations()
        
        # Get or create conversation
        conv_input = input("Conversation ID (or press Enter for new): ").strip()
        if conv_input:
            try:
                conversation = Conversation.query.get(int(conv_input))
                if not conversation:
                    print("❌ Conversation not found")
                    return
            except ValueError:
                print("❌ Invalid conversation ID")
                return
        else:
            conversation = self.create_conversation()
            if not conversation:
                return
        
        # Get collection if desired
        use_collection = input("Use a collection? (y/N): ").strip().lower()
        collection_name = None
        if use_collection == 'y':
            self.list_collections()
            try:
                cid = int(input("Collection ID: "))
                collection = Collection.query.get(cid)
                if collection:
                    collection_name = collection.name
            except ValueError:
                pass
        
        message = input("Your message: ").strip()
        if not message:
            return
        
        try:
            # Save user message
            user_msg = Message(
                conversation_id=conversation.id,
                role='user',
                content=message,
                collection_used=collection_name
            )
            db.session.add(user_msg)
            
            # Get AI response
            print("🤖 Generating AI response...")
            response_data = self.ai_agent.generate_response(
                user_message=message,
                collection_name=collection_name,
                conversation_history=[]
            )
            
            # Save AI response
            ai_msg = Message(
                conversation_id=conversation.id,
                role='assistant',
                content=response_data['response'],
                collection_used=collection_name,
                verified=response_data['verified']
            )
            
            if response_data.get('images'):
                ai_msg.set_images(response_data['images'])
            
            db.session.add(ai_msg)
            db.session.commit()
            
            print(f"\n🤖 AI Response:")
            print("-" * 40)
            print(response_data['response'])
            
            if response_data.get('verified'):
                print(f"\n✅ Response verified")
            else:
                print(f"\n⚠️ Response unverified")
            
            if response_data.get('images'):
                print(f"\n🖼️ Images found: {len(response_data['images'])}")
                for i, img in enumerate(response_data['images'], 1):
                    print(f"   {i}. {img['metadata'].get('file_path', 'Unknown')}")
                    print(f"      {img['content']}")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Chat error: {e}")
    
    def test_ai_response(self):
        """Test AI response without saving to database."""
        message = input("Test message: ").strip()
        if not message:
            return
        
        # Get collection if desired
        use_collection = input("Use a collection? (y/N): ").strip().lower()
        collection_name = None
        if use_collection == 'y':
            self.list_collections()
            try:
                cid = int(input("Collection ID: "))
                collection = Collection.query.get(cid)
                if collection:
                    collection_name = collection.name
            except ValueError:
                pass
        
        try:
            print("🤖 Testing AI response...")
            response_data = self.ai_agent.generate_response(
                user_message=message,
                collection_name=collection_name,
                conversation_history=[]
            )
            
            print(f"\n🤖 Test Response:")
            print("-" * 40)
            print(response_data['response'])
            
            print(f"\nVerified: {response_data.get('verified', False)}")
            print(f"Context Used: {response_data.get('context_used', False)}")
            
            if response_data.get('images'):
                print(f"Images: {len(response_data['images'])}")
            
        except Exception as e:
            print(f"❌ AI test error: {e}")
    
    def test_image_search_chat(self):
        """Test image search through chat interface."""
        query = input("Image search query: ").strip()
        if not query:
            return
        
        self.list_collections()
        try:
            cid = int(input("Collection ID: "))
            collection = Collection.query.get(cid)
            if not collection:
                print("❌ Collection not found")
                return
        except ValueError:
            print("❌ Invalid collection ID")
            return
        
        try:
            print("🖼️ Searching for images...")
            images = self.ai_agent._search_images(collection.name, query, 5)
            
            if not images:
                print("🔍 No images found")
                return
            
            print(f"\n🖼️ Found {len(images)} images:")
            print("-" * 50)
            for i, img in enumerate(images, 1):
                print(f"{i}. {img['metadata'].get('file_path', 'Unknown')}")
                print(f"   {img['content']}")
                if 'similarity' in img:
                    print(f"   Similarity: {img['similarity']:.3f}")
                print()
            
        except Exception as e:
            print(f"❌ Image search error: {e}")
    
    # File Linking Implementation
    def list_files_in_collection(self):
        """List files in collection with download info."""
        self.list_collections()
        try:
            collection_id = int(input("Collection ID: "))
            collection = Collection.query.get(collection_id)
            if not collection:
                print("❌ Collection not found")
                return
        except ValueError:
            print("❌ Invalid collection ID")
            return
        
        if not collection.documents:
            print("📭 No files in this collection")
            return
        
        print(f"\n🔗 Files in '{collection.name}'")
        print("-" * 70)
        for doc in collection.documents:
            print(f"📄 {doc.filename} ({doc.file_type})")
            print(f"   Size: {doc.file_size or 0} bytes")
            print(f"   Storage: {doc.stored_file_path or 'Not stored'}")
            print(f"   Download: {doc.original_file_url or 'No URL'}")
            
            # Check if physical file exists
            if doc.stored_file_path and os.path.exists(doc.stored_file_path):
                print(f"   Physical: ✅ File exists")
            else:
                print(f"   Physical: ❌ File missing")
            print()
    
    def test_download_urls(self):
        """Test that download URLs are properly generated."""
        collections = Collection.query.all()
        total_files = 0
        files_with_urls = 0
        
        print(f"\n🔗 Download URL Test")
        print("-" * 40)
        
        for collection in collections:
            for doc in collection.documents:
                total_files += 1
                if doc.original_file_url:
                    files_with_urls += 1
                    print(f"✅ {doc.filename}: {doc.original_file_url}")
                else:
                    print(f"❌ {doc.filename}: No URL")
        
        print(f"\n📊 Summary: {files_with_urls}/{total_files} files have download URLs")
        if total_files > 0:
            percentage = (files_with_urls / total_files) * 100
            print(f"📊 Coverage: {percentage:.1f}%")
    
    def verify_file_storage(self):
        """Verify that all files are properly stored."""
        collections = Collection.query.all()
        total_files = 0
        stored_files = 0
        
        print(f"\n📁 File Storage Verification")
        print("-" * 40)
        
        for collection in collections:
            print(f"\n📁 Collection: {collection.name}")
            for doc in collection.documents:
                total_files += 1
                if doc.stored_file_path and os.path.exists(doc.stored_file_path):
                    stored_files += 1
                    print(f"   ✅ {doc.filename}")
                else:
                    print(f"   ❌ {doc.filename} (missing: {doc.stored_file_path})")
        
        print(f"\n📊 Summary: {stored_files}/{total_files} files properly stored")
        if total_files > 0:
            percentage = (stored_files / total_files) * 100
            print(f"📊 Storage integrity: {percentage:.1f}%")
    
    def test_file_serving(self):
        """Test file serving URLs."""
        print("This would test the Flask file serving endpoints")
        print("To test file serving:")
        print("1. Start the Flask app: python3 app.py")
        print("2. Visit file URLs in browser or use curl")
        print()
        
        # Show some example URLs
        collections = Collection.query.all()
        for collection in collections[:2]:
            for doc in collection.documents[:3]:
                if doc.original_file_url:
                    print(f"Test URL: http://localhost:3000{doc.original_file_url}")
    
    def check_file_linking(self):
        """Check that all files are properly linked."""
        print(f"\n🔗 File Linking Health Check")
        print("-" * 50)
        
        collections = Collection.query.all()
        issues = []
        
        for collection in collections:
            for doc in collection.documents:
                # Check database fields
                if not doc.filename:
                    issues.append(f"Missing filename: Document {doc.id}")
                
                if not doc.file_path:
                    issues.append(f"Missing file_path: {doc.filename}")
                
                if not doc.stored_file_path:
                    issues.append(f"Missing stored_file_path: {doc.filename}")
                
                if not doc.original_file_url:
                    issues.append(f"Missing download URL: {doc.filename}")
                
                # Check physical file
                if doc.stored_file_path and not os.path.exists(doc.stored_file_path):
                    issues.append(f"Physical file missing: {doc.filename}")
        
        if issues:
            print(f"❌ Found {len(issues)} issues:")
            for issue in issues:
                print(f"   • {issue}")
        else:
            print("✅ All files properly linked!")
    
    # Database and System Status
    def show_database_status(self):
        """Show database and system status."""
        print(f"\n🗄️ Database Status")
        print("-" * 40)
        
        # Collections
        collections_count = Collection.query.count()
        print(f"Collections: {collections_count}")
        
        # Documents
        documents_count = Document.query.count()
        print(f"Documents: {documents_count}")
        
        # Chunks
        chunks_count = DocumentChunk.query.count()
        print(f"Document Chunks: {chunks_count}")
        
        # Conversations
        conversations_count = Conversation.query.count()
        print(f"Conversations: {conversations_count}")
        
        # Messages
        messages_count = Message.query.count()
        print(f"Messages: {messages_count}")
        
        # File types distribution
        if documents_count > 0:
            print(f"\n📊 File Types:")
            from sqlalchemy import func
            file_types = db.session.query(
                Document.file_type,
                func.count(Document.id)
            ).group_by(Document.file_type).all()
            
            for file_type, count in file_types:
                print(f"   {file_type}: {count}")
        
        # Vector store status
        print(f"\n🔢 Vector Store:")
        print(f"   Client: ChromaDB")
        print(f"   Directory: ./chroma_db")
        
        # Model status
        print(f"\n🤖 Models:")
        print(f"   Sentence Transformer: {self.vector_store.model.get_model_name() if hasattr(self.vector_store.model, 'get_model_name') else 'all-MiniLM-L6-v2'}")
        print(f"   CLIP: ViT-B/32")
        print(f"   Device: {self.doc_processor.device}")
    
    def create_test_data(self):
        """Create sample test data for testing."""
        print("🧪 Creating Test Data")
        print("-" * 30)
        
        try:
            # Create test collection
            collection = Collection(name="Test Collection")
            db.session.add(collection)
            db.session.flush()
            
            # Create test files
            test_dir = tempfile.mkdtemp()
            
            # Text file
            text_file = os.path.join(test_dir, "test_document.txt")
            with open(text_file, 'w') as f:
                f.write("This is a test document about machine learning and AI. "
                       "It contains information about neural networks, training data, "
                       "and deep learning algorithms.")
            
            # Image file
            image_file = os.path.join(test_dir, "test_image.png")
            img = Image.new('RGB', (100, 100), color='red')
            img.save(image_file)
            
            print(f"📁 Created test files in: {test_dir}")
            
            # Process and upload files
            for file_path in [text_file, image_file]:
                self.process_and_upload_file(file_path, collection)
            
            # Create test conversation
            conversation = Conversation(title="Test Conversation")
            db.session.add(conversation)
            db.session.flush()
            
            # Add test messages
            user_msg = Message(
                conversation_id=conversation.id,
                role='user',
                content='Tell me about machine learning',
                collection_used=collection.name
            )
            db.session.add(user_msg)
            
            ai_msg = Message(
                conversation_id=conversation.id,
                role='assistant',
                content='Machine learning is a subset of AI that enables systems to learn from data.',
                collection_used=collection.name,
                verified=True
            )
            db.session.add(ai_msg)
            
            db.session.commit()
            
            print(f"✅ Test data created successfully!")
            print(f"   Collection: {collection.name} (ID: {collection.id})")
            print(f"   Documents: 2 (text + image)")
            print(f"   Conversation: {conversation.title} (ID: {conversation.id})")
            
            # Clean up temp files
            import shutil
            shutil.rmtree(test_dir)
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error creating test data: {e}")
    
    def run_full_test_suite(self):
        """Run comprehensive test suite."""
        print("🧪 Running Full Test Suite")
        print("=" * 50)
        
        tests = [
            ("Database Connection", self.test_database_connection),
            ("Vector Store", self.test_vector_store),
            ("Document Processing", self.test_document_processing_suite),
            ("CLIP Functionality", self.test_clip_functionality),
            ("Search Operations", self.test_search_operations),
            ("File Linking", self.test_file_linking_suite),
            ("AI Agent", self.test_ai_agent)
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"\n🔍 Testing {test_name}...")
            try:
                result = test_func()
                if result:
                    print(f"✅ {test_name} - PASSED")
                    results.append((test_name, True, None))
                else:
                    print(f"❌ {test_name} - FAILED")
                    results.append((test_name, False, "Test returned False"))
            except Exception as e:
                print(f"❌ {test_name} - ERROR: {e}")
                results.append((test_name, False, str(e)))
        
        # Summary
        print(f"\n📊 Test Suite Results")
        print("=" * 30)
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)
        
        for test_name, success, error in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} - {test_name}")
            if error and not success:
                print(f"      Error: {error}")
        
        print(f"\n📊 Summary: {passed}/{total} tests passed")
        if passed == total:
            print("🎉 All tests passed!")
        else:
            print(f"⚠️ {total - passed} tests failed")
    
    def test_database_connection(self):
        """Test database connection and basic operations."""
        try:
            # Test basic query
            count = Collection.query.count()
            return True
        except:
            return False
    
    def test_vector_store(self):
        """Test vector store operations."""
        try:
            # Test embedding generation
            embeddings = self.vector_store.model.encode(["test text"])
            return len(embeddings[0]) > 0
        except:
            return False
    
    def test_document_processing_suite(self):
        """Test document processing functionality."""
        try:
            # Create temp text file
            temp_dir = tempfile.mkdtemp()
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("This is a test document.")
            
            # Process file
            result = self.doc_processor.process_single_file(test_file)
            
            # Clean up
            import shutil
            shutil.rmtree(temp_dir)
            
            return result is not None and 'content' in result
        except:
            return False
    
    def test_clip_functionality(self):
        """Test CLIP image processing."""
        try:
            # Create temp image
            temp_dir = tempfile.mkdtemp()
            test_image = os.path.join(temp_dir, "test.png")
            img = Image.new('RGB', (50, 50), color='blue')
            img.save(test_image)
            
            # Test embedding
            embedding = self.doc_processor.get_image_embedding(test_image)
            
            # Clean up
            import shutil
            shutil.rmtree(temp_dir)
            
            return embedding is not None and len(embedding) == 512
        except:
            return False
    
    def test_search_operations(self):
        """Test search functionality."""
        try:
            collections = Collection.query.all()
            if not collections:
                return True  # No collections to test
            
            # Test search in first collection
            results = self.vector_store.search_similar_chunks(
                collections[0].name, "test query", 1
            )
            return True  # Search completed without error
        except:
            return False
    
    def test_file_linking_suite(self):
        """Test file linking functionality."""
        try:
            documents = Document.query.all()
            if not documents:
                return True  # No documents to test
            
            # Check that documents have required fields
            for doc in documents[:5]:  # Test first 5
                if not doc.filename or not doc.file_path:
                    return False
            
            return True
        except:
            return False
    
    def test_ai_agent(self):
        """Test AI agent functionality."""
        try:
            # Test simple response (without API call)
            # Just test that agent initializes
            return self.ai_agent is not None
        except:
            return False


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="CLI Testing Interface for theOrb-web",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument('command', nargs='?', default='interactive',
                       choices=['interactive', 'collections', 'documents', 'search', 
                               'images', 'chat', 'files', 'full-test'],
                       help='Command to run')
    
    parser.add_argument('--create', help='Create collection with name')
    parser.add_argument('--query', help='Search query')
    parser.add_argument('--collection', type=int, help='Collection ID')
    parser.add_argument('--file', help='File path to process')
    
    args = parser.parse_args()
    
    # Initialize tester
    try:
        tester = OrbCLITester()
    except Exception as e:
        print(f"❌ Failed to initialize tester: {e}")
        return 1
    
    # Execute command
    try:
        if args.command == 'interactive':
            tester.interactive_mode()
        
        elif args.command == 'collections':
            if args.create:
                tester.create_collection(args.create)
            else:
                tester.list_collections()
        
        elif args.command == 'search':
            if args.query and args.collection:
                collection = Collection.query.get(args.collection)
                if collection:
                    results = tester.vector_store.search_similar_chunks(
                        collection.name, args.query, 5
                    )
                    print(f"Found {len(results)} results")
                    for i, r in enumerate(results, 1):
                        print(f"{i}. {r['metadata'].get('filename', 'Unknown')}")
            else:
                print("Usage: --query 'search term' --collection ID")
        
        elif args.command == 'full-test':
            tester.run_full_test_suite()
        
        else:
            print(f"Command {args.command} not implemented in non-interactive mode")
            print("Use 'interactive' for full menu")
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())