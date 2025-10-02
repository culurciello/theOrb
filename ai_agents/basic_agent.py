from typing import Dict, Any, Optional, List
import json
import re
import logging
from .base_agent import BaseAgent
from vector_store import VectorStore
from document_processor import DocumentProcessor
from .tools.tool_manager import ToolManager

# Set up logger
logger = logging.getLogger('orb')

class BasicAgent(BaseAgent):
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the basic agent."""
        super().__init__(api_key)
        self.vector_store = VectorStore()
        self.document_processor = DocumentProcessor()
        self.tool_manager = ToolManager()
    
    def get_agent_name(self) -> str:
        """Return the name of this agent."""
        return "Basic Agent"

    def get_system_prompt(self) -> str:
        """Return the system prompt for the basic agent."""
        tools_description = self.tool_manager.get_tools_description()
        return f"""You are Orb, an AI knowledge agent. You help users by providing accurate, helpful responses based on their queries and any relevant documents provided.

When document context is provided, use it to inform your response but also draw on your general knowledge when appropriate. Always be clear about what information comes from the provided documents versus your general knowledge.

You have access to the following tools:
{tools_description}

When a user asks for something that can be handled by one of these tools (like current time, date, or mathematical calculations), respond with a tool call in this format:
TOOL_CALL: tool_name(parameters)

For example:
- For "What time is it?": TOOL_CALL: get_datetime({{"format": "human"}})
- For "Calculate 15 * 23": TOOL_CALL: calculate({{"expression": "15 * 23"}})
- For "What's the current date?": TOOL_CALL: get_datetime({{"format": "date"}})

Be conversational, helpful, and concise in your responses. Provide direct answers to user questions without unnecessary elaboration unless specifically requested."""

    def process_request(self, user_message: str, context: str = "", 
                       conversation_history: Optional[List[Dict[str, str]]] = None,
                       progress_callback: Optional[callable] = None,
                       collection_name: Optional[str] = None) -> Dict[str, Any]:
        """Process a request using a single LLM call without verification."""
        
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
                        # Add image URL for display
                        if 'original_file_url' in img['metadata']:
                            img['url'] = img['metadata']['original_file_url']
                        elif 'stored_file_path' in img['metadata']:
                            stored_path = img['metadata']['stored_file_path']
                            if 'uploads/' in stored_path:
                                relative_path = stored_path.split('uploads/', 1)[1]
                                img['url'] = f'/api/files/{relative_path}'
                        
                        if 'url' not in img and 'file_path' in img['metadata']:
                            img['url'] = f"/api/images/{img['metadata']['file_path']}"
                        final_context += "\n"
                    notify_progress("context", f"Found {len(images)} relevant images")
                else:
                    notify_progress("context", "No matching images found")
                    final_context = "\n\n--- No matching images found ---\nTry using different keywords or upload an image to find similar ones.\n"
            else:
                # Regular document search
                relevant_chunks = self.vector_store.search_similar_chunks(
                    collection_name, user_message, n_results=5
                )
                if relevant_chunks:
                    final_context = "\n\n--- Relevant Information ---\n"
                    for i, chunk in enumerate(relevant_chunks):
                        final_context += f"Document {i+1}:\n{chunk['content']}\n\n"
                    notify_progress("context", f"Found {len(relevant_chunks)} relevant documents")
                else:
                    notify_progress("context", "No relevant documents found")
        
        # Step 2: Generate response (single pass, no verification)
        notify_progress("generating", "Generating response...")
        response_text = self._generate_response(user_message, final_context, conversation_history)

        # Step 3: Check for tool calls and execute them
        response_text = self._process_tool_calls(response_text, notify_progress)

        notify_progress("finalizing", "Finalizing response...")
        
        return {
            "response": response_text,
            "verified": None,  # Basic agent doesn't perform verification
            "verification_notes": "No verification performed (basic agent)",
            "context_used": final_context != "",
            "images": images,
            "agent_type": "basic"
        }

    def _generate_response(self, user_message: str, context: str,
                          conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Generate response to user query using single LLM call."""
        messages = self._build_messages(user_message, context, conversation_history)

        # Get current model info for logging
        current_model = self.llm_manager.get_current_provider_info()
        model_name = f"{current_model.get('display_name', 'unknown')} ({current_model.get('model', 'unknown')})"

        logger.info(f"🤖 LLM REQUEST | Agent: {self.get_agent_name()} | Model: {model_name} | Message: {user_message[:100]}...")

        if self.debug:
            print(f"\n🔵 {self.get_agent_name()} - GENERATING RESPONSE")
            print(f"Model: {current_model.get('model', 'unknown')} ({current_model.get('display_name', 'unknown')})")
            print(f"System: {self.get_system_prompt()}")

        response_text = self._make_api_call(messages, self.get_system_prompt(), max_tokens=1500)

        logger.info(f"💬 LLM RESPONSE | Agent: {self.get_agent_name()} | Model: {model_name} | Length: {len(response_text)} chars")

        if self.debug:
            print(f"\n🟢 {self.get_agent_name()} - RESPONSE GENERATED")
            print(f"Response: {response_text}")

        return response_text

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

    def _process_tool_calls(self, response_text: str, notify_progress: callable) -> str:
        """Process any tool calls in the response text."""
        import re

        def find_tool_calls(text):
            """Find tool calls with proper parentheses matching."""
            results = []
            pattern = r'TOOL_CALL:\s*(\w+)\s*\('

            for match in re.finditer(pattern, text):
                start = match.end() - 1  # Position of opening parenthesis
                tool_name = match.group(1)

                # Find matching closing parenthesis
                paren_count = 0
                i = start
                while i < len(text):
                    if text[i] == '(':
                        paren_count += 1
                    elif text[i] == ')':
                        paren_count -= 1
                        if paren_count == 0:
                            # Found matching closing parenthesis
                            params_str = text[start + 1:i].strip()
                            full_match = text[match.start():i + 1]
                            results.append((full_match, tool_name, params_str))
                            break
                    i += 1

            return results

        def replace_tool_call(tool_call_text, tool_name, params_str):
            try:
                notify_progress("tool_execution", f"Executing {tool_name}...")


                # Parse parameters
                if params_str:
                    # Try to parse as JSON
                    try:
                        parameters = json.loads(params_str)
                    except json.JSONDecodeError:
                        # If not valid JSON, try to create a safe evaluation
                        try:
                            # Replace single quotes with double quotes for JSON compatibility
                            fixed_params = params_str.replace("'", '"')
                            parameters = json.loads(fixed_params)
                        except json.JSONDecodeError:
                            # Last resort: use ast.literal_eval for safety
                            import ast
                            try:
                                parameters = ast.literal_eval(params_str)
                            except:
                                parameters = {}
                else:
                    parameters = {}

                # Execute the tool
                logger.info(f"🔧 TOOL CALL | Tool: {tool_name} | Parameters: {parameters}")
                result = self.tool_manager.execute_tool(tool_name, parameters)

                if "error" in result:
                    logger.error(f"❌ TOOL ERROR | Tool: {tool_name} | Error: {result['error']}")
                    return f"Error executing {tool_name}: {result['error']}"
                else:
                    logger.info(f"✅ TOOL SUCCESS | Tool: {tool_name} | Result: {str(result)[:200]}...")

                # Format the result nicely
                if tool_name == "get_datetime":
                    if "component" in result:
                        return f"The {result['component']} is {result['value']}"
                    else:
                        return f"Current date/time: {result['datetime']}"
                elif tool_name == "calculate":
                    return f"The result is: {result['result']}"
                else:
                    # Generic formatting for other tools
                    if "result" in result:
                        return str(result["result"])
                    else:
                        return str(result)

            except Exception as e:
                return f"Error executing {tool_name}: {str(e)}"

        # Process all tool calls
        processed_response = response_text
        tool_calls = find_tool_calls(response_text)

        # Process in reverse order to maintain text positions
        for tool_call_text, tool_name, params_str in reversed(tool_calls):
            replacement = replace_tool_call(tool_call_text, tool_name, params_str)
            processed_response = processed_response.replace(tool_call_text, replacement, 1)

        return processed_response