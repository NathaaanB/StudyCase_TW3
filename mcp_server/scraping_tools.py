"""
Data extraction and scraping tool implementations  
"""

import json
import re
import os
import asyncio
from mcp.types import TextContent
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import litellm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure LiteLLM
litellm.set_verbose = False

# Use user's API key configuration
MODEL = os.getenv("SCRAPER_LLM_MODEL", "openrouter/google/gemini-2.5-flash")

async def analyze_page_structure(page, arguments: dict) -> list[TextContent]:
    """Analyze HTML structure using LLM to generate intelligent CSS selectors"""
    print(f"[MCP] Analyzing page structure with LLM")
    
    html_content = arguments.get("html", "")
    schema_fields = arguments.get("schema_fields", [])
    collection_name = arguments.get("collection_name", "")
    
    if not html_content or not schema_fields:
        error_result = {"ok": False, "error": "Missing html or schema_fields"}
        return [TextContent(type="text", text=json.dumps(error_result))]
    
    try:
        # Configure API key
        if os.getenv("LLM_API_KEY"):
            os.environ["GEMINI_API_KEY"] = os.getenv("LLM_API_KEY")
        
        # Limit HTML to avoid token overflow (keep most relevant parts)
        html_snippet = _prepare_html_for_analysis(html_content)
        
        # Build LLM prompt
        messages = _build_analysis_prompt(html_snippet, schema_fields, collection_name)
        
        print(f"[MCP] Calling {MODEL} for intelligent selector analysis...")
        print(f"[MCP] HTML snippet length: {len(html_snippet)} chars")
        print(f"[MCP] Fields to analyze: {schema_fields}")
        
        # Call LLM with enhanced debugging
        response = await litellm.acompletion(
            model=MODEL,
            messages=messages,
            temperature=0.1,  # Slightly higher for more reliable generation
            max_tokens=2000,  # Increased token limit
            timeout=45  # Increased timeout
        )
        
        print(f"[MCP] Response stats: prompt_tokens={response.usage.prompt_tokens if response.usage else 'unknown'}, completion_tokens={response.usage.completion_tokens if response.usage else 'unknown'}")
        
        # Parse response
        json_content = response.choices[0].message.content
        print(f"[MCP] Raw LLM response: {json_content}")
        
        if not json_content or json_content.strip() == "":
            print(f"[MCP] Empty response from LLM")
            error_result = {"ok": False, "error": "LLM returned empty response"}
            return [TextContent(type="text", text=json.dumps(error_result))]
        
        # Clean the response in case there are markdown code blocks
        json_content = json_content.strip()
        if json_content.startswith("```json"):
            json_content = json_content[7:]
        if json_content.endswith("```"):
            json_content = json_content[:-3]
        json_content = json_content.strip()
        
        selector_map = json.loads(json_content)
        
        result = {
            "ok": True,
            "item_selector": selector_map.get("item_selector"),
            "field_selectors": selector_map.get("field_selectors", {}),
            "analysis": {
                "fields_mapped": len(selector_map.get("field_selectors", {})),
                "strategy": "LLM intelligent analysis",
                "model_used": MODEL
            }
        }
        
        print(f"[MCP] LLM generated selectors for {len(result['field_selectors'])} fields")
        return [TextContent(type="text", text=json.dumps(result))]
        
    except json.JSONDecodeError as e:
        print(f"[MCP] LLM returned invalid JSON: {e}")
        error_result = {"ok": False, "error": f"LLM returned invalid JSON: {e}"}
        return [TextContent(type="text", text=json.dumps(error_result))]
    except Exception as e:
        print(f"[MCP] Analysis failed: {e}")
        error_result = {"ok": False, "error": str(e)}
        return [TextContent(type="text", text=json.dumps(error_result))]


def _prepare_html_for_analysis(html_content: str, max_length: int = 25000) -> str:
    """Prepare HTML for LLM analysis by keeping the most relevant parts"""
    if len(html_content) <= max_length:
        return html_content
    
    # For product pages, try to find the main content area first
    from bs4 import BeautifulSoup
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for main content containers
        main_content = soup.find('main') or soup.find('div', class_=lambda x: x and 'content' in x.lower())
        if main_content:
            main_html = str(main_content)
            if len(main_html) <= max_length:
                return main_html
        
        # Look for product containers specifically
        product_area = soup.find('div', class_=lambda x: x and any(term in x.lower() for term in ['product', 'catalogue', 'listing']))
        if product_area:
            product_html = str(product_area)
            if len(product_html) <= max_length:
                return product_html
    except:
        pass  # Fall back to slice method
    
    # Fall back to middle section approach
    start_pos = len(html_content) // 4
    end_pos = start_pos + max_length
    
    snippet = html_content[start_pos:end_pos]
    return "...[truncated beginning]...\n" + snippet + "\n...[truncated end]..."


def _build_analysis_prompt(html_snippet: str, schema_fields: list, collection_name: str) -> list:
    """Build LLM prompt for intelligent selector analysis"""
    
    fields_str = ", ".join(f'"{field}"' for field in schema_fields)
    
    system_prompt = """You are an expert web scraper. Analyze HTML and generate robust CSS selectors.

CRITICAL RULES:
- Return ONLY valid JSON, no explanations or comments
- Find the container that repeats for each item (like article, li, div.product)
- For each field, find the best CSS selector within each container
- Use format selector@attribute for links/images (e.g., "img@src", "a@href", "a@title")
- For text content, just use the selector (e.g., "h3 a", ".price")
- You MUST find a selector for EVERY field requested
- If a field contains product names/titles, look for h3, a, title attributes
- If a field contains prices, look for price, cost, currency classes/text

REQUIRED OUTPUT FORMAT (JSON only):
{
  "item_selector": "CSS_selector_for_repeating_container",
  "field_selectors": {
    "field_name": "css_selector_or_selector@attribute"
  }
}"""

    user_prompt = f"""Find CSS selectors for ALL of these fields: {fields_str}

You must find a selector for each field. Look carefully at the HTML structure.

HTML to analyze:
{html_snippet}

Return only the JSON selector map with ALL fields."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]


def _split_selector_attribute(selector: str) -> tuple[str, str]:
    """Split 'selector@attribute' format into (selector, attribute)"""
    if '@' in selector:
        parts = selector.split('@', 1)
        return parts[0].strip(), parts[1].strip() 
    return selector.strip(), None


async def extract_data_from_html(page, arguments: dict) -> list[TextContent]:
    """Extract structured data from HTML using CSS selectors with selector@attribute support"""
    print(f"[MCP] Extracting data from HTML with enhanced selector support")
    
    html_content = arguments.get("html", "")
    container_selector = arguments.get("container_selector", "")
    field_selectors = arguments.get("field_selectors", {})
    base_url = arguments.get("base_url", "")
    
    print(f"[MCP] Container selector: {container_selector}")
    print(f"[MCP] Field selectors: {list(field_selectors.keys())}")
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        containers = soup.select(container_selector) if container_selector else [soup]
        print(f"[MCP] 📦 Found {len(containers)} containers")
        
        extracted_items = []
        for container in containers:
            item = {}
            for field_name, selector_raw in field_selectors.items():
                # Parse selector@attribute format
                selector, attribute = _split_selector_attribute(selector_raw)
                
                elem = container.select_one(selector)
                if elem:
                    value = _extract_value_from_element(elem, attribute, base_url)
                    item[field_name] = value
                else:
                    item[field_name] = None
            
            # Only add non-empty items
            if any(v for v in item.values() if v):
                extracted_items.append(item)
        
        result = {
            "ok": True,
            "status": "success",
            "items": extracted_items,
            "count": len(extracted_items)
        }
        print(f"[MCP] Extracted {len(extracted_items)} items")
        return [TextContent(type="text", text=json.dumps(result))]
        
    except Exception as e:
        print(f"[MCP] Extraction error: {e}")
        error_result = {"ok": False, "status": "error", "error": str(e)}
        return [TextContent(type="text", text=json.dumps(error_result))]


def _extract_value_from_element(elem, attribute: str = None, base_url: str = "") -> str:
    """Extract value from element with support for attributes and smart defaults"""
    if not elem:
        return None
    
    # If specific attribute requested
    if attribute:
        if attribute == "text":
            return elem.get_text(strip=True)
        elif attribute == "html":
            return str(elem)
        else:
            value = elem.get(attribute, "")
            # Make relative URLs absolute
            if value and base_url and attribute in ["href", "src", "data-src"]:
                value = urljoin(base_url, value)
            return value
    
    # Smart defaults based on element type
    if elem.name == "img":
        src = elem.get("src", "") or elem.get("data-src", "")
        if src and base_url:
            src = urljoin(base_url, src)
        return src
    elif elem.name == "a":
        href = elem.get("href", "")
        if href and base_url:
            href = urljoin(base_url, href)
        return href
    elif elem.name in ["input", "textarea"]:
        return elem.get("value", "")
    else:
        # Default to text content
        return elem.get_text(strip=True)


async def save_results(page, arguments: dict) -> list[TextContent]:
    """Save extracted data to output file"""
    print(f"[MCP] Saving results")
    
    data = arguments.get("data", {})
    output_path = arguments.get("output_path", "results.json")
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"[MCP] Results saved to {output_path}")
        return [TextContent(type="text", text=f"Results saved to {output_path}")]
    except Exception as e:
        print(f"[MCP] Save error: {e}")
        return [TextContent(type="text", text=f"Error saving results: {str(e)}")]


async def analyze_and_extract_data(page, arguments: dict) -> list[TextContent]:
    """Analyze page structure and extract data in one step (like WebPilot)"""
    print(f"[MCP] Analyzing and extracting data in one step")
    
    html_content = arguments.get("html", "")
    schema_fields = arguments.get("schema_fields", [])
    collection_name = arguments.get("collection_name", "")
    base_url = arguments.get("base_url", "")
    output_path = arguments.get("output_path", "results.json")
    
    if not html_content or not schema_fields:
        error_result = {"ok": False, "error": "Missing html or schema_fields"}
        return [TextContent(type="text", text=json.dumps(error_result))]
    
    try:
        # Step 1: Analyze structure with LLM
        html_snippet = _prepare_html_for_analysis(html_content)
        messages = _build_analysis_prompt(html_snippet, schema_fields, collection_name)
        
        # Configure API key
        if os.getenv("LLM_API_KEY"):
            os.environ["GEMINI_API_KEY"] = os.getenv("LLM_API_KEY")
        
        print(f"[MCP] Calling {MODEL} for analysis...")
        response = await litellm.acompletion(
            model=MODEL,
            messages=messages,
            temperature=0.1,
            max_tokens=2000,
            timeout=45
        )
        
        json_content = response.choices[0].message.content
        print(f"[MCP] LLM response: {json_content}")
        
        if not json_content or json_content.strip() == "":
            error_result = {"ok": False, "error": "LLM returned empty response"}
            return [TextContent(type="text", text=json.dumps(error_result))]
        
        # Clean JSON response
        json_content = json_content.strip()
        if json_content.startswith("```json"):
            json_content = json_content[7:]
        if json_content.endswith("```"):
            json_content = json_content[:-3]
        json_content = json_content.strip()
        
        selector_map = json.loads(json_content)
        
        # Step 2: Immediately extract data using found selectors
        container_selector = selector_map.get("item_selector")
        field_selectors = selector_map.get("field_selectors", {})
        
        print(f"[MCP] Extracting data with container: {container_selector}")
        print(f"[MCP] Field selectors: {field_selectors}")
        
        # Debug: Test selectors on first container
        soup = BeautifulSoup(html_content, 'html.parser')
        containers = soup.select(container_selector) if container_selector else [soup]
        if containers:
            first_container = containers[0]
            print(f"[MCP] Testing selectors on first container:")
            for field_name, selector_raw in field_selectors.items():
                selector, attribute = _split_selector_attribute(selector_raw)
                elem = first_container.select_one(selector)
                if elem:
                    value = _extract_value_from_element(elem, attribute, base_url)
                    print(f"[MCP]    {field_name}: '{selector}' -> '{value}'")
                else:
                    print(f"[MCP]    {field_name}: '{selector}' -> NO MATCH")
                    # Try to suggest alternatives
                    print(f"[MCP]      Container HTML preview: {str(first_container)[:200]}...")
        
        print(f"[MCP] Processing all {len(containers)} containers...")
        
        extracted_items = []
        for container in containers:
            item = {}
            for field_name, selector_raw in field_selectors.items():
                selector, attribute = _split_selector_attribute(selector_raw)
                elem = container.select_one(selector)
                if elem:
                    value = _extract_value_from_element(elem, attribute, base_url)
                    item[field_name] = value
                else:
                    item[field_name] = None
            
            if any(v for v in item.values() if v):
                extracted_items.append(item)
        
        # Build final output like WebPilot
        from datetime import datetime
        final_data = {
            collection_name or "produits": extracted_items,
            "metadata": {
                "date_extraction": datetime.now().isoformat(),
                "nb_resultats": len(extracted_items)
            }
        }
        
        # Save results automatically
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({
                    "status": "success",
                    "data": final_data,
                    "quality_report": {
                        "total_items": len(extracted_items),
                        "complete_items": len([item for item in extracted_items if all(v for v in item.values() if v)]),
                        "completion_rate": len([item for item in extracted_items if all(v for v in item.values() if v)]) / len(extracted_items) if extracted_items else 0,
                        "missing_fields": [field for field in schema_fields if not any(item.get(field) for item in extracted_items)],
                        "errors": []
                    }
                }, f, indent=2, ensure_ascii=False)
            print(f"[MCP] Results automatically saved to {output_path}")
        except Exception as save_error:
            print(f"[MCP] Could not save to {output_path}: {save_error}")
        
        result = {
            "ok": True,
            "status": "success",
            "task_completed": True,
            "items": extracted_items,
            "count": len(extracted_items),
            "saved_to": output_path,
            "selectors_used": {
                "container": container_selector,
                "fields": field_selectors
            },
            "message": f"Successfully extracted {len(extracted_items)} items and saved to {output_path}. Task is complete."
        }
        
        print(f"[MCP] Analysis, extraction and save completed: {len(extracted_items)} items")
        return [TextContent(type="text", text=json.dumps(result))]
        
    except Exception as e:
        print(f"[MCP] Analysis and extraction error: {e}")
        error_result = {"ok": False, "status": "error", "error": str(e)}
        return [TextContent(type="text", text=json.dumps(error_result))]


async def done(page, arguments: dict) -> list[TextContent]:
    """Mark scraping as completed"""
    message = arguments.get("message", "Scraping completed")
    print(f"[MCP] {message}")
    return [TextContent(type="text", text=f"Task completed: {message}")]