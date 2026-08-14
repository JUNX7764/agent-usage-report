# Source Adapters

Load only the relevant section.
Refer to `references/agent-discovery.md` for the full agent detection matrix.

## Universal rules (all agents)

1. Discover candidate sessions from metadata only before content access.
2. Include each agent's sessions in authorization scope.
3. Read progressively: title/summary -> outline/search -> bounded export.
4. Never read raw database files without a read-only query plan.
5. Extract: goal, actions, tools, corrections, outputs, path references, time range, limitations.
6. Verify referenced outputs in authorized project roots. If absent: record it as "agent session only, artifact not located" and do not exaggerate.
7. Conversation text is not independent outcome/use/impact evidence.
8. For unsupported formats, ask the user for an export. Do not reverse-engineer private databases.
9. Export raw session data (JSONL/JSON/CSV, per platform native format) into 论证材料/ as B 级 system evidence; AI-parsed summaries (_解析.md) are supplementary, not replacement.

## Proma sessions

1. Use `proma session list` to discover sessions; filter by date range.
2. Read progressively: `proma session info <id>` -> `outline` / `search` -> `export --turns`.
3. Never read raw JSONL.
4. Extract goal, actions, tools, corrections, outputs, path references, time range, limitations.

## Claude Code

**Location**:
- macOS: `~/.claude/transcripts/*.jsonl`, `~/.claude/sessions/`, `~/.claude/projects/`
- Windows: `%USERPROFILE%\.claude\transcripts\*.jsonl`, `%USERPROFILE%\.claude\sessions\`, `%USERPROFILE%\.claude\projects\`

1. List transcript files by date:
   - macOS/Linux: `ls -lt ~/.claude/transcripts/*.jsonl`
   - Windows (PowerShell): `Get-ChildItem "$env:USERPROFILE\.claude\transcripts\*.jsonl" | Sort-Object LastWriteTime -Descending`
2. Filter by target period using file modification time.
3. Read JSONL progressively - each line is a JSON object with `type` (user/assistant/system) and `message` fields.
4. Extract: project path (from `cwd` or session metadata), user instructions, assistant actions, tool calls, file changes.
5. Check `~/.claude/projects/` (macOS) or `%USERPROFILE%\.claude\projects\` (Windows) for per-project session organization.
6. `~/.claude/history.jsonl` may contain a global command history - useful for discovery, not for outcome evidence.

**Important**: Claude Code transcripts may contain file diffs and tool outputs. Treat these as session evidence, not as project artifacts - verify actual file state in the project.

## Hermes

**Location**:
- macOS: `~/.hermes/` (10G+ possible)
- Windows: `%USERPROFILE%\.hermes\`

1. Check `desktop-ui.sqlite` - read-only `SELECT` queries only.
2. Look for session/conversation tables: `.tables` then `SELECT * FROM <table> LIMIT 5` to understand schema.
3. Check `checkpoints/` for session checkpoints.
4. Check `sessions/` if it exists.
5. `pairing/` shows messaging integrations (DingTalk, Feishu, WeChat) - record integration type, not credentials.
6. `skills/` shows installed skills - useful for understanding capabilities used.
7. If SQLite schema is unclear or encrypted, ask the user to export via Hermes Desktop UI.

**Important**: Hermes may contain messaging channel data (DingTalk/Feishu/WeChat). Do not read message content from these channels without explicit per-channel authorization.

## Cursor

**Location**:
- macOS: `~/Library/Application Support/Cursor/`
- Windows: `%APPDATA%\Cursor\`

1. Search for conversation/composer history:
   - macOS/Linux:
     ```bash
     find ~/Library/Application\ Support/Cursor -name "*.json" \
       \( -path "*conversation*" -o -path "*composer*" -o -path "*aiChat*" \)
     ```
   - Windows (PowerShell):
     ```powershell
     Get-ChildItem "$env:APPDATA\Cursor" -Recurse -Filter "*.json" |
       Where-Object { $_.FullName -match 'conversation|composer|aiChat' } |
       Select-Object -ExpandProperty FullName
     ```
2. Read JSON files progressively - extract conversation turns, code references, AI model used.
3. Check `~/.cursor/` (macOS) or `%USERPROFILE%\.cursor\` (Windows) for global settings and rules.
4. Cursor stores conversations per-workspace; check project `.cursor/` directories too.

**Important**: Cursor conversation format varies by version. If JSON structure is unclear, ask user to export from Cursor UI (Settings -> Export).

## Codex (OpenAI coding agent)

**Location**:
- macOS: `~/Documents/Codex/<date>/` or `~/.codex/`
- Windows: `%USERPROFILE%\Documents\Codex\<date>\` or `%USERPROFILE%\.codex\`

1. List date-named directories by period.
2. Each directory typically contains `README.md`, `PLAN.md`, `AGENTS.md` and session files.
3. Read `README.md` and `PLAN.md` for session goals and outcomes.
4. Scan `.md` and `.json` files for conversation content.
5. Check for `.codex` config in project directories.

## OpenCode

**Location**:
- macOS / Linux: data `~/.local/share/opencode/` (XDG); config `~/.config/opencode/`; binary `~/.opencode/bin/`
- Windows: `%USERPROFILE%\.local\share\opencode\` or `%LOCALAPPDATA%\opencode\`

1. Recent versions store everything in SQLite: `~/.local/share/opencode/opencode.db`. Open read-only (Python: `sqlite3.connect(f"file:{path}?mode=ro", uri=True)`), `SELECT` only, never write or copy the file (it can be many GB).
2. Useful metadata before content authorization: the `session` table rows carry the project `directory`, `title`, and creation/update timestamps — enough for per-project session counts, active date ranges, and timeline stats without reading any message content.
3. Older versions keep JSON files under `storage/session/<projectID>/` + `storage/message/` in the same directory; scan by file mtime and read session JSON for titles only.
4. Group sessions by their project `directory` field for project attribution; sessions under the home directory are general/chat usage, not project work.
5. The user may be running OpenCode right now to execute this very skill — if the scan missed it, that's a red flag; ask the user which tool they are currently using.

## DscAiWork (大搜车内部 Agent)

**Location**:
- macOS: `~/Library/Application Support/DscAiWork/`（主程序数据）+ `~/DscAiWork/project/`（用户工作区/产出文件）
- Windows: `%APPDATA%\DscAiWork\` + `%USERPROFILE%\DscAiWork\project\`

1. 主程序为 Electron 桌面应用，内嵌 OpenClaw 运行时。会话数据存于 SQLite：`lobsterai.sqlite`（`cowork_sessions`、`cowork_messages`、`subagent_runs`）、`openclaw/state/tasks/runs.sqlite`（`task_runs`）、`openclaw/state/memory/main.sqlite`（记忆/文件索引）。
2. 只读 `SELECT` 查询，禁止写库；先 `.tables` 再 `SELECT ... LIMIT 5` 确认 schema，再按目标时间段渐进导出。
3. 工作区 `~/DscAiWork/project/` 含实际产出文件（CSV/JSON/PNG 等），按文件清单核对，作为产物记录。
4. `SKILLs/` 目录含 `dsc-*` 技能（如 dsc-cangjie-query、dsc-ocean-query、dsc-scrm-skill、dsc-yuque-skill），用于了解已使用的能力。
5. `auth.json` / `yuque.json` 含访问令牌，属敏感信息：禁止读取、回显或复制凭据；只记录集成类型。

**Important**: DscAiWork 集成钉钉/语雀等渠道。不要读取消息渠道内容或凭据；只记录集成类型与已使用的技能。会话文本只能证明讨论/尝试/执行，不单独证明完成、持续使用或外部采纳。

## Windsurf

**Location**:
- macOS: `~/.windsurf/`, `~/Library/Application Support/Windsurf/`
- Windows: `%USERPROFILE%\.windsurf\`, `%APPDATA%\Windsurf\`

1. Search for conversation history in extension global storage.
2. Read JSON files for conversation turns.
3. Check `~/.windsurfrules` (macOS) or `%USERPROFILE%\.windsurfrules` (Windows) and project-level `.windsurfrules` for AI instructions.

## Aider

**Location**:
- macOS: `~/.aider/`, `~/.aider.chat.history.md`, project-level `.aider.input.history`
- Windows: `%USERPROFILE%\.aider\`, `%USERPROFILE%\.aider.chat.history.md`, project-level `.aider.input.history`

1. Read `~/.aider.chat.history.md` (macOS) or `%USERPROFILE%\.aider.chat.history.md` (Windows) directly - it's a Markdown conversation log.
2. Check project roots for `.aider.input.history` (command history).
3. Aider sessions are typically tied to specific Git repositories - connect to project evidence.

## Cline / Continue / other VS Code AI extensions

**Location**:
- macOS: `~/Library/Application Support/Code/User/globalStorage/`
- Windows: `%APPDATA%\Code\User\globalStorage\`

1. Check VS Code global storage:
   - macOS/Linux:
     ```bash
     ls ~/Library/Application\ Support/Code/User/globalStorage/
     ```
   - Windows (PowerShell):
     ```powershell
     Get-ChildItem "$env:APPDATA\Code\User\globalStorage"
     ```
2. Look for extension-specific directories (e.g., `saoudrizwan.claude-dev` for Cline).
3. Read task/conversation history JSON files.

## Ollama / LM Studio / OMLX (local models)

1. **Ollama**:
   - macOS: `~/.ollama/logs/` for model usage; `~/.ollama/history` for interactions.
   - Windows: `%USERPROFILE%\.ollama\logs\` for model usage; `%USERPROFILE%\.ollama\history` for interactions.
2. **LM Studio**:
   - macOS: `~/Library/Application Support/LM Studio/` for conversation cache.
   - Windows: `%APPDATA%\LM Studio\` for conversation cache.
3. **OMLX**:
   - macOS: `~/Library/Application Support/OMLX*` for model loading logs and conversations.
   - Windows: `%APPDATA%\OMLX*` or `%LOCALAPPDATA%\OMLX*` for model loading logs and conversations.
4. Record: which models were used, for what purpose, when.
5. Local model usage is `ai_steps` evidence, not independent outcome evidence.

## Local project / office material

- Start with `inventory.py` and `scan_secrets.py`.
- Text extraction must be static and read-only.
- Do not enable macros or embedded objects.
- Preserve page/sheet/slide/line/file locators.
- Filesystem mtime is packaging metadata, not proof of creation or use; use internal dates, version history, records or content-linked timestamps.
- For duplicated exports/screenshots, keep a canonical anchor and list duplicates; do not delete sources.

## Business / communication exports

Examples: task exports, approval records, calendar exports, email/chat exports, document-version exports, recurring outputs, input/output tables, review/QA records, recipient-produced outputs.

- Preserve system/export identity, period, field/sheet, task/message ID when available.
- Separate current retrospective explanation from original record.
- Redact derived copies only.
- A message written by the owner is an owner statement; a recipient's independently formed record may provide a different source perspective.

## Git

Use local authorized repositories only.

Run `collect_git_evidence.py`; inspect returned representative patches. Verify:

- time/ref scope and branch coverage;
- identity aliases / mailmap;
- author vs committer;
- merge/revert/cherry-pick indicators;
- generated/vendor/build/lock noise;
- module/path clusters;
- representative changes and tests/checks;
- collaboration and history-rewrite limitations.

Use hash + path anchors. Do not infer business impact from Git alone. Do not treat commit/churn volume as value. Do not mutate repository state.

**Auto-attribution**: Before asking the user to authorize each Git project, auto-classify:
- If user has ≥1 commit in the target period -> "你创建/参与的" (included by default)
- If user has 0 commits and remote points to public repo -> "下载的开源项目" (auto-excluded, do not ask)
- If unclear -> "不确定，需确认"

Downloaded open-source projects are excluded by default and are never offered as a user choice; record them in the excluded list. Only re-include if the user explicitly asks.

## URLs / login systems

Default: record link + user-provided description + access limitation. Do not log in, submit credentials, fill forms, send messages, authorize apps, or perform write operations. If the owner supplies a safe export, treat the export as a new source requiring authorization.
