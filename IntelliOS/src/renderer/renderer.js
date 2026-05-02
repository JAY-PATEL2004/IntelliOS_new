// DOM Elements
const captureBtn = document.getElementById('captureBtn');
const selectAllBtn = document.getElementById('selectAllBtn');
const unselectAllBtn = document.getElementById('unselectAllBtn');
const logoutBtn = document.getElementById('logoutBtn');
const userNameSpan = document.getElementById('userName');
const saveWorkspaceBtn = document.getElementById('saveWorkspaceBtn');
const workspaceNameInput = document.getElementById('workspaceName');
const capturedStateSection = document.getElementById('capturedState');
const browserTabsContainer = document.getElementById('browserTabs').querySelector('.items');
const applicationsContainer = document.getElementById('applications').querySelector('.items');
const workspacesList = document.querySelector('.workspace-list');

// Modal Elements
const infoModal = document.getElementById('infoModal');
const editModal = document.getElementById('editModal');
const closeInfoBtn = document.getElementById('closeInfoBtn');
const closeEditBtn = document.getElementById('closeEditBtn');
const editWorkspaceBtn = document.getElementById('editWorkspaceBtn');
const saveEditBtn = document.getElementById('saveEditBtn');
const infoModalCloseBtn = infoModal.querySelector('.modal-close-btn');
const editModalCloseBtn = editModal.querySelector('.modal-close-btn');

// Suggestions Modal Elements
const suggestionsLoadingModal = document.getElementById('suggestionsLoadingModal');
const suggestionsModal = document.getElementById('suggestionsModal');
const suggestionsListEl = document.getElementById('suggestionsList');
const skipSuggestionsBtn = document.getElementById('skipSuggestionsBtn');
const applySuggestionBtn = document.getElementById('applySuggestionBtn');
const closeSuggestionsModalBtn = document.getElementById('closeSuggestionsModalBtn');

// Current state storage
let currentState = null;
let currentUsername = null;
let currentWorkspaceInfo = null;
let currentWorkspaceName = null;
let selectedSuggestionTopic = null;

// API Configuration
const API_BASE_URL = 'http://127.0.0.1:8000';
const SUGGESTIONS_API_URL = 'http://127.0.0.1:8000/api/suggestions';
const TOPIC_CANDIDATES = [
  // FILL THESE 100 TOPICS
  // 'Finance',
  // 'Development',
  // 'Marketing',
];

// Initialize
async function initialize() {
  const userData = await window.api.getUserData();
  if (userData) {
    userNameSpan.textContent = `Welcome, ${userData.username}`;
    currentUsername = userData.username;
    loadWorkspaces();
  } else {
    window.location.href = 'auth.html';
  }
}
initialize();

// Event Listeners
captureBtn.addEventListener('click', captureCurrentState);
selectAllBtn.addEventListener('click', selectAllItems);
unselectAllBtn.addEventListener('click', unselectAllItems);
logoutBtn.addEventListener('click', () => window.api.logout());
saveWorkspaceBtn.addEventListener('click', saveCurrentWorkspace);

// Modal Event Listeners
closeInfoBtn.addEventListener('click', closeInfoModal);
closeEditBtn.addEventListener('click', closeEditModal);
infoModalCloseBtn.addEventListener('click', closeInfoModal);
editModalCloseBtn.addEventListener('click', closeEditModal);
editWorkspaceBtn.addEventListener('click', openEditModal);
saveEditBtn.addEventListener('click', saveEditedWorkspace);

// Suggestions Modal Event Listeners
skipSuggestionsBtn.addEventListener('click', closeSuggestionsModal);
closeSuggestionsModalBtn.addEventListener('click', closeSuggestionsModal);
applySuggestionBtn.addEventListener('click', applySelectedSuggestion);

// Close modals when clicking outside
infoModal.addEventListener('click', (e) => {
  if (e.target === infoModal) closeInfoModal();
});

editModal.addEventListener('click', (e) => {
  if (e.target === editModal) closeEditModal();
});

suggestionsModal.addEventListener('click', (e) => {
  if (e.target === suggestionsModal) closeSuggestionsModal();
});

// Functions
async function captureCurrentState() {
  try {
    captureBtn.disabled = true;
    captureBtn.textContent = 'Capturing...';

    currentState = await window.api.captureState();
    displayCapturedState(currentState.state);
    capturedStateSection.classList.remove('hidden');
    captureBtn.textContent = 'Capture Current State';

    if (currentState && currentState.state) {
      fetchTopicSuggestions(currentState.state);
    }
  } catch (error) {
    console.error('Failed to capture state:', error);
    alert('Failed to capture current state. Please try again.');
    captureBtn.textContent = 'Capture Current State';
  } finally {
    captureBtn.disabled = false;
  }
}

function displayCapturedState(state) {
  browserTabsContainer.innerHTML = '';
  applicationsContainer.innerHTML = '';

  if (state.browsers && state.browsers.length > 0) {
    state.browsers.forEach(browser => {
      browser.windows.forEach(windowItem => {
        windowItem.tabs.forEach(tab => {
          const tabElement = createItemCard({
            id: `tab-${tab.id || Date.now() + Math.random()}`,
            title: tab.title || 'Untitled Tab',
            details: tab.url || 'No URL',
            type: 'browser',
            data: {
              browser: browser.browser,
              profile: windowItem.profile,
              debuggingPort: windowItem.debuggingPort,
              tab: tab,
              exe: browser.exe
            }
          });
          browserTabsContainer.appendChild(tabElement);
        });
      });
    });
  }

  if (state.apps && state.apps.length > 0) {
    state.apps.forEach(app => {
      const itemsList = app.items && app.items.length > 0
      ? app.items.map(item => escapeHtml(item)).join(', ')
      : 'No items';
      const appElement = createItemCard({
        id: `app-${app.pid || Date.now() + Math.random()}`,
        title: app.name || 'Unknown Application',
        details: `Opened items: ${app.items && app.items.length > 0 ? itemsList : 'N/A'}`,
        type: 'application',
        data: app
      });
      applicationsContainer.appendChild(appElement);
    });
  }
}

function createItemCard({ id, title, details, type, data }) {
  const div = document.createElement('div');
  div.className = 'item-card';
  div.innerHTML = `
    <input type="checkbox" id="${id}" data-type="${type}" data-item='${JSON.stringify(data)}'>
    <div class="item-info">
      <div class="item-title">${escapeHtml(title)}</div>
      <div class="item-details">${escapeHtml(details)}</div>
    </div>
  `;
  return div;
}

function selectAllItems() {
  document.querySelectorAll('.item-card input[type="checkbox"]').forEach(checkbox => {
    checkbox.checked = true;
  });
}

function unselectAllItems() {
  document.querySelectorAll('.item-card input[type="checkbox"]').forEach(checkbox => {
    checkbox.checked = false;
  });
}

async function saveCurrentWorkspace() {
  const name = workspaceNameInput.value.trim();
  if (!name) {
    alert('Please enter a workspace name');
    return;
  }

  const selectedItems = Array.from(document.querySelectorAll('.item-card input[type="checkbox"]:checked')).map(checkbox => ({
    type: checkbox.dataset.type,
    data: JSON.parse(checkbox.dataset.item)
  }));

  if (selectedItems.length === 0) {
    alert('Please select at least one item');
    return;
  }

  try {
    saveWorkspaceBtn.disabled = true;
    saveWorkspaceBtn.textContent = 'Saving...';

    const stateToSave = {
      saved_at: new Date().toISOString(),
      user: currentUsername,
      browsers: [],
      apps: []
    };

    selectedItems.forEach(item => {
      if (item.type === 'browser') {
        stateToSave.browsers.push({
          browser: item.data.browser,
          exe: item.data.exe,
          windows: [{
            profile: item.data.profile,
            debuggingPort: item.data.debuggingPort,
            tabs: [item.data.tab]
          }]
        });
      } else if (item.type === 'application') {
        stateToSave.apps.push(item.data);
      }
    });

    const response = await fetch(`${API_BASE_URL}/api/workspace`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: currentUsername,
        workspacename: name,
        state: stateToSave
      })
    });

    const result = await response.json();

    if (result.status === 'success') {
      alert('Workspace saved successfully!');
      workspaceNameInput.value = '';
      loadWorkspaces();
    } else {
      alert(`Failed to save workspace: ${result.message}`);
    }
  } catch (error) {
    console.error('Failed to save workspace:', error);
    alert('Failed to save workspace. Please try again.');
  } finally {
    saveWorkspaceBtn.disabled = false;
    saveWorkspaceBtn.textContent = 'Save as Workspace';
  }
}

async function loadWorkspaces() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/workspaces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: currentUsername })
    });

    const result = await response.json();

    if (result.status === 'success') {
      displayWorkspaces(result.workspaces);
    } else {
      console.error('Failed to load workspaces:', result.message);
    }
  } catch (error) {
    console.error('Failed to load workspaces:', error);
  }
}

function displayWorkspaces(workspaces) {
  workspacesList.innerHTML = '';

  if (!workspaces || Object.keys(workspaces).length === 0) {
    workspacesList.innerHTML = `
      <p style="grid-column: 1 / -1; text-align: center; color: #999;">
        No workspaces yet. Capture state and save a workspace!
      </p>
    `;
    return;
  }

  Object.entries(workspaces).forEach(([workspaceName, workspaceData]) => {
    const card = document.createElement('div');
    card.className = 'workspace-card';

    const browserCount = workspaceData.browsers ? workspaceData.browsers.length : 0;
    const appCount = workspaceData.apps ? workspaceData.apps.length : 0;
    const savedAt = new Date(workspaceData.saved_at || workspaceData.savedat).toLocaleDateString();

    card.innerHTML = `
      <h3>${escapeHtml(workspaceName)}</h3>
      <div class="workspace-meta">
        Saved: ${savedAt}<br>
        Browsers: ${browserCount} | Apps: ${appCount}
      </div>
      <div class="workspace-card-buttons">
        <button class="info-btn secondary-btn">Info</button>
        <button class="restore-btn primary-btn">Restore</button>
      </div>
    `;

    const infoBtn = card.querySelector('.info-btn');
    const restoreBtn = card.querySelector('.restore-btn');

    infoBtn.addEventListener('click', () => showWorkspaceInfo(workspaceName));
    restoreBtn.addEventListener('click', () => restoreWorkspace(workspaceName));

    workspacesList.appendChild(card);
  });
}

async function showWorkspaceInfo(workspaceName) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/workspaces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: currentUsername })
    });

    const result = await response.json();

    if (result.status === 'success' && result.workspaces[workspaceName]) {
      currentWorkspaceName = workspaceName;
      currentWorkspaceInfo = result.workspaces[workspaceName];
      displayWorkspaceInfo(workspaceName, currentWorkspaceInfo);
      infoModal.classList.remove('hidden');
    }
  } catch (error) {
    console.error('Failed to load workspace info:', error);
    alert('Failed to load workspace information.');
  }
}

function displayWorkspaceInfo(workspaceName, workspaceData) {
  const infoModalTitle = document.getElementById('infoModalTitle');
  const infoBrowsersList = document.getElementById('infoBrowsersList');
  const infoAppsList = document.getElementById('infoAppsList');

  infoModalTitle.textContent = `${workspaceName} - Information`;

  infoBrowsersList.innerHTML = '';
  if (workspaceData.browsers && workspaceData.browsers.length > 0) {
    workspaceData.browsers.forEach((browser, bIndex) => {
      browser.windows.forEach((windowItem, wIndex) => {
        const item = document.createElement('div');
        item.className = 'info-item';
        // const tabCount = windowItem.tabs ? windowItem.tabs.length : 0;
        item.innerHTML = `
          <div style="width: 100%">
            <div class="info-item-title">${escapeHtml((browser.browser || 'browser').toUpperCase())} - Window ${wIndex + 1}</div>
            <div class="info-item-details">
              <strong>Profile:</strong> ${escapeHtml(windowItem.profile || 'N/A')}<br>
              <strong>Debugging Port:</strong> ${escapeHtml(String(windowItem.debuggingPort || 'N/A'))}<br>
              <strong>Tabs:</strong> ${windowItem.tabs && windowItem.tabs.length ? windowItem.tabs.map(tab => tab.title).join(', ') : 'No tabs'}
            </div>
          </div>
        `;
        infoBrowsersList.appendChild(item);
      });
    });
  } else {
    infoBrowsersList.innerHTML = `<div class="info-item-empty">No browsers in this workspace</div>`;
  }

  infoAppsList.innerHTML = '';
  if (workspaceData.apps && workspaceData.apps.length > 0) {
    workspaceData.apps.forEach(app => {
      const item = document.createElement('div');
      item.className = 'info-item';
      const itemsList = app.items && app.items.length > 0
      ? app.items.map(item => escapeHtml(item)).join(', ')
      : 'No items';
      item.innerHTML = `
        <div style="width: 100%">
          <div class="info-item-title">${escapeHtml(app.name || 'Unknown Application')}</div>
          <div class="info-item-details">
            <strong>Opened Items: </strong> ${itemsList}<br>
            ${app.exe ? `<strong>Executable:</strong> ${escapeHtml(app.exe)}<br>` : ''}
            ${app.windowInfo ? `<strong>Window State:</strong> ${escapeHtml(app.windowInfo.state || 'N/A')}` : ''}
          </div>
        </div>
      `;
      infoAppsList.appendChild(item);
    });
  } else {
    infoAppsList.innerHTML = `<div class="info-item-empty">No applications in this workspace</div>`;
  }
}

function closeInfoModal() {
  infoModal.classList.add('hidden');
  currentWorkspaceName = null;
  currentWorkspaceInfo = null;
}

async function openEditModal() {
  infoModal.classList.add('hidden');

  try {
    const captureResponse = await window.api.captureState();
    const availableState = captureResponse.state;
    displayEditModal(availableState);
    editModal.classList.remove('hidden');
  } catch (error) {
    console.error('Failed to capture current state for editing:', error);
    alert('Failed to load current state for editing.');
  }
}

function displayEditModal(availableState) {
  const editWorkspaceBrowsers = document.getElementById('editWorkspaceBrowsers');
  const editWorkspaceApps = document.getElementById('editWorkspaceApps');
  const editAvailableBrowsers = document.getElementById('editAvailableBrowsers');
  const editAvailableApps = document.getElementById('editAvailableApps');

  editWorkspaceBrowsers.innerHTML = '';
  editWorkspaceApps.innerHTML = '';
  editAvailableBrowsers.innerHTML = '';
  editAvailableApps.innerHTML = '';

  if (currentWorkspaceInfo.browsers && currentWorkspaceInfo.browsers.length > 0) {
    currentWorkspaceInfo.browsers.forEach((browser, bIndex) => {
      browser.windows.forEach((windowItem, wIndex) => {
        const item = createEditItem(
          `ws-browser-${bIndex}-${wIndex}`,
          `${(browser.browser || 'browser').toUpperCase()} - Window ${wIndex + 1}`,
          `Port ${windowItem.debuggingPort || 'N/A'} \n Tabs: ${windowItem.tabs && windowItem.tabs.length ? windowItem.tabs.map(tab => tab.title).join(', ') : 'No tabs'}`,
          true,
          'browser'
        );
        editWorkspaceBrowsers.appendChild(item);
      });
    });
  } else {
    editWorkspaceBrowsers.innerHTML = `<div class="edit-item-empty">No browsers in workspace</div>`;
  }

  if (currentWorkspaceInfo.apps && currentWorkspaceInfo.apps.length > 0) {
    currentWorkspaceInfo.apps.forEach((app, aIndex) => {
      const itemsList = app.items && app.items.length > 0
      ? app.items.map(item => escapeHtml(item)).join(', ')
      : 'No items';
      const item = createEditItem(
        `ws-app-${aIndex}`,
        app.name || 'Unknown Application',
        `Opened items: ${app.items && app.items.length ? itemsList : 'N/A'}`,
        true,
        'application'
      );
      editWorkspaceApps.appendChild(item);
    });
  } else {
    editWorkspaceApps.innerHTML = `<div class="edit-item-empty">No applications in workspace</div>`;
  }

  if (availableState.browsers && availableState.browsers.length > 0) {
    availableState.browsers.forEach((browser, bIndex) => {
      browser.windows.forEach((windowItem, wIndex) => {
        const item = createEditItem(
          `avail-browser-${bIndex}-${wIndex}`,
          `${(browser.browser || 'browser').toUpperCase()} - Window ${wIndex + 1}`,
          `Port ${windowItem.debuggingPort || 'N/A'} \n Tabs: ${windowItem.tabs && windowItem.tabs.length ? windowItem.tabs.map(tab => tab.title).join(', ') : 'No tabs'}`,
          false,
          'browser'
        );
        editAvailableBrowsers.appendChild(item);
      });
    });
  } else {
    editAvailableBrowsers.innerHTML = `<div class="edit-item-empty">No browsers available</div>`;
  }

  if (availableState.apps && availableState.apps.length > 0) {
    availableState.apps.forEach((app, aIndex) => {
      const itemsList = app.items && app.items.length > 0
      ? app.items.map(item => escapeHtml(item)).join(', ')
      : 'No items';
      const item = createEditItem(
        `avail-app-${aIndex}`,
        app.name || 'Unknown Application',
        `Opened items: ${app.items && app.items.length ? app.items : 'N/A'}`,
        false,
        'application'
      );
      editAvailableApps.appendChild(item);
    });
  } else {
    editAvailableApps.innerHTML = `<div class="edit-item-empty">No applications available</div>`;
  }
}

function createEditItem(id, title, details, isInWorkspace, type) {
  const div = document.createElement('div');
  div.className = 'edit-item';
  div.innerHTML = `
    <input type="checkbox" id="${id}" ${isInWorkspace ? 'checked' : ''} data-type="${type}">
    <div class="edit-item-info">
      <div class="edit-item-title">${escapeHtml(title)}</div>
      <div class="edit-item-details">${escapeHtml(details)}</div>
    </div>
  `;
  return div;
}

function closeEditModal() {
  editModal.classList.add('hidden');
}

async function saveEditedWorkspace() {
  try {
    saveEditBtn.disabled = true;
    saveEditBtn.textContent = 'Saving...';

    const captureResponse = await window.api.captureState();
    const freshState = captureResponse.state;

    const selectedWorkspaceBrowsers = Array.from(
      document.querySelectorAll('#editWorkspaceBrowsers input[type="checkbox"]:checked')
    ).map(checkbox => checkbox.id);

    const selectedWorkspaceApps = Array.from(
      document.querySelectorAll('#editWorkspaceApps input[type="checkbox"]:checked')
    ).map(checkbox => checkbox.id);

    const selectedAvailableBrowsers = Array.from(
      document.querySelectorAll('#editAvailableBrowsers input[type="checkbox"]:checked')
    ).map(checkbox => checkbox.id);

    const selectedAvailableApps = Array.from(
      document.querySelectorAll('#editAvailableApps input[type="checkbox"]:checked')
    ).map(checkbox => checkbox.id);

    const newState = {
      saved_at: new Date().toISOString(),
      user: currentUsername,
      browsers: [],
      apps: []
    };

    currentWorkspaceInfo.browsers?.forEach((browser, bIndex) => {
      browser.windows.forEach((windowItem, wIndex) => {
        const id = `ws-browser-${bIndex}-${wIndex}`;
        if (selectedWorkspaceBrowsers.includes(id)) {
          newState.browsers.push(browser);
        }
      });
    });

    freshState.browsers?.forEach((browser, bIndex) => {
      browser.windows.forEach((windowItem, wIndex) => {
        const id = `avail-browser-${bIndex}-${wIndex}`;
        if (selectedAvailableBrowsers.includes(id)) {
          newState.browsers.push(browser);
        }
      });
    });

    currentWorkspaceInfo.apps?.forEach((app, aIndex) => {
      const id = `ws-app-${aIndex}`;
      if (selectedWorkspaceApps.includes(id)) {
        newState.apps.push(app);
      }
    });

    freshState.apps?.forEach((app, aIndex) => {
      const id = `avail-app-${aIndex}`;
      if (selectedAvailableApps.includes(id)) {
        newState.apps.push(app);
      }
    });

    const response = await fetch(`${API_BASE_URL}/api/workspace`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: currentUsername,
        workspacename: currentWorkspaceName,
        state: newState
      })
    });

    const result = await response.json();

    if (result.status === 'success') {
      alert('Workspace updated successfully!');
      closeEditModal();
      loadWorkspaces();
    } else {
      alert(`Failed to update workspace: ${result.message}`);
    }
  } catch (error) {
    console.error('Failed to save edited workspace:', error);
    alert('Failed to save workspace changes. Please try again.');
  } finally {
    saveEditBtn.disabled = false;
    saveEditBtn.textContent = 'Save Changes';
  }
}

async function restoreWorkspace(workspaceName) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/workspaces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: currentUsername })
    });

    const result = await response.json();

    if (result.status === 'success' && result.workspaces[workspaceName]) {
      const workspaceState = result.workspaces[workspaceName];

      if (!confirm(`Restore workspace "${workspaceName}"? This will launch the saved browsers and applications.`)) {
        return;
      }

      const restoreResponse = await window.api.restoreState(workspaceState);

      if (restoreResponse.status === 'success') {
        alert('Workspace restored successfully!');
      } else {
        alert(`Failed to restore workspace: ${restoreResponse.message}`);
      }
    }
  } catch (error) {
    console.error('Failed to restore workspace:', error);
    alert('Failed to restore workspace. Please try again.');
  }
}

// Suggestions helpers
function showSuggestionsLoading() {
  suggestionsLoadingModal.classList.remove('hidden');
}

function hideSuggestionsLoading() {
  suggestionsLoadingModal.classList.add('hidden');
}

function closeSuggestionsModal() {
  suggestionsModal.classList.add('hidden');
  selectedSuggestionTopic = null;
  applySuggestionBtn.disabled = true;
  suggestionsListEl.innerHTML = '';
}

function openSuggestionsModal(suggestions) {
  suggestionsListEl.innerHTML = '';
  selectedSuggestionTopic = null;
  applySuggestionBtn.disabled = true;

  suggestions.forEach((item, index) => {
    const topic = item.topic;
    const percentage = item.percentage;

    const div = document.createElement('div');
    div.className = 'suggestion-item';
    div.dataset.topic = topic;
    div.innerHTML = `
      <span class="suggestion-topic">${escapeHtml(topic)}</span>
      <span class="suggestion-score">${escapeHtml(String(percentage))}%</span>
    `;

    div.addEventListener('click', () => {
      document.querySelectorAll('.suggestion-item').forEach(el => {
        el.classList.remove('selected');
      });

      div.classList.add('selected');
      selectedSuggestionTopic = topic;
      applySuggestionBtn.disabled = false;
    });

    suggestionsListEl.appendChild(div);
  });

  suggestionsModal.classList.remove('hidden');
}

async function fetchTopicSuggestions(state) {
  if (!SUGGESTIONS_API_URL) {
    console.warn('SUGGESTIONS_API_URL is not configured.');
    return;
  }

  try {
    showSuggestionsLoading();

    const response = await fetch(SUGGESTIONS_API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        state: state,
        // topics: TOPIC_CANDIDATES
      })
    });

    if (!response.ok) {
      throw new Error(`Suggestion API returned ${response.status}`);
    }

    const data = await response.json();

    let suggestions = [];
    if (Array.isArray(data)) {
      suggestions = data;
    } else if (Array.isArray(data.suggestions)) {
      suggestions = data.suggestions;
    } else if (Array.isArray(data.topics)) {
      suggestions = data.topics;
    }

    if (suggestions.length > 0) {
      openSuggestionsModal(suggestions);
    } else {
      console.warn('Suggestion API returned empty suggestions.');
    }
  } catch (error) {
    console.error('Failed to fetch topic suggestions:', error);
  } finally {
    hideSuggestionsLoading();
  }
}


async function applySelectedSuggestion() {
  if (!selectedSuggestionTopic) return;

  try {
    applySuggestionBtn.disabled = true;
    applySuggestionBtn.textContent = 'Saving...';

    if (!currentState || !currentState.state) {
      alert('No captured state available to save.');
      return;
    }

    const fullStateToSave = {
      ...currentState.state,
      saved_at: new Date().toISOString(),
      user: currentUsername
    };

    const response = await fetch(`${API_BASE_URL}/api/workspace`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: currentUsername,
        workspace_name: selectedSuggestionTopic,
        state: fullStateToSave
      })
    });

    const result = await response.json();

    if (result.status === 'success') {
      workspaceNameInput.value = selectedSuggestionTopic;
      closeSuggestionsModal();
      alert('Workspace saved successfully!');
      loadWorkspaces();
    } else {
      alert(`Failed to save workspace: ${result.message}`);
    }
  } catch (error) {
    console.error('Failed to save suggested workspace:', error);
    alert('Failed to save workspace. Please try again.');
  } finally {
    applySuggestionBtn.disabled = false;
    applySuggestionBtn.textContent = 'Use Selected';
  }
}

// Utility
function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// Make functions available globally
window.showWorkspaceInfo = showWorkspaceInfo;
window.restoreWorkspace = restoreWorkspace;