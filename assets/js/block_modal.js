/**
 * Role: Mounts the directory list block modal frontend.
 * File Name: block_modal.js
 * Author: Alexandre EL
 * Email: alex@hackinvent.com
 * Created Date: 2026-06-10
 */

(function () {
  "use strict";

  const registry = (window.CWBlockUiBlocks = window.CWBlockUiBlocks || {});

  registry.directory_list = {
    /**
     * Mount the Directory List modal bindings using the modal update action.
     *
     * @param {HTMLElement} root - Mounted Directory List modal root.
     * @param {object} api - Generic block UI API exposing block actions.
     * @returns {void}
     */
    mount(root, api) {
      window.CWDirectoryListBlockUi?.mountDirectoryListEditor?.(root, api, {
        actionName: "modal_update_directory_list",
      });
    },
  };
})();
