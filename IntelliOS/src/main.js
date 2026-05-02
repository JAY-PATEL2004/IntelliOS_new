const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');
// const fetch = (...args) => import('node-fetch').then(({default: fetch}) => fetch(...args));

// Handle to main window
let mainWindow;

// Paths for storing data
const USER_DATA_FILE = path.join(app.getPath('userData'), 'user_data.json');
const WORKSPACES_FILE = path.join(app.getPath('userData'), 'workspaces.json');

// Store current user data
let currentUser = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    }
  });

  // Check if user is logged in
  if (fs.existsSync(USER_DATA_FILE)) {
    try {
      const userData = JSON.parse(fs.readFileSync(USER_DATA_FILE, 'utf8'));
      if (userData.username) {
        currentUser = userData;
        mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
        return;
      }
    } catch (error) {
      console.error('Error reading user data:', error);
    }
  }

  // If no user data, show login page
  mainWindow.loadFile(path.join(__dirname, 'renderer', 'auth.html'));
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Authentication Handlers
ipcMain.handle('login', async (event, credentials) => {
  try {
    console.log(JSON.stringify(credentials))
    console.log("Node version:", process.version);
    console.log("Fetch available:", typeof fetch);
    const response = await fetch('http://127.0.0.1:8000/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials)
    });
    // console.log(response)
    return await response.json();
  } catch (error) {
    console.error('Login failed:', error);
    throw error;
  }
});

ipcMain.handle('signup', async (event, userData) => {
  try {
    const response = await fetch('http://127.0.0.1:8000/api/signup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData)
    });
    return await response.json();
  } catch (error) {
    console.error('Signup failed:', error);
    throw error;
  }
});

ipcMain.handle('logout', () => {
  currentUser = null;
  if (fs.existsSync(USER_DATA_FILE)) {
    fs.unlinkSync(USER_DATA_FILE);
  }
  mainWindow.loadFile(path.join(__dirname, 'renderer', 'auth.html'));
});

ipcMain.handle('set-user-data', (event, data) => {
  currentUser = data;
  fs.writeFileSync(USER_DATA_FILE, JSON.stringify(data));
});

ipcMain.handle('get-user-data', () => {
  return currentUser;
});

// IPC Handlers
ipcMain.handle('capture-state', async () => {
  try {
    const response = await fetch('http://127.0.0.1:8000/api/capture');
    return await response.json();
  } catch (error) {
    console.error('Failed to capture state:', error);
    throw error;
  }
});

ipcMain.handle('restore-state', async (event, state) => {
  try {
    console.log("restoration_request : ",state.browsers[0].windows[0].tabs)
    const response = await fetch('http://127.0.0.1:8000/api/restore', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(state)
    });
    return await response.json();
  } catch (error) {
    console.error('Failed to restore state:', error);
    throw error;
  }
});

// Workspace management - All through API
ipcMain.handle('get-workspaces', async (event) => {
  try {
    const user = currentUser;
    if (!user) {
      throw new Error('User not authenticated');
    }
    
    const response = await fetch('http://127.0.0.1:8000/api/workspaces', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: user.username })
    });
    
    const result = await response.json();
    if (result.status === 'success') {
      return result.workspaces;
    } else {
      throw new Error(result.message || 'Failed to fetch workspaces');
    }
  } catch (error) {
    console.error('Failed to read workspaces:', error);
    return {};
  }
});

ipcMain.handle('save-workspace', async (event, workspaceData) => {
  try {
    const { username, workspace_name, state } = workspaceData;
    
    const response = await fetch('http://127.0.0.1:8000/api/workspace', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username,
        workspace_name,
        state
      })
    });
    
    const result = await response.json();
    if (result.status === 'success') {
      return true;
    } else {
      throw new Error(result.message || 'Failed to save workspace');
    }
  } catch (error) {
    console.error('Failed to save workspace:', error);
    throw error;
  }
});