import os
import json
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

class WebAgent:
    """
    Enhanced web agent with conversational capabilities:
    - Multi-turn conversations with memory
    - Web search and research
    - Page understanding and content extraction
    - Smart action suggestions
    - Citation tracking
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        self.conversation_history: List[Dict[str, Any]] = []
        self.page_context: Optional[Dict[str, Any]] = None
        self.citations: List[Dict[str, str]] = []

    def add_page_context(self, url: str, title: str, content: str, screenshot_base64: str, interactive_elements: List[Dict[str, Any]]):
        """Store current page context for understanding"""
        self.page_context = {
            "url": url,
            "title": title,
            "content": content,
            "screenshot": screenshot_base64,
            "elements": interactive_elements,
        }

    def add_citation(self, source_url: str, relevant_text: str, context: str):
        """Track citations for answers"""
        self.citations.append({
            "url": source_url,
            "text": relevant_text,
            "context": context
        })

    async def chat(self, user_message: str, mode: str = "assist") -> Dict[str, Any]:
        """
        Handle multi-turn conversation with different modes:
        - 'assist': Answer questions about current page, suggest actions
        - 'research': Search and synthesize information from multiple sources
        - 'automate': Plan and execute automation tasks
        """

        # Build context-aware system prompt
        system_prompt = self._build_system_prompt(mode)

        # Add user message to conversation
        user_content = self._build_user_content(user_message)

        self.conversation_history.append({
            "role": "user",
            "content": user_content
        })

        try:
            # Call LLM with conversation history
            messages = [
                {"role": "system", "content": system_prompt},
                *self.conversation_history
            ]

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                response_format={"type": "json_object"},
                max_tokens=2000
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            # Add assistant response to conversation
            self.conversation_history.append({
                "role": "assistant",
                "content": content
            })

            return result

        except Exception as e:
            print(f"Error in chat: {e}")
            return {
                "type": "error",
                "message": str(e)
            }

    def _build_system_prompt(self, mode: str) -> str:
        """Build context-aware system prompt based on mode"""

        base_prompt = """
You are an intelligent web assistant with advanced capabilities.
You can:
1. Answer questions about the current web page
2. Search the web and synthesize information with citations
3. Suggest and execute actions on web pages
4. Help users accomplish complex tasks through conversation

You must respond in JSON format with the following structure:
{
    "type": "answer|action|search|plan",
    "response": "Your natural language response to the user",
    "citations": [{"url": "...", "title": "...", "snippet": "..."}],
    "suggested_actions": [{"action": "click|type|navigate", "target": "...", "reason": "..."}],
    "next_steps": ["step 1", "step 2", ...],
    "confidence": 0.0-1.0
}
"""

        if mode == "assist":
            mode_prompt = """
**ASSIST MODE**: You are helping the user understand and interact with the current web page.

When the user asks questions:
- Use the current page context (URL, title, visible content, screenshot) to answer
- Identify relevant interactive elements that could help them
- Suggest specific actions they can take
- Explain what you see on the page

Be conversational and helpful, like a knowledgeable assistant sitting next to them.
"""
        elif mode == "research":
            mode_prompt = """
**RESEARCH MODE**: You are helping the user research and gather information.

When the user asks questions:
- Indicate what you would search for (you'll trigger actual search separately)
- Synthesize information from the current page if relevant
- Suggest navigating to authoritative sources
- Provide citations for all factual claims
- Compare and contrast different sources

Be thorough and cite your sources properly.
"""
        elif mode == "automate":
            mode_prompt = """
**AUTOMATE MODE**: You are helping the user accomplish a task on this website.

When the user describes a task:
- Break it down into clear steps
- Map steps to specific UI actions (click, type, navigate)
- Verify each step before proceeding to the next
- Explain what you're doing and why

Be precise and careful - verify actions worked before continuing.
"""
        else:
            mode_prompt = ""

        context_prompt = ""
        if self.page_context:
            context_prompt = f"""

**CURRENT PAGE CONTEXT**:
- URL: {self.page_context['url']}
- Title: {self.page_context.get('title', 'N/A')}
- Visible Elements: {len(self.page_context.get('elements', []))} interactive elements detected
- Content Preview: {self.page_context.get('content', '')[:500]}...

You can see the current page state in the screenshot provided.
"""

        return base_prompt + mode_prompt + context_prompt

    def _build_user_content(self, message: str) -> List[Dict[str, Any]]:
        """Build user content including text and optional screenshot"""

        content = [
            {
                "type": "text",
                "text": message
            }
        ]

        # Include screenshot if we have page context
        if self.page_context and self.page_context.get("screenshot"):
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{self.page_context['screenshot']}",
                    "detail": "high"
                }
            })

        return content

    def clear_conversation(self):
        """Reset conversation history"""
        self.conversation_history = []
        self.citations = []

    def get_conversation_summary(self) -> str:
        """Get a summary of the conversation for context"""
        if not self.conversation_history:
            return "No conversation yet"

        summary_messages = []
        for msg in self.conversation_history[-6:]:  # Last 3 exchanges
            role = msg["role"]
            content = msg["content"]
            if isinstance(content, list):
                # Extract text from multi-part content
                text_parts = [c["text"] for c in content if c.get("type") == "text"]
                content = " ".join(text_parts)
            elif isinstance(content, str):
                try:
                    parsed = json.loads(content)
                    content = parsed.get("response", content)
                except:
                    pass

            summary_messages.append(f"{role}: {content[:100]}")

        return "\n".join(summary_messages)


class EnhancedVisionAgent:
    """
    Enhanced version of VisionAgent that integrates with WebAgent
    for smarter decision making
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"
        self.web_agent = WebAgent()

    async def analyze_with_context(
        self,
        task: str,
        screenshot_base64: str,
        previous_actions: List[str],
        interactive_elements: List[Dict[str, Any]],
        conversation_context: Optional[str] = None,
        accessibility_tree: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze page state with enhanced context understanding.
        Uses accessibility tree for efficiency when available.
        """

        # Use enhanced prompt that considers conversation
        system_prompt = self._build_enhanced_system_prompt()

        # Build compact element representation (limit to save tokens)
        compact_elements = []
        for i, el in enumerate(interactive_elements[:50]):  # Limit to 50 elements
            compact_el = {
                "idx": i,
                "tag": el.get("tagName", ""),
                "text": el.get("text", "")[:40],  # Truncate text
                "role": el.get("role", ""),
            }
            # Only include non-empty fields
            compact_elements.append({k: v for k, v in compact_el.items() if v})

        elements_str = json.dumps(compact_elements, separators=(',', ':'))  # Compact JSON

        # Build context
        context_parts = [f"Task: {task}"]

        if previous_actions:
            context_parts.append(f"Previous Actions: {previous_actions[-5:]}")  # Last 5 actions

        # Use accessibility tree if available (more token efficient)
        if accessibility_tree:
            context_parts.append(f"Page Structure (Accessibility Tree):\n{accessibility_tree[:2000]}")

        context_parts.append(f"Interactive Elements (idx=element_index for clicking):\n{elements_str}")

        if conversation_context:
            context_parts.append(f"Conversation Context: {conversation_context[:500]}")

        user_text = "\n\n".join(context_parts)

        # Use lower detail for screenshot to save tokens
        user_content = [
            {"type": "text", "text": user_text},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{screenshot_base64}",
                    "detail": "low"  # Use low detail to save tokens
                }
            }
        ]

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                max_tokens=400  # Reduce max tokens for faster response
            )

            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            print(f"Error calling enhanced LLM: {e}")
            return {"action": "fail", "params": {"reason": str(e)}}

    def _build_enhanced_system_prompt(self) -> str:
        """Build enhanced system prompt - optimized for token efficiency"""

        return """You are a UI automation agent. Execute tasks by interacting with web pages.

## VISUAL UNDERSTANDING
The screenshot shows RED BOXES with NUMBER LABELS on interactive elements.
- Each red box has a number (0, 1, 2, etc.) - this is the element_index
- Look at the POSITION of elements to understand what they do:
  - TOP AREA (y < 100): Header buttons, main actions like "Create", "New", "+"
  - LEFT SIDEBAR: Navigation links (NOT action buttons!)
  - CENTER/RIGHT: Content area, tables, forms
- "+" or "Add" buttons in the HEADER area are action buttons
- "Projects", "Issues" in the SIDEBAR are navigation links (don't click for "create" tasks)

## ALLOWED ACTIONS
- click: {element_index: N, text: "visible text"}
- type: {element_index: N, text: "text to type"}
- press: {key: "Enter"|"Tab"|"Escape"|"p"|"n"}  (keyboard shortcuts!)
- scroll: {direction: "up"|"down"}
- done: {message: "what was accomplished"}
- fail: {reason: "why task cannot be completed"}

## OUTPUT FORMAT (JSON)
{"thought": "Looking at red box #X in the header area which shows '+ Add project'", "action": "click", "params": {"element_index": X, "text": "+ Add project"}, "confidence": 0.9}

## KEYBOARD SHORTCUTS (Use when clicking fails!)
- Linear: Press "p" to create new project, "c" to create issue
- Asana: Press "Tab+Q" to quick add
- Notion: Press "n" for new page
- General: Press "Enter" to confirm, "Escape" to cancel

## LINEAR SPECIFIC
In Linear, to create a new project:
1. FIRST: Look for "+ Add project" button in the HEADER TOOLBAR (top of page, near filter/display buttons)
2. OR: Use keyboard shortcut - press "p"
3. DO NOT click sidebar navigation items!
The button looks like: [+ Add project] with a plus icon, located near "Filter" and "Display" buttons

## STATE FEEDBACK
After each action, I'll tell you:
- "UI_CHANGED" = click worked, continue
- "NO_CHANGE" = wrong element, try keyboard shortcut or different element
- "MODAL_OPENED" = form appeared, fill it in
- "FAILED_ELEMENTS: [...]" = don't click these again

## LOOP PREVENTION
If Previous Actions show clicking same thing twice with NO_CHANGE:
1. TRY KEYBOARD SHORTCUT instead (press "p" for project)
2. If that fails, look for element in DIFFERENT area of screen
3. If still stuck, use "fail" action"""

    async def suggest_actions(self, screenshot_base64: str, interactive_elements: List[Dict[str, Any]], user_intent: str) -> List[Dict[str, Any]]:
        """
        Suggest possible actions based on current page state and user intent
        """

        elements_str = json.dumps(interactive_elements[:100], indent=2)

        prompt = f"""
Given this page state and user intent, suggest 3-5 specific actions the user might want to take.

User Intent: {user_intent}

Interactive Elements: {elements_str}

Respond with JSON:
{{
    "suggestions": [
        {{
            "label": "Human-readable action description",
            "action": "click|type|navigate",
            "params": {{"element_index": 0, "text": "..."}},
            "reasoning": "Why this might be helpful"
        }}
    ]
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
                    {"role": "system", "content": "You are a helpful assistant that suggests actions."},
                    {"role": "user", "content": user_content}
                ],
                response_format={"type": "json_object"},
                max_tokens=500
            )

            content = response.choices[0].message.content
            result = json.loads(content)
            return result.get("suggestions", [])
        except Exception as e:
            print(f"Error suggesting actions: {e}")
            return []
