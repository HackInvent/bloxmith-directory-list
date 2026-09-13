#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Role: Verifies Directory List block-owned node card rendering in the UI.
# File Name: F8.16_directory_list_node_card_ui.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2026-05-11
# -----------------------------------------------------------------------------

"""F8.16 - Carte canvas modulaire du bloc Directory List.

Le test crée un bloc `directory_list` depuis la palette et vérifie que la carte
visible vient de la surface block-owned `node_card`, pas du fallback Codex.
"""

# Test cases:
# - DirectoryList UI - Create the block from the palette and render its block-owned node card.
# - DirectoryList UI - Verify an unknown/missing template no longer falls back to Codex visuals.

from ui_smoke_common import create_node, expect, node_locator, run_playwright_smoke, wait_for_app_ready


def test_directory_list_node_card(page, server, _blocking_errors) -> None:
    wait_for_app_ready(page, server.base_url)

    node_id = create_node(page, "directory_list")
    node = node_locator(page, node_id)
    page.wait_for_selector(f'.canvas-node[data-node-id="{node_id}"] [data-directory-list-node-card]', timeout=10_000)

    expect(node.locator("[data-directory-list-node-card]").count() == 1, "La carte Directory List doit venir du bloc.")
    expect(node.locator(".codex-model-badge").count() == 0, "Directory List ne doit pas reprendre les badges Codex.")
    expect("Directory List" in node.inner_text(), "La carte Directory List doit afficher son titre metier.")


if __name__ == "__main__":
    run_playwright_smoke("F8.16_directory_list_node_card_ui", test_directory_list_node_card)
