// Narrow, typed bridge. The renderer can only ask the main process to call
// allow-listed local API paths; it never receives the backend token.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("nocturne", {
  request: (method, path, body, raw) => ipcRenderer.invoke("nocturne:request", { method, path, body, raw }),
  status: () => ipcRenderer.invoke("nocturne:status"),
  onStatus: (callback) => {
    const listener = (_e, s) => callback(s);
    ipcRenderer.on("nocturne:status", listener);
    return () => ipcRenderer.removeListener("nocturne:status", listener);
  },
  saveFile: (name, content) => ipcRenderer.invoke("nocturne:save-file", { name, content }),
  revealLog: () => ipcRenderer.invoke("nocturne:reveal-log"),
});
