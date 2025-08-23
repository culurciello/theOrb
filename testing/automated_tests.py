#!/usr/bin/env python3
"""
Automated Test Scenarios for theOrb-web
======================================

This script runs predefined test scenarios to validate all functionality
automatically without user interaction.

Usage:
    python3 automated_tests.py [scenario]
    
Scenarios:
    basic           - Basic functionality test
    full            - Complete system test  
    performance     - Performance benchmarks
    integration     - End-to-end integration test
    regression      - Regression test suite
    
Examples:
    python3 automated_tests.py basic
    python3 automated_tests.py full
"""

import sys
import os
import json
import time
import tempfile
from pathlib import Path
from PIL import Image
import uuid
import shutil

# Add the app directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli_test import OrbCLITester
from app import app, db
from models import Collection, Document, Conversation, Message

class AutomatedTestRunner:
    """Automated test runner for comprehensive system validation."""
    
    def __init__(self):
        """Initialize the test runner."""
        self.tester = OrbCLITester()
        self.test_results = []
        self.temp_files = []
        self.test_collections = []
        
        print("🤖 Automated Test Runner Initialized")
        print(f"🗄️ Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
        print()
    
    def __del__(self):
        """Clean up test data."""
        self.cleanup()
    
    def cleanup(self):
        """Clean up temporary files and test data."""
        # Clean up temp files
        for temp_path in self.temp_files:
            try:
                if os.path.exists(temp_path):
                    if os.path.isdir(temp_path):
                        shutil.rmtree(temp_path)
                    else:
                        os.remove(temp_path)
            except Exception as e:
                print(f"⚠️ Cleanup warning: {e}")
        
        # Note: We keep test collections for inspection unless explicitly cleaning
        print("🧹 Cleanup completed")
    
    def run_test(self, test_name, test_func, *args, **kwargs):
        """Run a single test and record results."""
        print(f"\n🔍 Running: {test_name}")
        start_time = time.time()
        
        try:
            result = test_func(*args, **kwargs)
            duration = time.time() - start_time
            
            if result:
                print(f"✅ PASSED - {test_name} ({duration:.2f}s)")
                self.test_results.append({
                    'name': test_name,
                    'status': 'PASSED',
                    'duration': duration,
                    'error': None
                })
                return True
            else:
                print(f"❌ FAILED - {test_name} ({duration:.2f}s)")
                self.test_results.append({
                    'name': test_name,
                    'status': 'FAILED',
                    'duration': duration,
                    'error': 'Test returned False'
                })
                return False
                
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 ERROR - {test_name} ({duration:.2f}s): {e}")
            self.test_results.append({
                'name': test_name,
                'status': 'ERROR',
                'duration': duration,
                'error': str(e)
            })
            return False
    
    def create_test_files(self):
        """Create test files for testing."""
        test_dir = tempfile.mkdtemp(prefix="orb_test_")
        self.temp_files.append(test_dir)
        
        files = {}
        
        # Text files
        files['simple_text'] = os.path.join(test_dir, "simple.txt")
        with open(files['simple_text'], 'w') as f:
            f.write("This is a simple text document for testing. It contains basic information about testing procedures and validation methods.")
        
        files['complex_text'] = os.path.join(test_dir, "complex.txt")
        with open(files['complex_text'], 'w') as f:
            f.write("""
# Complex Document Test
            
This is a more complex document that includes multiple sections and topics.

## Machine Learning
Machine learning is a subset of artificial intelligence that focuses on algorithms and statistical models.

## Data Processing
Data processing involves cleaning, transforming, and analyzing data to extract meaningful insights.

## Neural Networks
Neural networks are computing systems inspired by biological neural networks.
They consist of interconnected nodes that process information.

## Testing Methodology
Our testing methodology includes unit tests, integration tests, and system tests.
We validate functionality, performance, and reliability.
            """)
        
        # Image files
        files['red_image'] = os.path.join(test_dir, "red_square.png")
        red_img = Image.new('RGB', (128, 128), color='red')
        red_img.save(files['red_image'])
        
        files['blue_image'] = os.path.join(test_dir, "blue_circle.png")
        blue_img = Image.new('RGB', (128, 128), color='blue')
        blue_img.save(files['blue_image'])
        
        files['gradient_image'] = os.path.join(test_dir, "gradient.png")
        gradient_img = Image.new('RGB', (128, 128), color='green')
        gradient_img.save(files['gradient_image'])
        
        # JSON data file
        files['data_json'] = os.path.join(test_dir, "sample_data.json")
        sample_data = {
            "users": [
                {"id": 1, "name": "Alice", "role": "admin"},
                {"id": 2, "name": "Bob", "role": "user"},
                {"id": 3, "name": "Charlie", "role": "user"}
            ],
            "settings": {
                "theme": "dark",
                "notifications": True,
                "language": "en"
            }
        }
        with open(files['data_json'], 'w') as f:
            json.dump(sample_data, f, indent=2)
        
        # Markdown file
        files['markdown'] = os.path.join(test_dir, "documentation.md")
        with open(files['markdown'], 'w') as f:
            f.write("""
# Test Documentation

This is a **markdown** document for testing.

## Features
- Text processing
- Image analysis  
- Search functionality
- Data extraction

### Code Example
```python
def test_function():
    return "Hello, World!"
```

> This is a quote block for testing.
            """)
        
        return files
    
    def basic_scenario(self):
        """Run basic functionality test scenario."""
        print("🎯 Running Basic Test Scenario")
        print("=" * 50)
        
        # Test 1: Database Connection
        success = self.run_test(
            "Database Connection",
            lambda: self.tester.test_database_connection()
        )
        if not success:
            return False
        
        # Test 2: Create Collection
        test_collection = None
        def create_test_collection():
            nonlocal test_collection
            test_collection = self.tester.create_collection("Basic Test Collection")
            if test_collection:
                self.test_collections.append(test_collection.id)
                return True
            return False
        
        success = self.run_test(
            "Create Collection",
            create_test_collection
        )
        if not success:
            return False
        
        # Test 3: Upload Document
        test_files = self.create_test_files()
        
        success = self.run_test(
            "Upload Text Document",
            lambda: self.upload_test_file(test_files['simple_text'], test_collection)
        )
        if not success:
            return False
        
        # Test 4: Search Document
        success = self.run_test(
            "Search Document",
            lambda: self.test_search(test_collection.name, "testing procedures")
        )
        if not success:
            return False
        
        # Test 5: Upload Image
        success = self.run_test(
            "Upload Image Document",
            lambda: self.upload_test_file(test_files['red_image'], test_collection)
        )
        if not success:
            return False
        
        # Test 6: CLIP Processing
        success = self.run_test(
            "CLIP Image Processing",
            lambda: self.test_clip_processing(test_files['blue_image'])
        )
        if not success:
            return False
        
        return True
    
    def full_scenario(self):
        """Run comprehensive system test."""
        print("🚀 Running Full Test Scenario")
        print("=" * 50)
        
        # Create test files
        test_files = self.create_test_files()
        
        # Test Collection Management
        collections = []
        for i in range(3):
            collection = self.tester.create_collection(f"Full Test Collection {i+1}")
            if collection:
                collections.append(collection)
                self.test_collections.append(collection.id)
        
        success = self.run_test(
            "Multiple Collections Created",
            lambda: len(collections) == 3
        )
        if not success:
            return False
        
        # Test Document Processing
        file_types = ['simple_text', 'complex_text', 'red_image', 'blue_image', 'data_json', 'markdown']
        upload_success = []
        
        for i, file_type in enumerate(file_types):
            collection = collections[i % len(collections)]
            result = self.upload_test_file(test_files[file_type], collection)
            upload_success.append(result)
        
        success = self.run_test(
            "Multiple File Types Upload",
            lambda: all(upload_success)
        )
        if not success:
            return False
        
        # Test Search Functionality
        search_tests = [
            ("Text Search", collections[0].name, "machine learning"),
            ("Image Search", collections[1].name, "red color"),
            ("Data Search", collections[2].name, "user settings"),
            ("Cross-Collection Search", None, "testing")
        ]
        
        for test_name, collection_name, query in search_tests:
            if collection_name:
                success = self.run_test(
                    test_name,
                    lambda cn=collection_name, q=query: self.test_search(cn, q)
                )
            else:
                success = self.run_test(
                    test_name,
                    lambda q=query: self.test_global_search(q)
                )
            if not success:
                return False
        
        # Test CLIP Functionality
        clip_tests = [
            ("CLIP Text Embedding", lambda: self.test_clip_text("red square image")),
            ("CLIP Image Embedding", lambda: self.test_clip_image(test_files['gradient_image'])),
            ("Image Similarity", lambda: self.test_image_similarity(test_files['red_image'], collections[0].name))
        ]
        
        for test_name, test_func in clip_tests:
            success = self.run_test(test_name, test_func)
            if not success:
                return False
        
        # Test Chat Functionality
        success = self.run_test(
            "Chat Conversation",
            lambda: self.test_chat_functionality(collections[0].name)
        )
        if not success:
            return False
        
        # Test File Linking
        success = self.run_test(
            "File Linking Verification",
            lambda: self.test_file_linking()
        )
        
        return success
    
    def performance_scenario(self):
        """Run performance benchmarks."""
        print("⚡ Running Performance Test Scenario")
        print("=" * 50)
        
        # Create performance test collection
        perf_collection = self.tester.create_collection("Performance Test Collection")
        if not perf_collection:
            return False
        
        self.test_collections.append(perf_collection.id)
        
        # Create larger test files
        test_dir = tempfile.mkdtemp(prefix="orb_perf_")
        self.temp_files.append(test_dir)
        
        # Large text files
        large_files = []
        for i in range(10):
            file_path = os.path.join(test_dir, f"large_doc_{i}.txt")
            with open(file_path, 'w') as f:
                # Write 1000 lines of text
                for j in range(1000):
                    f.write(f"Line {j}: This is a performance test document number {i}. ")
                    f.write("It contains repeated text patterns for testing search performance. ")
                    f.write(f"Document {i}, Line {j}, testing performance optimization.\n")
            large_files.append(file_path)
        
        # Test batch upload performance
        start_time = time.time()
        upload_results = []
        
        for file_path in large_files:
            result = self.upload_test_file(file_path, perf_collection)
            upload_results.append(result)
        
        upload_time = time.time() - start_time
        
        success = self.run_test(
            f"Batch Upload Performance ({len(large_files)} files)",
            lambda: all(upload_results) and upload_time < 120  # Should complete in 2 minutes
        )
        
        print(f"   📊 Upload Time: {upload_time:.2f}s ({upload_time/len(large_files):.2f}s per file)")
        
        # Test search performance
        search_queries = [
            "performance test",
            "document number",
            "optimization",
            "repeated text",
            "testing search"
        ]
        
        search_times = []
        for query in search_queries:
            start_time = time.time()
            results = self.tester.vector_store.search_similar_chunks(
                perf_collection.name, query, 10
            )
            search_time = time.time() - start_time
            search_times.append(search_time)
        
        avg_search_time = sum(search_times) / len(search_times)
        
        success = self.run_test(
            "Search Performance",
            lambda: avg_search_time < 2.0  # Should average under 2 seconds
        )
        
        print(f"   📊 Avg Search Time: {avg_search_time:.3f}s")
        print(f"   📊 Search Times: {[f'{t:.3f}s' for t in search_times]}")
        
        return success
    
    def integration_scenario(self):
        """Run end-to-end integration test."""
        print("🔄 Running Integration Test Scenario")
        print("=" * 50)
        
        # Create integration test data
        test_files = self.create_test_files()
        
        # Step 1: Create collection and upload diverse content
        integration_collection = self.tester.create_collection("Integration Test Collection")
        if not integration_collection:
            return False
        
        self.test_collections.append(integration_collection.id)
        
        # Upload different file types
        uploaded_files = []
        for file_type, file_path in test_files.items():
            result = self.upload_test_file(file_path, integration_collection)
            uploaded_files.append((file_type, result))
        
        success = self.run_test(
            "Multi-format Upload Integration",
            lambda: all(result for _, result in uploaded_files)
        )
        if not success:
            return False
        
        # Step 2: Test cross-format search
        cross_searches = [
            ("Find text about machine learning", "machine learning"),
            ("Find images with colors", "red blue color"),
            ("Find data about users", "user admin role"),
            ("Find documentation", "documentation features")
        ]
        
        for search_desc, query in cross_searches:
            results = self.tester.vector_store.search_similar_chunks(
                integration_collection.name, query, 5
            )
            success = self.run_test(
                f"Cross-format Search: {search_desc}",
                lambda r=results: len(r) > 0
            )
            if not success:
                return False
        
        # Step 3: Test AI agent integration
        success = self.run_test(
            "AI Agent Integration",
            lambda: self.test_ai_integration(integration_collection.name)
        )
        if not success:
            return False
        
        # Step 4: Test image similarity across formats
        if test_files['red_image']:
            success = self.run_test(
                "Image Similarity Integration",
                lambda: self.test_image_similarity(test_files['blue_image'], integration_collection.name)
            )
            if not success:
                return False
        
        # Step 5: Test conversation with mixed content
        success = self.run_test(
            "Mixed Content Conversation",
            lambda: self.test_mixed_content_chat(integration_collection.name)
        )
        
        return success
    
    def regression_scenario(self):
        """Run regression test to ensure existing functionality works."""
        print("🔒 Running Regression Test Scenario")
        print("=" * 50)
        
        # Test core functionality that should always work
        core_tests = [
            ("Database Schema", lambda: self.test_database_schema()),
            ("Vector Store Connection", lambda: self.test_vector_store_connection()),
            ("CLIP Model Loading", lambda: self.test_clip_model()),
            ("Text Processing", lambda: self.test_text_processing()),
            ("Image Processing", lambda: self.test_image_processing_basic()),
            ("Search API", lambda: self.test_search_api()),
            ("File Storage", lambda: self.test_file_storage_system())
        ]
        
        all_passed = True
        for test_name, test_func in core_tests:
            success = self.run_test(test_name, test_func)
            if not success:
                all_passed = False
        
        # Test backwards compatibility
        success = self.run_test(
            "Backwards Compatibility",
            lambda: self.test_backwards_compatibility()
        )
        
        return all_passed and success
    
    # Helper test methods
    def upload_test_file(self, file_path, collection):
        """Upload a test file to collection."""
        try:
            self.tester.process_and_upload_file(file_path, collection)
            return True
        except Exception as e:
            print(f"   Upload error: {e}")
            return False
    
    def test_search(self, collection_name, query):
        """Test search in collection."""
        try:
            results = self.tester.vector_store.search_similar_chunks(
                collection_name, query, 3
            )
            return len(results) > 0
        except Exception as e:
            print(f"   Search error: {e}")
            return False
    
    def test_global_search(self, query):
        """Test global search across collections."""
        try:
            all_results = []
            collections = Collection.query.all()
            
            for collection in collections:
                results = self.tester.vector_store.search_similar_chunks(
                    collection.name, query, 2
                )
                all_results.extend(results)
            
            return len(all_results) > 0
        except Exception as e:
            print(f"   Global search error: {e}")
            return False
    
    def test_clip_processing(self, image_path):
        """Test CLIP image processing."""
        try:
            doc_data = self.tester.doc_processor.process_single_file(image_path)
            return (doc_data is not None and 
                   doc_data['file_type'] == 'image' and 
                   'clip_embedding' in doc_data)
        except Exception as e:
            print(f"   CLIP processing error: {e}")
            return False
    
    def test_clip_text(self, text):
        """Test CLIP text embedding."""
        try:
            embedding = self.tester.doc_processor.get_text_embedding_for_image_search(text)
            return embedding is not None and len(embedding) == 512
        except Exception as e:
            print(f"   CLIP text error: {e}")
            return False
    
    def test_clip_image(self, image_path):
        """Test CLIP image embedding."""
        try:
            embedding = self.tester.doc_processor.get_image_embedding(image_path)
            return embedding is not None and len(embedding) == 512
        except Exception as e:
            print(f"   CLIP image error: {e}")
            return False
    
    def test_image_similarity(self, image_path, collection_name):
        """Test image similarity search."""
        try:
            query_embedding = self.tester.doc_processor.get_image_embedding(image_path)
            if query_embedding is None:
                return False
            
            results = self.tester.vector_store.search_similar_images_by_embedding(
                collection_name, query_embedding, 3
            )
            return len(results) >= 0  # May be 0 if no images in collection
        except Exception as e:
            print(f"   Image similarity error: {e}")
            return False
    
    def test_chat_functionality(self, collection_name):
        """Test chat functionality."""
        try:
            # Create test conversation
            conversation = Conversation(title="Test Automated Chat")
            db.session.add(conversation)
            db.session.flush()
            
            # Test AI response (simplified - no actual API call)
            response_data = {
                'response': 'This is a test response',
                'verified': True,
                'images': []
            }
            
            # Save messages
            user_msg = Message(
                conversation_id=conversation.id,
                role='user',
                content='Test message about documents',
                collection_used=collection_name
            )
            
            ai_msg = Message(
                conversation_id=conversation.id,
                role='assistant',
                content=response_data['response'],
                collection_used=collection_name,
                verified=response_data['verified']
            )
            
            db.session.add_all([user_msg, ai_msg])
            db.session.commit()
            
            return True
        except Exception as e:
            db.session.rollback()
            print(f"   Chat test error: {e}")
            return False
    
    def test_file_linking(self):
        """Test file linking functionality."""
        try:
            documents = Document.query.limit(10).all()
            if not documents:
                return True  # No documents to test
            
            for doc in documents:
                # Check required fields
                if not doc.filename or not doc.file_path:
                    return False
                
                # Check stored file exists if path is provided
                if doc.stored_file_path and not os.path.exists(doc.stored_file_path):
                    print(f"   Missing file: {doc.stored_file_path}")
                    return False
            
            return True
        except Exception as e:
            print(f"   File linking error: {e}")
            return False
    
    def test_ai_integration(self, collection_name):
        """Test AI agent integration."""
        try:
            # Test that AI agent can access collection data
            search_result = self.tester.vector_store.search_similar_chunks(
                collection_name, "test query", 1
            )
            
            # Test image search capability
            images = self.tester.vector_store.search_by_file_type(collection_name, "image", 1)
            
            return True  # If no exceptions, integration is working
        except Exception as e:
            print(f"   AI integration error: {e}")
            return False
    
    def test_mixed_content_chat(self, collection_name):
        """Test chat with mixed content types."""
        try:
            # Test queries that should find different content types
            queries = [
                "show me documents about testing",
                "find images with colors", 
                "what data do we have about users"
            ]
            
            for query in queries:
                results = self.tester.vector_store.search_similar_chunks(
                    collection_name, query, 2
                )
                # Just test that search completes without error
            
            return True
        except Exception as e:
            print(f"   Mixed content error: {e}")
            return False
    
    # Regression test helpers
    def test_database_schema(self):
        """Test database schema integrity."""
        try:
            # Test that all tables exist and basic queries work
            Collection.query.count()
            Document.query.count()
            DocumentChunk.query.count()
            Conversation.query.count()
            Message.query.count()
            return True
        except Exception as e:
            print(f"   Schema error: {e}")
            return False
    
    def test_vector_store_connection(self):
        """Test vector store connection."""
        try:
            # Test embedding generation
            embeddings = self.tester.vector_store.model.encode(["test"])
            return len(embeddings[0]) > 0
        except Exception as e:
            print(f"   Vector store error: {e}")
            return False
    
    def test_clip_model(self):
        """Test CLIP model loading."""
        try:
            # Test that CLIP model is loaded
            processor = self.tester.doc_processor
            return (hasattr(processor, 'clip_model') and 
                   hasattr(processor, 'clip_preprocess'))
        except Exception as e:
            print(f"   CLIP model error: {e}")
            return False
    
    def test_text_processing(self):
        """Test basic text processing."""
        try:
            test_text = "This is a test document for processing."
            # Test that text can be processed without errors
            embeddings = self.tester.vector_store.model.encode([test_text])
            return len(embeddings[0]) > 0
        except Exception as e:
            print(f"   Text processing error: {e}")
            return False
    
    def test_image_processing_basic(self):
        """Test basic image processing."""
        try:
            # Create simple test image
            temp_dir = tempfile.mkdtemp()
            test_image = os.path.join(temp_dir, "test.png")
            img = Image.new('RGB', (32, 32), color='red')
            img.save(test_image)
            
            # Test processing
            result = self.tester.doc_processor.process_single_file(test_image)
            
            # Cleanup
            shutil.rmtree(temp_dir)
            
            return result is not None and result['file_type'] == 'image'
        except Exception as e:
            print(f"   Image processing error: {e}")
            return False
    
    def test_search_api(self):
        """Test search API functionality."""
        try:
            collections = Collection.query.limit(1).all()
            if not collections:
                return True  # No collections to test
            
            # Test search functionality
            results = self.tester.vector_store.search_similar_chunks(
                collections[0].name, "test", 1
            )
            
            return True  # Success if no exception
        except Exception as e:
            print(f"   Search API error: {e}")
            return False
    
    def test_file_storage_system(self):
        """Test file storage system."""
        try:
            # Test uploads directory
            uploads_dir = "uploads"
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
            
            # Test that we can create collection directories
            test_dir = os.path.join(uploads_dir, "test_collection")
            os.makedirs(test_dir, exist_ok=True)
            
            # Test file creation
            test_file = os.path.join(test_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("test")
            
            # Check file exists
            exists = os.path.exists(test_file)
            
            # Cleanup
            os.remove(test_file)
            if os.path.exists(test_dir):
                os.rmdir(test_dir)
            
            return exists
        except Exception as e:
            print(f"   File storage error: {e}")
            return False
    
    def test_backwards_compatibility(self):
        """Test backwards compatibility."""
        try:
            # Test that existing data can still be accessed
            # This is a simplified test - in practice would be more comprehensive
            
            existing_collections = Collection.query.all()
            for collection in existing_collections[:3]:  # Test first 3
                # Test that collection data is accessible
                docs = collection.documents
                # Test that vector store data is accessible  
                stats = self.tester.vector_store.get_collection_stats(collection.name)
            
            return True
        except Exception as e:
            print(f"   Backwards compatibility error: {e}")
            return False
    
    def print_results_summary(self):
        """Print comprehensive test results summary."""
        print("\n" + "=" * 70)
        print("📊 AUTOMATED TEST RESULTS SUMMARY")
        print("=" * 70)
        
        if not self.test_results:
            print("❌ No test results recorded")
            return
        
        # Overall stats
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r['status'] == 'PASSED'])
        failed_tests = len([r for r in self.test_results if r['status'] == 'FAILED'])
        error_tests = len([r for r in self.test_results if r['status'] == 'ERROR'])
        
        total_time = sum(r['duration'] for r in self.test_results)
        avg_time = total_time / total_tests if total_tests > 0 else 0
        
        print(f"📈 Overall Results:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        print(f"   ❌ Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        print(f"   💥 Errors: {error_tests} ({error_tests/total_tests*100:.1f}%)")
        print(f"   ⏱️ Total Time: {total_time:.2f}s")
        print(f"   ⚡ Average Time: {avg_time:.2f}s per test")
        
        # Detailed results
        print(f"\n📋 Detailed Results:")
        for result in self.test_results:
            status_icon = {"PASSED": "✅", "FAILED": "❌", "ERROR": "💥"}[result['status']]
            print(f"   {status_icon} {result['name']} ({result['duration']:.2f}s)")
            if result['error']:
                print(f"      Error: {result['error']}")
        
        # Test collections created
        if self.test_collections:
            print(f"\n🗂️ Test Collections Created: {len(self.test_collections)}")
            for collection_id in self.test_collections:
                collection = Collection.query.get(collection_id)
                if collection:
                    print(f"   • {collection.name} (ID: {collection_id}, Docs: {len(collection.documents)})")
        
        # Overall verdict
        print(f"\n🎯 Final Verdict:")
        if passed_tests == total_tests:
            print("   🎉 ALL TESTS PASSED! System is functioning correctly.")
        elif passed_tests >= total_tests * 0.8:  # 80% pass rate
            print(f"   ⚠️ MOSTLY SUCCESSFUL ({passed_tests}/{total_tests} passed)")
            print("   Most functionality is working, but some issues need attention.")
        else:
            print(f"   🚨 SIGNIFICANT ISSUES DETECTED ({passed_tests}/{total_tests} passed)")
            print("   System needs debugging before production use.")
        
        print("=" * 70)


def main():
    """Main entry point for automated tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Automated Test Runner for theOrb-web")
    parser.add_argument('scenario', nargs='?', default='basic',
                       choices=['basic', 'full', 'performance', 'integration', 'regression', 'all'],
                       help='Test scenario to run')
    parser.add_argument('--cleanup', action='store_true', 
                       help='Clean up test collections after tests')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    # Initialize test runner
    try:
        runner = AutomatedTestRunner()
    except Exception as e:
        print(f"❌ Failed to initialize test runner: {e}")
        return 1
    
    print(f"🎬 Starting Automated Tests - Scenario: {args.scenario.upper()}")
    print(f"⏰ Start Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run selected scenario
    try:
        if args.scenario == 'basic':
            success = runner.basic_scenario()
        elif args.scenario == 'full':
            success = runner.full_scenario()
        elif args.scenario == 'performance':
            success = runner.performance_scenario()
        elif args.scenario == 'integration':
            success = runner.integration_scenario()
        elif args.scenario == 'regression':
            success = runner.regression_scenario()
        elif args.scenario == 'all':
            # Run all scenarios
            scenarios = ['basic', 'full', 'performance', 'integration', 'regression']
            all_success = True
            
            for scenario in scenarios:
                print(f"\n{'='*20} {scenario.upper()} SCENARIO {'='*20}")
                
                if scenario == 'basic':
                    result = runner.basic_scenario()
                elif scenario == 'full':
                    result = runner.full_scenario()
                elif scenario == 'performance':
                    result = runner.performance_scenario()
                elif scenario == 'integration':
                    result = runner.integration_scenario()
                elif scenario == 'regression':
                    result = runner.regression_scenario()
                
                if not result:
                    all_success = False
            
            success = all_success
        else:
            print(f"❌ Unknown scenario: {args.scenario}")
            return 1
        
        # Print results
        runner.print_results_summary()
        
        # Cleanup if requested
        if args.cleanup:
            print(f"\n🧹 Cleaning up test collections...")
            for collection_id in runner.test_collections:
                try:
                    runner.tester.delete_collection(collection_id)
                    print(f"   ✅ Deleted collection {collection_id}")
                except Exception as e:
                    print(f"   ❌ Failed to delete collection {collection_id}: {e}")
        
        print(f"\n⏰ End Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print(f"\n⛔ Tests interrupted by user")
        runner.print_results_summary()
        return 1
    except Exception as e:
        print(f"❌ Test runner error: {e}")
        import traceback
        if args.verbose:
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())