import os
import json
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv
import httpx
from bs4 import BeautifulSoup

load_dotenv()


class WebResearcher:
    """
    Web research capabilities:
    - Search the web for information
    - Extract and analyze content from pages
    - Synthesize information with citations
    - Answer questions with source attribution
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        # You can integrate with search APIs like Tavily, SerpAPI, or Bing Search API
        self.search_api_key = os.getenv("TAVILY_API_KEY") or os.getenv("SERP_API_KEY")

    async def search_and_answer(
        self,
        query: str,
        max_sources: int = 5,
        current_page_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search the web and synthesize an answer with citations
        """

        # Step 1: Perform web search
        search_results = await self._search_web(query, max_results=max_sources)

        if not search_results:
            return {
                "answer": "I couldn't find relevant information. Please try rephrasing your query.",
                "citations": [],
                "confidence": 0.0
            }

        # Step 2: Fetch and extract content from top results
        sources = []
        for result in search_results[:max_sources]:
            content = await self._fetch_and_extract(result["url"])
            if content:
                sources.append({
                    "url": result["url"],
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "content": content[:2000]  # Limit content length
                })

        # Step 3: Synthesize answer using LLM
        answer_data = await self._synthesize_answer(query, sources, current_page_content)

        return answer_data

    async def _search_web(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Search the web using available search API
        Returns list of {"url": "...", "title": "...", "snippet": "..."}
        """

        # Option 1: Using Tavily API (recommended for AI apps)
        if os.getenv("TAVILY_API_KEY"):
            return await self._search_tavily(query, max_results)

        # Option 2: Using SerpAPI (Google search results)
        elif os.getenv("SERP_API_KEY"):
            return await self._search_serpapi(query, max_results)

        # Option 3: Fallback - simulate search (for demo without API keys)
        else:
            print("⚠️  No search API configured. Using fallback mode.")
            print("   Configure TAVILY_API_KEY or SERP_API_KEY for real web search.")
            return self._fallback_search(query)

    async def _search_tavily(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Search using Tavily API (https://tavily.com)"""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": os.getenv("TAVILY_API_KEY"),
                        "query": query,
                        "max_results": max_results,
                        "search_depth": "advanced"
                    },
                    timeout=10.0
                )
                data = response.json()
                results = []
                for item in data.get("results", []):
                    results.append({
                        "url": item.get("url"),
                        "title": item.get("title"),
                        "snippet": item.get("content", "")[:300]
                    })
                return results
        except Exception as e:
            print(f"Tavily search error: {e}")
            return []

    async def _search_serpapi(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """Search using SerpAPI (https://serpapi.com)"""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "q": query,
                        "api_key": os.getenv("SERP_API_KEY"),
                        "num": max_results
                    },
                    timeout=10.0
                )
                data = response.json()
                results = []
                for item in data.get("organic_results", [])[:max_results]:
                    results.append({
                        "url": item.get("link"),
                        "title": item.get("title"),
                        "snippet": item.get("snippet", "")
                    })
                return results
        except Exception as e:
            print(f"SerpAPI search error: {e}")
            return []

    def _fallback_search(self, query: str) -> List[Dict[str, str]]:
        """Fallback when no search API is configured"""
        return [
            {
                "url": f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
                "title": f"{query} - Wikipedia",
                "snippet": f"Information about {query}..."
            }
        ]

    async def _fetch_and_extract(self, url: str) -> Optional[str]:
        """
        Fetch a URL and extract main text content
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=5.0
                )

                if response.status_code != 200:
                    return None

                # Parse HTML and extract text
                soup = BeautifulSoup(response.text, 'html.parser')

                # Remove script and style elements
                for script in soup(["script", "style", "nav", "footer", "header"]):
                    script.decompose()

                # Get text from main content areas
                main_content = soup.find('main') or soup.find('article') or soup.find('body')
                if main_content:
                    text = main_content.get_text(separator='\n', strip=True)
                else:
                    text = soup.get_text(separator='\n', strip=True)

                # Clean up whitespace
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                text = '\n'.join(lines)

                return text[:5000]  # Limit to first 5000 chars

        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    async def _synthesize_answer(
        self,
        query: str,
        sources: List[Dict[str, str]],
        current_page_content: Optional[str]
    ) -> Dict[str, Any]:
        """
        Use LLM to synthesize answer from multiple sources
        """

        # Build sources context
        sources_text = ""
        for i, source in enumerate(sources):
            sources_text += f"\n\n[Source {i+1}] {source['title']}\nURL: {source['url']}\n{source['content']}\n"

        current_page_text = ""
        if current_page_content:
            current_page_text = f"\n\nCurrent Page Content:\n{current_page_content[:1000]}\n"

        prompt = f"""
You are a research assistant. Answer the user's question by synthesizing
information from multiple sources.

User Question: {query}

{sources_text}
{current_page_text}

Provide a comprehensive answer with these requirements:
1. Synthesize information from multiple sources
2. Cite sources using [1], [2], etc. notation
3. Be accurate and factual
4. Indicate if sources disagree
5. Note if information is from the current page vs web search

Respond in JSON format:
{{
    "answer": "Your comprehensive answer with [1] [2] citations...",
    "key_points": ["point 1", "point 2", ...],
    "citations": [
        {{"index": 1, "url": "...", "title": "...", "relevant_quote": "..."}},
        {{"index": 2, "url": "...", "title": "...", "relevant_quote": "..."}}
    ],
    "confidence": 0.0-1.0,
    "caveats": ["limitation 1", "limitation 2", ...]
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a research assistant that synthesizes information with citations."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=1500
            )

            content = response.choices[0].message.content
            return json.loads(content)

        except Exception as e:
            print(f"Error synthesizing answer: {e}")
            return {
                "answer": "I encountered an error while synthesizing the answer.",
                "citations": [],
                "confidence": 0.0
            }

    async def extract_page_content(self, page_html: str, page_url: str) -> Dict[str, Any]:
        """
        Extract structured content from current page for understanding
        """

        soup = BeautifulSoup(page_html, 'html.parser')

        # Remove noise
        for element in soup(["script", "style", "nav", "footer"]):
            element.decompose()

        # Extract key elements
        title = soup.find('title')
        title_text = title.get_text() if title else ""

        # Get main headings
        headings = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3'])[:10]]

        # Get main content
        main = soup.find('main') or soup.find('article') or soup.find('body')
        if main:
            paragraphs = [p.get_text(strip=True) for p in main.find_all('p')[:20]]
            content = '\n'.join(paragraphs)
        else:
            content = soup.get_text(separator='\n', strip=True)[:2000]

        # Detect page type
        page_type = self._detect_page_type(soup, page_url)

        return {
            "url": page_url,
            "title": title_text,
            "headings": headings,
            "content": content,
            "page_type": page_type,
            "summary": await self._summarize_page(title_text, headings, content)
        }

    def _detect_page_type(self, soup: BeautifulSoup, url: str) -> str:
        """Detect what type of page this is"""

        # Check for common patterns
        if soup.find('form') and soup.find(['input', 'textarea']):
            return "form"
        elif soup.find('article') or 'blog' in url or 'post' in url:
            return "article"
        elif soup.find('table') or soup.find_all('li', limit=10):
            return "list"
        elif 'search' in url:
            return "search_results"
        else:
            return "general"

    async def _summarize_page(self, title: str, headings: List[str], content: str) -> str:
        """Generate concise summary of page"""

        prompt = f"""
Summarize this web page in 2-3 sentences.

Title: {title}
Headings: {', '.join(headings[:5])}
Content Preview: {content[:500]}

Provide a concise summary.
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",  # Use faster model for summaries
                messages=[
                    {"role": "system", "content": "You summarize web pages concisely."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100
            )

            return response.choices[0].message.content.strip()

        except:
            return f"Page about: {title}"


class PageUnderstanding:
    """
    Deep understanding of current page state for intelligent assistance
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"

    async def answer_about_page(
        self,
        question: str,
        screenshot_base64: str,
        page_content: str,
        page_url: str
    ) -> Dict[str, Any]:
        """
        Answer questions about the current page using vision + content
        """

        prompt = f"""
The user is viewing this page: {page_url}

Page content:
{page_content[:2000]}

User question: {question}

Answer their question based on what you can see in the screenshot and the page content.
Be specific and helpful. If you can see UI elements that could help them, mention them.

Respond in JSON:
{{
    "answer": "Your answer...",
    "relevant_elements": ["element description 1", "element description 2"],
    "suggested_action": "Optional suggestion for what they could do next"
}}
"""

        user_content = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{screenshot_base64}",
                    "detail": "high"
                }
            }
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You help users understand web pages."},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                max_tokens=500
            )

            content = response.choices[0].message.content
            return json.loads(content)

        except Exception as e:
            return {
                "answer": f"Error: {e}",
                "relevant_elements": [],
                "suggested_action": None
            }
