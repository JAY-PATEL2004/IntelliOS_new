const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld(
  'api', {
    // Authentication
    login: (credentials) => ipcRenderer.invoke('login', credentials),
    signup: (userData) => ipcRenderer.invoke('signup', userData),
    logout: () => ipcRenderer.invoke('logout'),
    setUserData: (data) => ipcRenderer.invoke('set-user-data', data),
    getUserData: () => ipcRenderer.invoke('get-user-data'),
    
    // State management
    captureState: () => ipcRenderer.invoke('capture-state'),
    restoreState: (state) => ipcRenderer.invoke('restore-state', state),
    
    // Workspace management
    getWorkspaces: () => ipcRenderer.invoke('get-workspaces'),
    saveWorkspace: (workspace) => ipcRenderer.invoke('save-workspace', workspace),
    updateWorkspace: (workspaceData) => ipcRenderer.invoke('update-workspace', workspaceData),
    deleteWorkspace: (workspaceId) => ipcRenderer.invoke('delete-workspace', workspaceId)
  }
);