"""
Tool dispatcher - routes tool calls to implementations
"""

from mcp.types import TextContent
from .web_tools import (
    navigate_web, capture_screen, extract_links, 
    fill_field, click_element, get_html
)
from .scraping_tools import analyze_and_extract_data, save_results, done


# Tool dispatch mapping
WEB_TOOLS = {
    "navigate_web": navigate_web,
    "capture_screen": capture_screen, 
    "extract_links": extract_links,
    "fill_field": fill_field,
    "click_element": click_element,
    "get_html": get_html
}

SCRAPING_TOOLS = {
    "analyze_and_extract_data": analyze_and_extract_data,
    "save_results": save_results,
    "done": done
}

ALL_TOOLS = {**WEB_TOOLS, **SCRAPING_TOOLS}


async def dispatch_tool(name: str, arguments: dict, page=None) -> list[TextContent]:
    """
    Dispatch tool call to appropriate implementation
    
    Args:
        name: Tool name
        arguments: Tool arguments
        page: Playwright page instance (required for web tools)
    
    Returns:
        Tool execution result
    """
    print(f"[MCP] Executing tool: {name}")
    
    if name not in ALL_TOOLS:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    # Web tools require page instance
    if name in WEB_TOOLS and page is None:
        return [TextContent(type="text", text=f"Web tool {name} requires browser page")]
    
    try:
        tool_func = ALL_TOOLS[name]
        return await tool_func(page, arguments)
    except Exception as e:
        print(f"[MCP] Tool execution error: {e}")
        return [TextContent(type="text", text=f"Tool execution failed: {str(e)}")]


def get_web_tool_names() -> set[str]:
    """Get names of tools that require browser"""
    return set(WEB_TOOLS.keys())