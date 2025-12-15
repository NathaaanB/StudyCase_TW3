#!/usr/bin/env python3
"""
scraper_agent_autonomous.py

Fully autonomous web scraping agent using MCP architecture.
The LLM has COMPLETE control - NO hardcoded workflow, NO fallbacks.

Architecture:
- LiteLLM: Multi-model support (OpenAI, Gemini, Claude, OpenRouter)
- MCP Integration: Dynamic tool discovery from MCP_server.py
- Pure LLM Orchestration: Agent decides ALL steps autonomously
- External Prompts: prompts_autonomous_scraper.py for easy customization
- Zero Hardcoded Logic: No predefined workflow, no fallback selectors

The LLM analyzes the target schema, devises a complete strategy,
uses MCP tools to navigate/extract/click, and adapts to obstacles.

Usage:
    python scraper_agent_autonomous.py --config schema.json --output results.json
"""

import asyncio
import json
import sys
import argparse
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import litellm

# MCP Integration
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# External prompts system
from prompts_autonomous_scraper_new import get_autonomous_scraper_system_prompt

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# =============================================================================
# MCP INTEGRATION (from agent_mcp.py)
# =============================================================================

_mcp_sessions = {}
_mcp_contexts = {}
_mcp_tools_cache = []


async def initialize_mcp_servers(server_path: str = "./MCP_server.py"):
    """
    Initialize MCP web automation server and discover tools.
    
    Args:
        server_path: Path to MCP server script
        
    Returns:
        List of available tools in OpenAI format
    """
    global _mcp_sessions, _mcp_contexts, _mcp_tools_cache
    
    if _mcp_sessions and _mcp_tools_cache:
        logging.info("[MCP] ♻️  Reusing existing session")
        return _mcp_tools_cache.copy()
    
    logging.info(f"[MCP] Initializing server: {server_path}")
    
    # Resolve absolute path
    from pathlib import Path
    abs_server_path = str(Path(server_path).resolve())
    
    if not Path(abs_server_path).exists():
        logging.error(f"[MCP] ✗ Server file not found: {abs_server_path}")
        return []
    
    logging.info(f"[MCP] Server absolute path: {abs_server_path}")
    
    try:
        # Create server parameters
        server_params = StdioServerParameters(
            command="python",
            args=[abs_server_path]
        )
        
        # Connect to server
        client_context = stdio_client(server_params)
        read_stream, write_stream = await client_context.__aenter__()
        
        # Create session
        session_context = ClientSession(read_stream, write_stream)
        session = await session_context.__aenter__()
        
        # Store contexts for cleanup
        _mcp_contexts["web_automation"] = (client_context, session_context)
        _mcp_sessions["web_automation"] = session
        
        # Initialize session
        await session.initialize()
        
        # Discover tools
        tools_response = await session.list_tools()
        tools = tools_response.tools if hasattr(tools_response, 'tools') else []
        
        # Convert to OpenAI format
        all_tools = []
        for tool in tools:
            tool_dict = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                },
                "_mcp_server": "web_automation"
            }
            all_tools.append(tool_dict)
        
        logging.info(f"[MCP] ✓ Discovered {len(tools)} tools")
        for tool in tools:
            logging.info(f"   - {tool.name}")
        
        _mcp_tools_cache = all_tools
        return all_tools
        
    except Exception as e:
        logging.error(f"[MCP] ✗ Server initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return []


async def execute_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Execute an MCP tool.
    
    Args:
        tool_name: Tool to execute
        arguments: Tool arguments
        
    Returns:
        Tool execution result
    """
    session = _mcp_sessions.get("web_automation")
    if not session:
        raise RuntimeError("MCP session not initialized")
    
    try:
        result = await session.call_tool(tool_name, arguments=arguments)
        
        # Extract result
        if hasattr(result, 'content') and result.content:
            content = result.content[0]
            if hasattr(content, 'text'):
                try:
                    return json.loads(content.text)
                except:
                    return content.text
            return content
        return result
        
    except Exception as e:
        error_msg = f"Tool execution failed: {str(e)}"
        logging.error(f"[MCP] ✗ {error_msg}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": error_msg}


async def cleanup_mcp_sessions():
    """Cleanup MCP sessions."""
    global _mcp_sessions, _mcp_contexts, _mcp_tools_cache
    
    from contextlib import suppress
    
    for server_name, (client_ctx, session_ctx) in _mcp_contexts.items():
        try:
            async with asyncio.timeout(2.0):
                with suppress(asyncio.CancelledError, RuntimeError):
                    await session_ctx.__aexit__(None, None, None)
                with suppress(asyncio.CancelledError, RuntimeError):
                    await client_ctx.__aexit__(None, None, None)
            logging.info(f"[MCP] ✓ Cleaned up {server_name}")
        except asyncio.TimeoutError:
            logging.warning(f"[MCP] ⚠ Timeout cleaning {server_name}")
        except Exception as e:
            logging.warning(f"[MCP] ⚠ Error cleaning {server_name}: {e}")
    
    _mcp_sessions.clear()
    _mcp_contexts.clear()
    _mcp_tools_cache.clear()


# =============================================================================
# PROMPT GENERATION (uses external prompts system)
# =============================================================================

def generate_scraping_prompt(config: Dict[str, Any], url: str) -> str:
    """
    Generate system prompt for autonomous scraping.
    Uses external prompts from prompts_autonomous_scraper.py
    
    Args:
        config: Full configuration including schema, options, etc.
        url: URL to scrape
        
    Returns:
        Complete system prompt
    """
    return get_autonomous_scraper_system_prompt(config, url)


# =============================================================================
# CUSTOM TOOLS FOR SCRAPING
# =============================================================================

def get_custom_scraping_tools() -> List[Dict[str, Any]]:
    """
    Define custom tools for scraping workflow.
    These complement the MCP tools.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": "extract_data_from_html",
                "description": "Extract structured data from HTML using CSS selectors. Returns list of extracted items.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "html": {
                            "type": "string",
                            "description": "HTML content to parse"
                        },
                        "container_selector": {
                            "type": "string",
                            "description": "CSS selector for item containers (e.g., 'article.product_pod')"
                        },
                        "field_selectors": {
                            "type": "object",
                            "description": "Map of field names to CSS selectors (e.g., {'nom': 'h3 a', 'prix': '.price_color'})"
                        },
                        "base_url": {
                            "type": "string",
                            "description": "Base URL for making relative URLs absolute (optional)"
                        }
                    },
                    "required": ["html", "container_selector", "field_selectors"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "save_results",
                "description": "Save extracted data to output file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "data": {
                            "type": "object",
                            "description": "Complete scraped data in JSON format"
                        }
                    },
                    "required": ["data"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "done",
                "description": "Call this when scraping is complete",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]


# =============================================================================
# AGENT EXECUTION
# =============================================================================

async def run_autonomous_scraper(
    config_path: str,
    output_path: str,
    model: str,
    server_path: str = "./MCP_server.py"
) -> Dict[str, Any]:
    """
    Run the autonomous scraping agent.
    
    Args:
        config_path: Path to schema configuration JSON
        output_path: Path to save results
        model: LLM model to use
        server_path: Path to MCP server
        
    Returns:
        Dict with status and results
    """
    logging.info("="*60)
    logging.info("🤖 AUTONOMOUS SCRAPING AGENT STARTED")
    logging.info("="*60)
    
    # Load configuration
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    url = config.get("url")
    schema = config.get("schema", {})
    options = config.get("options", {})
    max_pages = options.get("max_pages")
    
    logging.info(f"📖 Target URL: {url}")
    logging.info(f"🤖 Model: {model}")
    if max_pages:
        logging.info(f"📄 Max pages: {max_pages}")
    
    # Initialize MCP server
    mcp_tools = await initialize_mcp_servers(server_path)
    if not mcp_tools:
        raise RuntimeError("Failed to initialize MCP server")
    
    # Add custom tools
    custom_tools = get_custom_scraping_tools()
    all_tools = mcp_tools + custom_tools
    
    logging.info(f"📋 Total tools available: {len(all_tools)}")
    
    # Generate system prompt (pass full config)
    system_prompt = generate_scraping_prompt(config, url)
    
    # Build user message with max_pages reminder if applicable
    user_message = f"Please scrape data from {url} according to the schema. Devise your strategy and execute it step by step."
    if max_pages:
        user_message += f"\n\n⚠️ IMPORTANT: Stop after scraping {max_pages} page(s). Do not scrape more than {max_pages} page(s)."
    
    user_message += "\n\n🚨 CRITICAL INSTRUCTION: After you analyze the HTML and find selectors, you MUST immediately call extract_data_from_html tool. Do NOT just say 'I will extract' - actually call the tool! Every iteration must end with a tool call."
    
    # Initialize conversation
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    # Agent loop
    max_iterations = 50
    iteration = 0
    scraped_data = None
    
    while iteration < max_iterations:
        iteration += 1
        logging.info(f"\n{'='*60}")
        logging.info(f"ITERATION {iteration}")
        logging.info(f"{'='*60}")
        
        try:
            # Call LLM with tool_choice="required" to force action
            # This prevents the LLM from just planning without executing
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                tools=all_tools,
                tool_choice="required",  # Force LLM to always call a tool
                temperature=0.2,  # Lower temperature for precise scraping
                max_tokens=2000  # Limit output tokens to avoid budget issues
            )
            
            assistant_message = response.choices[0].message
            
            # Log thinking
            if assistant_message.content:
                logging.info(f"\n🤔 Agent reasoning:")
                logging.info(assistant_message.content)
            
            # Check for tool calls
            tool_calls = assistant_message.tool_calls if hasattr(assistant_message, 'tool_calls') else None
            
            if not tool_calls:
                logging.info("\n💭 Agent finished without tool call")
                break
            
            # Add assistant message to history
            messages.append({
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [tc.model_dump() for tc in tool_calls]
            })
            
            # Execute tools
            task_done = False
            for tool_call in tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                
                logging.info(f"\n🔧 Executing: {tool_name}")
                logging.info(f"   Arguments: {json.dumps(tool_args, indent=2)}")
                
                # Execute tool
                if tool_name == "done":
                    task_done = True
                    result = {"status": "completed"}
                    
                elif tool_name == "save_results":
                    # Save results to file
                    scraped_data = tool_args.get("data", {})
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(scraped_data, f, indent=2, ensure_ascii=False)
                    result = {"status": "saved", "path": output_path}
                    logging.info(f"💾 Results saved to {output_path}")
                
                elif tool_name == "extract_data_from_html":
                    # Extract data from HTML using BeautifulSoup
                    html_content = tool_args.get("html", "")
                    container_selector = tool_args.get("container_selector", "")
                    field_selectors = tool_args.get("field_selectors", {})
                    base_url = tool_args.get("base_url", "")
                    
                    try:
                        soup = BeautifulSoup(html_content, 'html.parser')
                        containers = soup.select(container_selector)
                        
                        extracted_items = []
                        for container in containers:
                            item = {}
                            for field_name, selector in field_selectors.items():
                                # Handle nested fields (e.g., "specifications.rating")
                                if '.' in field_name:
                                    parts = field_name.split('.')
                                    if parts[0] not in item:
                                        item[parts[0]] = {}
                                    
                                    elem = container.select_one(selector)
                                    if elem:
                                        # Try text content first
                                        text = elem.get_text(strip=True)
                                        if not text:
                                            # Check for class attribute (star-rating case)
                                            classes = elem.get('class', [])
                                            if isinstance(classes, list) and len(classes) > 1:
                                                text = classes[-1]
                                        
                                        # Check for href or src attributes
                                        if not text:
                                            text = elem.get('href', '') or elem.get('src', '')
                                            if text and base_url:
                                                text = urljoin(base_url, text)
                                        
                                        item[parts[0]][parts[1]] = text
                                    else:
                                        item[parts[0]][parts[1]] = ""
                                else:
                                    elem = container.select_one(selector)
                                    if elem:
                                        # Check if we need href, src, or text
                                        if 'link' in field_name.lower() or 'url' in field_name.lower() or 'href' in field_name.lower():
                                            value = elem.get('href', '') or elem.get('src', '')
                                            if value and base_url:
                                                value = urljoin(base_url, value)
                                        elif 'image' in field_name.lower() or 'img' in field_name.lower():
                                            value = elem.get('src', '') or elem.get('data-src', '')
                                            if value and base_url:
                                                value = urljoin(base_url, value)
                                        else:
                                            value = elem.get_text(strip=True)
                                            
                                            # Try to parse numbers
                                            if value:
                                                # Extract numbers from strings like "£51.77"
                                                number_match = re.search(r'[\d,\.]+', value.replace(' ', ''))
                                                if number_match and ('prix' in field_name.lower() or 'price' in field_name.lower()):
                                                    try:
                                                        value = float(number_match.group().replace(',', '.'))
                                                    except:
                                                        pass
                                        
                                        item[field_name] = value
                                    else:
                                        item[field_name] = ""
                            
                            if item:
                                extracted_items.append(item)
                        
                        result = {
                            "status": "success",
                            "items": extracted_items,
                            "count": len(extracted_items)
                        }
                        logging.info(f"✅ Extracted {len(extracted_items)} items")
                        
                    except Exception as e:
                        result = {"status": "error", "error": str(e)}
                        logging.error(f"❌ Extraction error: {e}")
                    
                else:
                    # Execute MCP tool
                    result = await execute_mcp_tool(tool_name, tool_args)
                
                logging.info(f"   Result: {str(result)[:200]}...")
                
                # Truncate large results to avoid token overflow
                # HTML responses can be massive - we only need confirmation
                result_to_send = result
                if isinstance(result, str) and len(result) > 5000:
                    result_to_send = result[:5000] + "...[truncated]"
                elif isinstance(result, dict):
                    # If result contains HTML, truncate it
                    if 'html' in str(result).lower() or any(len(str(v)) > 5000 for v in result.values() if isinstance(v, str)):
                        result_to_send = {
                            "status": result.get("status", "success"),
                            "summary": f"HTML retrieved ({len(str(result))} chars)" if "<!DOCTYPE" in str(result) else str(result)[:500]
                        }
                        if "items" in result:
                            result_to_send["items"] = result["items"][:3] + [{"...": "truncated"}] if len(result["items"]) > 3 else result["items"]
                            result_to_send["count"] = result.get("count", len(result["items"]))
                
                # Add result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result_to_send)
                })
            
            if task_done:
                logging.info("\n✅ Agent completed the task")
                break
                
        except Exception as e:
            logging.error(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            break
    
    # Cleanup
    await cleanup_mcp_sessions()
    
    logging.info("\n" + "="*60)
    logging.info("🏁 SCRAPING COMPLETED")
    logging.info("="*60)
    
    if scraped_data:
        product_count = len(scraped_data.get("produits", []))
        logging.info(f"📊 Products extracted: {product_count}")
        logging.info(f"💾 Output: {output_path}")
    
    return {
        "status": "success" if scraped_data else "incomplete",
        "data": scraped_data,
        "iterations": iteration
    }


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Autonomous Web Scraping Agent")
    parser.add_argument("--config", required=True, help="Path to schema configuration JSON")
    parser.add_argument("--output", required=True, help="Path to save results JSON")
    parser.add_argument("--model", default=os.getenv("SCRAPER_LLM_MODEL", "openrouter/google/gemini-2.5-flash-lite"), help="LLM model to use")
    
    # Default server path relative to this script's location
    script_dir = Path(__file__).parent
    default_server = str(script_dir.parent / "MCP-server" / "MCP_server.py")
    parser.add_argument("--server", default=default_server, help="Path to MCP server script")
    
    args = parser.parse_args()
    
    try:
        result = await run_autonomous_scraper(
            config_path=args.config,
            output_path=args.output,
            model=args.model,
            server_path=args.server
        )
        
        if result["status"] == "success":
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
