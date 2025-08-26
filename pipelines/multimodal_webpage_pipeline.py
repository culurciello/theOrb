from typing import Dict, Any, List
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import tempfile
import os
from .multimodal_text_pipeline import MultiModalTextPipeline
from .video_pipeline import VideoPipeline
from .image_pipeline import ImagePipeline

class MultiModalWebpagePipeline:
    """
    Multi-modal webpage processing pipeline:
    - like multimodal text + videos
    - extract text content, images, and embedded videos from web pages
    - process each component according to their respective pipelines
    """
    
    def __init__(self):
        self.multimodal_text_pipeline = MultiModalTextPipeline()
        self.video_pipeline = VideoPipeline()
        self.image_pipeline = ImagePipeline()
    
    def process(self, url_or_file_path: str) -> Dict[str, Any]:
        """Process webpage (URL or local HTML file) according to the pipeline specification."""
        if url_or_file_path.startswith(('http://', 'https://')):
            return self._process_url(url_or_file_path)
        else:
            return self._process_local_html(url_or_file_path)
    
    def _process_url(self, url: str) -> Dict[str, Any]:
        """Process a webpage from URL."""
        try:
            # Fetch webpage content
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse HTML content
            soup = BeautifulSoup(response.content, 'html.parser')
            
            return self._process_html_content(soup, url)
            
        except Exception as e:
            print(f"Error processing URL {url}: {e}")
            return {
                'link_to_original_file': url,
                'error': str(e),
                'file_type': 'multimodal_webpage',
                'content': '',
                'summary': f"Error processing webpage: {str(e)}",
                'image_list': [],
                'video_list': [],
                'metadata': {'error': True}
            }
    
    def _process_local_html(self, file_path: str) -> Dict[str, Any]:
        """Process a local HTML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            soup = BeautifulSoup(content, 'html.parser')
            return self._process_html_content(soup, file_path)
            
        except Exception as e:
            print(f"Error processing HTML file {file_path}: {e}")
            return {
                'link_to_original_file': file_path,
                'error': str(e),
                'file_type': 'multimodal_webpage',
                'content': '',
                'summary': f"Error processing HTML file: {str(e)}",
                'image_list': [],
                'video_list': [],
                'metadata': {'error': True}
            }
    
    def _process_html_content(self, soup: BeautifulSoup, source_path: str) -> Dict[str, Any]:
        """Process parsed HTML content to extract text, images, and videos."""
        try:
            # Extract text content
            text_content = self._extract_text_from_html(soup)
            
            # Extract and process images
            image_list = self._extract_and_process_images(soup, source_path)
            
            # Extract and process videos
            video_list = self._extract_and_process_videos(soup, source_path)
            
            # Process text using multimodal text pipeline approach
            text_chunks = self.multimodal_text_pipeline.text_pipeline.chunk_text(text_content)
            text_embeddings = self.multimodal_text_pipeline.text_pipeline.get_sentence_embeddings(text_chunks)
            
            # Generate summary from first 1000 words
            words = text_content.split()[:1000]
            summary_text = ' '.join(words)
            summary = self.multimodal_text_pipeline.text_pipeline.generate_summary(summary_text)
            
            # Categorize content
            category = self.multimodal_text_pipeline.text_pipeline.categorize_content(summary_text)
            
            return {
                'link_to_original_file': source_path,
                'category': category,
                'summary': summary,
                'content': text_content,
                'embedding_list': text_embeddings,
                'text_chunks': text_chunks,
                'image_list': image_list,
                'video_list': video_list,
                'file_type': 'multimodal_webpage',
                'metadata': {
                    'word_count': len(text_content.split()),
                    'image_count': len(image_list),
                    'video_count': len(video_list),
                    'chunk_count': len(text_chunks),
                    'title': soup.find('title').get_text() if soup.find('title') else 'No title'
                }
            }
            
        except Exception as e:
            print(f"Error processing HTML content: {e}")
            return {
                'link_to_original_file': source_path,
                'error': str(e),
                'file_type': 'multimodal_webpage',
                'content': '',
                'summary': f"Error processing webpage content: {str(e)}",
                'image_list': [],
                'video_list': [],
                'metadata': {'error': True}
            }
    
    def _extract_text_from_html(self, soup: BeautifulSoup) -> str:
        """Extract clean text content from HTML."""
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _extract_and_process_images(self, soup: BeautifulSoup, source_path: str) -> List[Dict[str, Any]]:
        """Extract and process images from HTML."""
        image_list = []
        
        try:
            img_tags = soup.find_all('img', src=True)
            
            for idx, img_tag in enumerate(img_tags):
                img_src = img_tag['src']
                img_alt = img_tag.get('alt', '')
                
                # Skip very small images (likely decorative)
                width = img_tag.get('width')
                height = img_tag.get('height')
                if width and height:
                    try:
                        if int(width) < 50 or int(height) < 50:
                            continue
                    except ValueError:
                        pass
                
                # For web URLs, try to download and process the image
                if source_path.startswith(('http://', 'https://')):
                    try:
                        if not img_src.startswith(('http://', 'https://')):
                            # Relative URL - construct full URL
                            from urllib.parse import urljoin
                            img_src = urljoin(source_path, img_src)
                        
                        # Download image temporarily
                        img_response = requests.get(img_src, timeout=5, stream=True)
                        img_response.raise_for_status()
                        
                        # Save to temporary file
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                            for chunk in img_response.iter_content(chunk_size=8192):
                                temp_file.write(chunk)
                            temp_path = temp_file.name
                        
                        # Generate caption
                        caption = self.image_pipeline.generate_caption(temp_path)
                        
                        # Clean up temp file
                        os.unlink(temp_path)
                        
                        image_list.append({
                            'image_index': idx,
                            'src': img_src,
                            'alt_text': img_alt,
                            'caption': caption,
                            'source': 'webpage'
                        })
                        
                    except Exception as e:
                        print(f"Error processing image {img_src}: {e}")
                        # Fallback to alt text or generic description
                        caption = img_alt if img_alt else f"Image from webpage: {img_src}"
                        image_list.append({
                            'image_index': idx,
                            'src': img_src,
                            'alt_text': img_alt,
                            'caption': caption,
                            'source': 'webpage',
                            'error': str(e)
                        })
                else:
                    # Local HTML file - use alt text as caption
                    caption = img_alt if img_alt else f"Local image: {img_src}"
                    image_list.append({
                        'image_index': idx,
                        'src': img_src,
                        'alt_text': img_alt,
                        'caption': caption,
                        'source': 'local_html'
                    })
                    
        except Exception as e:
            print(f"Error extracting images from HTML: {e}")
        
        return image_list
    
    def _extract_and_process_videos(self, soup: BeautifulSoup, source_path: str) -> List[Dict[str, Any]]:
        """Extract and process videos from HTML."""
        video_list = []
        
        try:
            # Find video tags
            video_tags = soup.find_all('video', src=True)
            
            # Also look for embedded video iframes (YouTube, Vimeo, etc.)
            iframe_tags = soup.find_all('iframe', src=True)
            video_iframes = [iframe for iframe in iframe_tags 
                           if any(domain in iframe.get('src', '') 
                                 for domain in ['youtube', 'vimeo', 'dailymotion'])]
            
            for idx, video_tag in enumerate(video_tags):
                video_src = video_tag['src']
                
                # For actual video files, we would need to download and process
                # For now, create a basic entry
                video_list.append({
                    'video_index': idx,
                    'src': video_src,
                    'type': 'video_tag',
                    'description': f"Video content from {video_src}",
                    'source': 'webpage'
                })
            
            for idx, iframe in enumerate(video_iframes):
                iframe_src = iframe['src']
                
                # Extract video platform and ID if possible
                platform = 'unknown'
                if 'youtube' in iframe_src:
                    platform = 'youtube'
                elif 'vimeo' in iframe_src:
                    platform = 'vimeo'
                
                video_list.append({
                    'video_index': len(video_tags) + idx,
                    'src': iframe_src,
                    'type': 'embedded_iframe',
                    'platform': platform,
                    'description': f"Embedded {platform} video",
                    'source': 'webpage'
                })
                
        except Exception as e:
            print(f"Error extracting videos from HTML: {e}")
        
        return video_list