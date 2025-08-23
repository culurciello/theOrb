#!/usr/bin/env python3
"""
Quick Test Script for theOrb-web
===============================

A fast validation script to quickly check that core functionality is working.
Perfect for development and debugging.

Usage:
    python3 quick_test.py
"""

import sys
import os
import tempfile
import time
from PIL import Image

# Add the app directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Collection, Document

def quick_test():
    """Run quick validation tests."""
    print("⚡ Quick Test - theOrb-web")
    print("=" * 40)
    
    with app.app_context():
        tests_passed = 0
        total_tests = 0
        
        # Test 1: Database Connection
        total_tests += 1
        try:
            count = Collection.query.count()
            print(f"✅ Database: Connected ({count} collections)")
            tests_passed += 1
        except Exception as e:
            print(f"❌ Database: {e}")
        
        # Test 2: Vector Store
        total_tests += 1
        try:
            from vector_store import VectorStore
            vs = VectorStore()
            embeddings = vs.model.encode(["test"])
            print(f"✅ Vector Store: Working ({len(embeddings[0])} dim)")
            tests_passed += 1
        except Exception as e:
            print(f"❌ Vector Store: {e}")
        
        # Test 3: Document Processor
        total_tests += 1
        try:
            from document_processor import DocumentProcessor
            dp = DocumentProcessor()
            
            # Create temp text file
            temp_dir = tempfile.mkdtemp()
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, 'w') as f:
                f.write("This is a test document.")
            
            result = dp.process_single_file(test_file)
            
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir)
            
            if result and 'content' in result:
                print(f"✅ Document Processor: Working")
                tests_passed += 1
            else:
                print(f"❌ Document Processor: No result")
                
        except Exception as e:
            print(f"❌ Document Processor: {e}")
        
        # Test 4: CLIP Model
        total_tests += 1
        try:
            from document_processor import DocumentProcessor
            dp = DocumentProcessor()
            
            # Create temp image
            temp_dir = tempfile.mkdtemp()
            test_image = os.path.join(temp_dir, "test.png")
            img = Image.new('RGB', (64, 64), color='blue')
            img.save(test_image)
            
            embedding = dp.get_image_embedding(test_image)
            
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir)
            
            if embedding is not None and len(embedding) == 512:
                print(f"✅ CLIP: Working ({len(embedding)} dim)")
                tests_passed += 1
            else:
                print(f"❌ CLIP: Invalid embedding")
                
        except Exception as e:
            print(f"❌ CLIP: {e}")
        
        # Test 5: AI Agent
        total_tests += 1
        try:
            from ai_agent import OrbAIAgent
            agent = OrbAIAgent()
            print(f"✅ AI Agent: Initialized")
            tests_passed += 1
        except Exception as e:
            print(f"❌ AI Agent: {e}")
        
        # Test 6: File Storage
        total_tests += 1
        try:
            uploads_dir = "uploads"
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
            
            # Test write
            test_file = os.path.join(uploads_dir, "quick_test.tmp")
            with open(test_file, 'w') as f:
                f.write("test")
            
            # Test read
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Cleanup
            os.remove(test_file)
            
            if content == "test":
                print(f"✅ File Storage: Working")
                tests_passed += 1
            else:
                print(f"❌ File Storage: Read/write issue")
                
        except Exception as e:
            print(f"❌ File Storage: {e}")
        
        # Results
        print("-" * 40)
        print(f"📊 Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            print("🎉 All systems operational!")
            return True
        elif tests_passed >= total_tests * 0.8:
            print("⚠️ Mostly working, minor issues")
            return True
        else:
            print("🚨 Major issues detected")
            return False

def main():
    """Main entry point."""
    start_time = time.time()
    success = quick_test()
    duration = time.time() - start_time
    
    print(f"⏱️ Completed in {duration:.2f}s")
    
    if success:
        print("✅ System ready for testing!")
        print("\nNext steps:")
        print("  • python3 cli_test.py interactive")
        print("  • python3 automated_tests.py basic")
        print("  • python3 app.py  (start GUI)")
    else:
        print("❌ Fix issues before proceeding")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())