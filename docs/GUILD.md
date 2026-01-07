# Gemini CLI 本地代理開發指導文件

## 一、專案目標

本專案旨在建立一個 **OpenAI API 相容的 Proxy Server**，接收外部（例如瀏覽器外掛、ChatGPT Sider、沉浸式翻譯等）以 OpenAI API 形式發出的請求，並於本地端透過 **Gemini CLI** 執行推論，將結果包裝回 OpenAI API 格式後回傳。

此設計可避免依賴雲端 Gemini API，減少 Free Tier 配額受限問題，同時保留既有外掛與應用相容性。

---

## 二、系統架構概述

```
瀏覽器外掛 / 外部應用
        │  (OpenAI API)
        ▼
  [本地 Proxy Server]
        │  (spawn 子程序)
        ▼
      Gemini CLI
        │
        ▼
     Gemini 模型輸出
```

### 核心組件

1. **Proxy Server**

   * 接收 OpenAI API 格式請求 (`/v1/chat/completions`、`/v1/models`)
   * 驗證 Token、處理 CORS
   * 組裝 prompt，呼叫 Gemini CLI
   * 解析 CLI 輸出、回傳 OpenAI 樣式回應

2. **Gemini CLI**

   * 實際執行模型推論
   * 以 `--output-format json` 或 `stream-json` 提供可機器解析結果

---

## 三、API 相容規格

### 1. `GET /v1/models`

回傳可用模型清單（映射表）：

```json
{
  "object": "list",
  "data": [
    {"id": "gpt-3.5-turbo", "object": "model"},
    {"id": "gpt-4", "object": "model"}
  ]
}
```

範例映射：

| 外部請求模型        | 實際執行模型           |
| ------------- | ---------------- |
| gpt-3.5-turbo | gemini-2.5-flash |
| gpt-4         | gemini-2.5-pro   |

---

### 2. `POST /v1/chat/completions`

支援參數：

* `model`：映射到對應 Gemini 模型
* `messages`：對話歷史
* `stream`：可選，布林值
* 其他（`temperature`, `top_p`, `max_tokens` 等）可忽略但需容忍

範例回應：

```json
{
  "id": "chatcmpl-001",
  "object": "chat.completion",
  "created": 1730000000,
  "model": "gpt-4",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "這是 Gemini CLI 回覆"},
      "finish_reason": "stop"
    }
  ]
}
```

---

## 四、Prompt 組裝規則

將 OpenAI `messages` 轉為 CLI prompt：

```
[System]
你是翻譯助理，輸出繁體中文。

[User]
請翻譯以下內容：Hello world.

[Assistant]
你好，世界。
```

處理邏輯：

* `system` 放最前
* 依序拼接 `user`、`assistant`
* 設定最大對話長度以防 prompt 過長

---

## 五、Gemini CLI 呼叫與輸出解析

### 1. 非串流（初版建議）

```bash
gemini -p "<prompt>" -m "<model>" --output-format json
```

解析 JSON 中 `.response` 欄位。

### 2. 串流模式（進階）

```bash
gemini --output-format stream-json -p "<prompt>"
```

解析 JSONL 事件流（type 為 `message` 時輸出內容），轉成 OpenAI SSE `delta` 格式。

---

## 六、串流實作策略

### 階段一：假串流

1. CLI 完整輸出後再切成片段送出
2. 使用 SSE（Server-Sent Events）模擬「逐字輸出」

### 階段二：真串流

1. 解析 CLI `--output-format stream-json` 的 JSONL
2. 即時轉發內容（`type=message`）成 OpenAI `delta` 格式

---

## 七、安全性建議

Gemini CLI 曾有安全性議題，應採以下防護措施：

* 使用 `--sandbox` 模式，隔離命令執行
* 禁用 `--yolo`（避免自動允許工具調用）
* 每次推論在臨時資料夾執行
* Proxy Server 加入：

  * **Bearer Token 驗證**
  * **CORS 限制**
  * **Request Rate Limit**
* 僅允許本機或信任來源訪問

---

## 八、錯誤與日誌機制

紀錄：

* `request_id`、`client_ip`、`user_agent`
* 請求模型、實際映射模型
* Gemini CLI 的 exit code、stderr 摘要
* 執行延遲時間、token 統計

錯誤映射：

| 類型       | CLI 狀況         | OpenAI error.code         |
| -------- | -------------- | ------------------------- |
| 解析失敗     | stdout 非 JSON  | `invalid_response_format` |
| CLI 執行錯誤 | exit code != 0 | `model_error`             |
| 超時       | 無輸出超過 timeout  | `timeout`                 |

---

## 九、專案開發里程碑

### Milestone A：MVP

* [ ] `GET /v1/models` 實作
* [ ] `POST /v1/chat/completions`（非串流）
* [ ] prompt 組裝邏輯
* [ ] CLI 呼叫 + JSON 解析
* [ ] CORS 與 Bearer token 驗證

### Milestone B：相容性強化

* [ ] 支援 `stream=true`（假串流）
* [ ] Rate Limit 管控
* [ ] Request 錯誤處理與重試機制

### Milestone C：進階功能

* [ ] 真串流（`stream-json` → SSE）
* [ ] 回傳 usage 欄位（token 統計）
* [ ] 完善模型對應設定檔

---

## 十、專案結構建議

```
/README.md
/docs/
  ├─ architecture.md
  ├─ api-compat.md
  ├─ prompting.md
  ├─ streaming.md
  ├─ security.md
  └─ operations.md
/src/
  ├─ server.ts        # 主伺服器
  ├─ routes/
  │   ├─ models.ts
  │   └─ chat.ts
  ├─ adapters/
  │   └─ gemini_cli.ts
  └─ utils/
      └─ prompt_builder.ts
/tests/
  ├─ integration/
  └─ unit/
```

---

## 十一、參考資料

| 主題                                                        | 文件來源                                                                               |
| --------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Gemini CLI 官方文件（含 `--output-format json` / `stream-json`） | [Google Developers 官方 CLI 文件]                                                      |
| Gemini CLI 使用安全模式與參數                                      | 官方 CLI 指令說明 (`gemini --help`)                                                      |
| OpenAI Chat Completions API 規格                            | [OpenAI API Reference](https://platform.openai.com/docs/api-reference/chat/create) |
| 參考專案 `snailyp/gemini-balance`                             | GitHub: [snailyp/gemini-balance](https://github.com/snailyp/gemini-balance)        |
| Node.js child_process 文件                                  | [Node.js 官方文件](https://nodejs.org/api/child_process.html)                          |

---

## 十二、補充建議

1. **使用 Node.js 實作 Proxy**

   * 方便直接呼叫 Gemini CLI（npm 套件相容）
   * 可用 `express` + `child_process.spawn` 搭配 `EventSource` 串流

2. **部署與使用**

   * 預設監聽 `http://127.0.0.1:11434`
   * 瀏覽器外掛改 `Base URL` 即可接入

3. **CLI 模型設定檔**

   * 透過 JSON/YAML 管理模型映射，例如：

     ```json
     {
       "gpt-3.5-turbo": "gemini-2.5-flash",
       "gpt-4": "gemini-2.5-pro"
     }
     ```

---
