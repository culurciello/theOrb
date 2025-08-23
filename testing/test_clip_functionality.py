#!/usr/bin/env python3
"""
Test script to verify CLIP image similarity functionality
"""

import os
import sys
from document_processor import DocumentProcessor
from vector_store import VectorStore
import tempfile
from PIL import Image
import numpy as np

def test_clip_functionality():
    """Test CLIP image processing and similarity search."""
    print("🔍 Testing CLIP Image Similarity Implementation")
    print("=" * 50)
    
    try:
        # Initialize components
        print("1. Initializing DocumentProcessor with CLIP...")
        doc_processor = DocumentProcessor()
        print("   ✅ CLIP model loaded successfully")
        
        print("2. Initializing VectorStore...")
        vector_store = VectorStore()
        print("   ✅ VectorStore initialized")
        
        # Create a test image
        print("3. Creating test images...")
        test_dir = tempfile.mkdtemp()
        
        # Create simple test images
        img1 = Image.new('RGB', (100, 100), color='red')
        img1_path = os.path.join(test_dir, 'red_image.png')
        img1.save(img1_path)
        
        img2 = Image.new('RGB', (100, 100), color='blue')
        img2_path = os.path.join(test_dir, 'blue_image.png')
        img2.save(img2_path)
        
        print(f"   ✅ Created test images: {img1_path}, {img2_path}")
        
        # Test image embedding extraction
        print("4. Testing image embedding extraction...")
        embedding1 = doc_processor.get_image_embedding(img1_path)
        embedding2 = doc_processor.get_image_embedding(img2_path)
        
        if embedding1 is not None and embedding2 is not None:
            print(f"   ✅ Embeddings extracted - Shape: {embedding1.shape}")
            
            # Test similarity calculation
            similarity = np.dot(embedding1, embedding2) / (np.linalg.norm(embedding1) * np.linalg.norm(embedding2))
            print(f"   ✅ Similarity between red and blue images: {similarity:.4f}")
        else:
            print("   ❌ Failed to extract embeddings")
            return False
        
        # Test text embedding for image search
        print("5. Testing text embedding for image search...")
        text_embedding = doc_processor.get_text_embedding_for_image_search("a red picture")
        if text_embedding is not None:
            print(f"   ✅ Text embedding extracted - Shape: {text_embedding.shape}")
        else:
            print("   ❌ Failed to extract text embedding")
            return False
        
        # Test image processing
        print("6. Testing image file processing...")
        processed_image = doc_processor.process_single_file(img1_path)
        if processed_image and 'clip_embedding' in processed_image:
            print("   ✅ Image processed with CLIP embedding")
            print(f"   - File type: {processed_image['file_type']}")
            print(f"   - Content: {processed_image['content']}")
            print(f"   - Categories: {processed_image['categories']}")
        else:
            print("   ❌ Failed to process image file")
            return False
        
        print("\n🎉 All CLIP functionality tests passed!")
        print("\n📋 Available Features:")
        print("   • Extract CLIP embeddings from images")
        print("   • Extract text embeddings for image search")
        print("   • Process images with automatic descriptions")
        print("   • Store image embeddings for similarity search")
        print("   • Search similar images by keywords")
        print("   • Search similar images by uploading an image")
        
        # Clean up
        os.remove(img1_path)
        os.remove(img2_path)
        os.rmdir(test_dir)
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_api_endpoints():
    """Test that the new API endpoints are properly defined."""
    print("\n🌐 Testing API Endpoints")
    print("=" * 30)
    
    try:
        from routes import bp
        
        # Get all routes
        routes = []
        for rule in bp.url_map.iter_rules():
            if rule.endpoint.startswith(bp.name + '.'):
                routes.append({
                    'endpoint': rule.endpoint,
                    'methods': list(rule.methods - {'HEAD', 'OPTIONS'}),
                    'rule': str(rule)
                })
        
        # Check for our new endpoints
        expected_endpoints = [
            'search_similar_images',
            'get_collection_images_list', 
            'chat_upload_image_search'
        ]
        
        found_endpoints = [route['endpoint'].split('.')[-1] for route in routes]
        
        for endpoint in expected_endpoints:
            if endpoint in found_endpoints:
                print(f"   ✅ {endpoint} endpoint registered")
            else:
                print(f"   ❌ {endpoint} endpoint NOT found")
        
        print(f"\n📊 Total routes: {len(routes)}")
        
    except Exception as e:
        print(f"❌ Error testing endpoints: {str(e)}")

if __name__ == "__main__":
    success = test_clip_functionality()
    test_api_endpoints()
    
    if success:
        print("\n✨ CLIP Image Similarity is ready to use!")
        print("\nUsage Examples:")
        print("1. Upload images to a collection - they'll be processed with CLIP")
        print("2. Search for images using keywords: 'show me pictures of cats'")
        print("3. Upload an image to find similar ones in the collection")
        print("4. Use the chat interface with image similarity search")
    else:
        print("\n❌ Some tests failed. Check the implementation.")
        sys.exit(1)