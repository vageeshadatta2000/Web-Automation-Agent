import base64
import asyncio
import os
import io
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Page, Browser, BrowserContext, ElementHandle
from PIL import Image, ImageDraw, ImageFont

class BrowserManager:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def start(self):
        """Starts the Playwright browser with a persistent context."""
        # Close existing context if any
        if self.context:
            try:
                await self.context.close()
            except:
                pass

        if self.playwright:
            try:
                await self.playwright.stop()
            except:
                pass

        self.playwright = await async_playwright().start()

        # Use a persistent context to save login session
        user_data_dir = os.path.abspath("user_data")
        os.makedirs(user_data_dir, exist_ok=True)

        # Full browser viewport - like a real Chrome window
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir,
            headless=self.headless,
            channel="chrome",
            viewport={"width": 1920, "height": 1080},  # Full HD viewport
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--window-size=1920,1080",
            ],
            ignore_default_args=["--enable-automation"],
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        self.browser = self.context # Store context as browser for checking if alive

    async def stop(self):
        """Stops the browser."""
        if self.context:
            await self.context.close()
        # Browser is implied in persistent context
        if self.playwright:
            await self.playwright.stop()

    def is_alive(self) -> bool:
        """Check if browser is still alive and connected."""
        try:
            if not self.page or not self.context:
                return False
            # Try to check if page is closed
            return not self.page.is_closed()
        except:
            return False

    async def navigate(self, url: str):
        """Navigates to a URL."""
        if not self.page:
            raise RuntimeError("Browser not started")
        await self.page.goto(url)
        # Notion/Linear are heavy SPAs, networkidle might never happen due to background polling
        # Relaxing to domcontentloaded to avoid timeouts
        await self.page.wait_for_load_state("domcontentloaded")
        await self.wait_for_ui_stability()

    async def wait_for_ui_stability(self):
        """Waits for the UI to settle by checking for common layout elements."""
        if not self.page:
            return
        
        try:
            # Wait for at least one interactive element to appear
            # or specific common containers (nav, main, sidebar)
            await self.page.wait_for_selector("button, a, input, [role='button'], nav, main", timeout=10000)
            # Small extra buffer for animations
            await asyncio.sleep(1)
        except:
            print("Warning: UI stability check timed out, proceeding anyway...")

    async def get_screenshot_base64(self) -> str:
        """Captures a screenshot and returns it as a base64 string."""
        if not self.page:
            raise RuntimeError("Browser not started")
        # Switch to PNG to resolve API error
        screenshot_bytes = await self.page.screenshot(type="png")
        return base64.b64encode(screenshot_bytes).decode("utf-8")

    async def get_accessibility_tree(self, max_depth: int = 3) -> str:
        """
        Get a simplified accessibility tree representation of the page.
        This is much more token-efficient than screenshots for LLM reasoning.
        Based on Playwright MCP's snapshot approach.
        """
        if not self.page:
            raise RuntimeError("Browser not started")

        try:
            # Get accessibility snapshot from Playwright
            snapshot = await self.page.accessibility.snapshot()

            if not snapshot:
                return "No accessibility tree available"

            def format_node(node, depth=0, max_depth=3):
                if depth > max_depth:
                    return ""

                indent = "  " * depth
                role = node.get("role", "")
                name = node.get("name", "")
                value = node.get("value", "")

                # Skip generic/container roles
                skip_roles = {"generic", "none", "presentation", "group"}
                if role in skip_roles and not name:
                    # Still process children
                    children = node.get("children", [])
                    return "\n".join(format_node(c, depth, max_depth) for c in children)

                # Build node representation
                parts = []
                if role:
                    parts.append(f"[{role}]")
                if name:
                    parts.append(f'"{name[:50]}"')
                if value:
                    parts.append(f"value={value[:30]}")

                # Add useful properties
                if node.get("focused"):
                    parts.append("(focused)")
                if node.get("disabled"):
                    parts.append("(disabled)")

                result = indent + " ".join(parts) if parts else ""

                # Process children
                children = node.get("children", [])
                child_results = [format_node(c, depth + 1, max_depth) for c in children]
                child_str = "\n".join(r for r in child_results if r)

                if result and child_str:
                    return result + "\n" + child_str
                return result or child_str

            tree_str = format_node(snapshot, 0, max_depth)

            # Limit total size to save tokens
            if len(tree_str) > 4000:
                tree_str = tree_str[:4000] + "\n... (truncated)"

            return tree_str

        except Exception as e:
            print(f"Error getting accessibility tree: {e}")
            return f"Error: {e}"

    async def get_interactive_elements(self) -> List[Dict[str, Any]]:
        """
        Scans the page (including frames and shadow DOM) for interactive elements.
        """
        if not self.page:
            raise RuntimeError("Browser not started")

        # Complex script to traverse frames and shadow roots
        elements = await self.page.evaluate("""async () => {
            const items = [];
            // Broad selector for modern apps
            const selector = 'button, a, input, textarea, select, [role="button"], [role="link"], [role="checkbox"], [role="menuitem"], [role="menuitemcheckbox"], [role="option"], [role="tab"], [role="treeitem"], [tabindex], li, div[onclick], span[onclick], svg';

            function isVisible(el) {
                const rect = el.getBoundingClientRect();
                const style = window.getComputedStyle(el);
                return rect.width > 5 && rect.height > 5 && style.visibility !== 'hidden' && style.display !== 'none' && style.opacity !== '0';
            }

            function processElement(el) {
                if (isVisible(el)) {
                    let text = el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('title') || '';
                    if (!text && el.tagName.toLowerCase() === 'svg') {
                         text = el.getAttribute('aria-label') || 'icon';
                    }
                    text = (text || "").replace(/\\s+/g, ' ').trim();
                    
                    // Heuristic: if it has text or is an input/button/link, keep it
                    if (text || ['input', 'textarea', 'select', 'button', 'a'].includes(el.tagName.toLowerCase()) || el.getAttribute('role')) {
                        const rect = el.getBoundingClientRect();
                        items.push({
                            index: items.length,
                            tagName: el.tagName.toLowerCase(),
                            text: text.substring(0, 50),
                            id: el.id,
                            placeholder: el.getAttribute('placeholder'),
                            type: el.getAttribute('type'),
                            ariaLabel: el.getAttribute('aria-label'),
                            role: el.getAttribute('role'),
                            rect: {x: rect.x, y: rect.y, width: rect.width, height: rect.height}
                        });
                    }
                }
            }

            // 1. Standard Query (Fast)
            document.querySelectorAll(selector).forEach(el => processElement(el));

            // 2. Shadow DOM Traversal (Deep)
            function traverse(root) {
                // Only traverse if we haven't found much, or just do it anyway? 
                // Let's just look for shadow roots specifically.
                const allEls = root.querySelectorAll('*');
                allEls.forEach(el => {
                    if (el.shadowRoot) {
                        el.shadowRoot.querySelectorAll(selector).forEach(shadowEl => processElement(shadowEl));
                        traverse(el.shadowRoot);
                    }
                });
            }
            traverse(document);
            
            return items;
        }""")
        
        # Also scan frames (Playwright handles this better from Python side usually, but let's try simple first)
        # Note: Cross-origin frames might block access, but for same-origin (Notion) it should work.
        
        print(f"Found {len(elements)} interactive elements.")
        return elements

    async def capture_screenshot(self, compress: bool = False, max_dimension: int = 1280) -> str:
        """
        Captures a clean screenshot without overlays for user display.
        Returns base64 encoded PNG.

        Args:
            compress: If True, compress the image to reduce size for LLM
            max_dimension: Maximum width/height when compressing
        """
        if not self.page:
            raise RuntimeError("Browser not started")

        screenshot_bytes = await self.page.screenshot(type="png")

        if compress:
            # Compress for LLM to reduce tokens
            image = Image.open(io.BytesIO(screenshot_bytes))

            # Resize if too large
            if max(image.size) > max_dimension:
                ratio = max_dimension / max(image.size)
                new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                image = image.resize(new_size, Image.LANCZOS)

            # Convert to JPEG with quality reduction for smaller size
            buffered = io.BytesIO()
            image.save(buffered, format="JPEG", quality=70, optimize=True)
            return base64.b64encode(buffered.getvalue()).decode('utf-8')

        return base64.b64encode(screenshot_bytes).decode('utf-8')

    async def capture_screenshot_with_cursor(self, x: float, y: float) -> str:
        """
        Captures screenshot with a blue cursor dot drawn at the specified position.
        Used to show where the agent is about to click.
        """
        if not self.page:
            raise RuntimeError("Browser not started")

        # Show cursor on page
        await self._show_visual_cursor(x, y, "blue")
        await asyncio.sleep(0.1)  # Brief pause to ensure cursor is rendered

        # Capture screenshot with cursor visible
        screenshot_bytes = await self.page.screenshot(type="png")
        return base64.b64encode(screenshot_bytes).decode('utf-8')

    async def capture_state_with_overlays(self, compress_for_llm: bool = True) -> (str, List[Dict[str, Any]]):
        """
        Captures screenshot and elements, then draws Set-of-Mark overlays (boxes + IDs).
        Returns (annotated_screenshot_base64, interactive_elements).
        This is used internally by the vision agent, NOT for user display.

        Args:
            compress_for_llm: If True, compress the output image to reduce LLM token usage
        """
        if not self.page:
            raise RuntimeError("Browser not started")

        # 1. Get elements and raw screenshot
        all_elements = await self.get_interactive_elements()
        screenshot_bytes = await self.page.screenshot(type="png")

        # 2. Filter to only visible, drawable elements to ensure index sync
        # This is CRITICAL: only elements that will be drawn get indices
        visible_elements = []
        for el in all_elements:
            rect = el['rect']
            x, y, w, h = rect['x'], rect['y'], rect['width'], rect['height']
            # Must be on-screen and have reasonable size
            if x >= 0 and y >= 0 and w > 5 and h > 5:
                visible_elements.append(el)

        # 3. Remove highly overlapping boxes (OmniParser approach: 90% IoU threshold)
        # This prevents parent/child elements from both being drawn
        def compute_iou(rect1, rect2):
            """Compute Intersection over Union between two rectangles."""
            x1, y1, w1, h1 = rect1['x'], rect1['y'], rect1['width'], rect1['height']
            x2, y2, w2, h2 = rect2['x'], rect2['y'], rect2['width'], rect2['height']

            # Intersection
            xi1 = max(x1, x2)
            yi1 = max(y1, y2)
            xi2 = min(x1 + w1, x2 + w2)
            yi2 = min(y1 + h1, y2 + h2)

            if xi2 <= xi1 or yi2 <= yi1:
                return 0.0

            inter_area = (xi2 - xi1) * (yi2 - yi1)

            # Union
            area1 = w1 * h1
            area2 = w2 * h2
            union_area = area1 + area2 - inter_area

            return inter_area / union_area if union_area > 0 else 0.0

        def compute_containment(rect1, rect2):
            """Check how much rect1 is contained within rect2."""
            x1, y1, w1, h1 = rect1['x'], rect1['y'], rect1['width'], rect1['height']
            x2, y2, w2, h2 = rect2['x'], rect2['y'], rect2['width'], rect2['height']

            # Intersection
            xi1 = max(x1, x2)
            yi1 = max(y1, y2)
            xi2 = min(x1 + w1, x2 + w2)
            yi2 = min(y1 + h1, y2 + h2)

            if xi2 <= xi1 or yi2 <= yi1:
                return 0.0

            inter_area = (xi2 - xi1) * (yi2 - yi1)
            area1 = w1 * h1

            return inter_area / area1 if area1 > 0 else 0.0

        # Sort by area (smaller elements first - prefer more specific elements)
        visible_elements.sort(key=lambda el: el['rect']['width'] * el['rect']['height'])

        # Filter out elements with high overlap
        filtered_elements = []
        for el in visible_elements:
            should_keep = True
            el_area = el['rect']['width'] * el['rect']['height']

            # Always keep input/textarea elements - they're critical for typing
            is_input = el.get('tagName') in ['input', 'textarea'] or el.get('role') in ['textbox', 'searchbox']

            for kept_el in filtered_elements:
                iou = compute_iou(el['rect'], kept_el['rect'])
                containment = compute_containment(el['rect'], kept_el['rect'])

                # Remove if >90% IoU (OmniParser threshold) or almost fully contained
                # BUT always keep inputs even if contained
                if (iou > 0.9 or containment > 0.95) and not is_input:
                    should_keep = False
                    break

            if should_keep:
                # Skip very large elements (likely containers) unless they're inputs
                # Threshold: 30% of viewport (1280x720 = 921600, 30% = ~276000)
                if el_area > 250000 and not is_input:
                    continue
                filtered_elements.append(el)

        visible_elements = filtered_elements

        # Re-index elements to match visual labels
        for i, el in enumerate(visible_elements):
            el['index'] = i

        # 3. Open image with PIL
        image = Image.open(io.BytesIO(screenshot_bytes))
        draw = ImageDraw.Draw(image)

        # Load a font (try default, fallback to simple)
        try:
            font = ImageFont.truetype("Arial.ttf", 14)
        except:
            font = ImageFont.load_default()

        # 4. Draw overlays - now indices match exactly
        for i, el in enumerate(visible_elements):
            rect = el['rect']
            x, y, w, h = rect['x'], rect['y'], rect['width'], rect['height']

            # Draw bounding box (Red)
            draw.rectangle([x, y, x + w, y + h], outline="red", width=2)

            # Draw ID tag (Red background, White text)
            tag_text = str(i)

            # Calculate text size using getbbox
            text_bbox = font.getbbox(tag_text)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]

            tag_w = text_width + 6
            tag_h = text_height + 6

            # Position tag at top-left of box, but keep inside image
            tag_x = x
            tag_y = y - tag_h if y > tag_h else y

            draw.rectangle([tag_x, tag_y, tag_x + tag_w, tag_y + tag_h], fill="red")
            draw.text((tag_x + 3, tag_y + 3), tag_text, fill="white", font=font)

        # 5. Compress for LLM if requested (reduces tokens significantly)
        buffered = io.BytesIO()
        if compress_for_llm:
            # Resize to max 800px and use JPEG with lower quality for smaller size
            # This significantly reduces tokens while maintaining readability
            max_dim = 800
            if max(image.size) > max_dim:
                ratio = max_dim / max(image.size)
                new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                image = image.resize(new_size, Image.LANCZOS)
            image.save(buffered, format="JPEG", quality=60, optimize=True)
        else:
            image.save(buffered, format="PNG")

        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        print(f"Labeled {len(visible_elements)} elements (filtered from {len(all_elements)} detected, removed overlaps via IoU).")

        return img_str, visible_elements

    async def highlight_element(self, selector: str):
        """Highlights an element for visual debugging."""
        if not self.page:
            return
        try:
            await self.page.eval_on_selector(selector, "el => el.style.border = '2px solid red'")
        except:
            pass

    async def _show_visual_cursor(self, x: float, y: float, color: str = "blue"):
        """Injects a visual cursor (colored dot) at the coordinates."""
        if not self.page:
            return

        # Color presets
        colors = {
            "blue": ("rgba(59, 130, 246, 0.9)", "rgba(59, 130, 246, 0.4)"),
            "red": ("rgba(255, 0, 0, 0.7)", "rgba(255, 0, 0, 0.5)"),
            "green": ("rgba(34, 197, 94, 0.9)", "rgba(34, 197, 94, 0.4)")
        }
        bg_color, shadow_color = colors.get(color, colors["blue"])

        await self.page.evaluate(f"""
            () => {{
                // Remove any existing cursor first
                const existingCursor = document.getElementById('agent-cursor');
                if (existingCursor) existingCursor.remove();

                const cursor = document.createElement('div');
                cursor.id = 'agent-cursor';
                cursor.style.position = 'fixed';
                cursor.style.left = '{x}px';
                cursor.style.top = '{y}px';
                cursor.style.width = '24px';
                cursor.style.height = '24px';
                cursor.style.backgroundColor = '{bg_color}';
                cursor.style.borderRadius = '50%';
                cursor.style.pointerEvents = 'none';
                cursor.style.zIndex = '99999';
                cursor.style.transform = 'translate(-50%, -50%)';
                cursor.style.boxShadow = '0 0 20px {shadow_color}, 0 0 40px {shadow_color}';
                cursor.style.border = '3px solid white';
                cursor.style.animation = 'pulse-cursor 1s ease-in-out infinite';

                // Add pulse animation
                const style = document.createElement('style');
                style.textContent = `
                    @keyframes pulse-cursor {{
                        0%, 100% {{ transform: translate(-50%, -50%) scale(1); opacity: 0.9; }}
                        50% {{ transform: translate(-50%, -50%) scale(1.2); opacity: 1; }}
                    }}
                `;
                document.head.appendChild(style);
                document.body.appendChild(cursor);

                // Remove after action completes
                setTimeout(() => cursor.remove(), 2000);
            }}
        """)

    async def click_element(self, text_content: str = None, selector: str = None, coords: Dict[str, float] = None):
        """Clicks an element. Prioritizes coordinates (SoM) if available.
        Returns screenshot with cursor if coords provided, else None."""
        if not self.page:
            raise RuntimeError("Browser not started")

        # 1. Priority: Coordinate Click (Visual Grounding / Set-of-Mark)
        # If the agent provided an index/coords, it chose a specific red box on the screenshot.
        # We trust this exact position over a potentially generic selector like "button".
        if coords:
            print(f"Executing SoM Click at {coords}...")
            try:
                x = coords["x"] + coords["width"] / 2
                y = coords["y"] + coords["height"] / 2

                await self._show_visual_cursor(x, y)
                await asyncio.sleep(0.2) # Brief pause to show cursor

                # Capture screenshot with cursor visible before clicking
                cursor_screenshot = await self.page.screenshot(type="png")

                await self.page.mouse.click(x, y)
                await asyncio.sleep(0.5) # Wait for UI response
                await self.page.wait_for_load_state("domcontentloaded")
                return cursor_screenshot
            except Exception as e:
                print(f"Coordinate click failed: {e}. Falling back to selector...")

        # 2. Fallback: Selector/Text Click
        locator = None
        if selector:
            locator = self.page.locator(selector).first
        elif text_content:
            locator = self.page.get_by_text(text_content).first
        
        if locator:
            try:
                # Wait for element to be attached and visible
                await locator.wait_for(state="visible", timeout=3000)
                
                # Highlight
                await locator.evaluate("el => el.style.outline = '3px solid red'")
                
                # Get position for cursor
                box = await locator.bounding_box()
                if box:
                    center_x = box["x"] + box["width"] / 2
                    center_y = box["y"] + box["height"] / 2
                    await self._show_visual_cursor(center_x, center_y)
                
                await asyncio.sleep(0.5)
                await locator.click()
                await self.page.wait_for_load_state("domcontentloaded")
                return
            except Exception as e:
                print(f"Locator click failed: {e}")
        
        raise ValueError("Could not click: No valid coordinates or selector worked.")

    async def type_text(self, text: str, selector: str = None):
        """Types text into an input with visual feedback."""
        if not self.page:
            raise RuntimeError("Browser not started")

        locator = None
        if selector:
            locator = self.page.locator(selector).first

        if locator:
            try:
                # Wait for element
                await locator.wait_for(state="visible", timeout=5000)

                # Highlight (Blue for typing)
                await locator.evaluate("el => el.style.outline = '3px solid blue'")

                # Visual cursor
                box = await locator.bounding_box()
                if box:
                    center_x = box["x"] + box["width"] / 2
                    center_y = box["y"] + box["height"] / 2
                    await self._show_visual_cursor(center_x, center_y)

                await asyncio.sleep(0.5)

                # Try fill first, then fallback to keyboard type for contenteditable
                try:
                    await locator.fill(text)
                except Exception as fill_error:
                    print(f"Fill failed (likely contenteditable): {fill_error}")
                    print("Using keyboard.type() instead...")
                    # Clear existing content and type
                    await locator.click()
                    await self.page.keyboard.press("Control+a")
                    await self.page.keyboard.type(text)
            except Exception as e:
                print(f"Type failed: {e}")
                print("Attempting blind typing (assuming focus)...")
                await self.page.keyboard.type(text)
        else:
            # Blind type - element should already be focused from click
            print("No selector provided, typing with keyboard...")
            await self.page.keyboard.type(text)

    async def press_key(self, key: str):
        if not self.page:
            raise RuntimeError("Browser not started")
        await self.page.keyboard.press(key)
        await self.page.wait_for_load_state("networkidle")

    async def scroll(self, direction: str = "down", amount: int = 500):
        """Scrolls the page."""
        if not self.page:
            raise RuntimeError("Browser not started")
        
        if direction == "down":
            await self.page.mouse.wheel(0, amount)
        elif direction == "up":
            await self.page.mouse.wheel(0, -amount)
        
        await asyncio.sleep(1) # Wait for scroll animation
