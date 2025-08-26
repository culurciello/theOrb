from typing import Dict, Any
from pathlib import Path
import torch
import clip
from PIL import Image
import numpy as np
from .base_pipeline import BasePipeline

class ImagePipeline(BasePipeline):
    """
    Image processing pipeline:
    - image to text --> caption --> sentence embeddings
    - send to database: [link to original file, caption]
    """
    
    def __init__(self):
        super().__init__()
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.clip_model, self.clip_preprocess = clip.load("ViT-B/32", device=self.device)
    
    def process(self, file_path: str) -> Dict[str, Any]:
        """Process image file according to the pipeline specification."""
        file_path = Path(file_path)
        
        # Image to text (caption generation)
        caption = self.generate_caption(str(file_path))
        
        # Generate sentence embeddings for the caption
        embedding_list = self.get_sentence_embeddings([caption])
        
        return {
            'link_to_original_file': str(file_path),
            'caption': caption,
            'embedding_list': embedding_list,
            'file_type': 'image',
            'metadata': {
                'file_extension': file_path.suffix,
                'image_dimensions': self.get_image_dimensions(str(file_path))
            }
        }
    
    def generate_caption(self, image_path: str) -> str:
        """Generate text caption for image using CLIP."""
        try:
            image = Image.open(image_path)
            image_tensor = self.clip_preprocess(image).unsqueeze(0).to(self.device)
            
            # Descriptive text queries for better captions
            text_queries = [
                "a photo of people in a meeting",
                "a screenshot of a document", 
                "a diagram showing information",
                "a chart or graph with data",
                "a personal photograph",
                "work-related content",
                "a presentation slide",
                "handwritten notes",
                "a drawing or artwork",
                "a landscape or outdoor scene",
                "an indoor scene with people",
                "text document or page",
                "data visualization",
                "office or workplace setting"
            ]
            
            text_tokens = clip.tokenize(text_queries).to(self.device)
            
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_tensor)
                text_features = self.clip_model.encode_text(text_tokens)
                
                similarities = (image_features @ text_features.T).softmax(dim=-1)
                best_match_idx = similarities.argmax().item()
                best_description = text_queries[best_match_idx]
                confidence = float(similarities.max())
                
            # Generate natural caption
            filename_stem = Path(image_path).stem
            if confidence > 0.3:
                caption = f"Image '{filename_stem}': {best_description}"
            else:
                caption = f"Image '{filename_stem}': an image with visual content"
                
            return caption
            
        except Exception as e:
            print(f"Error generating caption for {image_path}: {e}")
            return f"Image: {Path(image_path).stem}"
    
    def get_image_dimensions(self, image_path: str) -> str:
        """Get image dimensions as a string."""
        try:
            with Image.open(image_path) as img:
                return f"{img.width}x{img.height}"
        except Exception:
            return "unknown"
    
    def get_image_embedding(self, image_path: str) -> np.ndarray:
        """Extract CLIP embedding from an image for similarity search."""
        try:
            image = Image.open(image_path)
            image_tensor = self.clip_preprocess(image).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_tensor)
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                
            return image_features.cpu().numpy().flatten()
        except Exception as e:
            print(f"Error extracting image embedding: {e}")
            return None