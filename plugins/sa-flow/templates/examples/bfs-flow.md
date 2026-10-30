> 本檔是 `templates/bfs.md` 的範例集，**按需讀取**：撰寫該章且不確定寫法時才讀。

# BFS §3／§4 流程圖 — 完整範例

對應 `templates/bfs.md` §3.1～§3.5、§4.1、§4.2、§4.3 的完整範例（模板內已改為骨架＋指路註解）。

## §3.1 整體資料流程圖 完整範例

```mermaid
flowchart LR
    subgraph Client["前端/外部系統"]
        A[API Request]
    end

    subgraph Backend["後端系統"]
        B[Controller] --> C[業務邏輯層]
        C --> D{業務驗證}
        D -->|通過| E[Repository]
        D -->|失敗| F[回傳錯誤]
        E --> G[(Database)]
    end

    A --> B
    F --> A
    G --> E --> C --> B --> A
```

## §3.2 新增資料流程 完整範例

```mermaid
sequenceDiagram
    participant C as Client
    participant Ctrl as Controller
    participant V as Validator
    participant H as 業務邏輯
    participant R as Repository
    participant DB as Database

    C->>Ctrl: POST /api/{Area}/{Entity}
    Ctrl->>V: Validate Request
    alt 驗證失敗
        V-->>Ctrl: ValidationException
        Ctrl-->>C: 400 Bad Request
    else 驗證通過
        V-->>Ctrl: Valid
        Ctrl->>H: Send Command
        H->>H: 執行業務邏輯
        H->>R: AddAsync(entity)
        R->>DB: INSERT
        DB-->>R: Success
        R-->>H: Entity
        H-->>Ctrl: Response
        Ctrl-->>C: 201 Created
    end
```

## §3.3 修改資料流程 完整範例

```mermaid
sequenceDiagram
    participant C as Client
    participant Ctrl as Controller
    participant V as Validator
    participant H as 業務邏輯
    participant R as Repository
    participant DB as Database

    C->>Ctrl: PUT /api/{Area}/{Entity}/{id}
    Ctrl->>V: Validate Request
    alt 驗證失敗
        V-->>Ctrl: ValidationException
        Ctrl-->>C: 400 Bad Request
    else 驗證通過
        Ctrl->>H: Send Command
        H->>R: GetByIdAsync(id)
        R->>DB: SELECT
        alt 資料不存在
            DB-->>R: null
            R-->>H: null
            H-->>Ctrl: NotFoundException
            Ctrl-->>C: 404 Not Found
        else 資料存在
            DB-->>R: Entity
            R-->>H: Entity
            H->>H: 執行業務邏輯
            H->>R: UpdateAsync(entity)
            R->>DB: UPDATE
            DB-->>R: Success
            R-->>H: Entity
            H-->>Ctrl: Response
            Ctrl-->>C: 200 OK
        end
    end
```

## §3.4 刪除資料流程 完整範例

```mermaid
sequenceDiagram
    participant C as Client
    participant Ctrl as Controller
    participant H as 業務邏輯
    participant R as Repository
    participant DB as Database

    C->>Ctrl: DELETE /api/{Area}/{Entity}/{id}
    Ctrl->>H: Send Command
    H->>R: GetByIdAsync(id)
    R->>DB: SELECT
    alt 資料不存在
        DB-->>R: null
        R-->>H: null
        H-->>Ctrl: NotFoundException
        Ctrl-->>C: 404 Not Found
    else 資料存在
        DB-->>R: Entity
        R-->>H: Entity
        H->>H: 檢查關聯資料
        alt 有關聯資料
            H-->>Ctrl: BusinessException
            Ctrl-->>C: 400 Bad Request
        else 無關聯資料
            H->>R: DeleteAsync(id)
            R->>DB: DELETE/UPDATE DELETED_FLAG
            DB-->>R: Success
            R-->>H: void
            H-->>Ctrl: Success
            Ctrl-->>C: 204 No Content
        end
    end
```

## §3.5 查詢資料流程 完整範例

```mermaid
sequenceDiagram
    participant C as Client
    participant Ctrl as Controller
    participant H as 業務邏輯
    participant R as Repository
    participant DB as Database

    C->>Ctrl: GET /api/{Area}/{Entity}/Paged?params
    Ctrl->>H: Send Query
    H->>R: GetPagedAsync(request)
    R->>DB: SELECT with pagination
    DB-->>R: Data + Count
    R-->>H: PagedResponse
    H-->>Ctrl: Response
    Ctrl-->>C: 200 OK
```

## §4.1 主要業務流程 完整範例

```mermaid
flowchart TD
    subgraph 使用者操作
        A[開始] --> B[輸入資料]
        B --> C[送出請求]
    end

    subgraph 系統處理
        C --> D{資料驗證}
        D -->|驗證失敗| E[顯示錯誤訊息]
        E --> B
        D -->|驗證通過| F{業務規則檢查}
        F -->|不符合| G[顯示業務錯誤]
        G --> B
        F -->|符合| H[執行資料庫操作]
        H --> I{是否需要通知}
        I -->|是| J[發送通知]
        I -->|否| K[回傳成功]
        J --> K
    end

    subgraph 後續處理
        K --> L[更新前端狀態]
        L --> M[結束]
    end
```

## §4.2 狀態流程圖 完整範例

<!--
說明：如果功能涉及狀態變化，狀態定義以 §2.4 表為準
-->

```mermaid
stateDiagram-v2
    [*] --> 草稿: 建立
    草稿 --> 待審核: 送審
    待審核 --> 已核准: 核准
    待審核 --> 退回: 退回
    退回 --> 草稿: 修改重送
    已核准 --> 已完成: 執行完成
    草稿 --> [*]: 刪除
    已完成 --> [*]
```

## §4.3 排程同步流程 完整範例

```mermaid
flowchart TD
    subgraph Phase1["第一階段：資料同步"]
        A1["排程觸發"] --> A2["查詢待處理資料"]
        A2 --> A3["寫入 Shadow 表"]
        A3 --> A4["轉換並寫入目標"]
        A4 --> A5["更新 MpStatus = 'P'"]
        A5 --> A6["註冊狀態回寫 Job"]
    end

    A6 --> B1

    subgraph Phase2["第二階段：狀態回寫"]
        B1["查詢待回寫記錄"] --> B2["讀取目標系統結果"]
        B2 --> B3{"處理結果"}
        B3 -->|成功| B4["ErpStatus = 'S'"]
        B3 -->|失敗| B5["ErpStatus = 'E'"]
    end
```
