from anthropic import Anthropic
import os
import json
from typing import List, Dict, Any, Optional
from vector_store import VectorStore
from document_processor import DocumentProcessor

class OrbAIAgent:
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the AI agent with Anthropic Claude."""
        self.client = Anthropic(api_key=api_key or os.getenv('ANTHROPIC_API_KEY'))
        self.vector_store = VectorStore()
        self.document_processor = DocumentProcessor()
        self.debug = True  # Enable debug mode
        
    def generate_response(self, user_message: str, collection_name: Optional[str] = None,
                         conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Generate response using two-step process: initial response + verification."""
        return self.generate_response_with_progress(user_message, collection_name, conversation_history)
    
    def generate_response_with_progress(self, user_message: str, collection_name: Optional[str] = None,
                                       conversation_history: Optional[List[Dict[str, str]]] = None,
                                       progress_callback: Optional[callable] = None) -> Dict[str, Any]:
        """Generate response with progress callbacks."""
        
        def notify_progress(status: str, message: str):
            if progress_callback:
                progress_callback(status, message)
        
        # Step 1: Get relevant context from documents if collection is specified
        notify_progress("context", "Searching for relevant information...")
        context = ""
        images = []
        
        if collection_name:
            # Check if user is asking for images
            is_image_query = self._is_image_query(user_message)
            
            if is_image_query:
                notify_progress("context", "Searching for images...")
                images = self._search_images(collection_name, user_message)
                if images:
                    context = f"\n\n--- Found {len(images)} relevant images ---\n"
                    for i, img in enumerate(images):
                        file_path = img['metadata'].get('file_path', 'Unknown')
                        context += f"Image {i+1}: {file_path}\n"
                        context += f"Description: {img['content']}\n"
                        if 'similarity' in img:
                            context += f"Similarity: {img['similarity']:.3f}\n"
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
                        context += "\n"
                    notify_progress("context", f"Found {len(images)} relevant images")
                else:
                    notify_progress("context", "No matching images found")
                    # Still set context to help user understand
                    context = "\n\n--- No matching images found ---\nTry using different keywords or upload an image to find similar ones.\n"
            else:
                # Regular document search
                relevant_chunks = self.vector_store.search_similar_chunks(
                    collection_name, user_message, n_results=3
                )
                if relevant_chunks:
                    context = "\n\n--- Relevant Information ---\n"
                    for i, chunk in enumerate(relevant_chunks):
                        context += f"Document {i+1}:\n{chunk['content']}\n\n"
                    notify_progress("context", f"Found {len(relevant_chunks)} relevant documents")
                else:
                    notify_progress("context", "No relevant documents found")
        
        # Step 2: Generate initial response
        notify_progress("generating", "Sending request to AI...")
        initial_response = self._get_initial_response(user_message, context, conversation_history, notify_progress)
        
        # Step 3: Verify the response
        notify_progress("verifying", "Verifying response accuracy...")
        verification_result = self._verify_response(user_message, initial_response, context, notify_progress)
        
        notify_progress("finalizing", "Finalizing response...")
        
        return {
            "response": verification_result["final_response"],
            "verified": verification_result["verified"],
            "verification_notes": verification_result.get("notes", ""),
            "context_used": context != "",
            "images": images
        }
    
    def _get_initial_response(self, user_message: str, context: str, 
                            conversation_history: Optional[List[Dict[str, str]]] = None,
                            progress_callback: Optional[callable] = None) -> str:
        """Generate initial response to user query."""
        
        # Build conversation messages
        messages = []
        
        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history[-10:]:  # Limit to last 10 messages
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Prepare the system message
        system_message = """You are Orb, an AI knowledge agent. You help users by providing accurate, helpful responses based on their queries and any relevant documents provided.

When document context is provided, use it to inform your response but also draw on your general knowledge when appropriate. Always be clear about what information comes from the provided documents versus your general knowledge.

Be conversational, helpful, and accurate in your responses."""

        # Prepare the user message with context
        user_content = user_message
        if context:
            user_content = f"{context}\n\n--- User Question ---\n{user_message}"
        
        messages.append({
            "role": "user",
            "content": user_content
        })
        
        try:
            # Progress update
            if progress_callback:
                progress_callback("generating", "Waiting for AI response...")
            
            # Debug: Print request details
            if self.debug:
                print("\n" + "="*50)
                print("🔵 INITIAL RESPONSE REQUEST")
                print("="*50)
                print(f"Model: claude-3-5-sonnet-20241022")
                print(f"Max tokens: 1000")
                print(f"System message:\n{system_message}")
                print(f"\nMessages:")
                for i, msg in enumerate(messages):
                    print(f"  [{i}] {msg['role']}: {msg['content'][:200]}...")
                print("="*50)
            
            response = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                system=system_message,
                messages=messages
            )
            
            response_text = response.content[0].text
            
            # Progress update
            if progress_callback:
                progress_callback("generating", "Initial response received")
            
            # Debug: Print response
            if self.debug:
                print("\n" + "="*50)
                print("🟢 INITIAL RESPONSE RECEIVED")
                print("="*50)
                print(f"Response: {response_text}")
                print("="*50)
            
            return response_text
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            if self.debug:
                print(f"\n🔴 ERROR in initial response: {error_msg}")
            return error_msg
    
    def _verify_response(self, original_question: str, initial_response: str, context: str,
                        progress_callback: Optional[callable] = None) -> Dict[str, Any]:
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

        try:
            # Progress update
            if progress_callback:
                progress_callback("verifying", "Sending verification request...")
            
            # Debug: Print verification request
            if self.debug:
                print("\n" + "="*50)
                print("🔵 VERIFICATION REQUEST")
                print("="*50)
                print(f"Model: claude-3-5-sonnet-20241022")
                print(f"Max tokens: 1200")
                print(f"Verification prompt:\n{verification_prompt}")
                print("="*50)
            
            verification = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1200,
                messages=[{
                    "role": "user",
                    "content": verification_prompt
                }]
            )
            
            verification_text = verification.content[0].text
            
            # Progress update
            if progress_callback:
                progress_callback("verifying", "Verification complete")
            
            # Debug: Print verification response
            if self.debug:
                print("\n" + "="*50)
                print("🟢 VERIFICATION RESPONSE RECEIVED")
                print("="*50)
                print(f"Verification: {verification_text}")
                print("="*50)
            
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
        except Exception as e:
            error_msg = f"Verification failed: {str(e)}"
            if self.debug:
                print(f"\n🔴 ERROR in verification: {error_msg}")
            return {
                "verified": False,
                "final_response": initial_response,
                "notes": error_msg
            }

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