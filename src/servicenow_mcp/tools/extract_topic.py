# import json
# import logging
# import re
# from typing import Any, Dict, List, Optional, Set

# from pydantic import BaseModel, Field

# from servicenow_mcp.auth.auth_manager import AuthManager
# from servicenow_mcp.utils.config import ServerConfig
# from servicenow_mcp.tools.table_tools import list_records, get_record, ListRecordsParams, GetRecordParams

# logger = logging.getLogger(__name__)


# class ExtractTopicParams(BaseModel):
#     topic_sys_id: str = Field(..., description="System ID of the topic to extract")
#     topic_table: str = Field(default="sys_cs_topic", description="Table name containing topics")
#     script_include_table: str = Field(default="sys_script_include", description="Table name containing script includes")


# def normalize_json(value: Any) -> Any:
#     if isinstance(value, dict):
#         return value
    
#     if isinstance(value, str):
#         try:
#             return json.loads(value)
#         except json.JSONDecodeError:
#             pass
        
#         normalized = value.replace('\\n', '\n')
#         normalized = normalized.replace('\\t', '\t')
#         normalized = normalized.replace('\\"', '"')
#         normalized = normalized.replace("\\'", "'")
        
#         try:
#             return json.loads(normalized)
#         except json.JSONDecodeError:
#             return {}
    
#     return {}


# def extract_script_classes(code: str) -> List[str]:
#     pattern = r'new\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('
#     matches = re.finditer(pattern, code)
    
#     classes = []
#     for match in matches:
#         class_name = match.group(1)
#         if not class_name.startswith('Glide'):
#             classes.append(class_name)
    
#     return list(set(classes))


# def get_topic_reference(node_data: Dict[str, Any]) -> Optional[str]:
#     topic_ref = node_data.get("reusableTopicId") or node_data.get("topic")
#     if isinstance(topic_ref, dict):
#         return topic_ref.get("sys_id") or topic_ref.get("value")
#     elif isinstance(topic_ref, str) and topic_ref:
#         return topic_ref
    
#     return node_data.get("topicId") or node_data.get("topic_id")


# def extract_topic(
#     config: ServerConfig,
#     auth_manager: AuthManager,
#     params: ExtractTopicParams
# ) -> Dict[str, Any]:
    
#     processed_topics: Set[str] = set()
#     processed_scripts: Set[str] = set()
#     all_nodes: List[Dict[str, Any]] = []
#     all_edges: List[Dict[str, Any]] = []
#     all_variables: List[Dict[str, Any]] = []
#     nested_topics: List[Dict[str, str]] = []
#     nested_scripts: List[Dict[str, str]] = []
    
#     def get_topic_record(sys_id: str) -> Optional[Dict[str, Any]]:
#         try:
#             result = get_record(
#                 config,
#                 auth_manager,
#                 GetRecordParams(table_name=params.topic_table, sys_id=sys_id, display_value=True)
#             )
#             if result.get("success"):
#                 return result.get("record", {})
#         except Exception as e:
#             logger.error(f"Error fetching topic: {e}")
#         return None
    
#     def get_script_record(script_name: str) -> Optional[Dict[str, Any]]:
#         try:
#             result = list_records(
#                 config,
#                 auth_manager,
#                 ListRecordsParams(
#                     table_name=params.script_include_table,
#                     query=f"name={script_name}",
#                     limit=1,
#                     display_value=True
#                 )
#             )
#             if result.get("success"):
#                 records = result.get("records", [])
#                 if records:
#                     return records[0]
#         except Exception as e:
#             logger.error(f"Error fetching script: {e}")
#         return None
    
#     def process_topic(topic_sys_id: str, parent_id: Optional[str] = None):
#         if topic_sys_id in processed_topics:
#             return
        
#         processed_topics.add(topic_sys_id)
        
#         topic_record = get_topic_record(topic_sys_id)
#         if not topic_record:
#             return
        
#         topic_name = topic_record.get("name", "") or topic_record.get("sys_name", "")
        
#         graph_value = topic_record.get("graph") or topic_record.get("flow_graph") or topic_record.get("definition")
#         graph_data = normalize_json(graph_value)
        
#         if not graph_data:
#             return
        
#         goals = graph_data.get("goals", {})
        
#         primary_goal = goals.get("primary", {})
#         if isinstance(primary_goal, dict):
#             nodes_data = primary_goal.get("nodes", {})
#             edges_data = primary_goal.get("edges", [])
#         else:
#             nodes_data = goals.get("nodes", {})
#             edges_data = goals.get("edges", [])
        
#         if isinstance(nodes_data, dict):
#             nodes = list(nodes_data.values())
#         elif isinstance(nodes_data, list):
#             nodes = nodes_data
#         else:
#             nodes = []
        
#         for node in nodes:
#             node_copy = node.copy()
#             node_copy["_source_topic"] = topic_sys_id
#             node_copy["_source_topic_name"] = topic_name
#             if parent_id:
#                 node_copy["_parent_node"] = parent_id
#             all_nodes.append(node_copy)
            
#             node_id = node.get("id")
#             node_type = node.get("stepType", "") or node.get("type", "")
            
#             if "ReusableTopic" in node_type or "topic" in node_type.lower():
#                 child_topic_id = get_topic_reference(node)
#                 if child_topic_id:
#                     nested_topics.append({
#                         "sys_id": child_topic_id,
#                         "parent_node": node_id,
#                         "parent_topic": topic_sys_id
#                     })
#                     process_topic(child_topic_id, node_id)
            
#             for key, value in node.items():
#                 if isinstance(value, str):
#                     script_classes = extract_script_classes(value)
#                     for script_class in script_classes:
#                         process_script(script_class, node_id)
#                 elif isinstance(value, dict):
#                     for sub_key, sub_value in value.items():
#                         if isinstance(sub_value, str):
#                             script_classes = extract_script_classes(sub_value)
#                             for script_class in script_classes:
#                                 process_script(script_class, node_id)
        
#         for edge in edges_data:
#             edge_copy = edge.copy()
#             edge_copy["_source_topic"] = topic_sys_id
#             all_edges.append(edge_copy)
        
#         variables_data = graph_data.get("variables", {})
#         if isinstance(variables_data, dict):
#             for var_id, var_data in variables_data.items():
#                 var_copy = var_data.copy() if isinstance(var_data, dict) else {"id": var_id, "value": var_data}
#                 var_copy["_source_topic"] = topic_sys_id
#                 all_variables.append(var_copy)
#         elif isinstance(variables_data, list):
#             for variable in variables_data:
#                 var_copy = variable.copy()
#                 var_copy["_source_topic"] = topic_sys_id
#                 all_variables.append(var_copy)
    
#     def process_script(script_name: str, parent_node_id: str):
#         if script_name in processed_scripts:
#             return
        
#         processed_scripts.add(script_name)
        
#         script_record = get_script_record(script_name)
#         if not script_record:
#             return
        
#         script_sys_id = script_record.get("sys_id", "")
#         script_code = script_record.get("script", "")
        
#         nested_scripts.append({
#             "name": script_name,
#             "sys_id": script_sys_id,
#             "parent_node": parent_node_id
#         })
        
#         script_node = {
#             "id": f"script_{script_sys_id}",
#             "type": "script_include",
#             "data": {
#                 "name": script_name,
#                 "sys_id": script_sys_id,
#                 "api_name": script_record.get("api_name", ""),
#                 "description": script_record.get("description", ""),
#                 "script": script_code
#             },
#             "_parent_node": parent_node_id,
#             "_is_script_include": True
#         }
#         all_nodes.append(script_node)
        
#         nested_classes = extract_script_classes(script_code)
#         for nested_class in nested_classes:
#             if nested_class != script_name:
#                 process_script(nested_class, script_node["id"])
    
#     try:
#         root_topic = get_topic_record(params.topic_sys_id)
#         if not root_topic:
#             return {
#                 "success": False,
#                 "message": "Topic not found",
#                 "basic_data": {},
#                 "summary": {},
#                 "components": {}
#             }
        
#         process_topic(params.topic_sys_id)
        
#         node_types = {}
#         for node in all_nodes:
#             node_type = node.get("stepType", "") or node.get("type", "unknown")
#             node_types[node_type] = node_types.get(node_type, 0) + 1
        
#         variables_by_node = {}
#         for var in all_variables:
#             node_id = var.get("nodeId")
#             if node_id:
#                 if node_id not in variables_by_node:
#                     variables_by_node[node_id] = []
#                 variables_by_node[node_id].append(var)
        
#         basic_data = {
#             "sys_id": params.topic_sys_id,
#             "name": root_topic.get("name", "") or root_topic.get("sys_name", ""),
#             "description": root_topic.get("description", ""),
#             "table": params.topic_table,
#             "type": root_topic.get("type", "")
#         }
        
#         summary = {
#             "total_nodes": len(all_nodes),
#             "total_edges": len(all_edges),
#             "total_variables": len(all_variables),
#             "nested_topics_count": len(nested_topics),
#             "nested_scripts_count": len(nested_scripts),
#             "nested_topics": nested_topics,
#             "nested_scripts": nested_scripts,
#             "node_types": node_types,
#             "variables_by_node": {k: len(v) for k, v in variables_by_node.items()}
#         }
        
#         components = {
#             "nodes": all_nodes,
#             "edges": all_edges,
#             "variables": all_variables,
#             "variables_by_node": variables_by_node
#         }
        
#         return {
#             "success": True,
#             "message": f"Successfully extracted topic with {len(all_nodes)} nodes",
#             "basic_data": basic_data,
#             "summary": summary,
#             "components": components
#         }
        
#     except Exception as e:
#         logger.error(f"Extraction failed: {e}")
#         return {
#             "success": False,
#             "message": f"Extraction failed: {str(e)}",
#             "basic_data": {},
#             "summary": {},
#             "components": {}
#         }

import json
import logging
import re
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig
from servicenow_mcp.tools.table_tools import list_records, get_record, ListRecordsParams, GetRecordParams

logger = logging.getLogger(__name__)


class ExtractTopicParams(BaseModel):
    topic_sys_id: str = Field(..., description="System ID of the topic to extract")
    topic_table: str = Field(default="sys_cb_topic", description="Table name containing topics")
    script_include_table: str = Field(default="sys_script_include", description="Table name containing script includes")


def normalize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
        
        normalized = value.replace('\\n', '\n')
        normalized = normalized.replace('\\t', '\t')
        normalized = normalized.replace('\\"', '"')
        normalized = normalized.replace("\\'", "'")
        
        try:
            return json.loads(normalized)
        except json.JSONDecodeError:
            return {}
    
    return {}


def extract_script_classes(code: str) -> List[str]:
    pattern = r'new\s+([A-Za-z_][A-Za-z0-9_]*)\s*\('
    matches = re.finditer(pattern, code)
    
    classes = []
    for match in matches:
        class_name = match.group(1)
        if not class_name.startswith('Glide'):
            classes.append(class_name)
    
    return list(set(classes))


def extract_global_classes(code: str) -> List[str]:
    pattern = r'global\.([A-Za-z_][A-Za-z0-9_]*)'
    matches = re.finditer(pattern, code)
    
    classes = []
    for match in matches:
        class_name = match.group(1)
        classes.append(class_name)
    
    return list(set(classes))


def get_topic_reference(node: Dict[str, Any]) -> Optional[str]:
    topic_id = node.get("reusableTopicId")
    if topic_id:
        return topic_id
    
    topic_ref = node.get("topic")
    if isinstance(topic_ref, dict):
        return topic_ref.get("sys_id") or topic_ref.get("value")
    elif isinstance(topic_ref, str) and topic_ref:
        return topic_ref
    
    return node.get("topicId") or node.get("topic_id")


def get_topic_by_name(name: str, config: ServerConfig, auth_manager: AuthManager, topic_table: str) -> Optional[str]:
    try:
        result = list_records(
            config,
            auth_manager,
            ListRecordsParams(
                table_name=topic_table,
                query=f"name={name}",
                limit=1,
                display_value=True
            )
        )
        if result.get("success"):
            records = result.get("records", [])
            if records:
                return records[0].get("sys_id")
    except Exception as e:
        logger.error(f"Error fetching topic by name: {e}")
    return None


def extract_topic(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ExtractTopicParams
) -> Dict[str, Any]:
    
    processed_topics: Set[str] = set()
    processed_scripts: Set[str] = set()
    all_nodes: List[Dict[str, Any]] = []
    all_edges: List[Dict[str, Any]] = []
    all_variables: List[Dict[str, Any]] = []
    nested_topics: List[Dict[str, str]] = []
    nested_scripts: List[Dict[str, str]] = []
    
    def get_topic_record(sys_id: str) -> Optional[Dict[str, Any]]:
        try:
            result = get_record(
                config,
                auth_manager,
                GetRecordParams(table_name=params.topic_table, sys_id=sys_id, display_value=True)
            )
            if result.get("success"):
                return result.get("record", {})
        except Exception as e:
            logger.error(f"Error fetching topic: {e}")
        return None
    
    def get_script_record(script_name: str) -> Optional[Dict[str, Any]]:
        try:
            result = list_records(
                config,
                auth_manager,
                ListRecordsParams(
                    table_name=params.script_include_table,
                    query=f"name={script_name}",
                    limit=1,
                    display_value=True
                )
            )
            if result.get("success"):
                records = result.get("records", [])
                if records:
                    return records[0]
        except Exception as e:
            logger.error(f"Error fetching script: {e}")
        return None
    
    def process_topic(topic_sys_id: str, parent_id: Optional[str] = None):
        if topic_sys_id in processed_topics:
            return
        
        processed_topics.add(topic_sys_id)
        
        topic_record = get_topic_record(topic_sys_id)
        if not topic_record:
            return
        
        topic_name = topic_record.get("name", "") or topic_record.get("sys_name", "")
        
        graph_value = topic_record.get("graph") or topic_record.get("flow_graph") or topic_record.get("definition")
        graph_data = normalize_json(graph_value)
        
        if not graph_data:
            return
        
        goals = graph_data.get("goals", {})
        
        primary_goal = goals.get("primary", {})
        if isinstance(primary_goal, dict):
            nodes_data = primary_goal.get("nodes", {})
            edges_data = primary_goal.get("edges", [])
        else:
            nodes_data = goals.get("nodes", {})
            edges_data = goals.get("edges", [])
        
        if isinstance(nodes_data, dict):
            nodes = list(nodes_data.values())
        elif isinstance(nodes_data, list):
            nodes = nodes_data
        else:
            nodes = []
        
        for node in nodes:
            node_copy = node.copy()
            node_copy["_source_topic"] = topic_sys_id
            node_copy["_source_topic_name"] = topic_name
            if parent_id:
                node_copy["_parent_node"] = parent_id
            all_nodes.append(node_copy)
            
            node_id = node.get("id")
            node_type = node.get("stepType", "") or node.get("type", "")
            
            if "ReusableTopic" in node_type or "topic" in node_type.lower():
                child_topic_id = get_topic_reference(node)
                
                if not child_topic_id:
                    topic_choice = node.get("reusableTopicChoice")
                    if topic_choice:
                        child_topic_id = get_topic_by_name(topic_choice, config, auth_manager, params.topic_table)
                
                if child_topic_id:
                    nested_topics.append({
                        "sys_id": child_topic_id,
                        "parent_node": node_id,
                        "parent_topic": topic_sys_id,
                        "name": node.get("reusableTopicChoice", "")
                    })
                    process_topic(child_topic_id, node_id)
            
            if "ScriptOutput" in node_type or "ScriptAction" in node_type or "script" in node_type.lower():
                script_code = node.get("script", "")
                if script_code:
                    global_classes = extract_global_classes(script_code)
                    for script_class in global_classes:
                        process_script(script_class, node_id)
                
                for key, value in node.items():
                    if isinstance(value, str) and key in ["script", "value", "expression", "code"]:
                        new_classes = extract_script_classes(value)
                        for script_class in new_classes:
                            process_script(script_class, node_id)
                        
                        global_refs = extract_global_classes(value)
                        for script_class in global_refs:
                            process_script(script_class, node_id)
            
            for key, value in node.items():
                if isinstance(value, str):
                    script_classes = extract_script_classes(value)
                    for script_class in script_classes:
                        process_script(script_class, node_id)
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if isinstance(sub_value, str):
                            script_classes = extract_script_classes(sub_value)
                            for script_class in script_classes:
                                process_script(script_class, node_id)
        
        for edge in edges_data:
            edge_copy = edge.copy()
            edge_copy["_source_topic"] = topic_sys_id
            all_edges.append(edge_copy)
        
        variables_data = graph_data.get("variables", {})
        if isinstance(variables_data, dict):
            for var_id, var_data in variables_data.items():
                var_copy = var_data.copy() if isinstance(var_data, dict) else {"id": var_id, "value": var_data}
                var_copy["_source_topic"] = topic_sys_id
                all_variables.append(var_copy)
        elif isinstance(variables_data, list):
            for variable in variables_data:
                var_copy = variable.copy()
                var_copy["_source_topic"] = topic_sys_id
                all_variables.append(var_copy)
    
    def process_script(script_name: str, parent_node_id: str):
        if script_name in processed_scripts:
            return
        
        processed_scripts.add(script_name)
        
        script_record = get_script_record(script_name)
        if not script_record:
            return
        
        script_sys_id = script_record.get("sys_id", "")
        script_code = script_record.get("script", "")
        
        nested_scripts.append({
            "name": script_name,
            "sys_id": script_sys_id,
            "parent_node": parent_node_id
        })
        
        script_node = {
            "id": f"script_{script_sys_id}",
            "type": "script_include",
            "stepType": "script_include",
            "data": {
                "name": script_name,
                "sys_id": script_sys_id,
                "api_name": script_record.get("api_name", ""),
                "description": script_record.get("description", ""),
                "script": script_code
            },
            "_parent_node": parent_node_id,
            "_is_script_include": True
        }
        all_nodes.append(script_node)
        
        nested_classes = extract_script_classes(script_code)
        for nested_class in nested_classes:
            if nested_class != script_name:
                process_script(nested_class, script_node["id"])
        
        global_classes = extract_global_classes(script_code)
        for global_class in global_classes:
            if global_class != script_name:
                process_script(global_class, script_node["id"])
    
    try:
        root_topic = get_topic_record(params.topic_sys_id)
        if not root_topic:
            return {
                "success": False,
                "message": "Topic not found",
                "basic_data": {},
                "summary": {},
                "components": {}
            }
        
        process_topic(params.topic_sys_id)
        
        node_types = {}
        for node in all_nodes:
            node_type = node.get("stepType", "") or node.get("type", "unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        variables_by_node = {}
        for var in all_variables:
            node_id = var.get("nodeId")
            if node_id:
                if node_id not in variables_by_node:
                    variables_by_node[node_id] = []
                variables_by_node[node_id].append(var)
        
        basic_data = {
            "sys_id": params.topic_sys_id,
            "name": root_topic.get("name", "") or root_topic.get("sys_name", ""),
            "description": root_topic.get("description", ""),
            "table": params.topic_table,
            "type": root_topic.get("type", "")
        }
        
        summary = {
            "total_nodes": len(all_nodes),
            "total_edges": len(all_edges),
            "total_variables": len(all_variables),
            "nested_topics_count": len(nested_topics),
            "nested_scripts_count": len(nested_scripts),
            "nested_topics": nested_topics,
            "nested_scripts": nested_scripts,
            "node_types": node_types,
            "variables_by_node": {k: len(v) for k, v in variables_by_node.items()}
        }
        
        components = {
            "nodes": all_nodes,
            "edges": all_edges,
            "variables": all_variables,
            "variables_by_node": variables_by_node
        }
        
        return {
            "success": True,
            "message": f"Successfully extracted topic with {len(all_nodes)} nodes",
            "basic_data": basic_data,
            "summary": summary,
            "components": components
        }
        
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return {
            "success": False,
            "message": f"Extraction failed: {str(e)}",
            "basic_data": {},
            "summary": {},
            "components": {}
        }
