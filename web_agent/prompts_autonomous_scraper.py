"""
prompts_autonomous_scraper.py

Externalized prompt system for the autonomous web scraping agent.
All prompts are in English and designed for complete LLM autonomy.
"""

import json
from typing import Dict, Any


def get_autonomous_scraper_system_prompt(schema: Dict[str, Any], url: str) -> str:
    """
    Generate the main system prompt for autonomous scraping.
    
    The LLM has COMPLETE control over the scraping strategy.
    NO hardcoded workflows, NO fallbacks.
    
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
        pagination_instruction = f"""
PAGINATION LIMIT: The 'options.max_pages' parameter is set to {max_pages}.
This means you MUST STOP after scraping {max_pages} page(s).
Do NOT scrape more than {max_pages} page(s) even if more pages exist.

Pagination strategy:
- Scrape page 1 completely
- If max_pages > 1, navigate to page 2 and scrape it
- If max_pages > 2, continue until reaching the limit
- STOP at page {max_pages} - do not go further
"""
    elif pagination:
        pagination_instruction = """
PAGINATION: The 'options.pagination' is true.
Scrape all available pages until no more pages exist.
"""
    
    return f"""Extract structured data from {url} according to this schema:

{schema_json}

{pagination_instruction}

OBJECTIVE: Extract all data matching the schema structure and produce a properly formatted result.

OUTPUT FORMAT REQUIRED:
{{
  "status": "success",
  "data": {{
    [collection_name]: [extracted_items],
    "metadata": {{
      "date_extraction": "ISO_datetime",
      "nb_resultats": number
    }}
  }},
  "quality_report": {{
    "total_items": number,
    "complete_items": number,
    "completion_rate": number,
    "missing_fields": [list],
    "errors": [list]
  }}
}}

RULES:
- Use available tools intelligently to discover the best extraction approach
- One tool call per response
- Complete the full extraction workflow autonomously
- CRITICAL: When you analyze page structure and get selectors, you MUST use those exact selectors for data extraction
- Always pass the container selector and field selectors from your analysis to the extraction step

WORKFLOW:
1. Navigate to the target URL
2. Retrieve the HTML content
3. Analyze the page structure to identify CSS selectors for each data field
4. Extract the actual data using the selectors you discovered
5. Save the results

Start by navigating to the target URL."""