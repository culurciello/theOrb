from typing import Dict, Any, List, Optional
from pathlib import Path
import mimetypes
from .text_pipeline import TextPipeline
from .image_pipeline import ImagePipeline
from .table_pipeline import TablePipeline
from .multimodal_text_pipeline import MultiModalTextPipeline
from .video_pipeline import VideoPipeline
from .multimodal_webpage_pipeline import MultiModalWebpagePipeline

class DocumentProcessor:
    """
    Main document processor orchestrator for the personal knowledge graph.
    
    Processes files into Orvin orb format according to document categories:
    [work, personal, general info, contacts info, conversations, meetings, notes]
    
    Processing data pipelines:
    - text only: TextPipeline
    - images: ImagePipeline  
    - tables: TablePipeline
    - multi-modal text: MultiModalTextPipeline
    - videos: VideoPipeline
    - multi-modal webpage: MultiModalWebpagePipeline
    """
    
    def __init__(self):
        # Initialize text-only pipelines (multimodal disabled for now)
        self.text_pipeline = TextPipeline()
        # self.image_pipeline = ImagePipeline()  # DISABLED: multimodal processing
        self.table_pipeline = TablePipeline()
        # self.multimodal_text_pipeline = MultiModalTextPipeline()  # DISABLED: multimodal processing
        # self.video_pipeline = VideoPipeline()  # DISABLED: multimodal processing
        # self.multimodal_webpage_pipeline = MultiModalWebpagePipeline()  # DISABLED: multimodal processing
        
        # File type mappings
        self.file_type_mapping = {
            'text': ['.txt', '.md', '.markdown'],  # DISABLED: .doc, .docx (docx module disabled)
            'pdf': ['.pdf'],
            'image': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.gif', '.webp'],
            'video': ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm'],
            'table': ['.csv', '.xlsx', '.xls'],
            'webpage': ['.html', '.htm']
        }
    
    def process_file(self, file_path: str) -> Dict[str, Any]:
        """
        Process a single file using the appropriate pipeline.
        
        Returns structured data ready for database storage according to the specification:
        - text only: [link to original file, category, summary, embedding list]
        - images: [link to original file, caption]
        - tables: [link to original file, JSON]
        - multi-modal text: [link to original file, category, summary, embedding list, image list, tables list]
        - videos: [link to original file, key_frames list, caption list]
        - multi-modal webpage: like multimodal text + videos
        """
        try:
            if file_path.startswith(('http://', 'https://')):
                # Web URL - use webpage pipeline
                return self.multimodal_webpage_pipeline.process(file_path)
            
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            file_type = self._determine_file_type(file_path_obj.suffix.lower())
            
            # Route to appropriate pipeline (text-only processing enabled)
            if file_type == 'text':
                return self.text_pipeline.process(file_path)
            elif file_type == 'pdf':
                # PDF processing - use text pipeline only (multimodal disabled)
                return self.text_pipeline.process(file_path)
            elif file_type == 'table':
                return self.table_pipeline.process(file_path)
            elif file_type == 'image':
                # return self.image_pipeline.process(file_path)  # DISABLED: multimodal processing
                raise ValueError(f"Image processing disabled - file type not supported: {file_path_obj.suffix}")
            elif file_type == 'video':
                # return self.video_pipeline.process(file_path)  # DISABLED: multimodal processing
                raise ValueError(f"Video processing disabled - file type not supported: {file_path_obj.suffix}")
            elif file_type == 'webpage':
                # return self.multimodal_webpage_pipeline.process(file_path)  # DISABLED: multimodal processing
                raise ValueError(f"Webpage processing disabled - file type not supported: {file_path_obj.suffix}")
            else:
                raise ValueError(f"Unsupported file type: {file_path_obj.suffix}")
                
        except Exception as e:
            print(f"Error processing file {file_path}: {e}")
            return {
                'link_to_original_file': file_path,
                'error': str(e),
                'file_type': 'error',
                'category': ['general info'],
                'summary': f"Error processing file: {str(e)}",
                'embedding_list': [],
                'metadata': {'error': True}
            }
    
    def process_directory(self, directory_path: str, recursive: bool = True) -> List[Dict[str, Any]]:
        """
        Process all files in a directory.
        
        Args:
            directory_path: Path to directory to process
            recursive: Whether to process subdirectories recursively
            
        Returns:
            List of processed document data dictionaries
        """
        processed_docs = []
        directory_path = Path(directory_path)
        
        if not directory_path.exists() or not directory_path.is_dir():
            raise ValueError(f"Invalid directory path: {directory_path}")
        
        # Get file iterator based on recursive flag
        file_iterator = directory_path.rglob('*') if recursive else directory_path.iterdir()
        
        for file_path in file_iterator:
            if file_path.is_file():
                try:
                    doc_data = self.process_file(str(file_path))
                    if doc_data and 'error' not in doc_data:
                        processed_docs.append(doc_data)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    continue
        
        return processed_docs
    
    def _determine_file_type(self, file_ext: str) -> str:
        """Determine the file type category based on extension."""
        for file_type, extensions in self.file_type_mapping.items():
            if file_ext in extensions:
                return file_type
        return 'unknown'
    
    def get_supported_file_types(self) -> Dict[str, List[str]]:
        """Get all supported file types and their extensions."""
        return self.file_type_mapping.copy()
    
    def is_supported_file(self, file_path: str) -> bool:
        """Check if a file type is supported for processing."""
        if file_path.startswith(('http://', 'https://')):
            return True  # Web URLs are supported
        
        file_ext = Path(file_path).suffix.lower()
        return self._determine_file_type(file_ext) != 'unknown'
    
    def batch_process_files(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Process a batch of files.
        
        Args:
            file_paths: List of file paths to process
            
        Returns:
            List of processed document data dictionaries
        """
        processed_docs = []
        
        for file_path in file_paths:
            try:
                doc_data = self.process_file(file_path)
                if doc_data:
                    processed_docs.append(doc_data)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
        
        return processed_docs