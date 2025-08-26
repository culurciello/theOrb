from typing import Dict, Any, List
from pathlib import Path
import cv2
import numpy as np
import torch
import clip
from PIL import Image
from .image_pipeline import ImagePipeline

class VideoPipeline(ImagePipeline):
    """
    Video processing pipeline:
    - extract key images from video --> key_frames
        - key_frames v0.1: 10 frames per video, equally spaced
        - key_frames v0.2: every new scene is detected (change in embeddings, or change of more pixels than threshold)
    - image to text --> caption --> sentence embeddings  
    - send to database: [link to original file, key_frames list, caption list]
    """
    
    def __init__(self):
        super().__init__()
        self.max_keyframes = 10
        self.scene_change_threshold = 0.3  # For scene detection
    
    def process(self, file_path: str) -> Dict[str, Any]:
        """Process video file according to the pipeline specification."""
        file_path = Path(file_path)
        
        # Extract key frames (v0.1: equally spaced)
        key_frames_v1 = self.extract_keyframes_v1(str(file_path))
        
        # Extract key frames (v0.2: scene detection)
        key_frames_v2 = self.extract_keyframes_v2(str(file_path))
        
        # Generate captions for all key frames
        caption_list_v1 = []
        for frame_data in key_frames_v1:
            caption = self.generate_frame_caption(frame_data['frame'], frame_data['timestamp'])
            caption_list_v1.append({
                'timestamp': frame_data['timestamp'],
                'caption': caption
            })
        
        caption_list_v2 = []
        for frame_data in key_frames_v2:
            caption = self.generate_frame_caption(frame_data['frame'], frame_data['timestamp'])
            caption_list_v2.append({
                'timestamp': frame_data['timestamp'],
                'caption': caption
            })
        
        # Generate embeddings for captions
        all_captions_v1 = [item['caption'] for item in caption_list_v1]
        all_captions_v2 = [item['caption'] for item in caption_list_v2]
        
        embedding_list_v1 = self.get_sentence_embeddings(all_captions_v1)
        embedding_list_v2 = self.get_sentence_embeddings(all_captions_v2)
        
        # Get video metadata
        metadata = self.get_video_metadata(str(file_path))
        
        return {
            'link_to_original_file': str(file_path),
            'key_frames_v1': {
                'method': 'equally_spaced',
                'frames': key_frames_v1,
                'count': len(key_frames_v1)
            },
            'key_frames_v2': {
                'method': 'scene_detection', 
                'frames': key_frames_v2,
                'count': len(key_frames_v2)
            },
            'caption_list_v1': caption_list_v1,
            'caption_list_v2': caption_list_v2,
            'embedding_list_v1': embedding_list_v1,
            'embedding_list_v2': embedding_list_v2,
            'file_type': 'video',
            'metadata': metadata
        }
    
    def extract_keyframes_v1(self, video_path: str) -> List[Dict[str, Any]]:
        """Extract 10 equally spaced keyframes from video."""
        try:
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            if total_frames == 0 or fps == 0:
                cap.release()
                return []
            
            # Calculate frame indices for 10 equally spaced frames
            frame_indices = []
            if total_frames <= self.max_keyframes:
                frame_indices = list(range(0, total_frames, max(1, total_frames // self.max_keyframes)))
            else:
                step = total_frames // self.max_keyframes
                frame_indices = [i * step for i in range(self.max_keyframes)]
            
            keyframes = []
            for frame_idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                
                if ret:
                    timestamp = frame_idx / fps if fps > 0 else frame_idx
                    
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    keyframes.append({
                        'frame_index': frame_idx,
                        'timestamp': timestamp,
                        'frame': frame_rgb
                    })
            
            cap.release()
            return keyframes
            
        except Exception as e:
            print(f"Error extracting v1 keyframes from {video_path}: {e}")
            return []
    
    def extract_keyframes_v2(self, video_path: str) -> List[Dict[str, Any]]:
        """Extract keyframes based on scene detection."""
        try:
            cap = cv2.VideoCapture(video_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            if fps == 0:
                cap.release()
                return []
            
            keyframes = []
            prev_frame = None
            frame_idx = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Convert to grayscale for comparison
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                # First frame is always a keyframe
                if prev_frame is None:
                    timestamp = frame_idx / fps
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    keyframes.append({
                        'frame_index': frame_idx,
                        'timestamp': timestamp,
                        'frame': frame_rgb
                    })
                    prev_frame = gray
                    frame_idx += 1
                    continue
                
                # Calculate difference between current and previous frame
                diff = cv2.absdiff(prev_frame, gray)
                diff_percentage = np.sum(diff > 30) / diff.size  # Threshold for pixel change
                
                # If significant change detected, add as keyframe
                if diff_percentage > self.scene_change_threshold:
                    timestamp = frame_idx / fps
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    keyframes.append({
                        'frame_index': frame_idx,
                        'timestamp': timestamp,
                        'frame': frame_rgb
                    })
                    
                    prev_frame = gray
                    
                    # Limit total keyframes to prevent excessive processing
                    if len(keyframes) >= 20:
                        break
                
                frame_idx += 1
            
            cap.release()
            return keyframes
            
        except Exception as e:
            print(f"Error extracting v2 keyframes from {video_path}: {e}")
            return []
    
    def generate_frame_caption(self, frame: np.ndarray, timestamp: float) -> str:
        """Generate caption for a video frame."""
        try:
            # Convert numpy array to PIL Image
            pil_image = Image.fromarray(frame)
            
            # Use CLIP to generate description
            image_tensor = self.clip_preprocess(pil_image).unsqueeze(0).to(self.device)
            
            # Video-specific text queries
            text_queries = [
                "people in a meeting or conference",
                "a presentation being given",
                "someone speaking or talking",
                "a workspace or office setting", 
                "a screen recording or tutorial",
                "people collaborating or working",
                "a video call or remote meeting",
                "someone demonstrating something",
                "a lecture or educational content",
                "people in a discussion"
            ]
            
            text_tokens = clip.tokenize(text_queries).to(self.device)
            
            with torch.no_grad():
                image_features = self.clip_model.encode_image(image_tensor)
                text_features = self.clip_model.encode_text(text_tokens)
                
                similarities = (image_features @ text_features.T).softmax(dim=-1)
                best_match_idx = similarities.argmax().item()
                best_description = text_queries[best_match_idx]
                confidence = float(similarities.max())
            
            # Create timestamped caption
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)
            time_str = f"{minutes}:{seconds:02d}"
            
            if confidence > 0.3:
                caption = f"At {time_str}: {best_description}"
            else:
                caption = f"At {time_str}: video content"
            
            return caption
            
        except Exception as e:
            print(f"Error generating frame caption: {e}")
            minutes = int(timestamp // 60)
            seconds = int(timestamp % 60)
            return f"At {minutes}:{seconds:02d}: video frame"
    
    def get_video_metadata(self, video_path: str) -> Dict[str, Any]:
        """Get video file metadata."""
        try:
            cap = cv2.VideoCapture(video_path)
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = total_frames / fps if fps > 0 else 0
            
            cap.release()
            
            file_path = Path(video_path)
            
            return {
                'file_extension': file_path.suffix,
                'file_size': file_path.stat().st_size,
                'duration_seconds': duration,
                'fps': fps,
                'resolution': f"{width}x{height}",
                'total_frames': total_frames
            }
            
        except Exception as e:
            print(f"Error getting video metadata: {e}")
            return {
                'error': str(e),
                'file_extension': Path(video_path).suffix
            }