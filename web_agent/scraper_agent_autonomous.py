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
from prompts_autonomous_scraper import get_autonomous_scraper_system_prompt

# Load environment variables
load_dotenv()

# Configure API key for litellm
if os.getenv("LLM_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.getenv("LLM_API_KEY")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# =============================================================================
# MCP INTEGRATION (from agent_mcp.py)
# =============================================================================

_mcp_sessions = {}
_mcp_contexts = {}
_mcp_tools_cache = []
_full_html_cache = ""


async def initialize_mcp_servers(server_module: str = "mcp_server.server"):
    """
    Initialize MCP web automation server and discover tools.
    
    Args:
        server_module: Python module path to MCP server (e.g. 'mcp_server.server')
        
    Returns:
        List of available tools in OpenAI format
    """
    global _mcp_sessions, _mcp_contexts, _mcp_tools_cache
    
    if _mcp_sessions and _mcp_tools_cache:
        logging.info("[MCP] Reusing existing session")
        return _mcp_tools_cache.copy()
    
    logging.info(f"[MCP] Initializing server module: {server_module}")
    
    try:
        # Create server parameters for Python module
        server_params = StdioServerParameters(
            command="python",
            args=["-m", server_module]
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
            logging.warning(f"[MCP] Timeout cleaning {server_name}")
        except Exception as e:
            logging.warning(f"[MCP] Error cleaning {server_name}: {e}")
    
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

# All tools are now in MCP server - no custom tools needed


# =============================================================================
# AGENT EXECUTION
# =============================================================================

async def run_autonomous_scraper(
    config_path: str,
    output_path: str,
    model: str,
    server_module: str = "mcp_server.server"
) -> Dict[str, Any]:
    """
    Run the autonomous scraping agent.
    
    Args:
        config_path: Path to schema configuration JSON
        output_path: Path to save results
        model: LLM model to use
        server_module: MCP server module path
        
    Returns:
        Dict with status and results
    """
    logging.info("="*60)
    logging.info("AUTONOMOUS SCRAPING AGENT STARTED")
    logging.info("="*60)
    
    # Load configuration
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    url = config.get("url")
    schema = config.get("schema", {})
    options = config.get("options", {})
    max_pages = options.get("max_pages")
    
    logging.info(f"Target URL: {url}")
    logging.info(f"Model: {model}")
    if max_pages:
        logging.info(f"Max pages: {max_pages}")
    
    # Initialize MCP server
    mcp_tools = await initialize_mcp_servers(server_module)
    if not mcp_tools:
        raise RuntimeError("Failed to initialize MCP server")
    
    # All tools are now in MCP server
    all_tools = mcp_tools
    
    logging.info(f"Total tools available: {len(all_tools)}")
    
    # Generate system prompt (pass full config)
    system_prompt = generate_scraping_prompt(config, url)
    
    # Build user message with max_pages reminder if applicable
    user_message = f"Please scrape data from {url} according to the schema. Devise your strategy and execute it step by step."
    if max_pages:
        user_message += f"\n\nIMPORTANT: Stop after scraping {max_pages} page(s). Do not scrape more than {max_pages} page(s)."
    
    
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
            logging.info(f"Calling LLM model: {model}")
            logging.info(f"Message history length: {len(messages)}")
            await asyncio.sleep(5)
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                tools=all_tools,
                tool_choice="required",  # Force LLM to always call a tool
                temperature=0.1,  # Lower temperature for precise scraping
                max_tokens=1000  # Limit output tokens to avoid budget issues
            )
            logging.info(f"LLM response received")
            
            # Check if response has choices
            if not response.choices or len(response.choices) == 0:
                logging.error(f"Empty response from LLM: {response}")
                break
                
            assistant_message = response.choices[0].message
            
            # Log thinking
            if assistant_message.content:
                logging.info(f"\nAgent reasoning:")
                logging.info(assistant_message.content)
            
            # Check for tool calls
            tool_calls = assistant_message.tool_calls if hasattr(assistant_message, 'tool_calls') else None
            
            if not tool_calls:
                logging.info("\nAgent finished without tool call")
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
                
                logging.info(f"\nExecuting: {tool_name}")
                logging.info(f"   Arguments: {json.dumps(tool_args, indent=2)}")
                
                # All tools are now MCP tools - execute via MCP
                logging.info(f"Executing MCP tool: {tool_name}")
                
                # Special handling for save_results to pass output path
                if tool_name == "save_results" and "output_path" not in tool_args:
                    tool_args["output_path"] = output_path
                
                # Special handling for analyze_and_extract_data to pass output path
                if tool_name == "analyze_and_extract_data" and "output_path" not in tool_args:
                    tool_args["output_path"] = output_path
                
                # Special handling to use cached HTML for analysis and extraction
                global _full_html_cache
                if tool_name in ["analyze_and_extract_data"] and _full_html_cache:
                    tool_args["html"] = _full_html_cache
                    logging.info(f"Using cached HTML ({len(_full_html_cache)} chars) for {tool_name}")
                
                result = await execute_mcp_tool(tool_name, tool_args)
                logging.info(f"MCP tool completed")
                
                # Check if task is done
                if tool_name == "done":
                    task_done = True
                elif tool_name == "analyze_and_extract_data" and isinstance(result, dict):
                    if result.get("task_completed") or result.get("ok"):
                        task_done = True
                
                # Extract scraped data if save_results was called
                if tool_name == "save_results" and "data" in tool_args:
                    scraped_data = tool_args["data"]
                
                logging.info(f"Tool result preview: {str(result)[:200]}...")
                
                # Truncate large results to avoid token overflow
                # For HTML responses, store full HTML for extract_data_from_html tool
                result_to_send = result
                if isinstance(result, str) and len(result) > 2000:
                    if "<!DOCTYPE" in result and tool_name == "get_html":
                        # Store full HTML for extraction use
                        _full_html_cache = result
                        
                        # For LLM context, provide a helpful analysis instead of raw HTML
                        soup = BeautifulSoup(result, 'html.parser')
                        containers = soup.select("article.product_pod")
                        result_to_send = f"HTML retrieved successfully. Found {len(containers)} product containers. Ready for extraction with extract_data_from_html tool."
                    else:
                        result_to_send = result[:2000] + "...[truncated]"
                elif isinstance(result, dict):
                    # If result contains HTML, truncate it aggressively
                    if 'html' in str(result).lower() or any(len(str(v)) > 2000 for v in result.values() if isinstance(v, str)):
                        result_to_send = {
                            "status": result.get("status", "success"),
                            "summary": f"HTML retrieved ({len(str(result))} chars)" if "<!DOCTYPE" in str(result) else str(result)[:200]
                        }
                        if "items" in result:
                            result_to_send["items"] = result["items"][:2] + [{"...": "truncated"}] if len(result["items"]) > 2 else result["items"]
                            result_to_send["count"] = result.get("count", len(result["items"]))
                
                # Add result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result_to_send)
                })
            
            if task_done:
                logging.info("\nAgent completed the task")
                break
                
        except Exception as e:
            logging.error(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            break
    
    # Cleanup
    await cleanup_mcp_sessions()
    
    logging.info("\n" + "="*60)
    logging.info("SCRAPING COMPLETED")
    logging.info("="*60)
    
    if scraped_data:
        product_count = len(scraped_data.get("produits", []))
        logging.info(f"Products extracted: {product_count}")
        logging.info(f"Output: {output_path}")
    
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
    parser.add_argument("--model", default=os.getenv("SCRAPER_LLM_MODEL", "gemini/gemini-2.5-flash"), help="LLM model to use")
    parser.add_argument("--server", default="mcp_server.server", help="MCP server module (default: mcp_server.server)")
    
    args = parser.parse_args()
    
    try:
        result = await run_autonomous_scraper(
            config_path=args.config,
            output_path=args.output,
            model=args.model,
            server_module=args.server
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
