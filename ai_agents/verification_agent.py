from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent
from vector_store import VectorStore
from document_processor import DocumentProcessor

class VerificationAgent(BaseAgent):
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the verification agent."""
        super().__init__(api_key)
        self.vector_store = VectorStore()
        self.document_processor = DocumentProcessor()
    
    def get_agent_name(self) -> str:
        """Return the name of this agent."""
        return "Verification Agent"

    def get_system_prompt(self) -> str:
        """Return the system prompt for the verification agent."""
        return """You are Orb, an AI knowledge agent. You help users by providing accurate, helpful responses based on their queries and any relevant documents provided.

When document context is provided, use it to inform your response but also draw on your general knowledge when appropriate. Always be clear about what information comes from the provided documents versus your general knowledge.

Be conversational, helpful, and accurate in your responses."""

    def process_request(self, user_message: str, context: str = "", 
                       conversation_history: Optional[List[Dict[str, str]]] = None,
                       progress_callback: Optional[callable] = None,
                       collection_name: Optional[str] = None) -> Dict[str, Any]:
        """Process a request using the two-step verification process with collection support."""
        
        def notify_progress(status: str, message: str):
            if progress_callback:
                progress_callback(status, message)
        
        # Step 1: Get relevant context from collection if specified
        notify_progress("context", "Searching for relevant information...")
        final_context = context
        images = []
        
        if collection_name:
            # Check if user is asking for images
            is_image_query = self._is_image_query(user_message)
            
            if is_image_query:
                notify_progress("context", "Searching for images...")
                images = self._search_images(collection_name, user_message)
                if images:
                    final_context = f"\n\n--- Found {len(images)} relevant images ---\n"
                    for i, img in enumerate(images):
                        file_path = img['metadata'].get('file_path', 'Unknown')
                        final_context += f"Image {i+1}: {file_path}\n"
                        final_context += f"Description: {img['content']}\n"
                        if 'similarity' in img:
                            final_context += f"Similarity: {img['similarity']:.3f}\n"
                        # Add image URL for display - prioritize original_file_url, fallback to file_path
                        if 'original_file_url' in img['metadata']:
                            img['url'] = img['metadata']['original_file_url']
                        elif 'stored_file_path' in img['metadata']:
                            # Extract collection and filename from stored_file_path
                            stored_path = img['metadata']['stored_file_path']
                            if 'uploads/' in stored_path:
                                relative_path = stored_path.split('uploads/', 1)[1]
                                img['url'] = f'/api/files/{relative_path}'
                        
                        # Ensure the image has a proper URL for the frontend
                        if 'url' not in img and 'file_path' in img['metadata']:
                            # This is for legacy images - use the file path directly
                            img['url'] = f"/api/images/{img['metadata']['file_path']}"
                        final_context += "\n"
                    notify_progress("context", f"Found {len(images)} relevant images")
                else:
                    notify_progress("context", "No matching images found")
                    # Still set context to help user understand
                    final_context = "\n\n--- No matching images found ---\nTry using different keywords or upload an image to find similar ones.\n"
            else:
                # Regular document search
                relevant_chunks = self.vector_store.search_similar_chunks(
                    collection_name, user_message, n_results=3
                )
                if relevant_chunks:
                    final_context = "\n\n--- Relevant Information ---\n"
                    for i, chunk in enumerate(relevant_chunks):
                        final_context += f"Document {i+1}:\n{chunk['content']}\n\n"
                    notify_progress("context", f"Found {len(relevant_chunks)} relevant documents")
                else:
                    notify_progress("context", "No relevant documents found")
        
        # Step 2: Generate initial response
        notify_progress("generating", "Generating initial response...")
        initial_response = self._get_initial_response(user_message, final_context, conversation_history)
        
        # Step 3: Verify the response
        notify_progress("verifying", "Verifying response accuracy...")
        verification_result = self._verify_response(user_message, initial_response, final_context)
        
        notify_progress("finalizing", "Finalizing response...")
        
        return {
            "response": verification_result["final_response"],
            "verified": verification_result["verified"],
            "verification_notes": verification_result.get("notes", ""),
            "context_used": final_context != "",
            "images": images,
            "agent_type": "verification"
        }

    def _get_initial_response(self, user_message: str, context: str, 
                            conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Generate initial response to user query."""
        messages = self._build_messages(user_message, context, conversation_history)
        
        if self.debug:
            print(f"\n🔵 {self.get_agent_name()} - INITIAL RESPONSE REQUEST")
            print(f"Model: claude-3-5-sonnet-20241022")
            print(f"System: {self.get_system_prompt()}")
        
        response_text = self._make_api_call(messages, self.get_system_prompt(), max_tokens=1000)
        
        if self.debug:
            print(f"\n🟢 {self.get_agent_name()} - INITIAL RESPONSE RECEIVED")
            print(f"Response: {response_text}")
        
        return response_text

    def _verify_response(self, original_question: str, initial_response: str, context: str) -> Dict[str, Any]:
        """Verify the initial response for accuracy and completeness."""
        
        verification_prompt = f"""Please review the following response to ensure it is accurate, helpful, and appropriate.

Original Question: {original_question}

Response to Verify: {initial_response}

Context Provided: {context if context else "No additional context provided"}

Please evaluate:
1. Is the response accurate?
2. Does it properly address the user's question?
3. If context was provided, does it appropriately use the information?
4. Are there any errors or improvements needed?

Provide either:
- "VERIFIED: [brief note]" if the response is good as-is
- "REVISED: [improved response]" if changes are needed"""

        messages = [{
            "role": "user",
            "content": verification_prompt
        }]
        
        if self.debug:
            print(f"\n🔵 {self.get_agent_name()} - VERIFICATION REQUEST")
        
        verification_text = self._make_api_call(messages, "", max_tokens=1200)
        
        if self.debug:
            print(f"\n🟢 {self.get_agent_name()} - VERIFICATION RESPONSE")
            print(f"Verification: {verification_text}")
        
        if verification_text.startswith("VERIFIED:"):
            return {
                "verified": True,
                "final_response": initial_response,
                "notes": verification_text[9:].strip()
            }
        elif verification_text.startswith("REVISED:"):
            return {
                "verified": True,
                "final_response": verification_text[8:].strip(),
                "notes": "Response was revised during verification"
            }
        else:
            return {
                "verified": False,
                "final_response": initial_response,
                "notes": f"Verification unclear: {verification_text[:100]}..."
            }

    def search_similar_images_by_upload(self, collection_name: str, uploaded_image_path: str, 
                                      n_results: int = 10) -> List[Dict[str, Any]]:
        """Search for similar images by uploading an image."""
        try:
            # Get CLIP embedding for the uploaded image
            query_embedding = self.document_processor.get_image_embedding(uploaded_image_path)
            if query_embedding is None:
                return []
            
            # Search for similar images
            results = self.vector_store.search_similar_images_by_embedding(
                collection_name, 
                query_embedding,
                n_results=n_results
            )
            
            return results
            
        except Exception as e:
            print(f"Error searching similar images: {e}")
            return []
    
    def generate_image_caption(self, image_path: str) -> str:
        """Generate a text caption for an image using CLIP."""
        try:
            # Use the document processor to get image description
            # This leverages the existing CLIP integration
            caption = self.document_processor.get_image_description(image_path)
            
            # If no caption generated, return a default
            if not caption or caption.strip() == "":
                return "An image was provided"
                
            return caption
            
        except Exception as e:
            print(f"Error generating image caption: {e}")
            return "An image was provided"

    def _is_image_query(self, user_message: str) -> bool:
        """Determine if the user is asking for images."""
        image_keywords = [
            'image', 'picture', 'pic', 'photo', 'show me', 'display', 'find image', 
            'find picture', 'find photo', 'look like', 'similar image', 'similar photo',
            'images related', 'photos related', 'visual', 'screenshots', 'diagrams'
        ]
        message_lower = user_message.lower()
        return any(keyword in message_lower for keyword in image_keywords)
    
    def _search_images(self, collection_name: str, query: str, n_results: int = 10) -> List[Dict[str, Any]]:
        """Search for images in the collection based on the query."""
        try:
            # First try keyword-based image search
            results = self.vector_store.search_images_by_keywords(
                collection_name, 
                query,
                n_results=n_results
            )
            
            # If we have text queries that could work with CLIP, try CLIP text search
            if not results or len(results) < n_results:
                try:
                    # Get CLIP text embedding for the query
                    text_embedding = self.document_processor.get_text_embedding_for_image_search(query)
                    if text_embedding is not None:
                        clip_results = self.vector_store.search_similar_images_by_embedding(
                            collection_name, 
                            text_embedding,
                            n_results=n_results
                        )
                        # Merge results, avoiding duplicates
                        existing_paths = {r['metadata'].get('file_path') for r in results}
                        for clip_result in clip_results:
                            if clip_result['metadata'].get('file_path') not in existing_paths:
                                results.append(clip_result)
                                if len(results) >= n_results:
                                    break
                except Exception as clip_e:
                    print(f"CLIP search failed: {clip_e}")
            
            return results[:n_results]
            
        except Exception as e:
            print(f"Error searching for images: {e}")
            return []