#!/usr/bin/env python3
"""
Chat Assistant for Web Automation

Interactive chat interface that combines:
- Conversational Q&A about web pages
- Web research with citations
- Smart action suggestions
- Task automation

Usage:
    python chat_assistant.py --url "https://example.com"
    python chat_assistant.py  # Start without a page, navigate later
"""

import asyncio
import argparse
import os
import sys
from typing import Optional
from src.browser_manager import BrowserManager
from src.perplexity_agent import WebAgent, EnhancedVisionAgent
from src.web_researcher import WebResearcher, PageUnderstanding


class ChatAssistant:
    """
    Main chat assistant orchestrator
    """

    def __init__(self, start_url: Optional[str] = None, headless: bool = False):
        self.browser = BrowserManager(headless=headless)
        self.web_agent = WebAgent()
        self.vision_agent = EnhancedVisionAgent()
        self.researcher = WebResearcher()
        self.page_understanding = PageUnderstanding()
        self.start_url = start_url
        self.current_mode = "assist"  # assist, research, automate

    async def start(self):
        """Initialize and start the chat session"""
        print("\n" + "="*70)
        print("Web Automation Assistant")
        print("="*70)
        print("\nCapabilities:")
        print("  💬 Chat about web pages - Ask questions about what you see")
        print("  🔍 Research mode - Search the web with citations")
        print("  🤖 Automate tasks - Execute complex workflows")
        print("  💡 Smart suggestions - Get action recommendations")
        print("\nCommands:")
        print("  /help       - Show all commands")
        print("  /mode       - Switch between assist/research/automate modes")
        print("  /navigate   - Navigate to a new URL")
        print("  /actions    - Show suggested actions for current page")
        print("  /clear      - Clear conversation history")
        print("  /quit       - Exit the assistant")
        print("="*70 + "\n")

        await self.browser.start()

        if self.start_url:
            print(f"🌐 Navigating to: {self.start_url}")
            await self.browser.navigate(self.start_url)
            await asyncio.sleep(2)  # Wait for page load
            await self._update_page_context()
            print("✓ Page loaded and analyzed\n")

        # Start chat loop
        await self._chat_loop()

    async def _chat_loop(self):
        """Main interactive chat loop"""

        while True:
            try:
                # Show current mode and page
                page_url = self.browser.page.url if self.browser.page else "No page loaded"
                mode_emoji = {"assist": "💬", "research": "🔍", "automate": "🤖"}

                prompt = f"{mode_emoji.get(self.current_mode, '💬')} [{self.current_mode}] > "

                user_input = input(prompt).strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    await self._handle_command(user_input)
                    continue

                # Process message based on mode
                await self._process_message(user_input)

            except KeyboardInterrupt:
                print("\n\nUse /quit to exit")
                continue
            except EOFError:
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                continue

    async def _process_message(self, message: str):
        """Process user message based on current mode"""

        if self.current_mode == "assist":
            await self._assist_mode(message)
        elif self.current_mode == "research":
            await self._research_mode(message)
        elif self.current_mode == "automate":
            await self._automate_mode(message)

    async def _assist_mode(self, message: str):
        """Assist mode: Answer questions about current page"""

        if not self.browser.page:
            print("❌ No page loaded. Use /navigate to open a page first.")
            return

        print("\n🤔 Analyzing page...", end="", flush=True)

        # Get current page state
        screenshot_b64, interactive_elements = await self.browser.capture_state_with_overlays()
        page_html = await self.browser.page.content()
        page_url = self.browser.page.url

        # Extract page content
        page_data = await self.researcher.extract_page_content(page_html, page_url)

        # Update agent context
        self.web_agent.add_page_context(
            url=page_url,
            title=page_data["title"],
            content=page_data["content"],
            screenshot_base64=screenshot_b64,
            interactive_elements=interactive_elements
        )

        # Get answer from page understanding
        result = await self.page_understanding.answer_about_page(
            question=message,
            screenshot_base64=screenshot_b64,
            page_content=page_data["content"],
            page_url=page_url
        )

        print("\r" + " "*50 + "\r", end="")  # Clear "Analyzing..."

        # Display answer
        print(f"\n💡 {result['answer']}\n")

        if result.get("relevant_elements"):
            print("📍 Relevant elements on page:")
            for elem in result["relevant_elements"]:
                print(f"   • {elem}")
            print()

        if result.get("suggested_action"):
            print(f"💭 Suggestion: {result['suggested_action']}\n")

    async def _research_mode(self, message: str):
        """Research mode: Search web and synthesize answer"""

        print("\n🔍 Researching...", end="", flush=True)

        # Get current page content if available
        current_page_content = None
        if self.browser.page:
            page_html = await self.browser.page.content()
            page_data = await self.researcher.extract_page_content(page_html, self.browser.page.url)
            current_page_content = page_data["content"]

        # Search and synthesize
        result = await self.researcher.search_and_answer(
            query=message,
            max_sources=5,
            current_page_content=current_page_content
        )

        print("\r" + " "*50 + "\r", end="")  # Clear "Researching..."

        # Display answer with citations
        print(f"\n💡 {result['answer']}\n")

        if result.get("key_points"):
            print("📋 Key Points:")
            for point in result["key_points"]:
                print(f"   • {point}")
            print()

        if result.get("citations"):
            print("📚 Sources:")
            for cite in result["citations"]:
                print(f"   [{cite['index']}] {cite['title']}")
                print(f"       {cite['url']}")
                if cite.get("relevant_quote"):
                    print(f"       \"{cite['relevant_quote'][:100]}...\"")
            print()

        if result.get("caveats"):
            print("⚠️  Caveats:")
            for caveat in result["caveats"]:
                print(f"   • {caveat}")
            print()

        confidence = result.get("confidence", 0.5)
        confidence_bar = "█" * int(confidence * 10) + "░" * (10 - int(confidence * 10))
        print(f"📊 Confidence: {confidence_bar} {confidence:.0%}\n")

    async def _automate_mode(self, message: str):
        """Automate mode: Execute tasks on the page"""

        if not self.browser.page:
            print("❌ No page loaded. Use /navigate to open a page first.")
            return

        print(f"\n🤖 Planning how to: {message}")
        print("="*70)

        # Get current state
        screenshot_b64, interactive_elements = await self.browser.capture_state_with_overlays()

        # Use enhanced vision agent to plan
        decision = await self.vision_agent.analyze_with_context(
            task=message,
            screenshot_base64=screenshot_b64,
            previous_actions=[],
            interactive_elements=interactive_elements,
            conversation_context=self.web_agent.get_conversation_summary()
        )

        # Display reasoning
        if decision.get("reasoning_chain"):
            print("\n💭 Reasoning:")
            for step in decision["reasoning_chain"]:
                print(f"   {step}")

        if decision.get("plan_ahead"):
            print("\n📋 Plan:")
            for i, step in enumerate(decision["plan_ahead"], 1):
                print(f"   {i}. {step}")

        print(f"\n🎯 Next Action: {decision.get('action')}")
        print(f"💡 Thought: {decision.get('thought')}\n")

        # Ask for confirmation if confidence is low
        confidence = decision.get("confidence", 1.0)
        if confidence < 0.7:
            confirm = input(f"⚠️  Low confidence ({confidence:.0%}). Proceed? [y/N] ").lower()
            if confirm != 'y':
                print("❌ Action cancelled")
                return

        # Execute action (simplified - you'd expand this)
        action = decision.get("action")
        params = decision.get("params", {})

        if action == "ask":
            question = params.get("question", "Should I proceed?")
            print(f"\n❓ Agent needs clarification: {question}")
            user_response = input("Your answer: ")
            print(f"✓ Got it: {user_response}\n")
            # Re-run with clarification
            await self._automate_mode(f"{message} (Note: {user_response})")

        elif action == "click":
            idx = params.get("element_index")
            text = params.get("text", "")
            print(f"🖱️  Clicking element {idx}: '{text}'...")

            if idx is not None and idx < len(interactive_elements):
                coords = interactive_elements[idx].get("rect")
                await self.browser.click_element(coords=coords)
                await asyncio.sleep(1)
                print("✓ Clicked")

        elif action == "type":
            text = params.get("text", "")
            print(f"⌨️  Typing: '{text}'...")
            await self.browser.page.keyboard.type(text)
            await asyncio.sleep(0.5)
            print("✓ Typed")

        elif action == "finish":
            print("✅ Task completed!")

        elif action == "fail":
            reason = params.get("reason", "Unknown")
            print(f"❌ Task failed: {reason}")

        else:
            print(f"⚠️  Unknown action: {action}")

        print()

    async def _handle_command(self, command: str):
        """Handle slash commands"""

        cmd = command.lower().split()[0]

        if cmd == "/help":
            print("\n📖 Available Commands:")
            print("  /mode [assist|research|automate] - Switch modes")
            print("  /navigate <url>                  - Navigate to URL")
            print("  /actions                         - Show suggested actions")
            print("  /clear                           - Clear conversation history")
            print("  /status                          - Show current status")
            print("  /quit                            - Exit assistant")
            print()

        elif cmd == "/mode":
            parts = command.split()
            if len(parts) > 1:
                new_mode = parts[1].lower()
                if new_mode in ["assist", "research", "automate"]:
                    self.current_mode = new_mode
                    print(f"✓ Switched to {new_mode} mode\n")
                else:
                    print("❌ Invalid mode. Use: assist, research, or automate\n")
            else:
                print(f"Current mode: {self.current_mode}")
                print("Available modes: assist, research, automate\n")

        elif cmd == "/navigate":
            parts = command.split(maxsplit=1)
            if len(parts) > 1:
                url = parts[1]
                print(f"🌐 Navigating to {url}...")
                await self.browser.navigate(url)
                await asyncio.sleep(2)
                await self._update_page_context()
                print("✓ Page loaded\n")
            else:
                print("❌ Usage: /navigate <url>\n")

        elif cmd == "/actions":
            if not self.browser.page:
                print("❌ No page loaded\n")
                return

            print("🔍 Analyzing page for suggestions...\n")
            screenshot_b64, interactive_elements = await self.browser.capture_state_with_overlays()

            user_intent = input("What do you want to do? (optional): ").strip()
            if not user_intent:
                user_intent = "general page actions"

            suggestions = await self.vision_agent.suggest_actions(
                screenshot_b64, interactive_elements, user_intent
            )

            if suggestions:
                print("\n💡 Suggested Actions:")
                for i, sug in enumerate(suggestions, 1):
                    print(f"\n  {i}. {sug.get('label')}")
                    print(f"     Reason: {sug.get('reasoning')}")
                print()
            else:
                print("No suggestions available\n")

        elif cmd == "/clear":
            self.web_agent.clear_conversation()
            print("Conversation history cleared\n")

        elif cmd == "/status":
            page_url = self.browser.page.url if self.browser.page else "No page loaded"
            print(f"\n📊 Status:")
            print(f"  Mode: {self.current_mode}")
            print(f"  Page: {page_url}")
            print(f"  Conversation: {len(self.web_agent.conversation_history)} messages")
            print()

        elif cmd == "/quit":
            print("\n👋 Goodbye!")
            await self.browser.stop()
            sys.exit(0)

        else:
            print(f"❌ Unknown command: {command}")
            print("Type /help for available commands\n")

    async def _update_page_context(self):
        """Update page context after navigation"""
        if self.browser.page:
            screenshot_b64, elements = await self.browser.capture_state_with_overlays()
            page_html = await self.browser.page.content()
            page_data = await self.researcher.extract_page_content(page_html, self.browser.page.url)

            self.web_agent.add_page_context(
                url=self.browser.page.url,
                title=page_data["title"],
                content=page_data["content"],
                screenshot_base64=screenshot_b64,
                interactive_elements=elements
            )


async def main():
    parser = argparse.ArgumentParser(
        description="Web Automation Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start on a specific page
  python chat_assistant.py --url "https://linear.app"

  # Start without a page (navigate later with /navigate)
  python chat_assistant.py

  # Run in headless mode
  python chat_assistant.py --url "https://example.com" --headless
        """
    )
    parser.add_argument("--url", type=str, help="Starting URL (optional)")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")

    args = parser.parse_args()

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found")
        print("Please set it in .env file or environment")
        return

    # Start assistant
    assistant = ChatAssistant(start_url=args.url, headless=args.headless)
    await assistant.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
