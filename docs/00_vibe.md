# n8n 文件分析與系統架構自動化流程規格

## 0. 文件定位（Purpose）

本 Markdown 作為：

- n8n 自動化流程的**單一真實來源（SSOT）**
- LLM（Gemini / OpenAI）分析文件的 **System / Context Prompt**
- 專案的流程規格與產出模板

**最終目標：**

> 使用者上傳文件或使用 google 雲端
> LLM 分析 → 自動產出包含系統架-構描述與 Mermaid 流程圖的 Markdown 文件。

---

## 1. 詳細工作流程規格 (Detailed Workflow Specification)

### 步驟 1：觸發流程 (Webhook)

- **n8n 節點建議**: `Webhook`
- **處理邏輯**: 建立一個接收檔案上傳的端點。n8n 會自動處理 `multipart/form-data`
  格式的請求。
- **輸入**: 使用者透過 HTTP POST 上傳的檔案。
- **輸出**: 檔案的二進位數據 (Binary Data) 及中繼資料 (Metadata)，如 `fileName`,
  `mimeType`。

---

### 步驟 2：檔案類型判斷與分流 (Routing)

- **n8n 節點建議**: `If`
- **處理邏輯**: 根據上一步輸出的 `mimeType` 或 `fileName`
  的副檔名，決定後續處理路徑。
- **輸入**: `mimeType` (e.g., `application/pdf`, `image/png`, `text/plain`)。
- **輸出**: 將執行流程導向「文字解析」或「圖片 OCR」分支。

---

### 步驟 3A：文字解析 (Text-based File Parsing)

- **適用檔案**: `.txt`, `.md`, `.docx`, 可直接讀取文字的 `.pdf`。
- **n8n 節點建議**: `Read PDF`, `Move Binary Data`, `Function` (用於其他格式)。
- **處理邏輯**: 從檔案中直接提取純文字內容。
- **輸入**: 檔案的二進位數據。
- **輸出**: 包含文件完整內容的純文字字串。

### 步驟 3B：圖片光學辨識 (Image OCR)

- **適用檔案**: `.png`, `.jpg`, `.jpeg`, 掃描件或圖片型 `.pdf`。
- **n8n 節點建議**: `Google Cloud Vision`, 或對外部 OCR API 的 `HTTP Request`。
- **處理邏輯**: 呼叫 OCR 服務，將圖片中的文字轉換為純文字。
- **輸入**: 檔案的二進位數據。
- **輸出**: 包含圖片辨識結果的純文字字串。

---

### 步驟 4：合併與準備 (Merge & Prepare)

- **n8n 節點建議**: `Merge` (若有需要), `Set`
- **處理邏輯**: 將從 3A 或 3B 來的文字結果合併回主流程，並整理成一個變數，準備提交給 LLM。
- **輸入**: 從分支來的純文字字串。
- **輸出**: 一個名為 `document_text` 的變數，內容為完整的文件文字。

---

### 步驟 5：LLM 文件理解與結構化摘要

- **n8n 節點建議**: `Gemini` / `OpenAI`
- **處理邏輯**: 這是第一個 LLM 呼叫。目標是讓 LLM 閱讀全文，並抽取出後續步驟所需的關鍵資訊，以結構化格式 (JSON) 回傳，避免後續 LLM 重複閱讀全文。
- **輸入**: `document_text` 變數。
- **關鍵 Prompt**:

  ```prompt
  You are an expert system analyst. Read the following document and produce a concise, structured summary focusing on key entities, processes, and their relationships. This summary will be used to generate system architecture diagrams. Output in JSON format with keys: "main_goal", "actors", "systems", "core_processes".

  Document:
  {{ $json.document_text }}
  ```

- **輸出**: 一個名為 `structured_summary` 的 JSON 物件。

---

### 步驟 6：LLM 系統架構生成

- **n8n 節點建議**: `Gemini` / `OpenAI`
- **處理邏輯**: 這是第二個 LLM 呼叫。利用上一步的結構化摘要，生成人類可讀的系統架構描述。
- **輸入**: `structured_summary` JSON 物件。
- **關鍵 Prompt**:

  ```prompt
  Based on the following system summary, describe the high-level system architecture. Identify the main components, their responsibilities, and how they interact. The output should be in clear Markdown.

  System Summary:
  {{ JSON.stringify($json.structured_summary) }}
  ```

- **輸出**: 一個名為 `architecture_markdown` 的 Markdown 格式文字。

---

### 步驟 7：LLM 流程圖生成 (Mermaid)

- **n8n 節點建議**: `Gemini` / `OpenAI`
- **處理邏輯**: 這是第三個 LLM 呼叫。同樣利用結構化摘要，生成 Mermaid.js 語法的流程圖。
- **輸入**: `structured_summary` JSON 物件。
- **關鍵 Prompt**:

  ````prompt
  Based on the following system summary, generate a Mermaid.js flowchart diagram that illustrates the main process flow. The diagram should start with the initial user action and follow the sequence of events. Only output the Mermaid code block, starting with ```mermaid and ending with ```.

  System Summary:
  {{ JSON.stringify($json.structured_summary) }}
  ````

- **輸出**: 一個名為 `mermaid_code` 的字串，包含完整的 Mermaid 語法。

---

### 步驟 8：最終產出組合

- **n8n 節點建議**: `Set` 或 `Function`
- **處理邏輯**: 將步驟 6 和 7 的結果組合成一個完整的 Markdown 文件。
- **輸入**: `architecture_markdown` 和 `mermaid_code`。
- **輸出**: 一個名為 `final_markdown` 的變數，內容為組合後的完整 Markdown。

  ```
  ## 系統架構分析

  {{ $json.architecture_markdown }}

  ## 流程圖

  {{ $json.mermaid_code }}
  ```

---

### 步驟 9：回傳或儲存結果

- **n8n 節點建議**: `Respond to Webhook` 或 `Write Binary File`
- **處理邏輯**: 將最終的 Markdown 文件作為 Webhook 的回應直接回傳給使用者，或儲存到伺服器指定位置。
- **輸入**: `final_markdown`。
- **輸出**: 成功訊息或檔案。
