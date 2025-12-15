"""
prompts_autonomous_scraper.py

Simplified prompt system for autonomous web scraping agent.
"""

import json
from typing import Dict, Any


def get_autonomous_scraper_system_prompt(schema: Dict[str, Any], url: str) -> str:
    """
    Generate the main system prompt for autonomous scraping.
    
    Args:
        schema: Target data schema (includes url, schema, options)
        url: URL to scrape
        
    Returns:
        System prompt string
    """
    schema_json = json.dumps(schema, indent=2, ensure_ascii=False)
    
    # Extract options
    options = schema.get('options', {})
    max_pages = options.get('max_pages', None)
    pagination = options.get('pagination', False)
    
    pagination_instruction = ""
    if pagination and max_pages:
        pagination_instruction = f"PAGINATION LIMIT: Stop after {max_pages} page(s). Do not exceed this limit."
    elif pagination:
        pagination_instruction = "PAGINATION: Scrape all available pages until exhausted."
    
    return f"""You are an autonomous web scraping agent.

EXECUTION PROTOCOL:
- Every response must be exactly ONE tool call
- No text explanations, no planning, no narration (or very few)
- Message content must be empty
- Continue until task completion or failure

MISSION:
Extract data from: {url}

Target schema:
{schema_json}

{pagination_instruction}

RULES:
1. Start by navigating to the target URL
2. Use standard CSS selectors only
3. Extract from list pages first, use detail pages if needed
4. Respect pagination limits strictly
5. Call save_results when data is complete
6. Call done after saving results

FIELD EXTRACTION:
- Text fields: text content
- Fields with "link" or "url": href attribute
- Fields with "image" or "img": src attribute
- Rating fields: class name if text empty

COMPLETION:
- save_results: when all required data extracted
- done: after saving or if impossible to continue

Each response = one tool call. No exceptions.
"""