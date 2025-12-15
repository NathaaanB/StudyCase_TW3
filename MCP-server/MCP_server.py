#!/usr/bin/env python3
import asyncio
import base64
from pathlib import Path
from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.server.stdio import stdio_server
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from tools import navigate_web_tool, capture_screenshot_tool, extract_links_tool, fill_field_tool, click_element_tool, retrieve_html_tool

# Création du serveur MCP
app = Server("serveur-web-automation")

# Une page globale pour la session (simplification pour démonstration)
browser = None
page = None

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="navigate_web",
            description="Navigate to a specified URL with error handling and timeout",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to visit"},
                    "timeout": {"type": "number", "description": "Timeout in seconds (optional, default 10s)"}
                },
                "required": ["url"]
            }
        ),
        Tool(
            name="capture_screenshot",
            description="Take a screenshot of the current page",
            inputSchema={
                "type": "object",
                "properties": {
                    "full_page": {"type": "boolean", "description": "Capture the entire page", "default": False}
                }
            }
        ),
        Tool(
            name="extract_links",
            description="Extract all links from the current page, with optional text filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter": {"type": "string", "description": "Filter links containing this text (optional)"}
                }
            }
        ),
        Tool(
            name="fill_field",
            description="Fill a field identified by a CSS selector",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the element"},
                    "value": {"type": "string", "description": "Value to fill"}
                },
                "required": ["selector", "value"]
            }
        ),
        Tool(
            name="click_element",
            description="Click on an element identified by a CSS selector",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the element to click"}
                },
                "required": ["selector"]
            }
        ),
        Tool(
            name="retrieve_html",
            description="Retrieve the complete HTML code of the current page",
            inputSchema={"type": "object"}
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    global browser, page

    if browser is None:
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()

    try:
        if name == "navigate_web":
            return await navigate_web_tool(arguments, page)

        elif name == "capture_screenshot":
            return await capture_screenshot_tool(arguments, page)

        elif name == "extract_links":
            return await extract_links_tool(arguments, page)
        
        elif name == "fill_field":
            return await fill_field_tool(arguments, page)

        elif name == "click_element":
            return await click_element_tool(arguments, page)

        elif name == "retrieve_html":
            return await retrieve_html_tool(arguments, page)

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Unexpected error: {str(e)}")]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())