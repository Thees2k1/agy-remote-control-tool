# Universal Agent-Bridge Interface (UABI) Specification

## Status: Draft v1.0 (Milestone 1.1)

## 1. Overview
The **Universal Agent-Bridge Interface (UABI)** defines the canonical, language-agnostic wire protocols and Data Transfer Objects (DTOs) for Mobile Remote Control. It establishes clean boundaries between:
1. **Agent Lifecycle Hooks** (`PreToolUse`, `PostToolUse`).
2. **Core Daemon IPC** (`/request_approval`, `/resolve`, `/health`).
3. **Multi-Client Provider Adapters** (Telegram, Discord, Web Push).

---

## 2. Agent Hook Wire Protocol (Protojson)

### 2.1 PreToolUse Hook Input (stdin)
The JSON structure passed by `OneHarness` (`agy.exe`) into the `PreToolUse` hook via standard input:

```json
{
  "conversationId": "374fc101-adfd-4249-9253-7c96c3eadccc",
  "stepIdx": 2,
  "modelName": "gemini-3.8-flash-medium",
  "lastUserInput": "Run test suite",
  "artifactDirectoryPath": "C:/Users/tongn/.gemini/antigravity-cli/brain/...",
  "transcriptPath": "C:/Users/tongn/.gemini/.../transcript_full.jsonl",
  "workspacePaths": ["C:/Users/tongn/projects/my-app"],
  "toolCall": {
    "name": "run_command",
    "args": {
      "CommandLine": "fvm flutter test",
      "Cwd": "C:/Users/tongn/projects/my-app",
      "toolSummary": "Run flutter unit tests"
    }
  }
}
```

### 2.2 PreToolUse Hook Output (stdout)
The hook must return a strict protojson dictionary on standard output:

```json
{
  "decision": "allow",
  "reason": "Approved via Mobile Remote Control (Telegram)",
  "permissionOverrides": [
    "command(fvm flutter test)"
  ]
}
```

#### Field Specifications:
| Field | Type | Required | Values / Description |
| :--- | :--- | :--- | :--- |
| `decision` | `string` | **Yes** | `"allow"` (permit), `"deny"` (abort tool call), `"ask"` (defer to native terminal UI). |
| `reason` | `string` | No | Human-readable explanation logged in agent transcript. |
| `permissionOverrides` | `string[]` | No | Overrides requested standard permission resources (only evaluated when decision is `"ask"`). |

> [!WARNING]
> Do NOT emit custom fields such as `hookSpecificOutput`. They violate Google's internal Protobuf unmarshaling contract and cause hook failures.

---

## 3. Daemon IPC REST Protocol (127.0.0.1:48201)

### 3.1 `POST /request_approval`
Dispatched by the bridge when a tool call requires remote authorization.

#### Request Body:
```json
{
  "req_id": "a1b2c3d4",
  "payload": { "...": "Full PreToolUse hook payload" },
  "timeout_seconds": 90,
  "auto_accept_eligible": true
}
```

#### Response Body (200 OK):
```json
{
  "req_id": "a1b2c3d4",
  "decision": "allow",
  "source": "Telegram (@antiex_bot)",
  "reason": "Decision: ALLOW via Telegram (@antiex_bot)"
}
```

### 3.2 `POST /resolve`
Called by local workstation keyboard listener or external webhook to resolve a pending request early.

#### Request Body:
```json
{
  "req_id": "a1b2c3d4",
  "decision": "allow",
  "source": "Workstation Keyboard [Y]"
}
```

#### Response Body (200 OK):
```json
{
  "status": "resolved",
  "req_id": "a1b2c3d4",
  "decision": "allow"
}
```

---

## 4. Provider Adapter Interface (M1.5+)

Providers (Telegram, Discord, Web Push) implement this interface to remain completely decoupled from daemon internals:

```typescript
interface ProviderAdapter {
  id: string; // "telegram" | "discord" | "webpush"
  
  // Format tool payload into provider-native message format
  formatMessage(payload: ToolCallPayload): ProviderMessage;
  
  // Dispatch outbound notification with interactive actions
  sendApprovalRequest(request: ApprovalRequest): Promise<MessageRef>;
  
  // Update existing notification when resolved or expired
  updateMessageStatus(ref: MessageRef, status: ResolutionStatus): Promise<void>;
  
  // Listen for inbound user actions (callbacks / interactions)
  startListening(onAction: (action: UserAction) => void): Promise<void>;
  stopListening(): Promise<void>;
}
```
