# AI Agent Discovery Reference

> Comprehensive catalog of local AI agent/tool traces to discover during Phase 1.
> Scan for all listed signals; include every agent found in the authorization scope.
> Paths are provided for both macOS and Windows; use the rows matching the current platform.

## Platform path reference

| Variable | macOS | Windows |
|----------|-------|---------|
| Home | `~` | `%USERPROFILE%` (`C:\Users\<user>`) |
| App data (Roaming) | `~/Library/Application Support/` | `%APPDATA%\` (`C:\Users\<user>\AppData\Roaming\`) |
| App data (Local) | `~/Library/Application Support/` | `%LOCALAPPDATA%\` (`C:\Users\<user>\AppData\Local\`) |
| Desktop | `~/Desktop/` | `%USERPROFILE%\Desktop\` |

> `~/.xxx` paths (e.g. `~/.proma`, `~/.claude`) work identically on both platforms —
> they resolve to `<home>/.xxx`. The differences are only in app-data directories
> that macOS puts under `~/Library/Application Support/` and Windows puts under
> `%APPDATA%\` or `%LOCALAPPDATA%\`.

## Detection matrix

| Agent | macOS path | Windows path | Format | Progressive read method |
|-------|-----------|--------------|--------|------------------------|
| **Proma** | `~/.proma/` | `%USERPROFILE%\.proma\` | JSONL (streaming) | `proma session info/outline/search/export` |
| **Claude Code** | `~/.claude/` | `%USERPROFILE%\.claude\` | JSONL | Read transcript JSONL; extract user/assistant turns; group by project |
| **Hermes** | `~/.hermes/` | `%USERPROFILE%\.hermes\` | SQLite + JSON | Read SQLite read-only (`SELECT` only); or ask user to export via Hermes Desktop |
| **Cursor** | `~/Library/Application Support/Cursor/` | `%APPDATA%\Cursor\` | JSON (conversation/composer) | Search for `*conversation*` `*composer*` `*aiChat*` JSON files |
| **Codex (OpenAI)** | `~/Documents/Codex/` or `~/.codex/` | `%USERPROFILE%\Documents\Codex\` or `%USERPROFILE%\.codex\` | Markdown + JSON | Read directory README/PLAN/AGENTS files; scan .md files for session content |
| **Windsurf** | `~/.windsurf/` `~/Library/Application Support/Windsurf/` | `%USERPROFILE%\.windsurf\` `%APPDATA%\Windsurf\` | JSON | Search for conversation history files |
| **Aider** | `~/.aider/` `~/.aider.chat.history.md` | `%USERPROFILE%\.aider\` `%USERPROFILE%\.aider.chat.history.md` | Markdown / plain text | Read chat history markdown directly |
| **Cline** | `~/Library/Application Support/Code/User/globalStorage/saoudrizwan.claude-dev/` | `%APPDATA%\Code\User\globalStorage\saoudrizwan.claude-dev\` | JSON (task history) | Read task history JSON files |
| **Continue** | `~/.continue/` | `%USERPROFILE%\.continue\` | JSON | Read session JSON files |
| **GitHub Copilot** | VS Code extension | No local session history (cloud-only) | N/A | User self-report; check `.github/copilot-instructions.md` in projects |
| **Ollama** | `~/.ollama/` | `%USERPROFILE%\.ollama\` | Log / JSON | Read log files for model usage; note models pulled |
| **LM Studio** | `~/Library/Application Support/LM Studio/` | `%APPDATA%\LM Studio\` | SQLite / JSON | Check for conversation history; may need user export |
| **OMLX** | `~/Library/Application Support/OMLX*` | `%APPDATA%\OMLX*` or `%LOCALAPPDATA%\OMLX*` | SQLite / JSON | Check for model loading logs and conversation history |
| **DingTalk AI** | Hermes pairing `~/.hermes/pairing/dingtalk-*.json` | Via Hermes integration (`%USERPROFILE%\.hermes\pairing\`) | JSON | Check Hermes pairing config; user self-report |
| **WorkBuddy** | `~/Library/Application Support/WorkBuddy/` | `%LOCALAPPDATA%\WorkBuddy\` | JSONL / SQLite | Check session storage; search for project configs |
| **TRAE** | `~/Library/Application Support/TRAE/` | `%APPDATA%\TRAE\` | JSONL / SQLite | Check session storage; search for `.trae/` configs |
| **Qoder** | `~/Library/Application Support/Qoder/` | `%LOCALAPPDATA%\Qoder\` | JSONL / SQLite | Check session storage; search for `.qoder/` or `.qoderwork/` configs |
| **悟空** | `~/Library/Application Support/Wukong/` or DingTalk sub-path | `%APPDATA%\DingTalk\Wukong\` | SQLite / JSON | Check for Wukong agent data; may be inside DingTalk directory |
| **千问办公** | `~/Library/Application Support/QianwenOffice/` | `%APPDATA%\QianwenOffice\` | SQLite / JSON | Check session storage; search for `.qianwen/` configs |
| **Lovable** | Web-based (local cache optional) | Web-based (local cache optional) | localStorage / IndexedDB | Web app; check project for `.lovable/` or `.gpt-engineer/` configs |
| **bolt.new** | Web-based | Web-based | Browser cache | Web app by StackBlitz; check project for `.bolt/` configs |
| **v0.dev** | Web-based | Web-based | Browser cache | Web app by Vercel; check project for `.v0/` configs |
| **Replit Agent** | Web-based | Web-based | Browser cache | Web app; check project for `.replit/` configs |
| **Cline (updated)** | `~/.vscode/extensions/saoudrizwan.claude-dev-*/` or `~/.cline/` | `%USERPROFILE%\.vscode\extensions\saoudrizwan.claude-dev-*\` or `%USERPROFILE%\.cline\` | JSON | VS Code extension; also check standalone `.cline/` directory |
| **Continue** | `~/.vscode/extensions/continue.continue-*/` | `%USERPROFILE%\.vscode\extensions\continue.continue-*\` | JSON / SQLite | VS Code extension (acquired by Cursor; open-source codebase remains available) |
| **Tabnine** | `~/Library/Application Support/TabNine/` | `%APPDATA%\TabNine\` | Binary / Log | Code completion tool; check for usage logs |
| **Codeium** | `~/Library/Application Support/Codeium/` | `%LOCALAPPDATA%\Codeium\` | Binary / Log | Code completion tool; check for logs and `.codeium/` project configs |
| **Supermaven** | VS Code extensions directory | VS Code extensions directory | Extension config | VS Code extension; search for `supermaven*` in extensions |
| **Amazon Q Developer** | `~/.aws/` sub-directory or IDE extension | `%USERPROFILE%\.aws\` sub-directory or IDE extension | SQLite / JSON | AWS-integrated coding assistant; check `.aws/` or IDE extension data |
| **Kimi Code** | `~/Library/Application Support/Kimi Code/` | `%LOCALAPPDATA%\Kimi Code\` | JSONL / SQLite | Check session storage; search for `.kimi/` configs |
| **Kimi Work** | `~/Library/Application Support/Kimi Work/` | `%LOCALAPPDATA%\Kimi Work\` | JSONL / SQLite | Check session storage; search for `.kimi/` configs |
| **CodeBuddy** | `~/Library/Application Support/CodeBuddy/` | `%LOCALAPPDATA%\CodeBuddy\` | JSONL / SQLite | Check session storage; search for `.codebuddy/` configs |
| **OMP** | `~/Library/Application Support/OMP/` | `%LOCALAPPDATA%\OMP\` | JSONL / SQLite | Check session storage; search for `.omp/` configs |
| **Gemini CLI** | `~/.gemini/` | `%USERPROFILE%\.gemini\` | JSON / Log | Check local data; may include conversation logs |
| **Antigravity CLI** | `~/.antigravity/` or `~/.agy/` | `%USERPROFILE%\.antigravity\` | JSON / Log | Check local data; may include conversation logs |
| **OpenCode** | `~/Library/Application Support/OpenCode/` | `%LOCALAPPDATA%\OpenCode\` | JSONL / SQLite | Check session storage; search for `.opencode/` configs |
| **Alma** | `~/Library/Application Support/Alma/` | `%LOCALAPPDATA%\Alma\` | JSONL / SQLite | Check session storage; search for `.alma/` configs |
| **Pi** | `~/Library/Application Support/Pi/` | `%LOCALAPPDATA%\Pi\` | JSONL / SQLite | Check session storage; search for `.pi/` configs |
| **Grok Build** | `~/Library/Application Support/Grok Build/` | `%LOCALAPPDATA%\Grok Build\` | JSONL / SQLite | Check session storage; search for `.grok/` configs |
| **Copilot CLI** | `~/.github/copilot/` | `%USERPROFILE%\.github\copilot\` | JSON / Log | GitHub Copilot CLI; check local logs and `.github/copilot-instructions.md` |
| **OpenClaw** | `~/Library/Application Support/OpenClaw/` | `%LOCALAPPDATA%\OpenClaw\` | JSONL / SQLite | Check session storage; search for `.openclaw/` configs |
| **Bub** | `~/Library/Application Support/Bub/` | `%LOCALAPPDATA%\Bub\` | JSONL / SQLite | Check session storage; search for `.bub/` configs |
| **Cradle** | `~/Library/Application Support/Cradle/` | `%LOCALAPPDATA%\Cradle\` | JSONL / SQLite | Check session storage; search for `.cradle/` configs |
| **MiMo Code** | `~/Library/Application Support/MiMo Code/` | `%LOCALAPPDATA%\MiMo Code\` | JSONL / SQLite | Check session storage; search for `.mimo/` configs |
| **Craft Agent** | `~/Library/Application Support/Craft Agent/` | `%LOCALAPPDATA%\Craft Agent\` | JSONL / SQLite | Check session storage; search for `.craft/` configs |
| **Droid** (Factory Droid) | `~/Library/Application Support/Droid/` | `%LOCALAPPDATA%\Droid\` | JSONL / SQLite | Check session storage; search for `.droid/` configs |
| **ZCode** (Z.ai) | `~/Library/Application Support/ZCode/` | `%LOCALAPPDATA%\ZCode\` | JSONL / SQLite | Check session storage; search for `.zcode/` configs |
| **Arkloop** | `~/Library/Application Support/Arkloop/` | `%LOCALAPPDATA%\Arkloop\` | JSONL / SQLite | Check session storage; search for `.arkloop/` configs |
| **OpticLM** | `~/Library/Application Support/OpticLM/` | `%LOCALAPPDATA%\OpticLM\` | JSONL / SQLite | Check session storage; search for `.opticlm/` configs |
| **Cherry Studio** | `~/Library/Application Support/Cherry Studio/` | `%APPDATA%\Cherry Studio\` | JSON / SQLite | Check session storage |
| **Raft** | `~/Library/Application Support/Raft/` | `%LOCALAPPDATA%\Raft\` | JSONL / SQLite | Multi-agent tool; check session storage |
| **Lody** | `~/Library/Application Support/Lody/` | `%LOCALAPPDATA%\Lody\` | JSONL / SQLite | Multi-agent tool; check session storage |
| **Multica** | `~/Library/Application Support/Multica/` | `%LOCALAPPDATA%\Multica\` | JSONL / SQLite | Multi-agent tool; check session storage |
| **Cumora** | `~/Library/Application Support/Cumora/` | `%LOCALAPPDATA%\Cumora\` | JSONL / SQLite | Multi-agent tool; check session storage |
| **Paseo** | `~/Library/Application Support/Paseo/` | `%LOCALAPPDATA%\Paseo\` | JSONL / SQLite | Multi-agent tool; check session storage |
| **Obsidian** | `~/Library/Application Support/obsidian/` | `%APPDATA%\obsidian\` | Markdown / JSON | Note tool; check `.obsidian/` plugin/AI settings; may include Canvas |
| **Notion** | `~/Library/Application Support/Notion/` | `%LOCALAPPDATA%\Notion\` | SQLite / JSON | Note tool; local cache; export via Notion API or user self-report |
| **Apple Notes** | `~/Library/Group Containers/group.com.apple.notes/` | N/A | SQLite (Notes database) | macOS only; do not read without explicit authorization |
| **TiddlyWiki** | `~/.tiddlywiki/` or project `.tiddlywiki/` | `%USERPROFILE%\.tiddlywiki\` | HTML / JSON | Note tool; check `.tiddlywiki/` directories |
| **Raycast** | `~/Library/Application Support/Raycast/` | N/A | SQLite / JSON | macOS launcher; includes Raycast AI history and extensions |
| **Raycast AI Exporter** | `~/Library/Application Support/Raycast/` (same as Raycast) | N/A | SQLite / JSON | Companion utility for exporting Raycast AI conversations |

## Project-level AI tool signals

Check each project directory for these files/directories to determine AI participation (same on both platforms):

```text
.claude/          AGENTS.md         .cursorrules      .aider*
.cursor/          CLAUDE.md         .clinerules       .aider.conf.yml
.codex/           .cursorrules      .windsurfrules    .ocx/
.opencode/        .hermes/          .continue/        .github/copilot-instructions.md
.workbuddy/       .trae/            .qoder/           .qoderwork/
.wukong/          .qianwen/         .codeium/         .bolt/
.v0/              .replit/          .lovable/         .gpt-engineer/
```

## Auto-attribution signals

To classify projects as user-created vs downloaded:

| Signal | Indicates user-created | Indicates downloaded |
|--------|----------------------|---------------------|
| Git author history | User has ≥1 commit | User has 0 commits |
| Git remote URL | Local/empty remote | Points to public GitHub repo |
| package.json `author` field | Matches user identity | Different author |
| README header | "by <user>" or user's org | Third-party org/person |
| `.claude/` with user's session | User worked on it with AI | May be cloned with configs |
| LICENSE | User's org | Third-party license |

## Scan procedure

### Cross-platform scan (Python, recommended)

Use the bundled Python script to scan for installed AI agents on any platform:

```bash
# macOS / Linux
python3 scripts/scan_agents.py -o <work>/agents_found.json

# Windows
python scripts/scan_agents.py -o <work>\agents_found.json
# or: py scripts/scan_agents.py -o <work>\agents_found.json
```

The script auto-detects the platform and checks the correct paths for each agent.

### Manual scan (bash, macOS/Linux)

```bash
# 1. Detect installed AI agents
for d in ~/.proma ~/.claude ~/.cursor ~/.hermes ~/.aider ~/.ollama \
         ~/Library/Application\ Support/Cursor \
         ~/Library/Application\ Support/Claude \
         ~/Library/Application\ Support/LM\ Studio \
         ~/Library/Application\ Support/OMLX*; do
  [ -e "$d" ] && echo "FOUND: $d ($(du -sh "$d" 2>/dev/null | cut -f1))"
done

# 2. Scan project directories for AI tool configs
find <project-root> -maxdepth 2 \( \
  -name ".claude" -o -name ".cursor" -o -name "AGENTS.md" -o -name "CLAUDE.md" \
  -o -name ".cursorrules" -o -name ".aider*" -o -name ".codex" \
  -o -name ".opencode" -o -name ".ocx" -o -name ".hermes" \
  \) -not -path "*/node_modules/*" 2>/dev/null

# 3. Check Git attribution
cd <repo> && git log --since="<start>" --until="<end>" --format='%an <%ae>' | sort -u
```

### Manual scan (PowerShell, Windows)

```powershell
# 1. Detect installed AI agents
$paths = @(
  "$env:USERPROFILE\.proma",
  "$env:USERPROFILE\.claude",
  "$env:USERPROFILE\.cursor",
  "$env:USERPROFILE\.hermes",
  "$env:USERPROFILE\.aider",
  "$env:USERPROFILE\.ollama",
  "$env:APPDATA\Cursor",
  "$env:APPDATA\Claude",
  "$env:APPDATA\LM Studio",
  "$env:APPDATA\Windsurf",
  "$env:LOCALAPPDATA\OpenAI"
)
foreach ($p in $paths) {
  if (Test-Path $p) { Write-Host "FOUND: $p" }
}

# 2. Scan project directories for AI tool configs
Get-ChildItem -Path <project-root> -Recurse -Depth 2 -Force -ErrorAction SilentlyContinue |
  Where-Object { $_.Name -match '^\.(claude|cursor|codex|hermes|aider|opencode|ocx|continue)|^(AGENTS|CLAUDE)\.md$|^\.cursorrules$|^\.windsurfrules$|^\.clinerules$|^\.aider' } |
  Select-Object -ExpandProperty FullName

# 3. Check Git attribution
cd <repo>; git log --since="<start>" --until="<end>" --format='%an <%ae>' | Sort-Object -Unique
```
