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


def get_html_analysis_prompt(html_content: str, schema: Dict[str, Any]) -> str:
    """
    Prompt for initial HTML analysis and strategy planning.
    
    Args:
        html_content: HTML content to analyze
        schema: Target data schema
        
    Returns:
        Analysis prompt
    """
    schema_json = json.dumps(schema, indent=2, ensure_ascii=False)
    
    # Truncate HTML for token limits
    html_sample = html_content[:8000]
    
    return f"""Analyze this HTML page and devise a complete scraping strategy.

TARGET SCHEMA:
{schema_json}

HTML CONTENT (first 8000 chars):
{html_sample}

YOUR TASK:
Analyze this page and create a detailed action plan.

ANALYSIS STEPS:
1. Identify blocking elements (popups, cookie banners, overlays)
   - Look for z-index, position:fixed, modal classes
   - Find close buttons or accept buttons
   
2. Find product/item containers
   - Look for repeating structures
   - Identify semantic tags (article, li, div with product classes)
   
3. For each field in the schema, find CSS selectors
   - Analyze HTML structure within containers
   - Identify the best selector for each field
   
4. Decide if detail pages are needed
   - Check if all fields are available on this page
   - If not, plan navigation to detail pages

RESPONSE FORMAT (JSON):
{{
    "blocking_elements": [
        {{"type": "popup", "selector": "#cookie-banner .accept", "action": "click", "reason": "Close cookie consent"}},
        ...
    ],
    "product_container": "article.product_pod",
    "selectors": {{
        "nom": "h3 a",
        "prix": ".price_color",
        "description": "__DETAIL_PAGE_NEEDED__",
        "image_url": "img",
        ...
    }},
    "detail_page_needed": true,
    "detail_page_link_selector": "h3 a",
    "strategy": "Detailed explanation of your plan",
    "confidence": "high|medium|low"
}}

IMPORTANT:
- Use "__DETAIL_PAGE_NEEDED__" for fields only available on detail pages
- Be specific with selectors - include parent context if needed
- Explain your reasoning in the strategy field

Respond ONLY with valid JSON, no markdown or extra text.
"""


def get_selector_validation_prompt(
    container_html: str,
    proposed_selectors: Dict[str, str],
    schema: Dict[str, Any]
) -> str:
    """
    Prompt for validating discovered selectors.
    
    Args:
        container_html: HTML of a single product container
        proposed_selectors: Selectors to validate
        schema: Target schema
        
    Returns:
        Validation prompt
    """
    schema_json = json.dumps(schema, indent=2, ensure_ascii=False)
    selectors_json = json.dumps(proposed_selectors, indent=2)
    
    return f"""Validate these CSS selectors against actual HTML.

TARGET SCHEMA:
{schema_json}

PROPOSED SELECTORS:
{selectors_json}

HTML SAMPLE (single product container):
{container_html[:3000]}

YOUR TASK:
Verify each selector actually matches the intended element.

VALIDATION PROCESS:
1. For each selector, check if it matches the right element
2. Verify the matched element contains the expected data type
3. Suggest improvements if needed

RESPONSE FORMAT (JSON):
{{
    "validated_selectors": {{
        "nom": {{"selector": "h3 a", "valid": true, "sample_value": "Book Title"}},
        "prix": {{"selector": ".price_color", "valid": true, "sample_value": "£51.77"}},
        "description": {{"selector": "__DETAIL_PAGE_NEEDED__", "valid": true, "note": "Not on list page"}},
        ...
    }},
    "issues_found": [
        "Selector for 'image_url' matches multiple elements - needs more specificity"
    ],
    "improvements": {{
        "image_url": ".image_container img.thumbnail"
    }},
    "overall_confidence": "high|medium|low"
}}

Respond ONLY with valid JSON.
"""


def get_detail_page_analysis_prompt(
    list_page_data: Dict[str, Any],
    detail_page_html: str,
    missing_fields: list
) -> str:
    """
    Prompt for analyzing detail pages and extracting missing fields.
    
    Args:
        list_page_data: Data already extracted from list page
        detail_page_html: HTML of the detail page
        missing_fields: Fields that need extraction
        
    Returns:
        Detail page analysis prompt
    """
    data_json = json.dumps(list_page_data, indent=2, ensure_ascii=False)
    
    return f"""Extract missing fields from this product detail page.

CURRENT DATA (from list page):
{data_json}

MISSING FIELDS TO EXTRACT:
{', '.join(missing_fields)}

DETAIL PAGE HTML (first 6000 chars):
{detail_page_html[:6000]}

YOUR TASK:
Find selectors for the missing fields on this detail page.

ANALYSIS STEPS:
1. For each missing field, analyze the HTML structure
2. Find the most specific and reliable selector
3. Extract sample values to verify correctness
4. Also check if any existing fields can be improved (fuller titles, better images, etc.)

RESPONSE FORMAT (JSON):
{{
    "detail_selectors": {{
        "description": "#product_description ~ p",
        "reviews_nb": ".product_page .review_count"
    }},
    "extracted_values": {{
        "description": "Sample description text...",
        "reviews_nb": "42"
    }},
    "improvements": {{
        "nom": "h1.product_title"
    }},
    "confidence": "high|medium|low",
    "notes": "Description found in paragraph after #product_description heading"
}}

Respond ONLY with valid JSON.
"""


def get_error_recovery_prompt(error_message: str, context: str) -> str:
    """
    Prompt for recovering from errors.
    
    Args:
        error_message: The error that occurred
        context: Context about what was being attempted
        
    Returns:
        Recovery prompt
    """
    return f"""An error occurred during scraping. Analyze and propose a recovery strategy.

ERROR MESSAGE:
{error_message}

CONTEXT:
{context}

YOUR TASK:
Analyze what went wrong and propose alternative approaches.

RESPONSE FORMAT (JSON):
{{
    "error_analysis": "Explanation of what likely caused the error",
    "alternative_strategies": [
        {{"approach": "Try a different selector", "details": "Use parent.child instead of .class"}},
        {{"approach": "Wait longer for page load", "details": "Increase timeout to 20s"}},
        ...
    ],
    "recommended_action": {{
        "tool": "tool_name",
        "arguments": {{}},
        "reason": "Why this should work"
    }},
    "continue_possible": true
}}

Respond ONLY with valid JSON.
"""
