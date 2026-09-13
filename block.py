# -----------------------------------------------------------------------------
# Role: Implements the directory list block runtime and UI contract.
# File Name: block.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2026-05-10
# -----------------------------------------------------------------------------

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any
import json
import os

from bloxsmith_app.block_api import (
    APPLICATION_JSON,
    BlockDefinition,
    BlockRuntimeContext,
    BlockRuntimeOutput,
    BlockRuntimeResult,
    render_inspector_template,
    render_path_browser_control,
)


DIRECTORY_LIST_DEFAULT_PATTERN = "*"


class DirectoryListBlockError(ValueError):
    """Raised when Directory List cannot list a folder."""


class DirectoryListBlockCancelled(RuntimeError):
    """Raised when the runtime asks the block to stop."""


@dataclass(frozen=True)
class DirectoryListItem:
    """Structured data used by this block implementation."""
    path: Path
    relative_path: str
    size_bytes: int


# Functional behavior:
# FB1 - Resolve a folder path from the input port or from config.folder_path.
# FB2 - Apply a shell-style glob pattern such as *.mp3 or **/*.wav.
# FB3 - Emit a standard List-compatible JSON array of {"item": {...}} objects for Iterator.
# FB4 - Render/update block-owned inspector controls without frontend business logic.
# FB5 - Run through the generic runtime path used by both centralized and zeromq_active execution modes.
class DirectoryListBlock(BlockDefinition):
    """Autonomous block implementation for `DirectoryListBlock`."""
    kind = "directory_list"

    def ui_assets(self, surface: str = "modal") -> list[dict[str, str]]:
        """Return block-owned frontend assets for the requested UI surface.

        Args:
            surface: UI surface requesting assets.
        """
        if surface == "modal":
            return [
                {"kind": "js", "path": "assets/js/common.js"},
                {"kind": "js", "path": "assets/js/block_modal.js"},
            ]
        if surface == "inspector_panel":
            return [
                {"kind": "js", "path": "assets/js/common.js"},
                {"kind": "js", "path": "assets/js/inspector_panel.js"},
            ]
        if surface == "node_card":
            return [{"kind": "css", "path": "assets/css/node_card.css"}]
        return []

    def render_node_card(self, *, node: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Render the canvas card body owned by the Directory List block."""

        config = self._ui_config(node)
        title = escape(str(node.get("title") or self.default_title()))
        folder = escape(str(config.get("folder_path") or "folder input"))
        pattern = escape(str(config.get("pattern") or DIRECTORY_LIST_DEFAULT_PATTERN))
        recursive_label = "recursive" if config.get("recursive") else "direct"
        template = (self.directory / "node_card.html").read_text(encoding="utf-8")
        html = (
            template.replace("__title__", title)
            .replace("__folder__", folder)
            .replace("__pattern__", pattern)
            .replace("__recursive_label__", recursive_label)
        )
        return {
            "html": html,
            "context": {
                "node_classes": ["directory-list-node"],
                "node_id": str(node.get("id") or ""),
            },
        }

    def render_modal(self, *, node: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Render the Directory List modal with the shared folder browser control."""

        config = self._ui_config(node)
        template = (self.directory / "block_modal.html").read_text(encoding="utf-8")
        html = self._render_generic_modal_template(
            template=(
                self._apply_ui_replacements(template, config, input_id="directoryListModalFolderPath")
                .replace("{{ config_fields_html }}", self._render_modal_technical_config_fields(node))
            ),
            node=node,
            payload=payload or {},
        )
        return {
            "html": html,
            "context": {
                "node_id": str(node.get("id") or ""),
                "node_kind": self.kind,
                **config,
            },
        }

    def render_inspector_panel(self, *, node: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Render the block-owned inspector panel HTML for the selected node.

        Args:
            node: Serialized graph node handled by the block.
            payload: Optional UI or runtime payload provided by the framework.
        """
        config = self._ui_config(node)
        template = (self.directory / "inspector_panel.html").read_text(encoding="utf-8")
        html = render_inspector_template(
            template=self._apply_ui_replacements(template, config, input_id="directoryListFolderPath"),
            node={**node, "type": self.kind, "kind": self.kind},
            payload=payload,
            replacements={
                "add_input_disabled": "disabled",
                "add_output_disabled": "disabled",
            },
            show_duplicate=False,
        )
        return {
            "html": html,
            "context": {
                "node_id": str(node.get("id") or ""),
                "full_panel": True,
                "inspector_title": str(node.get("title") or self.default_title()),
            },
        }

    def handle_ui_action(
        self,
        *,
        node: dict[str, Any],
        action: str,
        values: dict[str, Any],
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Handle a block-owned UI action and return the updated node payload.

        Args:
            node: Serialized graph node handled by the block.
            action: Block-owned action name requested by the frontend.
            values: Values value used by this block helper.
            payload: Optional UI or runtime payload provided by the framework.
        """
        if action not in {"inspector_update_directory_list", "modal_update_directory_list"}:
            return super().handle_ui_action(node=node, action=action, values=values, payload=payload)
        pattern = self._normalize_pattern(values.get("pattern"))
        return {
            "node_patch": {
                "config": {
                    "folder_path": str(values.get("folder_path") or "").strip(),
                    "pattern": pattern,
                    "recursive": self._bool(values.get("recursive", False)),
                }
            },
            "message": f"[directory-list] Filtre applique: {pattern}.",
            "rerender_inspector": False,
        }

    def _apply_ui_replacements(self, template: str, config: dict[str, Any], *, input_id: str) -> str:
        """Fill Directory List UI placeholders shared by modal and inspector."""

        replacements = {
            "folder_path_browser_html": self._render_folder_path_browser(config, input_id=input_id),
            "pattern": escape(str(config.get("pattern") or DIRECTORY_LIST_DEFAULT_PATTERN)),
            "recursive_checked": "checked" if config.get("recursive") else "",
        }
        html = template
        for key, value in replacements.items():
            html = html.replace(f"{{{{ {key} }}}}", str(value))
        return html

    def _render_folder_path_browser(self, config: dict[str, Any], *, input_id: str) -> str:
        """Render the shared directory browser for the folder to list."""

        return render_path_browser_control(
            input_id=input_id,
            label="Dossier",
            value=str(config.get("folder_path") or ""),
            placeholder="./audio",
            input_attrs="data-directory-list-folder-path",
            select_mode="directory",
        )

    def _render_modal_technical_config_fields(self, node: dict[str, Any]) -> str:
        """Render Directory List config keys not owned by the dedicated folder controls."""

        config = self.default_config()
        node_config = node.get("config")
        if isinstance(node_config, dict):
            config.update(node_config)
        hidden_keys = {"folder_path", "pattern", "recursive"}
        fields = [
            self._render_generic_modal_config_field(key, value)
            for key, value in config.items()
            if str(key) not in hidden_keys
        ]
        return "\n".join(fields) if fields else '<div class="ports-editor-empty">Aucun attribut technique.</div>'

    def preview_received(self, *, node: Any, **runtime_services: Any) -> str:
        """Return a compact preview value for runtime display surfaces.

        Args:
            node: Serialized graph node handled by the block.
            runtime_services: Runtime services value used by this block helper.
        """
        config = getattr(node, "config", {}) if isinstance(getattr(node, "config", {}), dict) else {}
        folder = str(config.get("folder_path") or "").strip()
        pattern = self._normalize_pattern(config.get("pattern"))
        return f"{folder or 'dossier non defini'} ({pattern})"

    def execute_runtime(self, context: BlockRuntimeContext) -> BlockRuntimeResult:
        """Execute the block through the generic runtime context and return runtime outputs.

        Args:
            context: Generic runtime context injected by the execution engine.
        """
        logs: list[str] = []
        try:
            config = self._runtime_config(context.config)
            folder_path = self._resolve_folder_path(context=context, config=config)
            items = self._list_files(folder_path=folder_path, config=config, context=context)
            payload = self._serialize_items(items=items, folder_path=folder_path, root_dir=context.root_dir)
            outputs = [
                BlockRuntimeOutput(
                    port_id=int(getattr(port, "id", 0) or 0),
                    port_name=str(getattr(port, "name", "") or ""),
                    value=payload,
                    content_type=APPLICATION_JSON,
                )
                for port in context.output_ports
            ]
            display_folder = self._display_path(folder_path, context.root_dir)
            self._emit_log(
                context,
                logs,
                f"[directory-list] {context.node_id}: dossier={display_folder} "
                f"filtre={config['pattern']} recursive={'on' if config['recursive'] else 'off'}.",
            )
            self._emit_log(context, logs, f"[done] Directory List {context.node_id}: {len(items)} fichier(s).")
            return BlockRuntimeResult(
                status="success",
                outputs=outputs,
                logs=logs,
                last_message=payload,
                content_type=APPLICATION_JSON,
                worker_received=display_folder,
                metadata={
                    "directory_list": {
                        "folder_path": display_folder,
                        "pattern": config["pattern"],
                        "recursive": config["recursive"],
                        "file_count": len(items),
                    }
                },
            )
        except DirectoryListBlockCancelled as exc:
            return BlockRuntimeResult(status="cancelled", logs=logs, error=str(exc), exit_code=130)
        except DirectoryListBlockError as exc:
            return BlockRuntimeResult(status="failed", logs=logs, error=str(exc), exit_code=1)

    def _runtime_config(self, raw_config: dict[str, Any] | None) -> dict[str, Any]:
        """Provide internal DirectoryListBlock behavior for `_runtime_config`.

        Args:
            raw_config: Raw value received from configuration or runtime input.
        """
        config = raw_config if isinstance(raw_config, dict) else {}
        return {
            "folder_path": str(config.get("folder_path") or "").strip(),
            "pattern": self._normalize_pattern(config.get("pattern")),
            "recursive": self._bool(config.get("recursive", False)),
        }

    def _ui_config(self, node: dict[str, Any]) -> dict[str, Any]:
        """Provide internal DirectoryListBlock behavior for `_ui_config`.

        Args:
            node: Serialized graph node handled by the block.
        """
        config = node.get("config") if isinstance(node.get("config"), dict) else {}
        return self._runtime_config(config)

    def _normalize_pattern(self, value: Any) -> str:
        """Normalize a raw value into the format expected by the block.

        Args:
            value: Value to normalize, render, serialize, or process.
        """
        pattern = str(value or "").strip()
        return pattern or DIRECTORY_LIST_DEFAULT_PATTERN

    def _bool(self, value: Any) -> bool:
        """Normalize a raw boolean-like configuration value.

        Args:
            value: Value to normalize, render, serialize, or process.
        """
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        return str(value or "").strip().lower() in {"1", "true", "yes", "on", "checked"}

    def _resolve_folder_path(self, *, context: BlockRuntimeContext, config: dict[str, Any]) -> Path:
        """Resolve a configured value against runtime or project context.

        Args:
            context: Generic runtime context injected by the execution engine.
            config: Raw or normalized block configuration.
        """
        raw_value = (
            context.input_value("folder")
            or context.input_value("1")
            or context.input_message
            or config.get("folder_path")
            or ""
        )
        folder_text = self._extract_path_value(raw_value)
        if not folder_text:
            raise DirectoryListBlockError("Directory List: aucun dossier fourni.")
        folder = Path(folder_text).expanduser()
        if not folder.is_absolute():
            folder = context.root_dir / folder
        folder = folder.resolve()
        if not folder.is_dir():
            raise DirectoryListBlockError(f"Directory List: dossier introuvable: {folder_text}")
        return folder

    def _extract_path_value(self, raw_value: Any) -> str:
        """Provide internal DirectoryListBlock behavior for `_extract_path_value`.

        Args:
            raw_value: Raw value received from configuration or runtime input.
        """
        if raw_value is None:
            return ""
        if isinstance(raw_value, dict):
            return self._path_from_dict(raw_value)
        text = str(raw_value or "").strip()
        if not text:
            return ""
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return text
        if isinstance(parsed, dict):
            return self._path_from_dict(parsed) or text
        return text

    def _path_from_dict(self, value: dict[str, Any]) -> str:
        """Provide internal DirectoryListBlock behavior for `_path_from_dict`.

        Args:
            value: Value to normalize, render, serialize, or process.
        """
        for key in ("path", "folder_path", "directory_path", "folder", "directory"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
        item = value.get("item")
        if isinstance(item, dict):
            return self._path_from_dict(item)
        if isinstance(item, str) and item.strip():
            return item.strip()
        return ""

    def _list_files(
        self,
        *,
        folder_path: Path,
        config: dict[str, Any],
        context: BlockRuntimeContext,
    ) -> list[DirectoryListItem]:
        """Provide internal DirectoryListBlock behavior for `_list_files`.

        Args:
            folder_path: Filesystem path handled by the block.
            config: Raw or normalized block configuration.
            context: Generic runtime context injected by the execution engine.
        """
        pattern = self._normalize_pattern(config.get("pattern"))
        matcher = folder_path.rglob(pattern) if config.get("recursive") else folder_path.glob(pattern)
        items: list[DirectoryListItem] = []
        for candidate in matcher:
            self._check_cancelled(context)
            try:
                if not candidate.is_file():
                    continue
                resolved = candidate.resolve()
                items.append(
                    DirectoryListItem(
                        path=resolved,
                        relative_path=self._relative_path(resolved, folder_path),
                        size_bytes=resolved.stat().st_size,
                    )
                )
            except OSError:
                continue
        return sorted(items, key=lambda item: item.relative_path.lower())

    def _serialize_items(self, *, items: list[DirectoryListItem], folder_path: Path, root_dir: Path) -> str:
        """Provide internal DirectoryListBlock behavior for `_serialize_items`.

        Args:
            items: Items value used by this block helper.
            folder_path: Filesystem path handled by the block.
            root_dir: Directory path used by the block runtime.
        """
        payload_items: list[dict[str, Any]] = []
        for index, entry in enumerate(items, start=1):
            item: dict[str, Any] = {
                "path": str(entry.path),
                "file_name": entry.path.name,
                "stem": entry.path.stem,
                "extension": entry.path.suffix,
                "relative_path": entry.relative_path,
                "directory": str(entry.path.parent),
                "size_bytes": entry.size_bytes,
                "index": index,
                "source_folder": str(folder_path),
            }
            root_relative = self._relative_path(entry.path, root_dir)
            if root_relative:
                item["root_relative_path"] = root_relative
            payload_items.append({"item": item})
        return json.dumps(payload_items, ensure_ascii=False, indent=2)

    def _relative_path(self, path: Path, root: Path) -> str:
        """Provide internal DirectoryListBlock behavior for `_relative_path`.

        Args:
            path: Filesystem path handled by the block.
            root: Mounted UI root element or repository root depending on the caller.
        """
        try:
            return os.path.relpath(path, root)
        except ValueError:
            return ""

    def _check_cancelled(self, context: BlockRuntimeContext) -> None:
        """Check runtime state and raise or return when execution should stop.

        Args:
            context: Generic runtime context injected by the execution engine.
        """
        checker = context.services.get("cancel_requested") if isinstance(context.services, dict) else None
        if callable(checker) and checker():
            raise DirectoryListBlockCancelled("Directory List: annulation demandee.")

    def _emit_log(self, context: BlockRuntimeContext, logs: list[str], message: str) -> None:
        """Emit a runtime log or event through the injected context.

        Args:
            context: Generic runtime context injected by the execution engine.
            logs: Logs value used by this block helper.
            message: Log or status message to emit.
        """
        append_log = context.services.get("append_log") if isinstance(context.services, dict) else None
        if callable(append_log):
            append_log(message)
        else:
            logs.append(message)

    def _display_path(self, path: Path, root_dir: Path) -> str:
        """Provide internal DirectoryListBlock behavior for `_display_path`.

        Args:
            path: Filesystem path handled by the block.
            root_dir: Directory path used by the block runtime.
        """
        try:
            return os.path.relpath(path, root_dir)
        except ValueError:
            return str(path)
