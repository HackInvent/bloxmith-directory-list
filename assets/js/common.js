/**
 * Role: Provides shared Directory List block UI helpers for modal and inspector surfaces.
 * File Name: common.js
 * Author: Alexandre EL
 * Email: alex@hackinvent.com
 * Created Date: 2026-06-10
 */

/**
 * Bind Directory List configuration fields for inspector and modal surfaces.
 *
 * @param {HTMLElement} root - Mounted inspector or modal root.
 * @param {object} api - Generic block UI API exposing block actions.
 * @param {object} options - Action name used by the current surface.
 * @returns {void}
 */
export function mountDirectoryListEditor(root, api, { actionName = "inspector_update_directory_list" } = {}) {
  const read = (selector) => root.querySelector(selector);
  const folderPath = read("[data-directory-list-folder-path]");
  const pattern = read("[data-directory-list-pattern]");
  const recursive = read("[data-directory-list-recursive]");
  const applyButton = read("[data-directory-list-apply]") || read("[data-block-apply]");
  let dirty = false;

  const values = () => ({
    folder_path: folderPath?.value || "",
    pattern: pattern?.value || "",
    recursive: Boolean(recursive?.checked),
  });

  const markDirty = () => {
    dirty = true;
    if (applyButton) {
      applyButton.disabled = false;
    }
  };

  const apply = () => {
    if (!dirty) {
      return;
    }
    void api.applyAction(actionName, values()).then    dirty = false;
    if (applyButton) {
      applyButton.disabled = true;
    }
  
).catch((error) => {
      api.log?.(`[error] Mise a jour Directory List impossible: ${error.message}`);
    });
  };

  recursive?.addEventListener("change", markDirty);
  [folderPath, pattern].forEach((element) => {
    element?.addEventListener("input", markDirty);
    element?.addEventListener("change", markDirty);
    element?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        apply();
      }
    });
  });
  applyButton?.addEventListener("click", apply);
};
