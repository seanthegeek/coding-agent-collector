# copilot (GitHub Copilot OAuth token store shared by editor plugins)

## 1. Source and evidence level

**Source/bundle**: github.com/github/copilot.vim, shallow clone at `scratchpad/repos/copilot.vim`, HEAD [a12fd5672110c8aa7e3c8419e28c96943ca179be](https://github.com/github/copilot.vim/commit/a12fd5672110c8aa7e3c8419e28c96943ca179be) (2026-01-09). The plugin vendors the closed `@github/copilot-language-server` 1.408.0 ([`copilot-language-server/package.json`](https://github.com/github/copilot.vim/blob/a12fd5672110c8aa7e3c8419e28c96943ca179be/copilot-language-server/package.json)) as a minified bundle [`copilot-language-server/dist/main.js`](https://github.com/github/copilot.vim/blob/a12fd5672110c8aa7e3c8419e28c96943ca179be/copilot-language-server/dist/main.js) (7.2 MB); the token-store code is in that bundle (readable JS, cited by function name). [`autoload/copilot/client.vim:514-515`](https://github.com/github/copilot.vim/blob/a12fd5672110c8aa7e3c8419e28c96943ca179be/autoload/copilot/client.vim#L514-L515) names the bundle. Confirmed names-only that `~/.config/github-copilot` is absent on this host (no editor Copilot installed), so no local confirmation.

## 2. Per-user storage

[`main.js`](https://github.com/github/copilot.vim/blob/a12fd5672110c8aa7e3c8419e28c96943ca179be/copilot-language-server/dist/main.js) `function Alt()` ("getXdgConfigPath"):
```
XDG_CONFIG_HOME set and absolute → $XDG_CONFIG_HOME/github-copilot
win32                            → %USERPROFILE%\AppData\Local\github-copilot
else                             → $HOME/.config/github-copilot
```
So macOS and Linux use the XDG config dir `~/.config/github-copilot` (no Library path), Windows uses `AppData\Local`. The only relocation variable is `XDG_CONFIG_HOME`. Files written there (same function's caller in [`main.js`](https://github.com/github/copilot.vim/blob/a12fd5672110c8aa7e3c8419e28c96943ca179be/copilot-language-server/dist/main.js)):
- `apps.json`: current store, object keyed `"<host>:<githubAppId>"` → `{user, oauth_token, githubAppId}`.
- `hosts.json`: legacy store keyed by host → `{user, oauth_token}`; on startup entries are copied into `apps.json` and `hosts.json` is deleted (`writeFile(join(l,"apps.json"))` then `rm(join(l,"hosts.json"),{force:true})`).
- `versions.json` not present in this bundle (0 hits).
The language server also creates `$TMPDIR/github-copilot-<rand>` temp dirs on non-Windows (same code), outside home. Logs go to the editor (Vim `:Copilot log`), not to this directory. The same store is read by Copilot plugins for Neovim, JetBrains, Xcode and Vim because they embed the same language server; the GitHub Copilot CLI does not use it (see copilot-cli). VS Code's Copilot Chat state lives in `User/globalStorage` (covered by the vscode entries) and its token in the VS Code secret store, not here.

## 3. Credentials

`apps.json` and `hosts.json` hold the GitHub OAuth token in plaintext (`oauth_token` field) with the GitHub login (`user`). No keychain use in this path. No config file embeds API keys.

## 4. Exclusions

None; the directory holds only small JSON files.

## 5. Project-local files

Read only: `.github/copilot-instructions.md`, `.github/git-commit-instructions.md`, `.github/instructions/` ([`main.js`](https://github.com/github/copilot.vim/blob/a12fd5672110c8aa7e3c8419e28c96943ca179be/copilot-language-server/dist/main.js) constants `QNi`, `jNi`, `Ckr`). Nothing written.

## 6. Where the project path is recorded

Not recorded; the store is per host, not per workspace.

## 7. Confidence

High: path resolution and both file names with their fields (readable code in the shipped bundle, version pinned). Medium: that JetBrains/Xcode plugins use the same store (same language server, but their bundles were not inspected). Not determined: whether a `versions.json` or terms-acceptance file is written by other editor hosts.
