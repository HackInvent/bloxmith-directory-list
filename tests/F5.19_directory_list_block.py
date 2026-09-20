#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Role: Verifies directory list block behavior for the directory list block.
# File Name: F5.19_directory_list_block.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2026-05-10
# -----------------------------------------------------------------------------

"""F5.19 - Bloc Directory List."""

# Test cases:
# - FB1/FB2/FB3/FB5 - Run text -> directory_list -> display in centralized and active runtime.
# - FB1/FB2 - Execute directly from config.folder_path with recursive filtering.
# - FB4 - Render/update the block-owned inspector and verify port creation is disabled.
# - FB5 - Verify describe_block exposes the discovered business block.

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
import json
import sys
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blocs.directory_list.block import DirectoryListBlock
from bloxsmith_app.block_runtime import BlockRuntimeContext
from bloxsmith_app.block_ui import handle_block_ui_action, render_block_inspector_panel, render_block_modal, render_block_node_card
from bloxsmith_app.graph_introspection import describe_block

from ui_smoke_common import (
    create_run_api,
    data_edge,
    display_node,
    expect,
    graph_payload,
    http_json,
    isolated_server,
    text_node,
    wait_for_run_terminal,
)
from urllib.parse import quote
from block_test_packages import install_test_package, release_key, surface_payload


def directory_list_node(folder_path: str = "", *, pattern: str = "*.mp3", recursive: bool = False) -> dict[str, Any]:
    return {
        "id": "directory-list-1",
        "kind": "directory_list",
        "title": "Directory List",
        "position": {"x": 360, "y": 120},
        "inputs": [
            {
                "id": 1,
                "name": "folder",
                "title": "Folder",
                "accepts": ["file/path", "message/*", "application/json"],
                "multiplicity": "many",
            }
        ],
        "outputs": [
            {"id": 1, "name": "liste", "title": "Files", "emits": ["application/json", "message/*"], "multiplicity": "many"}
        ],
        "config": {
            "folder_path": folder_path,
            "pattern": pattern,
            "recursive": recursive,
        },
    }


def direct_context(*, root_dir: Path, run_dir: Path, config: dict[str, Any], input_message: str = "") -> BlockRuntimeContext:
    return BlockRuntimeContext(
        run_id="direct-run",
        node_id="directory-list-direct",
        kind="directory_list",
        title="Directory List",
        config=config,
        inputs={},
        input_content_types={},
        input_message=input_message,
        input_ports=(),
        output_ports=(SimpleNamespace(id=1, name="liste"),),
        root_dir=root_dir,
        run_dir=run_dir,
    )


def write_fixture_tree(root: Path) -> Path:
    folder = root / "tmp" / "directory-list"
    nested = folder / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    (folder / "b.mp3").write_text("b", encoding="utf-8")
    (folder / "a.mp3").write_text("a", encoding="utf-8")
    (folder / "notes.txt").write_text("notes", encoding="utf-8")
    (nested / "c.mp3").write_text("c", encoding="utf-8")
    return folder


def assert_directory_list_payload(payload: str, *, expected_names: list[str]) -> list[dict[str, Any]]:
    parsed = json.loads(payload)
    expect(isinstance(parsed, list), "Directory List doit emettre une liste JSON.")
    names = [wrapper.get("item", {}).get("file_name") for wrapper in parsed]
    expect(names == expected_names, f"Fichiers inattendus: {names}")
    for index, wrapper in enumerate(parsed, start=1):
        expect(isinstance(wrapper, dict) and "item" in wrapper, "Chaque entree doit etre compatible List: {item: ...}.")
        item = wrapper["item"]
        expect(Path(item["path"]).is_file(), "Chaque item doit contenir un path fichier valide.")
        expect(item["index"] == index, "Chaque item doit exposer son index.")
        expect(item["extension"] == ".mp3", "Le filtre *.mp3 doit sortir uniquement des MP3.")
        expect(int(item["size_bytes"]) > 0, "Chaque item doit exposer size_bytes.")
    return parsed


def runtime_node_id_for_kind(run: dict[str, Any], kind: str) -> str:
    """Return the normalized runtime node id for one unique node kind in a run payload."""

    nodes = (run.get("document") or {}).get("nodes") or []
    matches = [str(node.get("id") or "") for node in nodes if node.get("kind") == kind]
    expect(len(matches) == 1 and matches[0], f"Node runtime {kind} introuvable ou ambigu: {matches}")
    return matches[0]


def run_directory_list_case(runtime_mode: str) -> None:
    with isolated_server() as server:
        # Les surfaces sont des assets de release : le bundled kind n'en sert aucun.
        model = install_test_package(server, "directory_list")
        key = quote(release_key(model), safe="")
        served = lambda payload, suffix: next(
            asset["path"] for asset in payload["assets"] if asset["path"].endswith(suffix))
        folder = write_fixture_tree(server.root_dir)
        document = graph_payload(
            f"F5 Directory List {runtime_mode}",
            [
                text_node("text-1", "Folder path", str(folder), 80, 120),
                directory_list_node(pattern="*.mp3"),
                display_node("display-1", "Display", 700, 120),
            ],
            [
                data_edge("edge-text-directory-list", "text-1", 1, "directory-list-1", 1),
                data_edge("edge-directory-list-display", "directory-list-1", 1, "display-1", 1),
            ],
        )
        created = create_run_api(server, document, runtime_mode=runtime_mode)
        run = wait_for_run_terminal(server, str(created.get("run_id") or ""), timeout_sec=25)

        logs = "\n".join(run.get("logs", []))
        directory_node_id = runtime_node_id_for_kind(run, "directory_list")
        node_logs = "\n".join(run.get("node_logs", {}).get(directory_node_id, []))
        expect(run.get("status") == "success", f"Le run Directory List {runtime_mode} doit reussir.")
        payload = run.get("output_values", {}).get(f"{directory_node_id}:1", {}).get("value") or ""
        assert_directory_list_payload(payload, expected_names=["a.mp3", "b.mp3"])
        expect("[done] Directory List" in f"{logs}\n{node_logs}", "Directory List doit tracer le nombre de fichiers.")
        if runtime_mode == "zeromq_active":
            expect(
                run.get("results", {}).get(directory_node_id, {}).get("transport") == "zeromq_active",
                "directory_list doit etre execute via zeromq_active.",
            )


def test_direct_runtime() -> None:
    with isolated_server() as server:
        folder = write_fixture_tree(server.root_dir)
        block = DirectoryListBlock()
        result = block.execute_runtime(
            direct_context(
                root_dir=server.root_dir,
                run_dir=server.root_dir / "runs" / "direct",
                config={"folder_path": str(folder), "pattern": "*.mp3", "recursive": True},
            )
        )
        expect(result.status == "success", "Directory List direct doit reussir.")
        parsed = assert_directory_list_payload(result.outputs[0].value, expected_names=["a.mp3", "b.mp3", "c.mp3"])
        expect(parsed[-1]["item"]["relative_path"] == "nested/c.mp3", "Le mode recursif doit conserver le chemin relatif.")
        expect(result.metadata.get("directory_list", {}).get("file_count") == 3, "Le metadata doit exposer file_count.")


def test_inspector_contract() -> None:
    node = directory_list_node("fixtures/audio", pattern="*.wav", recursive=True)
    rendered = render_block_inspector_panel("directory_list", {"node": node})
    html = str(rendered.get("html") or "")
    expect("data-directory-list-inspector-root" in html, "Le panneau inspecteur Directory List doit venir du bloc.")
    expect("data-path-browser" in html, "Le panneau Directory List doit utiliser le path browser commun.")
    expect('data-path-browser-select-mode="directory"' in html, "Directory List doit sélectionner un dossier.")
    expect("data-directory-list-folder-path" in html, "Le panneau doit exposer le dossier.")
    expect("data-directory-list-pattern" in html, "Le panneau doit exposer le filtre.")
    expect("data-directory-list-recursive" in html, "Le panneau doit exposer le mode recursif.")
    expect("data-block-apply" in html, "Le panneau Directory List doit exposer le bouton Appliquer.")
    assets = rendered.get("assets") or []
    expect(rendered.get("context", {}).get("inspector_title") == "Directory List", "Le titre inspecteur doit venir du bloc.")

    ports_rendered = render_block_inspector_panel("directory_list", {"node": node, "inspector_tab": "ports"})
    ports_html = str(ports_rendered.get("html") or "")
    expect('data-inspector-panel-tab="ports"' in ports_html, "Le panneau doit exposer l'onglet Ports.")
    expect("data-add-input-port type=\"button\" disabled" in ports_html, "Directory List ne doit pas permettre d'ajouter un input.")
    expect("data-add-output-port type=\"button\" disabled" in ports_html, "Directory List ne doit pas permettre d'ajouter une sortie.")

    result = handle_block_ui_action(
        "directory_list",
        {
            "node": node,
            "action": "inspector_update_directory_list",
            "values": {
                "folder_path": "./media",
                "pattern": "",
                "recursive": False,
            },
        },
    )
    config = result.get("node_patch", {}).get("config", {})
    expect(config.get("folder_path") == "./media", "Le dossier doit etre conserve.")
    expect(config.get("pattern") == "*", "Un filtre vide doit retomber sur *.")
    expect(config.get("recursive") is False, "Le mode recursif doit etre modifiable.")

    modal = render_block_modal("directory_list", {"node": node, "runtime": {}})
    modal_html = str(modal.get("html") or "")
    expect("data-directory-list-modal-root" in modal_html, "Le modal Directory List doit venir du bloc.")
    expect("data-block-runtime-refresh=\"autonomous\"" in modal_html, "Le modal Directory List doit gérer son refresh runtime.")
    expect("data-path-browser" in modal_html, "Le modal Directory List doit utiliser le path browser commun.")
    expect("data-directory-list-apply" in modal_html, "Le modal Directory List doit exposer son action Appliquer.")
    modal_assets = modal.get("assets") or []

    modal_result = handle_block_ui_action(
        "directory_list",
        {
            "node": node,
            "action": "modal_update_directory_list",
            "values": {
                "folder_path": "./modal-media",
                "pattern": "*.wav",
                "recursive": True,
            },
        },
    )
    modal_config = modal_result.get("node_patch", {}).get("config", {})
    expect(modal_config.get("folder_path") == "./modal-media", "Le modal doit persister le dossier.")
    expect(modal_config.get("pattern") == "*.wav", "Le modal doit persister le filtre.")
    expect(modal_config.get("recursive") is True, "Le modal doit persister le mode recursif.")


def test_node_card_contract() -> None:
    node = directory_list_node("fixtures/audio", pattern="*.mp3", recursive=True)
    rendered = render_block_node_card("directory_list", {"node": node})
    html = str(rendered.get("html") or "")
    expect("data-directory-list-node-card" in html, "La carte Directory List doit venir du bloc.")
    expect("*.mp3" in html, "La carte Directory List doit exposer le filtre.")
    expect("recursive" in html, "La carte Directory List doit exposer le mode recursif.")
    expect(
        "directory-list-node" in (rendered.get("context", {}).get("node_classes") or []),
        "La carte doit demander sa classe visuelle de node.",
    )


def test_node_card_endpoint() -> None:
    with isolated_server() as server:
        # Les surfaces sont des assets de release : le bundled kind n'en sert aucun.
        model = install_test_package(server, "directory_list")
        key = quote(release_key(model), safe="")
        served = lambda payload, suffix: next(
            asset["path"] for asset in payload["assets"] if asset["path"].endswith(suffix))
        node = directory_list_node("fixtures/audio", pattern="*.wav", recursive=False)
        rendered = surface_payload(server, model, node, "node_card")
        html = str(rendered.get("html") or "")
        expect("data-directory-list-node-card" in html, "Endpoint node-card doit rendre le HTML Directory List.")
        expect("*.wav" in html, "Endpoint node-card doit transmettre le filtre.")
        assets = rendered.get("assets") or []
        with urlopen(f"{server.base_url}/api/blocks/{key}/assets/{served(rendered, 'assets/css/node_card.css')}", timeout=5) as response:
            body = response.read().decode("utf-8")
        expect("directory-list-node" in body, "Asset CSS node_card non servi.")


def test_introspection() -> None:
    description = describe_block("directory_list")
    expect(description["title"] == "Directory List", "Le bloc Directory List doit etre decouvert par introspection.")
    expect(description["default_config"]["pattern"] == "*", "Le filtre par defaut doit etre introspecte.")
    expect(description["capabilities"]["runtime_executable"], "directory_list doit etre runtime_executable.")
    expect(description["capabilities"]["active_worker"], "directory_list doit etre active_worker.")
    expect(description["capabilities"]["file_browser"], "directory_list doit exposer le browse dossier.")


def main() -> None:
    run_directory_list_case("centralized")
    run_directory_list_case("zeromq_active")
    test_direct_runtime()
    test_inspector_contract()
    test_node_card_contract()
    test_node_card_endpoint()
    test_introspection()
    expect(DirectoryListBlock().kind == "directory_list", "Le bloc Directory List doit exposer son kind.")
    print("[ok] F5.19_directory_list_block")


if __name__ == "__main__":
    main()
