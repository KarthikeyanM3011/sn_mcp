import json
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)

class MapFlowParams(BaseModel):
    extracted_flow: Dict[str, Any] = Field(..., description="Extracted ServiceNow VA Designer flow from extract_topic tool")
    target_platform: str = Field("moveworks", description="Target platform for mapping")
    output_format: str = Field("json", description="Output format: json or yaml")

SYSTEM_KNOWLEDGE = """You are an expert in both ServiceNow Virtual Agent Designer and Moveworks AI Agent platform. Your task is to analyze a ServiceNow flow and map it to Moveworks components with high accuracy.

SERVICENOW COMPONENTS:
USER INPUT: Text(free text), StaticChoice(fixed options), ReferenceChoice(dynamic DB options), Boolean(yes/no), DateTime(date/time), FilePicker(upload), Carousel(scrollable)
BOT RESPONSE: Text(message), Image(display), Link(URL), HTML(rich content), Card(structured), MultiFlowOutput(conditional)
UTILITY: ScriptAction(JavaScript), ScriptOutput(JS output), RecordAction(DB CRUD), Lookup(DB query), Decision(if/else), TopicBlock(sub-flow), Action(workflow trigger)
SPECIALTY: InputCollector(AI multi-input), CustomControl(custom), ScriptInclude(reusable JS)

MOVEWORKS COMPONENTS:
SLOTS: slot_text, slot_enum, slot_lookup, slot_boolean, slot_datetime
ACTIONS: llm_action, http_action, script_action, compound_action
MESSAGES: message_text, message_card, message_link
CONTROL: if/else conditionals, for loops

JAVASCRIPT TO APITHON:
Remove: var/let/const, new, GlideRecord, .query(), .next()
Replace: function->def, ===->==, !==->!=, true->True, false->False, null->None
Convert GlideRecord to http_action API calls
Access: context['input_vars']['x'], context['slots']['x'], context['action_outputs']['x']
Output: context['output'] = value

MAPPINGS:
Text->slot_text, StaticChoice->slot_enum, ReferenceChoice->slot_lookup+http_action
Boolean->slot_boolean, DateTime->slot_datetime, FilePicker->http_action
Text_Output->message_text, Card->message_card, Link->message_link
ScriptAction->script_action, RecordAction->http_action, Lookup->http_action
Decision->if/else, TopicBlock->compound_action, ScriptInclude->script_action

OUTPUT JSON STRUCTURE (EXACT FORMAT REQUIRED):
{
  "flow_metadata": {
    "original_name": "str",
    "original_sys_id": "str",
    "original_description": "str",
    "target_platform": "moveworks",
    "total_components": int,
    "mapped_components": int,
    "unmapped_components": int,
    "confidence_overall": float
  },
  "dependency_graph": {
    "execution_order": ["id1", "id2"],
    "dependencies": {"comp_id": {"depends_on": [], "provides_to": []}},
    "variable_flow": {"var": {"defined_by": "id", "used_by": ["id"], "type": "slot/action/const"}}
  },
  "components": [{
    "component_id": "unique_id",
    "original_node_id": "sn_node_id",
    "original_type": "SN_type",
    "target_type": "MW_type",
    "category": "slot/action/message/control",
    "confidence": float,
    "mapping_notes": "str",
    "dependencies": {"input_variables": [], "output_variables": [], "requires_before": [], "provides_for": []},
    "code": {"language": "python", "function_name": "name", "code_string": "code", "parameters": {}},
    "original_properties": {},
    "validation": {"syntax_valid": bool, "dependencies_resolved": bool, "warnings": []}
  }],
  "unmapped_components": [{"component_id": "id", "original_node_id": "id", "original_type": "type", "reason": "str", "suggestion": "str", "original_properties": {}}],
  "script_includes": [{"name": "name", "original_sys_id": "id", "functions": [{"function_name": "name", "code": "code", "parameters": [], "returns": "desc"}], "used_by": []}],
  "generated_files": {"main_flow": {"filename": "main_flow.py", "content": "code"}, "components": [{"category": "cat", "filename": "file.py", "content": "code"}]},
  "validation_report": {"total_validations": int, "passed": int, "failed": int, "warnings": int, "errors": [{"component_id": "id", "error_type": "type", "message": "msg"}]}
}

CONFIDENCE SCORING: 1.0(direct 1:1), 0.8-0.9(simple conversion), 0.6-0.7(needs extra components), 0.4-0.5(complex logic), 0.0-0.3(manual review)

CRITICAL RULES:
1. Process ALL nodes from extracted_flow
2. Use edges for execution order and dependencies
3. Track all variables (defined_by, used_by)
4. NO COMMENTS in generated code
5. Descriptive names, try-except blocks, explicit returns
6. Handle nested topics in compound_action
7. Convert all ScriptIncludes to functions
8. Validate syntax, dependencies, variables
9. Return ONLY valid JSON, no markdown, no extra text

ANALYSIS STEPS:
1. Extract metadata from basic_data
2. Index all nodes, edges, variables
3. Identify script_includes
4. For each node: identify type, map to MW, extract properties, track dependencies, generate code, score confidence
5. Build dependency graph and execution order
6. Generate files
7. Validate
8. Return JSON"""

USER_PROMPT_TEMPLATE = """Analyze this ServiceNow Virtual Agent Designer flow and map it to Moveworks components.

EXTRACTED FLOW DATA:
{flow_data}

REQUIREMENTS:
- Map every node to Moveworks equivalent
- Generate executable Python code without comments
- Track all dependencies and variable flow
- Build complete dependency graph
- Assign confidence scores
- Handle nested topics and script includes
- Validate all components
- Return output in exact JSON format specified

Return ONLY the JSON object, no other text."""

def map_flow_to_moveworks(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: MapFlowParams
) -> Dict[str, Any]:
    try:
        extracted_flow = params.extracted_flow
        
        if not extracted_flow.get("success"):
            return {
                "success": False,
                "message": "Input flow extraction failed",
                "error": extracted_flow.get("message", "Unknown error")
            }
        
        flow_data_str = json.dumps(extracted_flow, indent=2)
        
        user_prompt = USER_PROMPT_TEMPLATE.format(flow_data=flow_data_str)
        
        api_url = "https://api.anthropic.com/v1/messages"
        
        headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        request_body = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 16000,
            "system": SYSTEM_KNOWLEDGE,
            "messages": [
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            "temperature": 0.3
        }
        
        import requests
        
        response = requests.post(
            api_url,
            headers=headers,
            json=request_body,
            timeout=300
        )
        
        response.raise_for_status()
        
        api_response = response.json()
        
        if "content" not in api_response or len(api_response["content"]) == 0:
            return {
                "success": False,
                "message": "Claude API returned no content",
                "error": "Empty response from API"
            }
        
        content_blocks = api_response["content"]
        full_response = ""
        for block in content_blocks:
            if block.get("type") == "text":
                full_response += block.get("text", "")
        
        full_response = full_response.strip()
        
        if full_response.startswith("```json"):
            full_response = full_response[7:]
        if full_response.startswith("```"):
            full_response = full_response[3:]
        if full_response.endswith("```"):
            full_response = full_response[:-3]
        full_response = full_response.strip()
        
        try:
            mapping_result = json.loads(full_response)
        except json.JSONDecodeError as je:
            logger.error(f"Failed to parse Claude response as JSON: {je}")
            logger.error(f"Response content: {full_response[:500]}")
            return {
                "success": False,
                "message": "Failed to parse mapping result",
                "error": str(je),
                "raw_response": full_response[:1000]
            }
        
        mapping_result["success"] = True
        mapping_result["message"] = "Flow mapping completed successfully"
        mapping_result["api_model_used"] = "claude-sonnet-4-20250514"
        
        return mapping_result
        
    except requests.RequestException as e:
        logger.error(f"API request failed: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"API request failed: {str(e)}",
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Flow mapping failed: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"Flow mapping failed: {str(e)}",
            "error": str(e)
        }