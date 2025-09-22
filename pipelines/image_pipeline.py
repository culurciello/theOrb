from typing import Dict, Any
from pathlib import Path
import torch
# import clip  # DISABLED: CLIP functionality commented out
# from PIL import Image  # DISABLED: PIL functionality commented out
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
        self._clip_model = None
        self._clip_preprocess = None
    
    # DISABLED: CLIP functionality commented out
    # @property
    # def clip_model(self):
    #     """Lazy load the CLIP model."""
    #     if self._clip_model is None:
    #         print("Loading CLIP model for ImagePipeline...")
    #         self._clip_model, self._clip_preprocess = clip.load("ViT-B/32", device=self.device)
    #     return self._clip_model
    #
    # @property
    # def clip_preprocess(self):
    #     """Lazy load the CLIP preprocessor."""
    #     if self._clip_preprocess is None:
    #         print("Loading CLIP model for ImagePipeline...")
    #         self._clip_model, self._clip_preprocess = clip.load("ViT-B/32", device=self.device)
    #     return self._clip_preprocess
    
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
        """Generate text caption for image (CLIP disabled)."""
        # DISABLED: CLIP functionality commented out - using simple fallback
        try:
            filename_stem = Path(image_path).stem
            file_ext = Path(image_path).suffix.lower()

            # Simple caption based on file extension and name
            if file_ext in ['.png', '.jpg', '.jpeg']:
                return f"Image '{filename_stem}': visual content (CLIP disabled)"
            else:
                return f"Image '{filename_stem}': image file (CLIP disabled)"

        except Exception as e:
            print(f"Error generating caption for {image_path}: {e}")
            return f"Image: {Path(image_path).stem}"
    
    def get_image_dimensions(self, image_path: str) -> str:
        """Get image dimensions as a string (PIL disabled)."""
        # DISABLED: PIL functionality commented out
        try:
            # with Image.open(image_path) as img:
            #     return f"{img.width}x{img.height}"
            return "unknown (PIL disabled)"
        except Exception:
            return "unknown"
    
    def get_image_embedding(self, image_path: str) -> np.ndarray:
        """Extract CLIP embedding from an image for similarity search (DISABLED)."""
        # DISABLED: CLIP functionality commented out
        print(f"Warning: CLIP image embedding disabled for {image_path}")
        return None