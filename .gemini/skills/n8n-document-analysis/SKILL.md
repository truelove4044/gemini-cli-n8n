# n8n Document Analysis Skill

## Description
Specialized skill for analyzing documents and generating system architecture using n8n workflows with Gemini integration. This skill understands the complete workflow from document upload to final Markdown output with Mermaid diagrams.

## When to Use
Use this skill when the user:
- Uploads documents (PDF, DOC, images) for analysis
- Requests system architecture generation from documents
- Needs guidance on n8n workflow implementation
- Asks about document conversion processes
- Wants to understand the document analysis pipeline

## Instructions

### Workflow Overview
1. **Document Upload**: Receive file via Webhook (multipart/form-data)
2. **Mode Extraction**: Extract analysis mode (strict_system_design or exploratory_architecture)
3. **Document Conversion**: Use DataLabTo API to convert document to Markdown
4. **Text Extraction**: Extract and prepare document text
5. **Validation**: Validate document text is not empty
6. **Structured Summary**: Generate JSON summary with main_goal, actors, systems, core_processes
7. **Summary Validation**: Parse and validate summary (strict mode requires all fields)
8. **Parallel Processing**: Generate architecture description and Mermaid diagram in parallel
9. **Mermaid Validation**: Validate Mermaid syntax, retry if needed (max 2-3 times)
10. **Final Output**: Combine results into final Markdown document

### Key Rules (from docs/01_rules.md)

#### Analysis Modes
- **strict_system_design**: 
  - PROHIBITED from inferring or guessing
  - Must use "Document not provided" for missing info
  - Workflow MUST abort if required fields are missing
  
- **exploratory_architecture**:
  - May make reasonable deductions
  - MUST label deductions as "Inferred" or "Assumption"

#### Mermaid Requirements
- Must start with ```mermaid and end with ```
- No text outside code block
- Must contain valid Mermaid keywords (flowchart, graph, etc.)
- Automatic retry on validation failure (2-3 attempts)

#### Document Conversion
- MUST use DataLabTo API (POST https://www.datalab.to/api/v1/marker)
- Supports: PDF, DOC, DOCX, PNG, JPG, JPEG, WEBP
- API key must be stored in n8n Credentials
- Output must be Markdown format

### Implementation Details

#### n8n Nodes Used
- Webhook: Receive file uploads
- Set: Extract mode, prepare variables
- HTTP Request: DataLabTo API call
- Code: Parse JSON, validate content
- If: Route based on validation results
- Loop: Retry mechanism for Mermaid validation
- Google Gemini Chat: LLM calls for analysis
- Merge: Combine parallel outputs
- Respond to Webhook: Return final result

#### Error Handling
- DataLabTo API failure → Abort workflow
- Empty document text → Abort workflow
- JSON parse failure → Abort workflow
- Missing required fields (strict mode) → Abort workflow
- Mermaid validation failure → Retry (max 2-3 times) → Abort if still fails

## Resources
- **Workflow Specification**: `docs/00_vibe.md` - Complete workflow steps and prompts
- **Rules and Constraints**: `docs/01_rules.md` - Mandatory rules for all workflows
- **Reference Workflows**: 
  - `workflow/document_conversion_workflow.json` - Full workflow
  - `workflow/stage1_basic_webhook.json` - Webhook setup
  - `workflow/stage2_file_upload.json` - File upload handling
  - `workflow/stage3_llm_summary.json` - LLM summary generation
  - `workflow/stage4_validation.json` - Validation logic

## Example Prompts

When user asks:
- "分析這個文件並生成系統架構圖" → Use this skill
- "幫我建立文件分析的 n8n workflow" → Use this skill
- "如何處理 PDF 文件轉換？" → Use this skill
- "Mermaid 流程圖驗證失敗怎麼辦？" → Use this skill

## Output Format

Final output must be Markdown with:
1. System architecture analysis (from LLM)
2. Mermaid flowchart diagram (validated and cleaned)

Format:
```markdown
## 系統架構分析

[Architecture description]

## 流程圖

```mermaid
[Validated Mermaid code]
```
```

## Important Notes
- Always follow docs/01_rules.md as the highest priority
- Mermaid validation is mandatory (step 8.5)
- DataLabTo API is the only allowed conversion method
- API keys must be stored securely in n8n Credentials
- Retry mechanisms are built-in for Mermaid generation
