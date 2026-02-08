import logging
from typing import Any, Dict, List, Optional

import requests
from pydantic import BaseModel, Field

from servicenow_mcp.auth.auth_manager import AuthManager
from servicenow_mcp.utils.config import ServerConfig

logger = logging.getLogger(__name__)


class ListTablesParams(BaseModel):
    limit: int = Field(10, description="Maximum number of tables to return")
    offset: int = Field(0, description="Offset for pagination")
    query: Optional[str] = Field(None, description="Search query for table names")
    include_system: bool = Field(False, description="Include system tables")


class GetTableParams(BaseModel):
    table_name: str = Field(..., description="Name of the table")


class ListRecordsParams(BaseModel):
    table_name: str = Field(..., description="Name of the table")
    limit: int = Field(10, description="Maximum number of records to return")
    offset: int = Field(0, description="Offset for pagination")
    query: Optional[str] = Field(None, description="ServiceNow query string for filtering")
    fields: Optional[List[str]] = Field(None, description="List of fields to return")
    display_value: bool = Field(True, description="Return display values")


class GetRecordParams(BaseModel):
    table_name: str = Field(..., description="Name of the table")
    sys_id: str = Field(..., description="System ID of the record")
    display_value: bool = Field(True, description="Return display values")


def list_tables(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListTablesParams,
) -> Dict[str, Any]:
    api_url = f"{config.instance_url}/api/now/table/sys_db_object"
    
    query_params = {
        "sysparm_limit": params.limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "true",
    }
    
    query_parts = []
    
    if not params.include_system:
        query_parts.append("sys_scope.scope!=global")
    
    if params.query:
        query_parts.append(f"nameLIKE{params.query}^ORlabelLIKE{params.query}")
    
    if query_parts:
        query_params["sysparm_query"] = "^".join(query_parts)
    
    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        result = response.json().get("result", [])
        
        tables = []
        for table in result:
            tables.append({
                "name": table.get("name"),
                "label": table.get("label"),
                "sys_id": table.get("sys_id"),
                "super_class": table.get("super_class"),
                "number_ref": table.get("number_ref"),
                "extension_model": table.get("extension_model"),
            })
        
        return {
            "success": True,
            "message": f"Found {len(tables)} tables",
            "tables": tables,
            "count": len(tables),
        }
    
    except requests.RequestException as e:
        logger.error(f"Failed to list tables: {e}")
        return {
            "success": False,
            "message": f"Failed to list tables: {str(e)}",
            "tables": [],
            "count": 0,
        }


def get_table(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetTableParams,
) -> Dict[str, Any]:
    table_api_url = f"{config.instance_url}/api/now/table/sys_db_object"
    
    table_query_params = {
        "sysparm_query": f"name={params.table_name}",
        "sysparm_limit": "1",
        "sysparm_display_value": "true",
    }
    
    try:
        response = requests.get(
            table_api_url,
            params=table_query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        result = response.json().get("result", [])
        
        if not result:
            return {
                "success": False,
                "message": f"Table '{params.table_name}' not found",
            }
        
        table_info = result[0]
        
        columns_api_url = f"{config.instance_url}/api/now/table/sys_dictionary"
        columns_query_params = {
            "sysparm_query": f"name={params.table_name}^element!=NULL",
            "sysparm_display_value": "true",
            "sysparm_fields": "element,column_label,internal_type,max_length,mandatory,reference,default_value",
        }
        
        columns_response = requests.get(
            columns_api_url,
            params=columns_query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        columns_response.raise_for_status()
        
        columns_result = columns_response.json().get("result", [])
        
        columns = []
        for col in columns_result:
            columns.append({
                "name": col.get("element"),
                "label": col.get("column_label"),
                "type": col.get("internal_type"),
                "max_length": col.get("max_length"),
                "mandatory": col.get("mandatory") == "true",
                "reference": col.get("reference"),
                "default_value": col.get("default_value"),
            })
        
        return {
            "success": True,
            "message": f"Retrieved table '{params.table_name}'",
            "table": {
                "name": table_info.get("name"),
                "label": table_info.get("label"),
                "sys_id": table_info.get("sys_id"),
                "super_class": table_info.get("super_class"),
                "number_ref": table_info.get("number_ref"),
                "extension_model": table_info.get("extension_model"),
                "columns": columns,
                "column_count": len(columns),
            },
        }
    
    except requests.RequestException as e:
        logger.error(f"Failed to get table: {e}")
        return {
            "success": False,
            "message": f"Failed to get table: {str(e)}",
        }


def list_records(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: ListRecordsParams,
) -> Dict[str, Any]:
    api_url = f"{config.instance_url}/api/now/table/{params.table_name}"
    
    query_params = {
        "sysparm_limit": params.limit,
        "sysparm_offset": params.offset,
        "sysparm_display_value": "true" if params.display_value else "false",
    }
    
    if params.query:
        query_params["sysparm_query"] = params.query
    
    if params.fields:
        query_params["sysparm_fields"] = ",".join(params.fields)
    
    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        result = response.json().get("result", [])
        
        return {
            "success": True,
            "message": f"Found {len(result)} records in table '{params.table_name}'",
            "records": result,
            "count": len(result),
            "table_name": params.table_name,
        }
    
    except requests.RequestException as e:
        logger.error(f"Failed to list records: {e}")
        return {
            "success": False,
            "message": f"Failed to list records: {str(e)}",
            "records": [],
            "count": 0,
        }


def get_record(
    config: ServerConfig,
    auth_manager: AuthManager,
    params: GetRecordParams,
) -> Dict[str, Any]:
    api_url = f"{config.instance_url}/api/now/table/{params.table_name}/{params.sys_id}"
    
    query_params = {
        "sysparm_display_value": "true" if params.display_value else "false",
    }
    
    try:
        response = requests.get(
            api_url,
            params=query_params,
            headers=auth_manager.get_headers(),
            timeout=config.timeout,
        )
        response.raise_for_status()
        
        result = response.json().get("result", {})
        
        if not result:
            return {
                "success": False,
                "message": f"Record with sys_id '{params.sys_id}' not found in table '{params.table_name}'",
            }
        
        return {
            "success": True,
            "message": f"Retrieved record from table '{params.table_name}'",
            "record": result,
            "table_name": params.table_name,
        }
    
    except requests.RequestException as e:
        logger.error(f"Failed to get record: {e}")
        return {
            "success": False,
            "message": f"Failed to get record: {str(e)}",
        }