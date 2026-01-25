#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
n8n Workflow Update Script
標準工作流更新腳本 - 遵循 docs/01_rules.md 的規則

使用方法:
    python update_workflow_to_n8n.py

環境變數:
    N8N_API_URL: n8n API URL (預設: http://localhost:5678)
    N8N_API_KEY: n8n API Key (必須設置)
"""

import json
import urllib.request
import os
import sys
from pathlib import Path

# 從環境變數或直接配置獲取 API 資訊
N8N_API_URL = os.getenv("N8N_API_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

# 工作流配置
WORKFLOW_ID = "RKfT3GgZKppFkc7oKfuaN"  # 可從 API 獲取或手動設置
WORKFLOW_FILE = "workflow/document_to_notion_workflow.json"


def update_workflow():
    """更新工作流到 n8n - 標準流程"""
    
    # 步驟 1: 讀取本地工作流文件
    print("Step 1: Reading local workflow file...")
    workflow_path = Path(WORKFLOW_FILE)
    if not workflow_path.exists():
        raise FileNotFoundError(f"Workflow file not found: {WORKFLOW_FILE}")
    
    with open(workflow_path, "r", encoding="utf-8") as f:
        local_workflow = json.load(f)
    
    # 步驟 2: 構建更新請求體（只包含可寫入字段）
    print("Step 2: Building update request body...")
    update_body = {
        "name": local_workflow.get("name", "Document Analysis Workflow"),
        "nodes": local_workflow["nodes"],
        "connections": local_workflow["connections"],
        "settings": {
            "executionOrder": "v1",
            "availableInMCP": True
        }
    }
    
    # 重要：移除所有只讀字段
    # 不包含：id, versionId, active, tags, meta, createdAt, updatedAt 等
    
    # 步驟 3: 準備 API 請求
    api_url = f"{N8N_API_URL}/api/v1/workflows/{WORKFLOW_ID}"
    headers = {
        "X-N8N-API-KEY": N8N_API_KEY,
        "Content-Type": "application/json"
    }
    
    # 步驟 4: 發送更新請求
    print("Step 3: Sending update request to n8n...")
    req = urllib.request.Request(
        api_url,
        data=json.dumps(update_body).encode("utf-8"),
        headers=headers,
        method="PUT"
    )
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))
            
            # 步驟 5: 驗證更新結果
            print("\n[SUCCESS] Workflow updated successfully!")
            print(f"Workflow name: {result.get('name')}")
            print(f"Node count: {len(result.get('nodes', []))}")
            
            # 驗證關鍵配置
            verify_configuration(result)
            
            return result
            
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"\n[ERROR] Update failed: {e.code}")
        print(f"Error message: {error_body}")
        
        # 常見錯誤處理
        if "read-only" in error_body.lower():
            print("\n[TIP] This error usually means you included read-only fields.")
            print("Make sure to exclude: id, versionId, active, tags, meta")
        elif "additional properties" in error_body.lower():
            print("\n[TIP] This error means you included fields that are not allowed.")
            print("Only include: name, nodes, connections, settings")
        
        raise
    except Exception as e:
        print(f"\n[ERROR] An error occurred: {str(e)}")
        raise


def verify_configuration(workflow):
    """驗證工作流配置是否正確"""
    print("\nVerifying workflow configuration:")
    
    # 驗證 API keys
    api_nodes = ["Send to Datalab API", "Get Markdown"]
    for node in workflow.get("nodes", []):
        if node.get("name") in api_nodes:
            params = node.get("parameters", {})
            headers_params = params.get("headerParameters", {}).get("parameters", [])
            
            api_key_found = False
            for header in headers_params:
                if header.get("name") == "X-API-Key":
                    api_key_value = header.get("value", "")
                    if api_key_value:
                        print(f"  [OK] {node.get('name')}: API key configured")
                        api_key_found = True
                        break
            
            if not api_key_found:
                print(f"  [WARNING] {node.get('name')}: X-API-Key header not found")
    
    # 驗證 multipart-form-data 配置
    for node in workflow.get("nodes", []):
        if node.get("name") == "Send to Datalab API":
            params = node.get("parameters", {})
            content_type = params.get("contentType") or params.get("bodyContentType")
            if content_type == "multipart-form-data":
                print(f"  [OK] {node.get('name')}: multipart-form-data configured")
            else:
                print(f"  [WARNING] {node.get('name')}: contentType is {content_type}")


def list_workflows():
    """列出所有工作流（用於查找 WORKFLOW_ID）"""
    api_url = f"{N8N_API_URL}/api/v1/workflows"
    headers = {
        "X-N8N-API-KEY": N8N_API_KEY
    }
    
    try:
        req = urllib.request.Request(api_url, headers=headers)
        with urllib.request.urlopen(req) as response:
            workflows = json.loads(response.read().decode("utf-8"))
            print("\nAvailable workflows:")
            for wf in workflows.get("data", []):
                print(f"  ID: {wf.get('id')}, Name: {wf.get('name')}")
    except Exception as e:
        print(f"[ERROR] Failed to list workflows: {str(e)}")


if __name__ == "__main__":
    if not N8N_API_KEY:
        print("[ERROR] N8N_API_KEY not set.")
        print("Please set it in .env file or environment variable.")
        print("\nYou can also list workflows to find the correct ID:")
        print("  python update_workflow_to_n8n.py --list")
        sys.exit(1)
    
    # 支持 --list 參數來列出工作流
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        list_workflows()
        sys.exit(0)
    
    try:
        update_workflow()
    except Exception as e:
        sys.exit(1)
