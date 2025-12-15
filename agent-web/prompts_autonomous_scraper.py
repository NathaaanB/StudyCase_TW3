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
⚠️ PAGINATION LIMIT: The 'options.max_pages' parameter is set to {max_pages}.
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
⚠️ PAGINATION: The 'options.pagination' is true.
Scrape all available pages until no more pages exist.
"""
    
    return f"""SYSTEM PROTOCOL — STRICT TOOL CALLING MODE

You are an autonomous web scraping agent operating under a STRICT EXECUTION PROTOCOL.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚫 ABSOLUTE OUTPUT RULE (NON-NEGOTIABLE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• You MUST respond using ONLY a SINGLE tool call per message.
• Plain text responses are STRICTLY FORBIDDEN.
• Your message content MUST be EMPTY unless you are calling a tool.
• Explanations, reasoning, planning, or narration are NOT allowed.
• If you cannot proceed, you MUST call the `done` tool.
• Any response without a tool call is INVALID.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️ EXECUTION MODEL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• You operate in discrete execution steps.
• Each response = EXACTLY ONE tool call.
• State is preserved between steps.
• Reasoning is implicit in your choice of tool and arguments.
• You MUST continue until the task is fully completed.




━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 MISSION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Extract structured data from the following URL:

TARGET_URL:
{url}

EXPECTED OUTPUT SCHEMA:
{schema_json}

PAGINATION INSTRUCTIONS (if any):
{pagination_instruction}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🛠️ AVAILABLE TOOLS (MCP Web Automation)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• navigate_web(url, timeout)
• retrieve_html()
• click_element(selector)
• fill_field(selector, value)
• capture_screenshot(full_page)
• extract_links(filter)
• extract_data_from_html(html, container_selector, field_selectors, base_url)
• save_results(data)
• done()

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 MANDATORY START ACTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Your FIRST response MUST be:
• a call to `navigate_web` using TARGET_URL

Any other response is INVALID.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📐 EXTRACTION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Use ONLY standard CSS selectors (no pseudo-elements).
• Prefer robust, semantic selectors.
• Field extraction behavior:
  - Text fields → text content
  - Fields containing "link" or "url" → href attribute
  - Fields containing "image" or "img" → src attribute
  - Rating fields → class name if text is empty

You are FORBIDDEN from calling extract_data_from_html with empty field_selectors.
If selectors are unknown, you MUST attempt to infer them from the HTML structure.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📄 LIST PAGE VS DETAIL PAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• FIRST attempt to extract all fields from the LIST PAGE.
• If ANY required field is missing:
  - You MUST extract the product/item link.
  - You MUST navigate to EACH item’s detail page.
  - You MUST extract missing fields there.
  - You MUST navigate back to the list page before continuing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 PAGINATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Handle pagination ONLY if instructed.
• Respect max_pages limits STRICTLY.
• Stop pagination when limit is reached or no next page exists.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💾 COMPLETION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• You MUST call `save_results` once ALL required data is extracted.
• After saving results, you MUST call `done`.
• Do NOT call `done` before all data is complete.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
❗ FAILURE HANDLING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• If extraction is impossible, call `done` with a failure reason.
• Do NOT output text explanations.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ REMINDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every response MUST be exactly ONE tool call.
No narration. No planning. No exceptions.
"""


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
