import { withProperties } from "./properties.js";

/**
 * Role: Mounts the directory list block inspector panel frontend.
 * File Name: inspector_panel.js
 * Author: Alexandre EL
 * Email: alex@hackinvent.com
 * Created Date: 2026-05-10
 */

import { mountDirectoryListEditor } from "./common.js";

/**
 * Mount the Directory List inspector panel bindings.
 *
 * @param {HTMLElement} root - Mounted Directory List inspector root.
 * @param {object} api - Generic block UI API exposing block actions.
 * @returns {void}
 */
function mountOwned(root, api) {
  mountDirectoryListEditor(root, api, {
    actionName: "inspector_update_directory_list",
  });
}

/** Keep the block behavior and add properties-only accessibility. */
export function mount(root, ...args) {
  return withProperties(mountOwned).call(this, root, ...args);
}
