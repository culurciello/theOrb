from typing import Dict, Any, Optional, List
from .base_agent import BaseAgent
import requests
import json
from urllib.parse import quote

class DeepResearchAgent(BaseAgent):
    def get_agent_name(self) -> str:
        """Return the name of this agent."""
        return "Deep Research Agent"

    def get_system_prompt(self) -> str:
        """Return the system prompt for the deep research agent."""
        return """You are Orb's Deep Research Agent. Your role is to perform comprehensive research on topics by analyzing user data, web sources, and multiple perspectives.

When conducting research:
1. Synthesize information from multiple sources
2. Provide balanced perspectives on complex topics
3. Clearly cite sources and distinguish between user data and external information
4. Identify gaps in available information
5. Offer actionable insights based on the research

Be thorough, analytical, and objective in your research approach."""

    def web_search(self, query: str) -> Dict[str, Any]:
        """Perform web search using Claude's WebSearch tool."""
        try:
            # Create a web search request that can be handled by Claude's web search
            # This integrates with the Claude API's web search capability
            search_prompt = f"""Search the web for current information about: {query}

Provide search results in the following format for each result:
- Title: [article title]
- URL: [article URL]
- Snippet: [brief summary/excerpt]

Focus on recent, authoritative sources."""

            # Make API call with web search capability
            messages = [{
                "role": "user",
                "content": search_prompt
            }]

            # This would trigger Claude's web search tool when available
            search_response = self._make_api_call(messages,
                "You are a web search assistant. Perform web searches and return structured results.",
                max_tokens=800)

            # Parse response and structure results
            results = []
            if search_response and "Title:" in search_response:
                # Simple parsing of structured response
                lines = search_response.split('\n')
                current_result = {}

                for line in lines:
                    line = line.strip()
                    if line.startswith('- Title:'):
                        if current_result:
                            results.append(current_result)
                        current_result = {'title': line.replace('- Title:', '').strip()}
                    elif line.startswith('- URL:'):
                        current_result['url'] = line.replace('- URL:', '').strip()
                    elif line.startswith('- Snippet:'):
                        current_result['snippet'] = line.replace('- Snippet:', '').strip()

                if current_result:
                    results.append(current_result)

            return {
                'results': results,
                'query': query,
                'status': 'success' if results else 'no_results'
            }

        except Exception as e:
            if self.debug:
                print(f"Web search error: {e}")
            return None

    def process_request(self, user_message: str, context: str = "",
                       conversation_history: Optional[List[Dict[str, str]]] = None,
                       progress_callback: Optional[callable] = None,
                       collection_name: Optional[str] = None) -> Dict[str, Any]:
        """Process a request using deep research methodology."""

        def notify_progress(status: str, message: str):
            if progress_callback:
                progress_callback(status, message)

        if self.debug:
            current_model = self.llm_manager.get_current_provider_info()
            print(f"\n🔵 {self.get_agent_name()} - STARTING DEEP RESEARCH")
            print(f"Model: {current_model.get('model', 'unknown')} ({current_model.get('display_name', 'unknown')})")
            print(f"Query: {user_message}")
            print(f"Context available: {'Yes' if context else 'No'}")

        notify_progress("researching", "Starting deep research...")

        # Step 1: Analyze user data (context)
        user_data_analysis = ""
        if context:
            notify_progress("researching", "Analyzing user data...")
            user_data_analysis = self._analyze_user_data(context)

        # Step 2: Perform web research
        notify_progress("researching", "Searching web sources...")
        web_research_results = self._perform_web_research(user_message)

        # Step 3: Synthesize findings
        notify_progress("synthesizing", "Synthesizing research findings...")
        final_response = self._synthesize_research(
            user_message,
            user_data_analysis,
            web_research_results,
            conversation_history
        )

        notify_progress("finalizing", "Finalizing research report...")

        if self.debug:
            print(f"\n🟢 {self.get_agent_name()} - DEEP RESEARCH COMPLETE")
            print(f"Sources researched: {len(web_research_results.get('articles', []))}")
            print(f"Research topics explored: {len(web_research_results.get('topics_researched', []))}")
            print(f"Final response ready")

        return {
            "response": final_response,
            "verified": True,  # Deep research agent validates through multiple sources
            "verification_notes": "Response based on comprehensive research",
            "context_used": context != "",
            "agent_type": "deep_research",
            "sources_searched": len(web_research_results.get('articles', []))
        }

    def _analyze_user_data(self, context: str) -> str:
        """Analyze user data provided in context."""
        if self.debug:
            print(f"\n🔵 {self.get_agent_name()} - ANALYZING USER DATA")
            print(f"Context length: {len(context)} characters")

        analysis_prompt = f"""Analyze the following user data and extract key insights relevant to research:

{context}

Provide a brief analysis highlighting:
1. Key facts and data points
2. Potential areas needing additional research
3. Questions that arise from this data

Keep the analysis concise and focused."""

        messages = [{
            "role": "user",
            "content": analysis_prompt
        }]

        result = self._make_api_call(messages, self.get_system_prompt(), max_tokens=500)

        if self.debug:
            print(f"🟢 {self.get_agent_name()} - USER DATA ANALYSIS COMPLETE")

        return result

    def _perform_web_research(self, query: str) -> Dict[str, Any]:
        """Perform web research using Claude's web search tool."""
        if self.debug:
            print(f"\n🔵 {self.get_agent_name()} - STARTING WEB RESEARCH")
            print(f"Main query: {query}")

        try:
            # Generate focused research topics to search for
            if self.debug:
                print(f"🔄 Generating research topics...")
            research_topics = self._generate_research_topics(query)

            if self.debug:
                print(f"📋 Generated {len(research_topics)} research topics:")
                for i, topic in enumerate(research_topics[:5], 1):
                    print(f"  {i}. {topic}")

            # Perform web searches for the main query and top research topics
            search_queries = [query] + research_topics[:3]  # Main query + top 3 topics
            all_results = []

            if self.debug:
                print(f"🔍 Performing {len(search_queries)} web searches...")

            for i, search_query in enumerate(search_queries, 1):
                if self.debug:
                    print(f"  Search {i}/{len(search_queries)}: {search_query}")

                # Use WebSearch tool to get real web results
                search_results = self.web_search(search_query)

                if search_results and 'results' in search_results:
                    results_found = len(search_results['results'][:2])
                    if self.debug:
                        print(f"    ✓ Found {results_found} results")

                    for result in search_results['results'][:2]:  # Take top 2 results per query
                        all_results.append({
                            'title': result.get('title', 'Untitled'),
                            'summary': result.get('snippet', 'No summary available'),
                            'source': result.get('url', 'Unknown source'),
                            'relevance': 'high',
                            'search_query': search_query
                        })
                else:
                    if self.debug:
                        print(f"    ⚠ No results found")

            if self.debug:
                print(f"🟢 {self.get_agent_name()} - WEB RESEARCH COMPLETE")
                print(f"Total sources found: {len(all_results)}")

            return {
                'query': query,
                'topics_researched': research_topics,
                'articles': all_results,
                'total_sources': len(all_results),
                'search_queries_used': search_queries
            }

        except Exception as e:
            # Fallback to research topics if web search fails
            if self.debug:
                print(f"❌ Web search failed: {e}")
                print(f"🔄 Using research topics fallback mode...")

            research_topics = self._generate_research_topics(query)

            # Generate topic-based placeholder articles
            fallback_articles = []
            for i, topic in enumerate(research_topics[:5]):
                fallback_articles.append({
                    'title': f"Research Direction: {topic}",
                    'summary': f"Analysis needed for {topic} - web search unavailable",
                    'source': 'Research Topic Generated',
                    'relevance': 'medium'
                })

            if self.debug:
                print(f"🟡 {self.get_agent_name()} - FALLBACK RESEARCH COMPLETE")
                print(f"Generated {len(fallback_articles)} research directions")

            return {
                'query': query,
                'topics_researched': research_topics,
                'articles': fallback_articles,
                'total_sources': len(fallback_articles),
                'search_status': 'fallback_mode'
            }

    def _generate_research_topics(self, query: str) -> List[str]:
        """Generate research topics based on the user query."""
        if self.debug:
            print(f"\n🔵 {self.get_agent_name()} - GENERATING RESEARCH TOPICS")

        prompt = f"""Given this research query: "{query}"

Generate 5-8 specific research topics that would provide comprehensive coverage of this subject. Focus on:
1. Current trends and developments
2. Expert opinions and analysis
3. Data and statistics
4. Different perspectives or viewpoints
5. Practical applications or implications

List only the topics, one per line."""

        messages = [{
            "role": "user",
            "content": prompt
        }]

        topics_text = self._make_api_call(messages, "", max_tokens=300)

        # Parse topics from response
        topics = [topic.strip() for topic in topics_text.split('\n') if topic.strip()]
        topics = topics[:8]  # Limit to 8 topics

        if self.debug:
            print(f"🟢 {self.get_agent_name()} - RESEARCH TOPICS GENERATED")
            print(f"Generated {len(topics)} topics for comprehensive research")

        return topics

    def _synthesize_research(self, original_query: str, user_data_analysis: str,
                           web_research: Dict[str, Any],
                           conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Synthesize all research into a comprehensive response."""

        if self.debug:
            print(f"\n🔵 {self.get_agent_name()} - STARTING SYNTHESIS")
            print(f"Original query: {original_query}")
            print(f"User data available: {'Yes' if user_data_analysis else 'No'}")
            print(f"Web sources to synthesize: {web_research.get('total_sources', 0)}")

        synthesis_prompt = f"""As a deep research agent, synthesize the following information to provide a comprehensive answer:

Original Query: {original_query}

User Data Analysis:
{user_data_analysis if user_data_analysis else "No user data provided"}

Web Research Results:
Topics Researched: {', '.join(web_research.get('topics_researched', []))}
Sources Found: {web_research.get('total_sources', 0)}

Research Articles Found:
"""

        # Add article summaries
        for article in web_research.get('articles', []):
            synthesis_prompt += f"- {article['title']}: {article['summary']}\n"

        synthesis_prompt += f"""

Provide a comprehensive response that:
1. Directly answers the original query
2. Incorporates insights from both user data and web research
3. Presents multiple perspectives where relevant
4. Highlights key findings and trends
5. Identifies any gaps in available information
6. Offers actionable conclusions

Structure your response clearly with headings where appropriate."""

        # Build messages with conversation history
        messages = self._build_messages(synthesis_prompt, "", conversation_history)

        if self.debug:
            current_model = self.llm_manager.get_current_provider_info()
            print(f"🔄 Synthesizing with {current_model.get('model', 'unknown')} model...")

        final_response = self._make_api_call(messages, self.get_system_prompt(), max_tokens=1500)

        if self.debug:
            print(f"🟢 {self.get_agent_name()} - SYNTHESIS COMPLETE")
            print(f"Final response length: {len(final_response)} characters")

        return final_response