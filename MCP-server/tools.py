#!/usr/bin/env python3
import asyncio
import base64
from pathlib import Path
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.server.stdio import stdio_server
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

async def navigate_web_tool(arguments, page):
    url = arguments["url"]
    timeout_val = arguments.get("timeout", 10)
    try:
        await page.goto(url, timeout=timeout_val * 1000)
        return [TextContent(type="text", text=f"Navigation successful to {url}")]
    except PlaywrightTimeoutError:
        return [TextContent(type="text", text=f"Timeout during navigation to {url}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error during navigation to {url}: {str(e)}")]

async def capture_screenshot_tool(arguments, page):
    full_page = arguments.get("full_page", False)
    project_dir = Path(__file__).parent
    filename = f"screenshot_{int(asyncio.get_event_loop().time())}.png"
    path = f"{project_dir}\\test\\screenshots\\{filename}"
    await page.screenshot(path=path, full_page=full_page)
    
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

async def extract_links_tool(arguments, page):
    filter_val = arguments.get("filter", None)
    links = await page.eval_on_selector_all("a", "els => els.map(e => ({text: e.innerText, href: e.href}))")
    if filter_val:
        links = [l for l in links if filter_val.lower() in l["text"].lower()]
    if not links:
        return [TextContent(type="text", text="No links found with this filter.")]
    return [TextContent(type="text", text="\n".join([f"{l['text']} -> {l['href']}" for l in links[:20]]))]

async def fill_field_tool(arguments, page):
    selector = arguments["selector"]
    value = arguments["value"]
    try:
        await page.fill(selector, value)
        return [TextContent(type="text", text=f"Field {selector} filled with '{value}'")]
    except Exception as e:
        return [TextContent(type="text", text=f"Unable to fill the field {selector}: {str(e)}")]

async def click_element_tool(arguments, page):
    selector = arguments["selector"]
    try:
        await page.click(selector)
        return [TextContent(type="text", text=f"Click performed on {selector}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Unable to click on {selector}: {str(e)}")]

async def retrieve_html_tool(arguments, page):
    html = await page.content()
    return [TextContent(type="text", text=html)]