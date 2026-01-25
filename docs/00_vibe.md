# n8n 文件分析與 Notion 自動化流程規格

## 0. 文件定位（Purpose）

本 Markdown 作為：

- n8n 自動化流程的**單一真實來源（SSOT）**
- LLM（Gemini）分析文件的 **System / Context Prompt**
- 專案的流程規格與產出模板

**最終目標：**

```
[Form Trigger]
↓
[Extract File / Binary]
↓
[Convert to Text（依檔案類型）]
↓
[Gemini API（分析 → Markdown）]
↓
[整理 Markdown]
↓
[Notion - Create Page]
```

---

## 1. 詳細工作流程規格 (Detailed Workflow Specification)

### 步驟 1：Form Trigger（表單觸發）

- **n8n 節點**: `Form Trigger`
- **處理邏輯**: 建立一個公開的表單，讓使用者可以上傳文件並填寫相關資訊
- **配置**:
  - **Form Title**: "文件分析與 Notion 匯入"
  - **Form Fields**:
    - `file`: File Upload（必填）
      - 支援格式：`.pdf`, `.doc`, `.docx`, `.png`, `.jpg`, `.jpeg`, `.webp`
    - `title`: Text（選填）
      - Notion 頁面標題，若未提供則使用文件名稱
    - `notion_database_id`: Text（必填）
      - Notion 資料庫 ID，用於指定要創建頁面的資料庫
- **輸出**: 
  - 表單提交的資料（包含上傳的文件 binary 數據）
  - `file`: Binary 文件數據
  - `title`: 頁面標題（可選）
  - `notion_database_id`: Notion 資料庫 ID

---

### 步驟 2：Extract File / Binary（提取文件）

- **n8n 節點**: `Code` 或 `Set`
- **處理邏輯**: 從 Form Trigger 的輸出中提取文件資訊和相關參數
- **輸入**: Form Trigger 的輸出
- **處理**:
  ```javascript
  const formData = $input.first().json;
  
  // 提取文件資訊
  const fileName = formData.file?.fileName || formData.file?.name || 'document';
  const fileMimeType = formData.file?.mimeType || formData.file?.type || '';
  const fileSize = formData.file?.fileSize || formData.file?.size || 0;
  
  // 提取表單參數
  const pageTitle = formData.title || fileName.replace(/\.[^/.]+$/, ''); // 移除副檔名
  const notionDatabaseId = formData.notion_database_id;
  
  // 驗證必要參數
  if (!notionDatabaseId) {
    throw new Error('Notion Database ID is required');
  }
  
  return {
    fileName: fileName,
    fileMimeType: fileMimeType,
    fileSize: fileSize,
    pageTitle: pageTitle,
    notionDatabaseId: notionDatabaseId,
    // 保留 binary 數據引用
    binaryData: formData.file
  };
  ```
- **輸出**: 
  - `fileName`: 文件名稱
  - `fileMimeType`: 文件 MIME 類型
  - `fileSize`: 文件大小
  - `pageTitle`: Notion 頁面標題
  - `notionDatabaseId`: Notion 資料庫 ID
  - `binaryData`: Binary 數據引用

---

### 步驟 3：Convert to Text（依檔案類型轉換為文字）

- **n8n 節點**: `HTTP Request`
- **處理邏輯**: 使用 DataLabTo API 統一處理多種文件格式，直接轉換為 Markdown 格式
- **適用檔案**: `.pdf`, `.doc`, `.docx`, `.png`, `.jpg`, `.jpeg`, `.webp` 等格式
- **API 端點**: `POST https://www.datalab.to/api/v1/marker`
- **請求設定**:
  - **Method**: POST
  - **URL**: `https://www.datalab.to/api/v1/marker`
  - **Headers**: 
    - `X-API-Key`: DataLabTo API 金鑰（從環境變數或 Credentials 讀取）
  - **Body**: 
    - **Content Type**: `multipart/form-data`
    - **Parameters**:
      - `file`: Binary File
        - **Parameter Type**: `File` 或 `Binary File`
        - **Input Data Field Name**: `data`（來自 Form Trigger 的 binary 數據）
- **輸入**: 步驟 2 的輸出（包含 binary 數據引用）
- **輸出**: DataLabTo API 回傳的 Markdown 格式文字
  - 可能是純文字 Markdown
  - 或 JSON 格式（包含 `markdown` 或 `text` 欄位）
- **錯誤處理**: 
  - 若 API 請求失敗，記錄錯誤並中止流程
  - 回傳明確的錯誤訊息

---

### 步驟 4：Extract Document Text（提取文件文字）

- **n8n 節點**: `Code`
- **處理邏輯**: 從 DataLabTo API 回應中提取 Markdown 文字
- **輸入**: DataLabTo API 的回應
- **處理**:
  ```javascript
  const response = $input.first().json;
  const metadata = $('Extract File / Binary').first().json;
  
  // 處理 DataLabTo API 回應
  let documentText = '';
  
  if (typeof response === 'string') {
    documentText = response;
  } else if (response.markdown) {
    documentText = response.markdown;
  } else if (response.text) {
    documentText = response.text;
  } else if (response.data?.markdown) {
    documentText = response.data.markdown;
  } else {
    // 嘗試提取任何文字內容
    documentText = JSON.stringify(response);
  }
  
  // 驗證文件文字不為空
  if (!documentText || documentText.trim().length === 0) {
    throw new Error('Document text extraction failed. The document may be empty or in an unsupported format.');
  }
  
  return {
    documentText: documentText.trim(),
    pageTitle: metadata.pageTitle,
    notionDatabaseId: metadata.notionDatabaseId,
    fileName: metadata.fileName
  };
  ```
- **輸出**: 
  - `documentText`: 完整的文件 Markdown 文字
  - `pageTitle`: Notion 頁面標題
  - `notionDatabaseId`: Notion 資料庫 ID
  - `fileName`: 原始文件名稱

---

### 步驟 5：Gemini API（分析 → Markdown）

- **n8n 節點**: `HTTP Request` 或 `Google Gemini`（如果 n8n 有內建節點）
- **處理邏輯**: 使用 Gemini API 分析文件內容，生成結構化的 Markdown 文件
- **API 端點**: `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent`
- **請求設定**:
  - **Method**: POST
  - **URL**: `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key={GEMINI_API_KEY}`
  - **Headers**: 
    - `Content-Type`: `application/json`
  - **Body**:
    ```json
    {
      "contents": [{
        "parts": [{
          "text": "{PROMPT}"
        }]
      }],
      "generationConfig": {
        "temperature": 0.3,
        "responseMimeType": "text/plain"
      }
    }
    ```
- **系統 Prompt**:
  ```prompt
  You are an expert document analyst. Your task is to analyze the provided document and generate a well-structured Markdown document.

  INSTRUCTIONS:
  1. Read and understand the entire document content
  2. Identify the main topics, key points, and structure
  3. Generate a comprehensive Markdown document that includes:
     - A clear title (based on the document content)
     - Well-organized sections with appropriate headings
     - Key information extracted and formatted
     - Any important details, lists, or structured data
     - Proper Markdown formatting (headings, lists, code blocks, etc.)

  REQUIREMENTS:
  - Use proper Markdown syntax
  - Organize content with clear hierarchy (H1, H2, H3 headings)
  - Preserve important information from the original document
  - Make the content readable and well-structured
  - If the document contains code, technical specifications, or structured data, format them appropriately

  Document Content:
  {{ $json.documentText }}
  ```
- **輸入**: 步驟 4 的輸出（`documentText`）
- **輸出**: Gemini API 回傳的 Markdown 格式文字
- **錯誤處理**: 
  - 若 API 請求失敗，記錄錯誤並中止流程
  - 回傳明確的錯誤訊息

---

### 步驟 6：Extract Analyzed Markdown（提取分析後的 Markdown）

- **n8n 節點**: `Code`
- **處理邏輯**: 從 Gemini API 回應中提取生成的 Markdown 文字
- **輸入**: Gemini API 的回應
- **處理**:
  ```javascript
  const response = $input.first().json;
  const metadata = $('Extract Document Text').first().json;
  
  // 從 Gemini API 回應中提取文字
  let analyzedMarkdown = '';
  
  if (response.candidates && response.candidates[0]) {
    const candidate = response.candidates[0];
    if (candidate.content && candidate.content.parts && candidate.content.parts[0]) {
      analyzedMarkdown = candidate.content.parts[0].text || '';
    }
  }
  
  if (!analyzedMarkdown && response.text) {
    analyzedMarkdown = response.text;
  }
  
  // 驗證 Markdown 不為空
  if (!analyzedMarkdown || analyzedMarkdown.trim().length === 0) {
    throw new Error('Gemini API did not return valid Markdown content.');
  }
  
  return {
    analyzedMarkdown: analyzedMarkdown.trim(),
    pageTitle: metadata.pageTitle,
    notionDatabaseId: metadata.notionDatabaseId,
    fileName: metadata.fileName
  };
  ```
- **輸出**: 
  - `analyzedMarkdown`: Gemini 生成的 Markdown 內容
  - `pageTitle`: Notion 頁面標題
  - `notionDatabaseId`: Notion 資料庫 ID
  - `fileName`: 原始文件名稱

---

### 步驟 7：整理 Markdown（格式化與優化）

- **n8n 節點**: `Code`
- **處理邏輯**: 整理和優化 Markdown 內容，準備匯入 Notion
- **輸入**: 步驟 6 的輸出
- **處理**:
  ```javascript
  const input = $input.first().json;
  
  // 確保 Markdown 有標題
  let finalMarkdown = input.analyzedMarkdown;
  
  // 如果 Markdown 沒有以 H1 開頭，添加標題
  if (!finalMarkdown.match(/^#\s+/)) {
    finalMarkdown = `# ${input.pageTitle}\n\n${finalMarkdown}`;
  }
  
  // 添加文件資訊（可選）
  const fileInfo = `\n\n---\n\n*原始文件：${input.fileName}*\n*處理時間：${new Date().toISOString()}*`;
  finalMarkdown = finalMarkdown + fileInfo;
  
  return {
    finalMarkdown: finalMarkdown,
    pageTitle: input.pageTitle,
    notionDatabaseId: input.notionDatabaseId
  };
  ```
- **輸出**: 
  - `finalMarkdown`: 整理後的完整 Markdown 內容
  - `pageTitle`: Notion 頁面標題
  - `notionDatabaseId`: Notion 資料庫 ID

---

### 步驟 8：Notion - Create Page（創建 Notion 頁面）

- **n8n 節點**: `Notion`（如果 n8n 有內建節點）或 `HTTP Request`
- **處理邏輯**: 在指定的 Notion 資料庫中創建新頁面，並將 Markdown 內容轉換為 Notion 格式
- **API 端點**: `POST https://api.notion.com/v1/pages`
- **請求設定**:
  - **Method**: POST
  - **URL**: `https://api.notion.com/v1/pages`
  - **Headers**: 
    - `Authorization`: `Bearer {NOTION_API_KEY}`
    - `Notion-Version`: `2022-06-28`
    - `Content-Type`: `application/json`
  - **Body**:
    ```json
    {
      "parent": {
        "database_id": "{{ $json.notionDatabaseId }}"
      },
      "properties": {
        "Name": {
          "title": [
            {
              "text": {
                "content": "{{ $json.pageTitle }}"
              }
            }
          ]
        }
      },
      "children": [
        {
          "object": "block",
          "type": "paragraph",
          "paragraph": {
            "rich_text": [
              {
                "type": "text",
                "text": {
                  "content": "{{ $json.finalMarkdown }}"
                }
              }
            ]
          }
        }
      ]
    }
    ```
  - **注意**: Notion API 需要將 Markdown 轉換為 Notion Block 格式。可以使用第三方工具或 Notion API 的 Markdown 轉換功能
- **輸入**: 步驟 7 的輸出
- **輸出**: Notion API 回傳的頁面資訊
  - `id`: 新創建的頁面 ID
  - `url`: 頁面 URL
- **錯誤處理**: 
  - 若 API 請求失敗，記錄錯誤並中止流程
  - 回傳明確的錯誤訊息

---

## 2. 環境變數與認證 (Environment Variables & Credentials)

### 2.1 環境變數

在 `.env` 文件中設置：

```env
# DataLabTo API Key
DATALABTO_API_KEY=your_datalab_api_key_here

# Google Gemini API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Notion API Key
NOTION_API_KEY=your_notion_api_key_here
```

### 2.2 n8n Credentials

建議在 n8n 中設置以下 Credentials：

1. **DataLabTo API**:
   - Type: Generic Credential Type
   - Fields: `X-API-Key`

2. **Google Gemini API**:
   - Type: Google Gemini API
   - 或使用 URL query parameter: `?key={GEMINI_API_KEY}`

3. **Notion API**:
   - Type: Notion API
   - 或使用 HTTP Header: `Authorization: Bearer {NOTION_API_KEY}`

---

## 3. 錯誤處理機制 (Error Handling)

### 3.1 Form Trigger 驗證失敗

- **觸發條件**: 使用者未上傳文件或未提供必要參數
- **處理方式**: Form Trigger 節點會自動驗證並顯示錯誤訊息

### 3.2 文件轉換失敗

- **觸發條件**: 
  - DataLabTo API 請求失敗
  - 不支援的檔案格式
  - 文件為空或損壞
- **處理方式**: 
  - 記錄錯誤訊息
  - 回傳使用者友好的錯誤訊息
  - 中止流程

### 3.3 Gemini API 分析失敗

- **觸發條件**: 
  - API 請求失敗
  - API 回應格式異常
  - Token 限制超出
- **處理方式**: 
  - 記錄錯誤訊息
  - 回傳使用者友好的錯誤訊息
  - 中止流程

### 3.4 Notion API 創建失敗

- **觸發條件**: 
  - API 請求失敗
  - 資料庫 ID 無效
  - 權限不足
- **處理方式**: 
  - 記錄錯誤訊息
  - 回傳使用者友好的錯誤訊息
  - 可選：將 Markdown 內容保存到本地或其他位置作為備份

---

## 4. 優化建議 (Optimization Suggestions)

### 4.1 效能優化

- **文件大小限制**: 建議在 Form Trigger 中設置文件大小限制（例如 10MB）
- **並行處理**: 如果處理多個文件，可以考慮並行處理
- **快取機制**: 對於相同的文件，可以考慮快取轉換結果

### 4.2 使用者體驗優化

- **進度提示**: 在 Form Trigger 中顯示處理進度
- **錯誤訊息**: 提供清晰、使用者友好的錯誤訊息
- **成功通知**: 創建 Notion 頁面後，可以發送通知（Email、Slack 等）

### 4.3 Notion 格式優化

- **Markdown 轉換**: 考慮使用 Notion API 的 Markdown 轉換功能，或使用第三方工具（如 `notion-md`）
- **頁面屬性**: 可以根據文件類型或內容自動設置 Notion 頁面的屬性（Tags、Status 等）
- **區塊結構**: 優化 Markdown 到 Notion Block 的轉換，確保格式正確

---

## 5. 擴展功能 (Extension Ideas)

### 5.1 多語言支援

- 檢測文件語言
- 使用對應語言的 Prompt
- 生成多語言版本的 Notion 頁面

### 5.2 文件分類

- 根據文件內容自動分類
- 設置對應的 Notion 標籤或屬性
- 路由到不同的 Notion 資料庫

### 5.3 版本控制

- 如果文件已存在，創建新版本而不是新頁面
- 保留處理歷史記錄

### 5.4 批量處理

- 支援一次上傳多個文件
- 並行處理多個文件
- 批量創建 Notion 頁面

---

## 6. 測試建議 (Testing Recommendations)

### 6.1 單元測試

- 測試每個節點的輸入輸出
- 測試錯誤處理邏輯
- 測試不同文件格式的處理

### 6.2 整合測試

- 測試完整流程
- 測試不同大小的文件
- 測試不同類型的文件（PDF、DOC、圖片等）

### 6.3 使用者測試

- 測試表單的使用者體驗
- 測試錯誤訊息的清晰度
- 測試 Notion 頁面的格式和內容

---

## 7. 部署建議 (Deployment Recommendations)

### 7.1 環境設置

- 使用 Docker Compose 部署 n8n
- 設置環境變數文件（`.env`）
- 配置適當的資源限制

### 7.2 監控與日誌

- 設置執行日誌記錄
- 監控 API 使用情況
- 設置錯誤警報

### 7.3 安全性

- 保護 API 金鑰
- 設置適當的權限控制
- 驗證使用者輸入

---

完成！這個規格文件提供了完整的流程說明，包括每個步驟的詳細配置、錯誤處理、優化建議和擴展想法。
