# n8n 工作流開發規則與常見錯誤

## 文件定位

本文檔記錄 n8n 工作流開發過程中的：
- **編碼問題與解決方案**
- **API 更新工作流時的常見錯誤**
- **節點配置的最佳實踐**
- **必須遵守的規則**

---

## 1. 編碼問題規則

### 1.1 PowerShell 腳本編碼問題

**問題描述：**
在 PowerShell 腳本中使用中文字符時，會出現解析錯誤：
```
ParserError: TerminatorExpectedAtEndOfString
```

**錯誤範例：**
```powershell
# ❌ 錯誤：中文字符導致解析失敗
Write-Host "錯誤：找不到 Convert to Text 節點"
```

**解決方案：**

1. **避免在 PowerShell 腳本中使用中文註釋和字符串**
   ```powershell
   # ✅ 正確：使用英文
   Write-Host "Error: Convert to Text node not found"
   ```

2. **使用 UTF-8 BOM 編碼保存腳本文件**
   ```powershell
   # 保存時指定編碼
   $content | Out-File -FilePath "script.ps1" -Encoding UTF8
   ```

3. **使用 Python 腳本替代複雜的 PowerShell 操作**
   - Python 對 UTF-8 支持更好
   - 更適合處理 JSON 和 API 調用

4. **在命令行中直接執行，避免創建包含中文的腳本文件**

**規則：**
- ✅ **優先使用 Python 進行 API 操作和 JSON 處理**
- ✅ **PowerShell 腳本中避免使用中文字符串**
- ✅ **使用英文錯誤訊息和註釋**

---

### 1.2 Python 腳本編碼問題

**問題描述：**
在 Windows 環境下，Python 腳本輸出中文字符或 emoji 時，會出現編碼錯誤：
```
UnicodeEncodeError: 'cp950' codec can't encode character '\u2705' in position 2: illegal multibyte sequence
```

**錯誤範例：**

1. **Emoji 字符編碼錯誤**
   ```python
   # ❌ 錯誤：在 Windows 終端輸出 emoji 會失敗
   print("✅ 工作流已成功更新！")
   # UnicodeEncodeError: 'cp950' codec can't encode character '\u2705'
   ```

2. **Subprocess 輸出編碼錯誤**
   ```python
   # ❌ 錯誤：subprocess 輸出包含非 ASCII 字符時會失敗
   result = subprocess.run(["git", "log"], capture_output=True, text=True)
   # UnicodeDecodeError: 'cp950' codec can't decode byte 0xe6 in position 1137
   ```

3. **中文字符串輸出錯誤**
   ```python
   # ❌ 錯誤：在 Windows 終端輸出中文可能失敗
   print("正在讀取本地工作流文件...")
   # UnicodeEncodeError: 'cp950' codec can't encode character
   ```

**解決方案：**

1. **避免使用 emoji 和特殊字符**
   ```python
   # ✅ 正確：使用英文和簡單符號
   print("[SUCCESS] Workflow updated successfully!")
   print("[ERROR] Update failed")
   print("[WARNING] This will rewrite git history!")
   ```

2. **設置環境變數強制使用 UTF-8**
   ```python
   # ✅ 正確：在腳本開頭設置
   import os
   import sys
   
   # 強制使用 UTF-8 編碼
   if sys.platform == "win32":
       os.environ["PYTHONIOENCODING"] = "utf-8"
       sys.stdout.reconfigure(encoding="utf-8")
       sys.stderr.reconfigure(encoding="utf-8")
   ```

3. **Subprocess 使用正確的編碼**
   ```python
   # ✅ 正確：指定編碼處理 subprocess 輸出
   result = subprocess.run(
       ["git", "log"],
       capture_output=True,
       text=True,
       encoding="utf-8",
       errors="replace"  # 或 "ignore"
   )
   ```

4. **文件讀寫明確指定編碼**
   ```python
   # ✅ 正確：明確指定 UTF-8 編碼
   with open("file.json", "r", encoding="utf-8") as f:
       data = json.load(f)
   
   with open("output.txt", "w", encoding="utf-8") as f:
       f.write("Content")
   ```

5. **使用英文輸出訊息**
   ```python
   # ✅ 正確：所有用戶可見的訊息使用英文
   print("Step 1: Reading local workflow file...")
   print("[SUCCESS] Workflow updated successfully!")
   print("[ERROR] Update failed: {}".format(error))
   ```

**實際案例：**

在 `clean_git_history_auto.py` 中遇到的錯誤：
```python
# ❌ 錯誤代碼
print("✅ 工作流已成功更新！")  # UnicodeEncodeError

# ✅ 修正後
print("[SUCCESS] Workflow updated successfully!")
```

在 `update_workflow_to_n8n.py` 中遇到的錯誤：
```python
# ❌ 錯誤代碼
result = subprocess.run(["git", "log"], capture_output=True, text=True)
# UnicodeDecodeError: 'cp950' codec can't decode byte

# ✅ 修正後
result = subprocess.run(
    ["git", "log"],
    capture_output=True,
    text=True,
    encoding="utf-8",
    errors="replace"
)
```

**規則：**
- ✅ **Python 腳本中避免使用 emoji 字符（✅❌⚠️ 等）**
- ✅ **所有用戶可見的輸出訊息使用英文**
- ✅ **文件操作明確指定 `encoding="utf-8"`**
- ✅ **Subprocess 調用指定 `encoding="utf-8"` 和 `errors="replace"`**
- ✅ **在 Windows 環境下，考慮在腳本開頭設置 UTF-8 編碼環境**

---

## 2. n8n API 更新工作流規則

### 2.1 只讀字段規則

**問題描述：**
使用 n8n API 更新工作流時，某些字段是只讀的，不能包含在更新請求中。

**只讀字段列表：**
- `id` - 工作流 ID（由系統生成）
- `versionId` - 版本 ID（由系統管理）
- `active` - 激活狀態（需使用專門的 API）
- `tags` - 標籤（需使用專門的 API）
- `createdAt` - 創建時間
- `updatedAt` - 更新時間
- `triggerCount` - 觸發次數
- `isArchived` - 歸檔狀態

**錯誤範例：**
```json
// ❌ 錯誤：包含只讀字段會導致 API 錯誤
{
  "id": "RKfT3GgZKppFkc7oKfuaN",
  "name": "Workflow Name",
  "nodes": [...],
  "active": false,  // ❌ 只讀字段
  "tags": []        // ❌ 只讀字段
}
```

**正確做法：**
```json
// ✅ 正確：只包含可寫入的字段
{
  "name": "Workflow Name",
  "nodes": [...],
  "connections": {...},
  "settings": {...}
}
```

**規則：**
- ✅ **更新工作流時，只包含以下字段：**
  - `name` - 工作流名稱
  - `nodes` - 節點陣列
  - `connections` - 連接關係
  - `settings` - 設置
- ✅ **從當前工作流獲取數據，只更新需要修改的部分**
- ✅ **使用 GET 獲取當前工作流，修改後使用 PUT 更新**

---

## 3. HTTP Request 節點配置規則

### 3.1 DataLabTo API 配置規則

**問題描述：**
DataLabTo API 要求使用 `multipart/form-data` 格式發送 binary 文件，而不是 JSON。

**錯誤配置：**
```json
// ❌ 錯誤：使用 JSON 格式
{
  "bodyContentType": "json",
  "sendBody": true,
  "body": "{{ $json.data }}"
}
```

**正確配置：**
```json
{
  "method": "POST",
  "url": "https://www.datalab.to/api/v1/marker",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      {
        "name": "X-API-Key",
        "value": "YOUR_API_KEY"
      }
    ]
  },
  "sendBody": true,
  "bodyContentType": "multipart-form-data",  // ✅ 必須是 multipart-form-data
  "bodyParameters": {
    "parameters": [
      {
        "name": "file",                        // ✅ 參數名必須是 "file"
        "parameterType": "binaryFile",        // ✅ 類型必須是 binaryFile
        "value": "={{ $binary.data }}"        // ✅ 必須指定 binary 數據來源
      }
    ]
  }
}
```

**關鍵配置點：**

1. **bodyContentType 必須設置**
   - ✅ `"multipart-form-data"` - 正確
   - ❌ `"json"` - 錯誤
   - ❌ 空值 - 錯誤

2. **bodyParameters.parameters 必須包含參數**
   - ✅ 必須是陣列，至少包含一個參數對象
   - ❌ 空陣列 `[]` - 錯誤
   - ❌ 空對象 `{}` - 錯誤

3. **參數對象必須包含三個字段**
   - `name`: `"file"` - 參數名稱
   - `parameterType`: `"binaryFile"` - 參數類型
   - `value`: `"={{ $binary.data }}"` - binary 數據來源表達式

**規則：**
- ✅ **DataLabTo API 必須使用 `multipart-form-data` 格式**
- ✅ **參數名必須是 `"file"`**
- ✅ **參數類型必須是 `"binaryFile"`**
- ✅ **value 必須設置為 `"={{ $binary.data }}"`**
- ✅ **bodyContentType 和 bodyParameters 必須同時正確配置**

---

## 4. Binary 數據傳遞規則

### 4.1 Binary 數據在節點間的傳遞

**問題描述：**
在 n8n 中，binary 數據會自動從一個節點傳遞到下一節點，但需要在 HTTP Request 節點中正確引用。

**錯誤做法：**
```javascript
// ❌ 錯誤：在 Code 節點中過早驗證 binary
if (!binaryData || !binaryData.data) {
  throw new Error('File binary data is required');
}
```

**正確做法：**
```javascript
// ✅ 正確：只提取文件資訊，binary 數據自動傳遞
const formData = $input.first().json;
const binaryData = $input.first().binary;

// 提取文件資訊
const fileInfo = formData.file || {};
const fileName = fileInfo.fileName || fileInfo.name || 'document';

// binary 數據會自動傳遞到下一節點
// 不需要在這裡驗證或處理 binary 數據本身

return {
  fileName: fileName,
  fileMimeType: fileInfo.mimeType || '',
  fileSize: fileInfo.fileSize || 0,
  pageTitle: formData.title || fileName.replace(/\.[^/.]+$/, '')
};
```

**規則：**
- ✅ **Binary 數據會自動在節點間傳遞，無需手動處理**
- ✅ **在 Code 節點中只提取文件資訊（名稱、類型、大小等）**
- ✅ **在 HTTP Request 節點中使用 `={{ $binary.data }}` 引用 binary 數據**
- ✅ **如果 binary 數據不存在，讓 HTTP Request 節點報錯，而不是在 Code 節點中過早驗證**

---

## 5. n8n API 操作最佳實踐

### 5.1 更新工作流的標準流程

**步驟：**

1. **獲取當前工作流**
   ```powershell
   $workflow = Invoke-RestMethod -Uri "http://localhost:5678/api/v1/workflows/{id}" -Method Get -Headers $headers
   ```

2. **修改需要更新的節點**
   ```powershell
   $node = $workflow.nodes | Where-Object { $_.name -eq "Node Name" }
   $node.parameters.someField = "new value"
   ```

3. **構建更新請求體（只包含可寫入字段）**
   ```powershell
   $updateBody = @{
       name = $workflow.name
       nodes = $workflow.nodes
       connections = $workflow.connections
       settings = $workflow.settings
   } | ConvertTo-Json -Depth 15
   ```

4. **發送更新請求**
   ```powershell
   $response = Invoke-RestMethod -Uri "http://localhost:5678/api/v1/workflows/{id}" -Method Put -Headers $headers -Body $updateBody
   ```

5. **驗證更新結果**
   ```powershell
   $updatedNode = $response.nodes | Where-Object { $_.name -eq "Node Name" }
   $updatedNode.parameters | ConvertTo-Json
   ```

**規則：**
- ✅ **總是先 GET 獲取當前工作流**
- ✅ **只修改需要更新的部分**
- ✅ **更新請求中只包含可寫入字段**
- ✅ **更新後驗證配置是否正確**

---

### 5.2 標準 n8n 工作流更新流程（經過驗證）

**重要：** 這是經過實際測試驗證的完整流程，請直接使用，避免重複犯錯。

#### 前置準備

1. **確認環境變數配置**
   - `.env` 文件中包含 `N8N_API_URL` 和 `N8N_API_KEY`
   - 確認 n8n 服務正在運行

2. **確認工作流文件路徑**
   - 工作流 JSON 文件位於 `workflow/document_to_notion_workflow.json`
   - 文件格式正確，包含 `nodes` 和 `connections`

#### 標準更新腳本（Python）

**創建 `update_workflow_to_n8n.py`：**

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import urllib.request
import os
import sys
from pathlib import Path

# Windows 環境編碼處理（避免 UnicodeEncodeError）
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        # Python < 3.7 不支持 reconfigure
        pass

# 從環境變數或直接配置獲取 API 資訊
N8N_API_URL = os.getenv("N8N_API_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

# 工作流配置
WORKFLOW_ID = "RKfT3GgZKppFkc7oKfuaN"  # 或從 API 獲取
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

if __name__ == "__main__":
    if not N8N_API_KEY:
        print("[ERROR] N8N_API_KEY not set. Please set it in .env file or environment.")
        exit(1)
    
    try:
        update_workflow()
    except Exception as e:
        exit(1)
```

#### 使用方式

1. **直接執行腳本**
   ```bash
   python update_workflow_to_n8n.py
   ```

2. **或從 Python 代碼中調用**
   ```python
   from update_workflow_to_n8n import update_workflow
   result = update_workflow()
   ```

#### 關鍵要點

1. **必須排除的字段（只讀）**
   - `id` - 工作流 ID
   - `versionId` - 版本 ID
   - `active` - 激活狀態
   - `tags` - 標籤
   - `meta` - 元數據
   - `createdAt` - 創建時間
   - `updatedAt` - 更新時間
   - `pinData` - 固定數據

2. **必須包含的字段（可寫入）**
   - `name` - 工作流名稱
   - `nodes` - 節點陣列
   - `connections` - 連接關係
   - `settings` - 設置（可選）

3. **編碼處理**
   - 使用 Python 而非 PowerShell（避免編碼問題）
   - 所有字符串使用 UTF-8 編碼
   - 輸出訊息使用英文（避免終端編碼問題）
   - **Windows 環境下，在腳本開頭設置 UTF-8 編碼：**
     ```python
     import sys
     import os
     
     if sys.platform == "win32":
         os.environ["PYTHONIOENCODING"] = "utf-8"
         sys.stdout.reconfigure(encoding="utf-8")
         sys.stderr.reconfigure(encoding="utf-8")
     ```
   - **Subprocess 調用必須指定編碼：**
     ```python
     result = subprocess.run(
         ["git", "log"],
         capture_output=True,
         text=True,
         encoding="utf-8",
         errors="replace"
     )
     ```

4. **錯誤處理**
   - 檢查 HTTP 狀態碼
   - 解析錯誤訊息
   - 提供有用的錯誤提示

#### 驗證清單

更新後必須驗證：
- [ ] 工作流名稱正確
- [ ] 節點數量正確
- [ ] API keys 已配置
- [ ] multipart-form-data 配置正確
- [ ] 連接關係正確

---

## 6. 錯誤處理規則

### 6.1 常見錯誤訊息與解決方案

**錯誤 1: "Bad request - please check your parameters"**
- **原因：** HTTP Request 節點的 bodyParameters 配置不正確
- **解決：** 檢查 bodyContentType 和 bodyParameters.parameters 是否正確設置

**錯誤 2: "You must provide a file or file URL"**
- **原因：** DataLabTo API 沒有收到文件數據
- **解決：** 確認 value 設置為 `"={{ $binary.data }}"` 且 binary 數據存在

**錯誤 3: "request/body must NOT have additional properties"**
- **原因：** 更新請求中包含了只讀字段
- **解決：** 移除 id, versionId, active, tags 等只讀字段

**錯誤 4: "request/body/active is read-only"**
- **原因：** 嘗試更新 active 字段
- **解決：** 從更新請求中移除 active 字段

**錯誤 5: PowerShell 解析錯誤（中文字符）**
- **原因：** PowerShell 腳本中包含中文字符導致編碼問題
- **解決：** 使用英文或改用 Python 腳本

**錯誤 6: Python UnicodeEncodeError（emoji/中文輸出）**
- **原因：** Windows 終端使用 cp950 編碼，無法輸出 emoji 或某些中文字符
- **錯誤訊息：** `UnicodeEncodeError: 'cp950' codec can't encode character '\u2705'`
- **解決：** 
  1. 避免使用 emoji，改用 `[SUCCESS]`、`[ERROR]` 等標記
  2. 所有輸出訊息使用英文
  3. 在腳本開頭設置 `sys.stdout.reconfigure(encoding="utf-8")`

**錯誤 7: Python UnicodeDecodeError（subprocess 輸出）**
- **原因：** subprocess 輸出包含非 ASCII 字符，Windows 默認使用 cp950 解碼失敗
- **錯誤訊息：** `UnicodeDecodeError: 'cp950' codec can't decode byte 0xe6`
- **解決：** 
  1. 在 subprocess.run 中明確指定 `encoding="utf-8"`
  2. 添加 `errors="replace"` 或 `errors="ignore"` 參數
  3. 示例：`subprocess.run(..., encoding="utf-8", errors="replace")`

---

## 7. 檢查清單

在更新或創建 n8n 工作流時，請確認：

### HTTP Request 節點（DataLabTo API）
- [ ] `bodyContentType` 設置為 `"multipart-form-data"`
- [ ] `bodyParameters.parameters` 是陣列且不為空
- [ ] 參數對象包含 `name: "file"`
- [ ] 參數對象包含 `parameterType: "binaryFile"`
- [ ] 參數對象包含 `value: "={{ $binary.data }}"`
- [ ] Header 中包含 `X-API-Key`

### n8n API 更新操作
- [ ] 更新請求中不包含只讀字段（id, versionId, active, tags 等）
- [ ] 只包含可寫入字段（name, nodes, connections, settings）
- [ ] 使用 GET 獲取當前工作流後再更新
- [ ] 更新後驗證配置

### 編碼與腳本
- [ ] PowerShell 腳本避免使用中文字符
- [ ] Python 腳本避免使用 emoji 字符（✅❌⚠️ 等）
- [ ] Python 腳本所有輸出訊息使用英文
- [ ] Python 文件操作明確指定 `encoding="utf-8"`
- [ ] Python subprocess 調用指定 `encoding="utf-8"` 和 `errors="replace"`
- [ ] 優先使用 Python 進行複雜操作
- [ ] 文件保存時使用 UTF-8 編碼

---

## 8. 參考資源

- [n8n API 文檔](https://docs.n8n.io/api/)
- [DataLabTo API 文檔](https://documentation.datalab.to/api-reference/marker)
- [n8n HTTP Request 節點文檔](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/)

---

---

## 9. 快速參考：n8n 更新命令

### 9.1 使用 Python 腳本（推薦）

**標準更新腳本已創建：** `update_workflow_to_n8n.py`

```bash
# 方法 1: 使用環境變數（從 .env 文件讀取）
python update_workflow_to_n8n.py

# 方法 2: 手動設置環境變數
export N8N_API_URL=http://localhost:5678
export N8N_API_KEY=your_api_key_here
python update_workflow_to_n8n.py

# 方法 3: 列出所有工作流（查找 WORKFLOW_ID）
python update_workflow_to_n8n.py --list
```

**腳本功能：**
- ✅ 自動讀取本地工作流文件
- ✅ 自動排除只讀字段
- ✅ 自動驗證配置
- ✅ 提供詳細的錯誤訊息
- ✅ 支持列出工作流

### 9.2 使用 PowerShell（不推薦，有編碼問題）

```powershell
# 僅用於簡單操作，避免中文字符
$apiKey = "your_api_key"
$headers = @{"X-N8N-API-KEY"=$apiKey; "Content-Type"="application/json"}
$workflow = Get-Content "workflow\document_to_notion_workflow.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$body = @{name=$workflow.name; nodes=$workflow.nodes; connections=$workflow.connections; settings=@{executionOrder="v1"}} | ConvertTo-Json -Depth 15
Invoke-RestMethod -Uri "http://localhost:5678/api/v1/workflows/{id}" -Method Put -Headers $headers -Body $body
```

### 9.3 檢查工作流列表

```bash
# Python
python -c "import urllib.request, json, os; req = urllib.request.Request('http://localhost:5678/api/v1/workflows', headers={'X-N8N-API-KEY': os.getenv('N8N_API_KEY')}); print(json.dumps(json.loads(urllib.request.urlopen(req).read().decode()), indent=2))"
```

---

**最後更新：** 2026-01-25  
**維護者：** AI Assistant  
**版本：** 2.0  
**重要更新：** 添加了經過驗證的標準更新流程和 Python 腳本模板
