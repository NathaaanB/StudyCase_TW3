"""
Web automation tool implementations using Playwright
"""

import asyncio
import base64
from pathlib import Path
from mcp.types import TextContent, ImageContent
from playwright.async_api import TimeoutError as PlaywrightTimeoutError


async def navigate_web(page, arguments: dict) -> list[TextContent]:
    """Navigate to a URL"""
    url = arguments["url"]
    timeout_val = arguments.get("timeout", 10)
    print(f"[MCP] Navigating to: {url}")
    
    try:
        await page.goto(url, timeout=timeout_val * 1000)
        print(f"[MCP] Successfully navigated to: {url}")
        return [TextContent(type="text", text=f"Successfully navigated to {url}")]
    except PlaywrightTimeoutError:
        print(f"[MCP] Timeout navigating to: {url}")
        return [TextContent(type="text", text=f"Timeout while navigating to {url}")]
    except Exception as e:
        print(f"[MCP] Error navigating to {url}: {str(e)}")
        return [TextContent(type="text", text=f"Error while navigating to {url}: {str(e)}")]


async def capture_screen(page, arguments: dict) -> list[TextContent | ImageContent]:
    """Take a screenshot"""
    full_page = arguments.get("full_page", False)
    print(f"[MCP] Taking screenshot (full_page={full_page})")
    
    project_dir = Path(__file__).parent.parent
    filename = f"screenshot_{int(asyncio.get_event_loop().time())}.png"
    path = f"{project_dir}/test/{filename}"
    
    await page.screenshot(path=path, full_page=full_page)
    print(f"[MCP] Screenshot saved: {path}")
    
    with open(path, "rb") as f:
        img_data = f.read()
        img_base64 = base64.b64encode(img_data).decode("utf-8")
    
    return [
        TextContent(type="text", text=f"Screenshot saved: {path}"),
        ImageContent(
            type="image",
            data=img_base64,
            mimeType="image/png"
        )
    ]


async def extract_links(page, arguments: dict) -> list[TextContent]:
    """Extract links from page"""
    filter_text = arguments.get("filter", None)
    print(f"[MCP] Extracting links (filter={filter_text})")
    
    links = await page.eval_on_selector_all("a", "els => els.map(e => ({text: e.innerText, href: e.href}))")
    if filter_text:
        links = [l for l in links if filter_text.lower() in l["text"].lower()]
    
    print(f"[MCP] Found {len(links)} links")
    
    if not links:
        return [TextContent(type="text", text="No links found with this filter.")]
    
    return [TextContent(type="text", text="\n".join([f"{l['text']} -> {l['href']}" for l in links[:20]]))]


async def fill_field(page, arguments: dict) -> list[TextContent]:
    """Fill a form field"""
    selector = arguments["selector"]
    value = arguments["value"]
    print(f"[MCP] Filling field {selector} with '{value}'")
    
    try:
        await page.fill(selector, value)
        print(f"[MCP] Field filled successfully")
        return [TextContent(type="text", text=f"Field {selector} filled with '{value}'")]
    except Exception as e:
        print(f"[MCP] Failed to fill field: {str(e)}")
        return [TextContent(type="text", text=f"Unable to fill field {selector}: {str(e)}")]


async def click_element(page, arguments: dict) -> list[TextContent]:
    """Click on an element"""
    selector = arguments["selector"]
    print(f"[MCP] Clicking on element: {selector}")
    
    try:
        await page.click(selector)
        print(f"[MCP] Click successful")
        return [TextContent(type="text", text=f"Clicked on {selector}")]
    except Exception as e:
        print(f"[MCP] Click failed: {str(e)}")
        return [TextContent(type="text", text=f"Unable to click on {selector}: {str(e)}")]


async def get_html(page, arguments: dict) -> list[TextContent]:
    """Get HTML content"""
    print(f"[MCP] Retrieving HTML content")
    html = await page.content()
    print(f"[MCP] HTML retrieved ({len(html)} characters)")
    return [TextContent(type="text", text=html)]