# 🖼️ CLIP Image Similarity Features

This document describes the CLIP-based image similarity functionality implemented in theOrb-web.

## Overview

The system now supports advanced image search and similarity detection using OpenAI's CLIP model. Users can:

1. **Search for images using text keywords**
2. **Upload an image to find similar images** 
3. **View all images in collections**
4. **Use image search in chat conversations**

## Features Implemented

### ✅ Core Functionality

- **CLIP Model Integration**: Uses OpenAI's CLIP ViT-B/32 model for image/text understanding
- **Image Embedding Storage**: CLIP embeddings are stored for fast similarity search  
- **Text-to-Image Search**: Search images using natural language descriptions
- **Image-to-Image Search**: Upload an image to find visually similar images
- **Automatic Image Processing**: Images are automatically processed when uploaded to collections

### ✅ API Endpoints

1. **`POST /api/collections/{collection_id}/search-similar-images`**
   - Upload an image to find similar images in a collection
   - Parameters: `image` (file), `n_results` (optional)
   - Returns: List of similar images with similarity scores

2. **`GET /api/collections/{collection_id}/images`**
   - Get all images in a collection
   - Returns: List of all images with metadata

3. **`POST /api/chat/upload-image-search`**
   - Upload an image for similarity search in chat interface
   - Parameters: `image` (file), `collection_id`, `conversation_id` (optional)
   - Returns: Chat response with similar images

### ✅ Enhanced Chat Features

- **Keyword Image Search**: Ask "show me images of cats" or "find pictures related to work"
- **Similar Image Discovery**: Chat recognizes image-related queries automatically
- **Visual Context**: Images are displayed in chat responses with similarity scores

## How It Works

### 1. Image Processing Pipeline

When an image is uploaded to a collection:
```
Upload Image → CLIP Feature Extraction → Generate Description → Store Embeddings → Index in Vector Store
```

### 2. Similarity Search Methods

**Text-to-Image Search:**
```
Text Query → CLIP Text Embedding → Compare with Image Embeddings → Rank by Similarity
```

**Image-to-Image Search:**
```
Query Image → CLIP Image Embedding → Compare with Stored Embeddings → Rank by Similarity
```

### 3. Chat Integration

The AI agent automatically detects image-related queries and:
- Searches using CLIP embeddings for better accuracy
- Combines keyword and visual similarity search
- Displays images with context and similarity scores

## Usage Examples

### 1. Text-Based Image Search in Chat

```
User: "Show me images of meetings"
AI: Found 5 relevant images:
    1. team_meeting.jpg (similarity: 0.892)
    2. conference_room.png (similarity: 0.845)
    ...
```

### 2. Upload Image for Similarity Search

```
POST /api/collections/1/search-similar-images
Content-Type: multipart/form-data

{
  "image": <uploaded_file>,
  "n_results": 5
}

Response:
{
  "similar_images": [
    {
      "content": "Image: a photo of office_photo",
      "metadata": {"file_path": "office_photo.jpg"},
      "similarity": 0.756
    }
  ]
}
```

### 3. Chat with Image Upload

```
POST /api/chat/upload-image-search
Content-Type: multipart/form-data

{
  "image": <uploaded_file>,
  "collection_id": 1,
  "conversation_id": 5
}
```

## Technical Details

### Models Used
- **CLIP**: ViT-B/32 for image/text embeddings (512-dimensional)
- **SentenceTransformers**: all-MiniLM-L6-v2 for text search
- **BART**: facebook/bart-large-cnn for text summarization

### Storage
- **Vector Database**: ChromaDB for efficient similarity search
- **Image Embeddings**: Stored separately in VectorStore for fast retrieval
- **Metadata**: File paths, descriptions, categories stored with embeddings

### Performance
- **GPU Acceleration**: Supports CUDA/MPS when available
- **Batch Processing**: Efficient processing of multiple images
- **Caching**: CLIP model loaded once and reused

## File Changes Made

### Core Files Modified:
1. **`document_processor.py`**: Added CLIP embedding extraction methods
2. **`vector_store.py`**: Added image similarity search functionality  
3. **`ai_agent.py`**: Enhanced image search in chat
4. **`routes.py`**: Added new API endpoints for image search
5. **`requirements.txt`**: Already included necessary dependencies

### New Methods Added:
- `DocumentProcessor.get_image_embedding()`
- `DocumentProcessor.get_text_embedding_for_image_search()`
- `VectorStore.search_similar_images_by_embedding()`
- `VectorStore.search_images_by_keywords()`
- `OrbAIAgent.search_similar_images_by_upload()`

## Next Steps & Potential Enhancements

### Frontend Integration (Not Implemented)
- Add image upload widget to chat interface
- Display image thumbnails in search results
- Add drag-and-drop image upload functionality

### Advanced Features (Future)
- **Multi-modal Search**: Combine text and image queries
- **Image Clustering**: Group similar images automatically
- **Face Recognition**: Search for images containing specific people
- **Object Detection**: Search by specific objects in images

## Troubleshooting

### Common Issues:
1. **CLIP Model Loading**: Requires torch, torchvision, and clip-by-openai packages
2. **Memory Usage**: CLIP model uses ~1GB GPU/RAM
3. **File Formats**: Supports JPG, PNG, BMP, TIFF, GIF
4. **Embedding Dimension**: CLIP embeddings are 512-dimensional vectors

### Performance Tips:
- Use GPU when available for faster processing
- Batch process multiple images when possible
- Store embeddings efficiently to reduce memory usage

## Testing

Run the test script to verify functionality:
```bash
python3 test_clip_functionality.py
```

This will test:
- CLIP model loading
- Image embedding extraction
- Text embedding extraction  
- Image file processing
- Similarity calculations

---

The CLIP image similarity system is now fully implemented and ready for use! 🎉