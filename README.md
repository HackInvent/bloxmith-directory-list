# Directory List Block

<!-- block-metadata:start -->
[![Block version: 0.1.0](https://img.shields.io/badge/block-0.1.0-blue)](model.json)
[![BloxSmith compatibility: 1.0.9](https://img.shields.io/badge/BloxSmith-1.0.9-brightgreen)](compatibility.json)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue)](LICENSE)

Verified BloxSmith versions: **1.0.9** (bundled-block tests; see [test evidence](compatibility.json)).
<!-- block-metadata:end -->


## Role

`directory_list` lists files in a folder using a shell-style glob pattern such as `*.mp3` and emits a standard List-compatible JSON array.

## Files

- `block.py`: folder resolution, glob filtering, runtime output, inspector actions.
- `model.json`: folder input, JSON list output, and default config.
- `block_modal.html`, `inspector_panel.html`, `assets/`: block-owned modal and inspector UI.
- `node_card.html`: block-owned canvas card body used by the editor.

## Ports

- Inputs:
  - `folder` (`id: 1`): optional folder path from `directory/path`, `file/path`, `message/*`, or JSON `{ "path": "..." }`.
- Outputs:
  - `liste` (`id: 1`): emits `[{ "item": { "path": "...", ... } }]` as `application/json`.

## Configuration

- `folder_path`: fallback folder path when the input port is not connected.
- `pattern`: glob pattern applied to the folder. Defaults to `*`.
- `recursive`: when true, applies the pattern recursively with `Path.rglob`.

## Runtime Behavior

The block resolves the folder from the input first, then from `folder_path`, filters regular files only, sorts them by relative path, and emits each file as an `item` containing absolute path, relative path, file name, extension, size, index, and source folder.

The same `execute_runtime()` path is used in centralized and `zeromq_active` runs.

## UI Behavior

The inspector and modal edit `folder_path`, `pattern`, and `recursive` through
`inspector_update_directory_list` or `modal_update_directory_list`. Edits stay pending until the user
clicks **Apply**. Folder selection uses the shared `CWPathBrowser` control in directory mode.

The Ports tab remains visible for inspection, but input/output port creation is disabled for this block.

## Editor Display

The canvas card is rendered by this block. It shows the configured folder fallback, the active glob pattern, and whether recursive mode is enabled. Ports, dragging, status, and graph links remain controlled by the shared editor shell.

## Modal

`block_modal.html` is owned by this block. It keeps the generic title binding and exposes the same
folder browser, filter, recursive flag, ports, and runtime state as the inspector.

## Integration tests

From the private integration workspace, `python3 -B tests/run_tests.py directory_list` runs the suite in an isolated framework copy. UI fixtures use relative paths.

## UI surface migration

- The modal declares `data-block-runtime-refresh="autonomous"` so folder, filter, and recursive-mode drafts survive runtime polling.
- Shared Directory List UI helpers live in `assets/js/common.js`.
- Modal behavior is mounted by `assets/js/block_modal.js`; inspector behavior is mounted by `assets/js/inspector_panel.js`.
- Durable folder and pattern edits continue to go through block-owned UI actions.

## Compatibility policy

[compatibility.json](compatibility.json) records HackInvent's verified BloxSmith versions and test evidence. Only the versions listed above have been verified, using the block-owned suites in a **bundled-block test installation**. This is not a certification of managed-package installation, every browser/OS, or live provider availability. Other framework versions are unverified, not necessarily incompatible.

The block-version badge follows `model.json`, not a published Git tag. `unversioned` means that no block release version is declared; no number is inferred from the framework version. The framework still uses `model.json` for its runtime/install contract; the tester-owned JSON does not replace it. Official integration tests run in the private `bloxmith-blocs` workspace. Test helpers and the proprietary framework are not bundled in this public block repository.
