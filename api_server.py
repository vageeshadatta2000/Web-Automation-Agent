#!/usr/bin/env python3
"""
FastAPI Backend Server for Web Automation Assistant

Bridges the React frontend with the Python automation agent.
Provides REST API and WebSocket support for real-time updates.
"""

import asyncio
import os
import base64
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

from src.browser_manager import BrowserManager
from src.perplexity_agent import WebAgent, EnhancedVisionAgent
from src.web_researcher import WebResearcher, PageUnderstanding


# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    mode: str = "assist"
    url: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    citations: Optional[List[Dict[str, Any]]] = None
    suggestedActions: Optional[List[Dict[str, Any]]] = None
    reasoning: Optional[List[str]] = None
    confidence: Optional[float] = None
    screenshot: Optional[str] = None


class NavigateRequest(BaseModel):
    url: str


class ActionRequest(BaseModel):
    action: str
    params: Dict[str, Any]


# Initialize FastAPI app
app = FastAPI(
    title="Web Automation Assistant API",
    description="Backend API for the web automation assistant",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
browser_manager: Optional[BrowserManager] = None
web_agent: Optional[WebAgent] = None
vision_agent: Optional[EnhancedVisionAgent] = None
researcher: Optional[WebResearcher] = None
page_understanding: Optional[PageUnderstanding] = None


# Startup/Shutdown Events
@app.on_event("startup")
async def startup_event():
    """Initialize browser and agents on startup"""
    global browser_manager, web_agent, vision_agent, researcher, page_understanding

    print("Starting Web Automation Assistant API...")

    # Initialize components
    browser_manager = BrowserManager(headless=True)
    web_agent = WebAgent()
    vision_agent = EnhancedVisionAgent()
    researcher = WebResearcher()
    page_understanding = PageUnderstanding()

    # Start browser
    await browser_manager.start()

    print("API Server ready!")
    print("Browser: Ready")
    print("Agents: Initialized")
    print("Server: http://localhost:8000")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global browser_manager

    print("\nShutting down...")

    if browser_manager:
        await browser_manager.stop()

    print("Cleanup complete")


# API Routes

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "service": "Web Automation Assistant API",
        "version": "1.0.0"
    }


@app.get("/api/status")
async def get_status():
    """Get current browser and agent status"""
    current_url = browser_manager.page.url if browser_manager and browser_manager.page else None

    return {
        "browser": {
            "active": browser_manager is not None,
            "url": current_url
        },
        "agents": {
            "web_agent": web_agent is not None,
            "vision": vision_agent is not None,
            "researcher": researcher is not None
        }
    }


@app.post("/api/navigate", response_model=Dict[str, Any])
async def navigate(request: NavigateRequest):
    """Navigate browser to a URL"""
    if not browser_manager:
        raise HTTPException(status_code=500, detail="Browser not initialized")

    try:
        # Check if browser is still alive, reinitialize if needed
        if not browser_manager.is_alive():
            print("⚠️  Browser was closed, reinitializing...")
            await browser_manager.start()

        await browser_manager.navigate(request.url)
        await asyncio.sleep(2)  # Wait for page load

        # Capture CLEAN screenshot for user display (no overlays)
        clean_screenshot = await browser_manager.capture_screenshot()

        # Get page content
        page_html = await browser_manager.page.content()
        page_data = await researcher.extract_page_content(page_html, request.url)

        # Get elements for context (but don't send annotated screenshot to user)
        elements = await browser_manager.get_interactive_elements()

        # Update web agent context (agent will generate overlays when needed)
        web_agent.add_page_context(
            url=request.url,
            title=page_data["title"],
            content=page_data["content"],
            screenshot_base64=clean_screenshot,
            interactive_elements=elements
        )

        return {
            "success": True,
            "url": request.url,
            "title": page_data["title"],
            "screenshot": clean_screenshot,  # Clean screenshot without overlays!
            "elementCount": len(elements)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat messages from frontend"""
    if not browser_manager:
        raise HTTPException(status_code=500, detail="Browser not initialized")

    try:
        # Check if browser is still alive, reinitialize if needed
        if not browser_manager.is_alive():
            print("⚠️  Browser was closed, reinitializing...")
            await browser_manager.start()

        # Get clean screenshot for user display
        clean_screenshot = await browser_manager.capture_screenshot()

        # Get interactive elements
        interactive_elements = await browser_manager.get_interactive_elements()

        if browser_manager.page:
            page_html = await browser_manager.page.content()
            page_url = browser_manager.page.url
        else:
            page_html = ""
            page_url = None

        # Detect navigation requests and handle them first
        import re
        navigated = False
        extracted_url = None

        # Common website patterns to detect
        website_patterns = [
            r'(https?://[^\s]+)',  # Full URLs
            r'([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}(?:\.[a-zA-Z]{2,})?(?:/[^\s]*)?)',  # domain.com patterns
        ]

        nav_keywords = ['navigate to', 'go to', 'open', 'visit', 'browse to', 'take me to']

        # Check if message contains navigation intent
        message_lower = request.message.lower()
        has_nav_intent = any(kw in message_lower for kw in nav_keywords)

        # Common sites mapping - used for both explicit navigation and implicit (automate mode)
        common_sites = {
            'youtube': 'youtube.com',
            'github': 'github.com',
            'google': 'google.com',
            'twitter': 'twitter.com',
            'x': 'x.com',
            'facebook': 'facebook.com',
            'linkedin': 'linkedin.com',
            'reddit': 'reddit.com',
            'amazon': 'amazon.com',
            'netflix': 'netflix.com',
            'linear': 'linear.app',
            'notion': 'notion.so',
            'asana': 'asana.com',
            'trello': 'trello.com',
            'slack': 'slack.com',
            'jira': 'atlassian.net',
            'figma': 'figma.com',
            'gmail': 'mail.google.com',
            'spotify': 'spotify.com',
            'instagram': 'instagram.com',
            'tiktok': 'tiktok.com',
            'pinterest': 'pinterest.com',
            'dropbox': 'dropbox.com',
            'zoom': 'zoom.us',
            'discord': 'discord.com',
            'whatsapp': 'web.whatsapp.com',
            'telegram': 'web.telegram.org',
            'medium': 'medium.com',
            'stackoverflow': 'stackoverflow.com',
            'stack overflow': 'stackoverflow.com',
            'chatgpt': 'chatgpt.com',
            'perplexityai': 'perplexity.ai',
            'claude': 'claude.ai',
        }

        # Check if we're on about:blank and need to navigate somewhere
        current_url = browser_manager.page.url if browser_manager and browser_manager.page else ""
        is_blank_page = current_url in ["about:blank", "chrome://new-tab-page/", ""]

        if has_nav_intent:
            # Try to extract URL from message
            for pattern in website_patterns:
                match = re.search(pattern, request.message, re.IGNORECASE)
                if match:
                    extracted_url = match.group(1)
                    break

            # If no URL found, try common site names
            if not extracted_url:
                for site_name, site_url in common_sites.items():
                    if site_name in message_lower:
                        extracted_url = site_url
                        break

        # IMPORTANT: In automate mode, if on blank page and site name mentioned, auto-navigate
        elif request.mode == "automate" and is_blank_page:
            print(f"🔍 Automate mode on blank page, checking for site names...")
            for site_name, site_url in common_sites.items():
                if site_name in message_lower:
                    extracted_url = site_url
                    print(f"   Found site: {site_name} -> {site_url}")
                    break

            # Also try to extract any URL pattern from the message
            if not extracted_url:
                for pattern in website_patterns:
                    match = re.search(pattern, request.message, re.IGNORECASE)
                    if match:
                        extracted_url = match.group(1)
                        break

        if extracted_url:
            # Add protocol if missing
            if not extracted_url.startswith('http'):
                extracted_url = f'https://{extracted_url}'

            print(f"🔍 Detected navigation request to: {extracted_url}")

            # Broadcast navigation starting
            await broadcast_update("automation_start", {
                "status": "Working...",
                "message": "Preparing to assist you"
            })

            await broadcast_update("automation_status", {
                "status": "Navigating...",
                "message": f"Navigating to {extracted_url}",
                "action": "navigate",
                "target": extracted_url
            })

            try:
                await browser_manager.navigate(extracted_url)
                await asyncio.sleep(2)  # Wait for page load
                navigated = True

                # Update screenshots and elements after navigation
                clean_screenshot = await browser_manager.capture_screenshot()
                interactive_elements = await browser_manager.get_interactive_elements()

                # Broadcast screenshot update
                await broadcast_update("screenshot_update", {
                    "screenshot": clean_screenshot,
                    "url": extracted_url
                })

                await broadcast_update("automation_status", {
                    "status": "Reading page...",
                    "message": f"Analyzing {extracted_url}",
                    "action": "analyze"
                })

                if browser_manager.page:
                    page_html = await browser_manager.page.content()
                    page_url = browser_manager.page.url

                # Broadcast complete
                await broadcast_update("automation_complete", {
                    "status": "Complete",
                    "actionsCount": 1
                })
            except Exception as nav_error:
                print(f"Navigation error: {nav_error}")
                await broadcast_update("automation_error", {
                    "error": str(nav_error),
                    "action": "navigate"
                })

        # For automate mode, we need annotated screenshot with overlays for the vision agent
        if request.mode == "automate":
            annotated_screenshot, _ = await browser_manager.capture_state_with_overlays()
        else:
            annotated_screenshot = clean_screenshot

        # Route to appropriate handler based on mode
        if request.mode == "assist":
            response_data = await handle_assist_mode(
                request.message,
                annotated_screenshot,  # Can use clean for assist
                interactive_elements,
                page_html,
                page_url,
                navigated
            )

        elif request.mode == "research":
            response_data = await handle_research_mode(
                request.message,
                page_html if page_html else None
            )

        elif request.mode == "automate":
            response_data = await handle_automate_mode(
                request.message,
                annotated_screenshot,  # Vision agent needs overlays
                interactive_elements
            )
            # Get updated screenshot after automation
            clean_screenshot = await browser_manager.capture_screenshot()

        else:
            response_data = {
                "response": "Invalid mode selected.",
                "citations": [],
                "suggestedActions": [],
                "reasoning": [],
                "confidence": 0.0
            }

        # Include CLEAN screenshot for user display (no red boxes!)
        response_data["screenshot"] = clean_screenshot

        return ChatResponse(**response_data)

    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


async def handle_assist_mode(message: str, screenshot: str, elements: List[Dict], page_html: str, page_url: str, navigated: bool = False):
    """Handle assist mode requests"""

    # Extract page content
    page_data = await researcher.extract_page_content(page_html, page_url)

    # Update agent context
    web_agent.add_page_context(
        url=page_url,
        title=page_data["title"],
        content=page_data["content"],
        screenshot_base64=screenshot,
        interactive_elements=elements
    )

    # If navigation happened, provide context about the new page
    if navigated:
        response_text = f"I've navigated to **{page_url}**.\n\n"

        # Get page overview
        result = await page_understanding.answer_about_page(
            question="What is this page about? Summarize the key sections and features.",
            screenshot_base64=screenshot,
            page_content=page_data["content"],
            page_url=page_url
        )
        response_text += result.get("answer", "Here's what I found on this page.")
    else:
        # Get answer to user's question
        result = await page_understanding.answer_about_page(
            question=message,
            screenshot_base64=screenshot,
            page_content=page_data["content"],
            page_url=page_url
        )
        response_text = result.get("answer", "I couldn't analyze the page.")

    # Get suggested actions
    suggested_actions = []
    if len(elements) > 0:
        suggestions = await vision_agent.suggest_actions(
            screenshot_base64=screenshot,
            interactive_elements=elements,
            user_intent=message
        )
        suggested_actions = suggestions[:3]  # Top 3 suggestions

    return {
        "response": response_text,
        "citations": [],
        "suggestedActions": suggested_actions,
        "reasoning": result.get("relevant_elements", []),
        "confidence": 0.85
    }


async def handle_research_mode(message: str, current_page_content: Optional[str]):
    """Handle research mode requests"""

    # Search and synthesize
    result = await researcher.search_and_answer(
        query=message,
        max_sources=5,
        current_page_content=current_page_content
    )

    # Format citations
    citations = result.get("citations", [])

    # Format reasoning as key points
    reasoning = result.get("key_points", [])

    return {
        "response": result.get("answer", "I couldn't find relevant information."),
        "citations": citations,
        "suggestedActions": [],
        "reasoning": reasoning,
        "confidence": result.get("confidence", 0.5)
    }


async def handle_automate_mode(message: str, screenshot: str, elements: List[Dict]):
    """Handle automate mode requests - ACTUALLY EXECUTES ACTIONS with real-time streaming"""

    actions_taken = []
    reasoning = []
    max_steps = 8  # Maximum automation steps per request
    previous_element_count = len(elements)
    previous_url = browser_manager.page.url if browser_manager.page else ""
    state_change_info = ""  # Track what changed between steps
    failed_clicks = set()  # Track elements that didn't work

    # Broadcast that automation is starting
    await broadcast_update("automation_start", {
        "status": "Working...",
        "message": "Preparing to assist you"
    })

    for step in range(max_steps):
        print(f"🤖 Automation Step {step + 1}")

        # Broadcast thinking status
        await broadcast_update("automation_status", {
            "status": "Thinking...",
            "message": f"Analyzing step {step + 1}",
            "step": step + 1,
            "maxSteps": max_steps
        })

        # CRITICAL: Get annotated screenshot with bounding boxes for agent
        # This lets the agent SEE where each element is visually
        annotated_screenshot, labeled_elements = await browser_manager.capture_state_with_overlays(compress_for_llm=True)

        # Get accessibility tree for more efficient analysis (saves tokens)
        accessibility_tree = await browser_manager.get_accessibility_tree(max_depth=2)

        # Build enhanced context with state change info
        enhanced_actions = actions_taken.copy()
        if state_change_info:
            enhanced_actions.append(f"STATE: {state_change_info}")
        if failed_clicks:
            enhanced_actions.append(f"FAILED_ELEMENTS: {list(failed_clicks)}")

        # Use enhanced vision agent to decide next action
        # Pass annotated screenshot so agent can see element indices visually
        decision = await vision_agent.analyze_with_context(
            task=message,
            screenshot_base64=annotated_screenshot,  # Use annotated screenshot with red boxes!
            previous_actions=enhanced_actions,
            interactive_elements=labeled_elements,  # Use the filtered/labeled elements
            conversation_context=web_agent.get_conversation_summary(),
            accessibility_tree=accessibility_tree
        )

        # Update elements reference for click execution
        elements = labeled_elements

        action = decision.get("action", "done")
        params = decision.get("params", {})
        thought = decision.get("thought", "")
        click_text = params.get("text", "")

        if thought:
            reasoning.append(thought)

        print(f"   Action: {action}, Params: {params}")

        # Loop detection: If agent is trying to click something that already failed, suggest keyboard shortcut
        if action == "click" and click_text and click_text in failed_clicks:
            print(f"   ⚠️ Loop detected: '{click_text}' already failed, suggesting keyboard shortcut")
            actions_taken.append(f"⚠️ Skipped repeated click on '{click_text}' - TRY KEYBOARD SHORTCUT")

            # Suggest keyboard shortcut based on task
            task_lower = message.lower()
            if "project" in task_lower and "linear" in (browser_manager.page.url if browser_manager.page else ""):
                state_change_info = f"LOOP_PREVENTED: Already tried '{click_text}'. USE press action with key='p' for Linear project creation!"
            elif "issue" in task_lower:
                state_change_info = f"LOOP_PREVENTED: Already tried '{click_text}'. USE press action with key='c' for issue creation!"
            else:
                state_change_info = f"LOOP_PREVENTED: Already tried '{click_text}'. Try a DIFFERENT element or keyboard shortcut."
            continue

        # Execute the action
        if action == "done" or action == "wait":
            actions_taken.append(f"✅ Task completed: {thought}")
            await broadcast_update("automation_status", {
                "status": "Complete",
                "message": "Task finished",
                "action": "done"
            })
            break

        elif action == "click":
            element_index = params.get("element_index")
            selector = params.get("selector")  # Agent might provide a CSS selector
            click_text = params.get("text", "")  # Agent might describe what to click

            # Broadcast clicking status
            target_desc = click_text[:30] if click_text else (selector if selector else "element")
            await broadcast_update("automation_status", {
                "status": "Clicking...",
                "message": f"Clicking on '{target_desc}'",
                "action": "click",
                "target": target_desc
            })

            try:
                clicked = False

                # Priority 1: Use element_index if valid
                if element_index is not None and element_index < len(elements):
                    element = elements[element_index]
                    coords = element.get("rect")
                    element_text = element.get("text", "element")[:30]

                    # Calculate click position
                    click_x = coords["x"] + coords["width"] / 2
                    click_y = coords["y"] + coords["height"] / 2

                    # Show cursor
                    cursor_screenshot = await browser_manager.capture_screenshot_with_cursor(click_x, click_y)
                    await broadcast_update("screenshot_update", {
                        "screenshot": cursor_screenshot,
                        "url": browser_manager.page.url if browser_manager.page else None
                    })

                    # Perform click
                    await browser_manager.click_element(coords=coords)
                    actions_taken.append(f"🖱️ Clicked on '{element_text}'")
                    clicked = True

                # Priority 2: Use CSS selector if provided
                elif selector:
                    print(f"Using selector for clicking: {selector}")
                    try:
                        locator = browser_manager.page.locator(selector).first
                        await locator.wait_for(state="visible", timeout=3000)
                        box = await locator.bounding_box()
                        if box:
                            cursor_screenshot = await browser_manager.capture_screenshot_with_cursor(
                                box["x"] + box["width"] / 2,
                                box["y"] + box["height"] / 2
                            )
                            await broadcast_update("screenshot_update", {
                                "screenshot": cursor_screenshot,
                                "url": browser_manager.page.url if browser_manager.page else None
                            })
                        await locator.click()
                        actions_taken.append(f"🖱️ Clicked on '{selector}'")
                        clicked = True
                    except Exception as sel_error:
                        print(f"Selector click failed: {sel_error}")

                # Priority 3: Try to find by text content
                if not clicked and click_text:
                    print(f"Trying to click by text: {click_text}")
                    try:
                        # Try various text-based selectors
                        text_selectors = [
                            f"button:has-text('{click_text}')",
                            f"a:has-text('{click_text}')",
                            f"[role='button']:has-text('{click_text}')",
                            f"text='{click_text}'",
                        ]
                        for text_sel in text_selectors:
                            try:
                                locator = browser_manager.page.locator(text_sel).first
                                await locator.wait_for(state="visible", timeout=1500)
                                box = await locator.bounding_box()
                                if box:
                                    cursor_screenshot = await browser_manager.capture_screenshot_with_cursor(
                                        box["x"] + box["width"] / 2,
                                        box["y"] + box["height"] / 2
                                    )
                                    await broadcast_update("screenshot_update", {
                                        "screenshot": cursor_screenshot,
                                        "url": browser_manager.page.url if browser_manager.page else None
                                    })
                                await locator.click()
                                actions_taken.append(f"🖱️ Clicked on '{click_text}'")
                                clicked = True
                                break
                            except:
                                continue
                    except Exception as text_error:
                        print(f"Text-based click failed: {text_error}")

                if not clicked:
                    actions_taken.append(f"❌ Could not find element to click (index: {element_index}, selector: {selector})")
                    failed_clicks.add(click_text or target_desc)
                    await broadcast_update("automation_error", {
                        "error": f"Element not found: {target_desc}",
                        "action": "click"
                    })
                    # Don't break - let agent try different approach
                    state_change_info = f"NO_CHANGE: Could not click '{target_desc}'"
                    continue

                await asyncio.sleep(1.0)

                # Get updated state after click
                screenshot = await browser_manager.capture_screenshot()
                elements = await browser_manager.get_interactive_elements()
                current_url = browser_manager.page.url if browser_manager.page else ""

                # Detect state changes for the agent
                new_element_count = len(elements)
                if current_url != previous_url:
                    state_change_info = f"NAVIGATION: URL changed to {current_url}"
                    previous_url = current_url
                elif abs(new_element_count - previous_element_count) > 20:
                    state_change_info = f"MODAL_OPENED: Significant UI change ({previous_element_count} -> {new_element_count} elements)"
                elif new_element_count != previous_element_count:
                    state_change_info = f"UI_CHANGED: Element count {previous_element_count} -> {new_element_count}"
                else:
                    state_change_info = f"NO_CHANGE: UI unchanged after clicking '{click_text}'"
                    failed_clicks.add(click_text or target_desc)

                previous_element_count = new_element_count
                print(f"   State: {state_change_info}")

                # Send updated screenshot to frontend
                await broadcast_update("screenshot_update", {
                    "screenshot": screenshot,
                    "url": browser_manager.page.url if browser_manager.page else None
                })

            except Exception as e:
                actions_taken.append(f"❌ Failed to click: {e}")
                await broadcast_update("automation_error", {
                    "error": str(e),
                    "action": "click"
                })
                break

        elif action == "type":
            text = params.get("text", "")
            element_index = params.get("element_index")
            selector = params.get("selector")  # Agent might provide a CSS selector

            # Broadcast typing status
            await broadcast_update("automation_status", {
                "status": "Typing...",
                "message": f"Typing '{text[:20]}{'...' if len(text) > 20 else ''}'",
                "action": "type",
                "target": text[:30]
            })

            try:
                # Priority 1: Use element_index if provided
                if element_index is not None and element_index < len(elements):
                    element = elements[element_index]
                    coords = element.get("rect")

                    # Show cursor at element position
                    click_x = coords["x"] + coords["width"] / 2
                    click_y = coords["y"] + coords["height"] / 2
                    cursor_screenshot = await browser_manager.capture_screenshot_with_cursor(click_x, click_y)
                    await broadcast_update("screenshot_update", {
                        "screenshot": cursor_screenshot,
                        "url": browser_manager.page.url if browser_manager.page else None
                    })

                    # Click first to focus
                    await browser_manager.click_element(coords=coords)
                    await asyncio.sleep(0.3)

                    # Then type
                    await browser_manager.type_text(text)

                # Priority 2: Use CSS selector if provided
                elif selector:
                    print(f"Using selector for typing: {selector}")
                    # Try to find and click the element using selector
                    try:
                        locator = browser_manager.page.locator(selector).first
                        await locator.wait_for(state="visible", timeout=3000)
                        box = await locator.bounding_box()
                        if box:
                            # Show cursor
                            cursor_screenshot = await browser_manager.capture_screenshot_with_cursor(
                                box["x"] + box["width"] / 2,
                                box["y"] + box["height"] / 2
                            )
                            await broadcast_update("screenshot_update", {
                                "screenshot": cursor_screenshot,
                                "url": browser_manager.page.url if browser_manager.page else None
                            })

                        await locator.click()
                        await asyncio.sleep(0.3)
                        await locator.fill(text)
                    except Exception as sel_error:
                        print(f"Selector failed: {sel_error}, trying keyboard type")
                        # Fallback: try to find search input by common patterns
                        search_selectors = [
                            "input[name='search_query']",
                            "input[placeholder*='Search']",
                            "input[type='search']",
                            "#search-input",
                            "[data-testid='search-input']"
                        ]
                        typed = False
                        for sel in search_selectors:
                            try:
                                loc = browser_manager.page.locator(sel).first
                                await loc.wait_for(state="visible", timeout=1000)
                                await loc.click()
                                await asyncio.sleep(0.2)
                                await loc.fill(text)
                                typed = True
                                break
                            except:
                                continue

                        if not typed:
                            # Last resort: keyboard type
                            await browser_manager.page.keyboard.type(text)

                # Priority 3: Try common search patterns
                else:
                    print("No element_index or selector, trying common search patterns")
                    search_selectors = [
                        "input[name='search_query']",
                        "input[placeholder*='Search']",
                        "input[type='search']",
                        "#search-input",
                        "input[aria-label*='Search']"
                    ]
                    typed = False
                    for sel in search_selectors:
                        try:
                            loc = browser_manager.page.locator(sel).first
                            await loc.wait_for(state="visible", timeout=1000)
                            box = await loc.bounding_box()
                            if box:
                                cursor_screenshot = await browser_manager.capture_screenshot_with_cursor(
                                    box["x"] + box["width"] / 2,
                                    box["y"] + box["height"] / 2
                                )
                                await broadcast_update("screenshot_update", {
                                    "screenshot": cursor_screenshot,
                                    "url": browser_manager.page.url if browser_manager.page else None
                                })
                            await loc.click()
                            await asyncio.sleep(0.2)
                            await loc.fill(text)
                            typed = True
                            break
                        except:
                            continue

                    if not typed:
                        await browser_manager.page.keyboard.type(text)

                actions_taken.append(f"⌨️ Typed '{text}'")
                await asyncio.sleep(0.5)

                # Get updated state and broadcast screenshot
                screenshot = await browser_manager.capture_screenshot()
                elements = await browser_manager.get_interactive_elements()

                await broadcast_update("screenshot_update", {
                    "screenshot": screenshot,
                    "url": browser_manager.page.url if browser_manager.page else None
                })

            except Exception as e:
                actions_taken.append(f"❌ Failed to type: {e}")
                await broadcast_update("automation_error", {
                    "error": str(e),
                    "action": "type"
                })
                break

        elif action == "scroll":
            direction = params.get("direction", "down")

            # Broadcast scrolling status
            await broadcast_update("automation_status", {
                "status": "Scrolling...",
                "message": f"Scrolling {direction}",
                "action": "scroll",
                "direction": direction
            })

            try:
                await browser_manager.scroll(direction)
                actions_taken.append(f"📜 Scrolled {direction}")
                await asyncio.sleep(1)

                # Get updated state and broadcast screenshot
                screenshot = await browser_manager.capture_screenshot()
                elements = await browser_manager.get_interactive_elements()

                await broadcast_update("screenshot_update", {
                    "screenshot": screenshot,
                    "url": browser_manager.page.url if browser_manager.page else None
                })
            except Exception as e:
                actions_taken.append(f"❌ Failed to scroll: {e}")

        elif action == "press":
            key = params.get("key", "Enter")

            # Broadcast key press status
            await broadcast_update("automation_status", {
                "status": "Pressing...",
                "message": f"Pressing {key}",
                "action": "press",
                "key": key
            })

            try:
                # Handle keyboard shortcuts properly
                if key.lower() in ['p', 'c', 'n', 'i']:  # Single char shortcuts
                    await browser_manager.page.keyboard.press(key.lower())
                else:
                    await browser_manager.press_key(key)
                actions_taken.append(f"⌨️ Pressed {key}")
                await asyncio.sleep(1.5)  # Wait longer for modal to appear

                # Get updated state and broadcast screenshot
                screenshot = await browser_manager.capture_screenshot()
                elements = await browser_manager.get_interactive_elements()

                await broadcast_update("screenshot_update", {
                    "screenshot": screenshot,
                    "url": browser_manager.page.url if browser_manager.page else None
                })
            except Exception as e:
                actions_taken.append(f"❌ Failed to press key: {e}")

        elif action == "navigate":
            url = params.get("url", "")
            if url:
                await broadcast_update("automation_status", {
                    "status": "Navigating...",
                    "message": f"Going to {url}",
                    "action": "navigate"
                })
                try:
                    await browser_manager.navigate(url)
                    actions_taken.append(f"🌐 Navigated to {url}")
                    await asyncio.sleep(1)
                    screenshot = await browser_manager.capture_screenshot()
                    elements = await browser_manager.get_interactive_elements()
                    await broadcast_update("screenshot_update", {
                        "screenshot": screenshot,
                        "url": browser_manager.page.url if browser_manager.page else None
                    })
                except Exception as e:
                    actions_taken.append(f"❌ Navigation failed: {e}")

        elif action == "wait":
            duration = params.get("duration", 2)
            await broadcast_update("automation_status", {
                "status": "Waiting...",
                "message": f"Waiting {duration}s for page to load",
                "action": "wait"
            })
            await asyncio.sleep(min(duration, 5))  # Cap at 5 seconds
            # Refresh state after waiting
            screenshot = await browser_manager.capture_screenshot()
            elements = await browser_manager.get_interactive_elements()
            await broadcast_update("screenshot_update", {
                "screenshot": screenshot,
                "url": browser_manager.page.url if browser_manager.page else None
            })
            actions_taken.append(f"⏳ Waited {duration}s")

        elif action == "ask":
            # Agent wants to ask user a question - we'll include it in response
            question = params.get("question", "What should I do next?")
            actions_taken.append(f"❓ Agent asks: {question}")
            reasoning.append(f"Need clarification: {question}")
            # Don't break - let the response include the question

        elif action in ["search", "analyze", "observe"]:
            # These are thinking/observation actions - agent is analyzing
            # Just continue to next iteration with fresh state
            await broadcast_update("automation_status", {
                "status": "Analyzing...",
                "message": params.get("question", "Analyzing the page"),
                "action": "analyze"
            })
            # Get fresh screenshot and elements
            screenshot, elements = await browser_manager.capture_state_with_overlays()
            actions_taken.append(f"🔍 Analyzed page")
            # Continue to next step with fresh data

        elif action == "finish":
            actions_taken.append(f"✅ Task completed: {params.get('message', 'Done')}")
            await broadcast_update("automation_status", {
                "status": "Complete",
                "message": params.get("message", "Task finished"),
                "action": "done"
            })
            break

        elif action == "fail":
            reason = params.get("reason", "Unknown error")
            actions_taken.append(f"❌ Failed: {reason}")
            await broadcast_update("automation_error", {
                "error": reason,
                "action": "fail"
            })
            break

        else:
            # Unknown action - log it and try to continue
            actions_taken.append(f"❓ Unknown action: {action} - skipping")
            print(f"Warning: Unknown action '{action}' with params {params}")
            # Don't break - try to continue

    # Broadcast automation complete
    await broadcast_update("automation_complete", {
        "status": "Complete",
        "actionsCount": len(actions_taken)
    })

    # Build response
    if actions_taken:
        response_text = "**Actions Performed:**\n\n"
        for action_desc in actions_taken:
            response_text += f"• {action_desc}\n"
    else:
        response_text = "I analyzed the page but couldn't determine what action to take. Please be more specific about what you'd like me to do."

    # Get suggested next actions
    suggested_actions = []
    plan_ahead = decision.get("plan_ahead", [])
    if plan_ahead:
        for step in plan_ahead[:3]:
            suggested_actions.append({
                "label": step,
                "action": "automate",
                "reasoning": "Next suggested step"
            })

    return {
        "response": response_text,
        "citations": [],
        "suggestedActions": suggested_actions,
        "reasoning": reasoning,
        "confidence": decision.get("confidence", 0.7)
    }


@app.post("/api/execute", response_model=Dict[str, Any])
async def execute_action(request: ActionRequest):
    """Execute an action on the browser"""
    if not browser_manager:
        raise HTTPException(status_code=500, detail="Browser not initialized")

    try:
        action = request.action
        params = request.params

        if action == "click":
            element_index = params.get("element_index")
            # Get current elements
            _, elements = await browser_manager.capture_state_with_overlays()

            if element_index is not None and element_index < len(elements):
                coords = elements[element_index].get("rect")
                await browser_manager.click_element(coords=coords)

        elif action == "type":
            text = params.get("text", "")
            await browser_manager.page.keyboard.type(text)

        elif action == "navigate":
            url = params.get("url")
            await browser_manager.navigate(url)

        # Wait for page to update
        await asyncio.sleep(1)

        # Get new state
        screenshot_b64, elements = await browser_manager.capture_state_with_overlays()

        return {
            "success": True,
            "screenshot": screenshot_b64,
            "elementCount": len(elements)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Global WebSocket connections for real-time updates
active_connections: List[WebSocket] = []


async def broadcast_update(update_type: str, data: Dict[str, Any]):
    """Broadcast update to all connected WebSocket clients"""
    message = {"type": update_type, **data}
    disconnected = []

    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception:
            disconnected.append(connection)

    # Clean up disconnected clients
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time browser state updates"""
    await websocket.accept()
    active_connections.append(websocket)
    print(f"WebSocket connected. Total connections: {len(active_connections)}")

    try:
        while True:
            # Wait for message from client (keep-alive or commands)
            data = await websocket.receive_text()

            if data == "ping":
                await websocket.send_json({"type": "pong"})
            elif data == "get_state":
                # Send current browser state on request
                if browser_manager and browser_manager.page:
                    clean_screenshot = await browser_manager.capture_screenshot()
                    await websocket.send_json({
                        "type": "state_update",
                        "screenshot": clean_screenshot,
                        "url": browser_manager.page.url
                    })

    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
        print(f"WebSocket disconnected. Total connections: {len(active_connections)}")


# Serve React frontend (production)
# app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="frontend")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Web Automation Assistant API Server")
    print("="*70)
    print("\nStarting server...")
    print("API: http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print("\nFrontend should be running on: http://localhost:3000")
    print("="*70 + "\n")

    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
