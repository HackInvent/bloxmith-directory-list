#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# Role: Verifies Directory List block-owned node card rendering in the UI.
# File Name: F8.16_directory_list_node_card_ui.py
# Author: Alexandre EL
# Email: alex@hackinvent.com
# Created Date: 2026-05-11
# -----------------------------------------------------------------------------

"""F8.16 - Modular canvas card of the Directory List block.

The test creates a `directory_list` block from the palette and checks that the
visible card comes from the block-owned `node_card` surface, not the Codex fallback.
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

    expect(node.locator("[data-directory-list-node-card]").count() == 1, "The Directory List card must come from the block.")
    expect(node.locator(".codex-model-badge").count() == 0, "Directory List must not reuse the Codex badges.")
    expect("Directory List" in node.inner_text(), "The Directory List card must show its business title.")


if __name__ == "__main__":
    run_playwright_smoke("F8.16_directory_list_node_card_ui", test_directory_list_node_card)
