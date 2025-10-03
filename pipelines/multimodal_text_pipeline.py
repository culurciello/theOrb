from typing import Dict, Any, List
from pathlib import Path
import fitz  # PyMuPDF for multi-modal PDF processing
from .text_pipeline import TextPipeline
from .image_pipeline import ImagePipeline
from .table_pipeline import TablePipeline

class MultiModalTextPipeline:
    """
    Multi-modal text processing pipeline:
    - break documents into pages --> for each page --> extract text, images, tables
    - text: process as text
    - images: process as images  
    - tables: process as tables
    - send to database: [link to original file, category, summary, embedding list, image list, tables list]
    """
    
    def __init__(self):
        self.text_pipeline = TextPipeline()
        self.image_pipeline = ImagePipeline()
        self.table_pipeline = TablePipeline()
    
    def process(self, file_path: str) -> Dict[str, Any]:
        """Process multi-modal document according to the pipeline specification."""
        file_path = Path(file_path)
        
        if file_path.suffix.lower() == '.pdf':
            return self._process_pdf(str(file_path))
        else:
            # For other document types, fall back to text processing
            return self.text_pipeline.process(str(file_path))
    
    def _process_pdf(self, file_path: str) -> Dict[str, Any]:
        """Process PDF with multi-modal content extraction."""
        try:
            doc = fitz.open(file_path)
            
            all_text = ""
            image_list = []
            tables_list = []
            page_data = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Extract text from page
                page_text = page.get_text()
                all_text += page_text + "\n"
                
                # Extract images from page
                page_images = self._extract_images_from_page(page, file_path, page_num)
                image_list.extend(page_images)
                
                # Extract tables from page (basic table detection)
                page_tables = self._extract_tables_from_page(page, page_num)
                tables_list.extend(page_tables)
                
                page_data.append({
                    'page_number': page_num + 1,
                    'text_length': len(page_text),
                    'image_count': len(page_images),
                    'table_count': len(page_tables)
                })
            
            doc.close()
            
            # Process text content
            text_chunks = self.text_pipeline.chunk_text(all_text)
            text_embeddings = self.text_pipeline.get_sentence_embeddings(text_chunks)
            
            # Generate summary from first 1000 words
            words = all_text.split()[:1000]
            summary_text = ' '.join(words)
            summary = self.text_pipeline.generate_summary(summary_text)
            
            # Categorize content
            category = self.text_pipeline.categorize_content(summary_text)
            
            return {
                'link_to_original_file': file_path,
                'category': category,
                'summary': summary,
                'embedding_list': text_embeddings,
                'image_list': image_list,
                'tables_list': tables_list,
                'text_chunks': text_chunks,
                'file_type': 'multimodal_text',
                'metadata': {
                    'total_pages': len(page_data),
                    'total_images': len(image_list),
                    'total_tables': len(tables_list),
                    'word_count': len(all_text.split()),
                    'page_breakdown': page_data
                }
            }
            
        except Exception as e:
            print(f"Error processing multi-modal PDF {file_path}: {e}")
            # Fallback to text-only processing
            return self.text_pipeline.process(file_path)
    
    def _extract_images_from_page(self, page, pdf_path: str, page_num: int) -> List[Dict[str, Any]]:
        """Extract images from a PDF page."""
        image_list = []
        
        try:
            image_list_from_page = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list_from_page):
                xref = img[0]
                pix = fitz.Pixmap(page.parent, xref)
                
                if pix.n - pix.alpha < 4:  # GRAY or RGB
                    # Create temporary image file name
                    temp_img_path = f"temp_img_p{page_num}_{img_index}.png"
                    pix.save(temp_img_path)
                    
                    # Generate caption using image pipeline
                    caption = self.image_pipeline.generate_caption(temp_img_path)
                    
                    # Clean up temporary file
                    import os
                    try:
                        os.remove(temp_img_path)
                    except:
                        pass
                    
                    image_list.append({
                        'page': page_num + 1,
                        'image_index': img_index,
                        'caption': caption,
                        'source_file': pdf_path
                    })
                
                pix = None  # Free memory
                
        except Exception as e:
            print(f"Error extracting images from page {page_num}: {e}")
        
        return image_list
    
    def _extract_tables_from_page(self, page, page_num: int) -> List[Dict[str, Any]]:
        """Extract tables from a PDF page (basic detection)."""
        tables_list = []
        
        try:
            # Basic table detection using text blocks
            blocks = page.get_text("dict")["blocks"]
            
            for block_num, block in enumerate(blocks):
                if "lines" in block:
                    # Look for structured text that might be a table
                    lines = block["lines"]
                    if len(lines) > 2:  # At least 3 lines for a table
                        # Check if lines have consistent spacing (table-like)
                        line_positions = []
                        for line in lines:
                            if line.get("spans"):
                                line_positions.append(line["spans"][0].get("bbox", [0])[0])
                        
                        # If lines are aligned, it might be a table
                        if len(set(line_positions)) <= 3:  # Allow some variation
                            table_text = ""
                            for line in lines:
                                for span in line.get("spans", []):
                                    table_text += span.get("text", "") + " "
                                table_text += "\n"
                            
                            tables_list.append({
                                'page': page_num + 1,
                                'table_index': block_num,
                                'content': table_text.strip(),
                                'line_count': len(lines)
                            })
                            
        except Exception as e:
            print(f"Error extracting tables from page {page_num}: {e}")
        
        return tables_list