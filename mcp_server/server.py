#!/usr/bin/env python3
"""
MCP Server - Modular web automation and scraping server
Clean architecture with separated concerns
"""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from playwright.async_api import async_playwright

from .tools_definitions import get_all_tools
from .tool_dispatcher import dispatch_tool, get_web_tool_names


class WebAutomationServer:
    """MCP Server for web automation and scraping"""
    
    def __init__(self):
        self.app = Server("web-automation-server")
        self.browser = None
        self.page = None
        self.playwright_instance = None
        
        # Register handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register MCP handlers"""
        
        @self.app.list_tools()
        async def list_tools():
            return get_all_tools()
        
        @self.app.call_tool()
        async def call_tool(name: str, arguments: dict):
            return await self._handle_tool_call(name, arguments)
    
    async def _ensure_browser(self):
        """Initialize browser if needed for web tools"""
        if self.browser is None:
            print("[MCP] Starting browser...")
            self.playwright_instance = await async_playwright().start()
            self.browser = await self.playwright_instance.chromium.launch(headless=True)
            self.page = await self.browser.new_page()
            print("[MCP] Browser started successfully")
    
    async def _handle_tool_call(self, name: str, arguments: dict):
        """Handle tool execution with browser management"""
        
        # Initialize browser for web tools
        if name in get_web_tool_names():
            await self._ensure_browser()
        
        # Dispatch to appropriate tool implementation
        return await dispatch_tool(name, arguments, self.page)
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.browser:
            await self.browser.close()
        if self.playwright_instance:
            await self.playwright_instance.stop()
    
    async def run(self):
        """Run the MCP server"""
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.app.run(
                    read_stream, 
                    write_stream, 
                    self.app.create_initialization_options()
                )
        finally:
            await self.cleanup()


async def main():
    """Main entry point"""
    server = WebAutomationServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())