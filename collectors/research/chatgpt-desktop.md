# chatgpt-desktop

## 1. Source and evidence level

Closed source; no package inspected. Evidence is **DFIR write-ups and press**: pvieito.com/2024/07/chatgpt-unprotected-conversations and 9to5mac.com/2024/07/03 (macOS paths, fix in 1.2024.171, Keychain key name); github.com/garr3ttmjo/Digital-Forensic-Report-Writeups "ChatGPT Desktop Forensics" (Windows paths, examined 2025-01-23); arXiv 2505.23938 (Windows app, Oct 2024 release; general, no exact paths). No official OpenAI documentation of on-disk paths was found. Codex integration data: not determined (see 8).

## 2. Per-user storage

macOS (native Swift app, not sandboxed):

- `~/Library/Application Support/com.openai.chat/` app data. Conversations originally plain JSON in `conversations-{uuid}/`; since 1.2024.171 in `conversations-v2-{uuid}/`, encrypted (pvieito; 9to5mac). Expect also Apple-standard `~/Library/Caches/com.openai.chat/`, `~/Library/Preferences/com.openai.chat.plist`, `~/Library/HTTPStorages/com.openai.chat/` (standard macOS layout for a non-sandboxed bundle id; not cited by a write-up, medium).
Windows (MSIX packaged WebView2/Electron-style app):
- `%LOCALAPPDATA%\Packages\OpenAI.ChatGPT-Desktop_2p2nqsd0c76g0\LocalCache\Roaming\ChatGPT\` root (garr3ttmjo).
- `...\ChatGPT\IndexedDB\https_chatgpt.com_0.indexeddb.leveldb\` chat history (LevelDB `.log`/`.ldb`), persists between sessions, removed on logout (garr3ttmjo).
- `...\ChatGPT\Local Storage\leveldb\` session ids and timestamps (garr3ttmjo).
- Standard Chromium siblings under the same root: `Session Storage\`, `Cache\`, `Code Cache\`, `GPUCache\`, `DawnGraphiteCache\`, `DawnWebGPUCache\`, `Network\Cookies`, `Local State`, `Preferences` (standard layout; the prior catalog already lists them, medium).
- The package `LocalState\` folder may hold app settings (MSIX convention, not cited).
Linux: no official app. No XDG paths. No environment variable relocates the data.

## 3. Credentials

- macOS: conversation encryption key is the Keychain item `com.openai.chat.conversations_v2_cache` (pvieito). Sign-in tokens are expected in the Keychain as well (not cited).
- Windows: web session cookies in `...\ChatGPT\Network\Cookies` (Chromium cookie DB, DPAPI/OSCrypt-protected with `Local State`); `Local Storage\leveldb` holds session identifiers (garr3ttmjo). No plaintext token file reported.
- No config file embeds API keys; the app uses account sign-in.

## 4. Exclusions

`*/Roaming/ChatGPT/Cache`, `Code Cache`, `GPUCache`, `DawnGraphiteCache`, `DawnWebGPUCache`; macOS `Library/Caches/com.openai.chat`. Keep `IndexedDB`, `Local Storage`, `Session Storage`, `Network`.

## 5. Project-local files

None. The app does not write into repositories.

## 6. Where the project path is recorded

Not applicable; conversations are chat transcripts without a workspace. If the Codex tab in the app records workspaces, it does so through the Codex app/CLI (`~/.codex/sessions` `cwd`, see codex-cli).

## 7. Confidence

High: macOS app-data dir and `conversations-v2-*` encryption (primary researcher post plus press); Windows root and IndexedDB/Local Storage paths (DFIR write-up). Medium: standard Chromium sibling directories and `Local State`; macOS Caches/Preferences/HTTPStorages (convention, uncited). Not determined: current (2026) macOS layout after the ChatGPT/Codex app merger; whether a `conversations-v3` or SQLite store exists; Windows `LocalState` contents; any Codex-specific data inside the ChatGPT app (the Codex desktop app writes to `~/.codex`, see codex-cli); the IndexedDB value schema.
