"""
MCP Tools Definitions
Centralized tool schema definitions
"""

from mcp.types import Tool

def get_web_automation_tools() -> list[Tool]:
    """Web automation tools using Playwright"""
    return [
        Tool(
            name="navigate_web",
            description="Navigate to a specific URL with error handling and timeout",
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
            name="capture_screen",
            description="Take a screenshot of the current page",
            inputSchema={
                "type": "object",
                "properties": {
                    "full_page": {"type": "boolean", "description": "Capture full page", "default": False}
                }
            }
        ),
        Tool(
            name="extract_links",
            description="Extract all links from current page with optional text filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter": {"type": "string", "description": "Filter links containing this text (optional)"}
                }
            }
        ),
        Tool(
            name="fill_field",
            description="Fill a field identified by CSS selector",
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
            description="Click on an element identified by CSS selector",
            inputSchema={
                "type": "object",
                "properties": {
                    "selector": {"type": "string", "description": "CSS selector of the element to click"}
                },
                "required": ["selector"]
            }
        ),
        Tool(
            name="get_html",
            description="Get complete HTML content of current page",
            inputSchema={"type": "object"}
        )
    ]

def get_scraping_tools() -> list[Tool]:
    """Data extraction and scraping tools"""
    return [
        Tool(
            name="save_results",
            description="Save extracted data to output file",
            inputSchema={
                "type": "object",
                "properties": {
                    "data": {
                        "type": "object",
                        "description": "Complete scraped data in JSON format"
                    },
                    "output_path": {
                        "type": "string", 
                        "description": "Path to save results"
                    }
                },
                "required": ["data", "output_path"]
            }
        ),
        Tool(
            name="analyze_and_extract_data",
            description="Analyze page structure and extract data in one step (recommended approach)",
            inputSchema={
                "type": "object",
                "required": ["html", "schema_fields"],
                "properties": {
                    "html": {
                        "type": "string",
                        "description": "HTML content to analyze and extract from"
                    },
                    "schema_fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of field names to extract (e.g. ['nom', 'prix'])"
                    },
                    "collection_name": {
                        "type": "string",
                        "description": "Name of the data collection (e.g. 'produits')"
                    },
                    "base_url": {
                        "type": "string",
                        "description": "Base URL for resolving relative links"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path where to save the extracted data"
                    }
                }
            }
        ),
        Tool(
            name="done",
            description="Call this when scraping is complete",
            inputSchema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Optional completion message"
                    }
                }
            }
        )
    ]

def get_all_tools() -> list[Tool]:
    """Get all available tools"""
    return get_web_automation_tools() + get_scraping_tools()