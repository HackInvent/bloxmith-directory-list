/**
 * Role: Mounts the directory list block modal frontend.
 * File Name: block_modal.js
 * Author: Alexandre EL
 * Email: alex@hackinvent.com
 * Created Date: 2026-06-10
 */

import { mountDirectoryListEditor } from "./common.js";

/**
 * Mount the Directory List modal bindings using the modal update action.
 *
 * @param {HTMLElement} root - Mounted Directory List modal root.
 * @param {object} api - Generic block UI API exposing block actions.
 * @returns {void}
 */
export function mount(root, api) {
  mountDirectoryListEditor(root, api, {
    actionName: "modal_update_directory_list",
  });
}
