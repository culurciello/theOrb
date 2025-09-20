// Settings Module
import { getState, setState } from './state.js';
import { 
    loadUserProfile, 
    saveUserProfile, 
    loadApiKeys, 
    saveApiKey, 
    deleteApiKey, 
    updateApiKey,
    loadAvailableLLMs,
    loadCurrentLLM,
    switchLLM,
    testLLM 
} from './api.js';
import { showNotification, showSmartSuggestion } from './ui.js';
import { elements, setHTML } from './dom.js';
import { triggerUIRefresh } from './refresh.js';
import { updateLLMSelector } from './selectors.js';

export function getSettingsContent() {
    const state = getState();
    
    return `
        <div class="settings-container">
            <div class="settings-tabs">
                <button class="settings-tab ${state.activeSettingsTab === 'profile' ? 'active' : ''}" 
                        onclick="switchSettingsTab('profile')">
                    Profile
                </button>
                <button class="settings-tab ${state.activeSettingsTab === 'api-keys' ? 'active' : ''}" 
                        onclick="switchSettingsTab('api-keys')">
                    API Keys
                </button>
                <button class="settings-tab ${state.activeSettingsTab === 'appearance' ? 'active' : ''}" 
                        onclick="switchSettingsTab('appearance')">
                    Appearance
                </button>
                <button class="settings-tab ${state.activeSettingsTab === 'llm' ? 'active' : ''}" 
                        onclick="switchSettingsTab('llm')">
                    LLM Settings
                </button>
            </div>
            <div class="settings-content">
                ${getActiveTabContent()}
            </div>
        </div>
    `;
}

export function getActiveTabContent() {
    const state = getState();
    
    switch (state.activeSettingsTab) {
        case 'profile':
            return getProfileTabContent();
        case 'api-keys':
            return getApiKeysTabContent();
        case 'appearance':
            return getAppearanceTabContent();
        case 'llm':
            return getLLMTabContent();
        default:
            return getProfileTabContent();
    }
}

export function getProfileTabContent() {
    const state = getState();
    const profile = state.userProfile || {};
    
    return `
        <div class="settings-section">
            <h3>User Profile</h3>
            <form id="profileForm" class="settings-form">
                <div class="form-group">
                    <label for="name">First Name</label>
                    <input type="text" id="name" name="name" value="${profile.name || ''}" required>
                </div>
                
                <div class="form-group">
                    <label for="lastname">Last Name</label>
                    <input type="text" id="lastname" name="lastname" value="${profile.lastname || ''}">
                </div>
                
                <div class="form-group">
                    <label for="email">Email</label>
                    <input type="email" id="email" name="email" value="${profile.email || ''}" required>
                </div>
                
                <div class="form-group">
                    <label for="organization">Organization</label>
                    <input type="text" id="organization" name="organization" value="${profile.organization || ''}">
                </div>
                
                <div class="form-actions">
                    <button type="button" class="btn-secondary" onclick="resetProfileForm()">
                        Reset
                    </button>
                    <button type="submit" class="btn-primary">
                        Save Profile
                    </button>
                </div>
            </form>
        </div>
    `;
}

export function getApiKeysTabContent() {
    const state = getState();
    const apiKeys = state.apiKeys || [];
    
    let html = `
        <div class="settings-section">
            <h3>API Keys</h3>
            <div class="api-keys-list">
    `;
    
    if (apiKeys.length === 0) {
        html += `
            <div class="empty-state">
                <p>No API keys configured</p>
            </div>
        `;
    } else {
        apiKeys.forEach(key => {
            html += `
                <div class="api-key-item">
                    <div class="api-key-info">
                        <div class="api-key-name">${key.name}</div>
                        <div class="api-key-provider">${key.provider}</div>
                        <div class="api-key-masked">••••••••${key.key_suffix}</div>
                    </div>
                    <div class="api-key-actions">
                        <button class="btn-small" onclick="editApiKey(${key.id})" title="Edit">
                            ✏️
                        </button>
                        <button class="btn-small delete-btn" onclick="deleteApiKey(${key.id})" title="Delete">
                            🗑️
                        </button>
                    </div>
                </div>
            `;
        });
    }
    
    html += `
            </div>
            
            <div class="add-api-key-section">
                <h4>Add New API Key</h4>
                <form id="apiKeyForm" class="settings-form">
                    <div class="form-group">
                        <label for="keyName">Key Name</label>
                        <input type="text" id="keyName" name="keyName" required placeholder="e.g. OpenAI Production">
                    </div>
                    
                    <div class="form-group">
                        <label for="keyProvider">Provider</label>
                        <select id="keyProvider" name="keyProvider" required>
                            <option value="">Select Provider</option>
                            <option value="openai">OpenAI</option>
                            <option value="anthropic">Anthropic</option>
                            <option value="google">Google</option>
                            <option value="azure">Azure OpenAI</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="keyValue">API Key</label>
                        <input type="password" id="keyValue" name="keyValue" required placeholder="Enter your API key">
                    </div>
                    
                    <div class="form-actions">
                        <button type="submit" class="btn-primary">
                            Add API Key
                        </button>
                    </div>
                </form>
            </div>
        </div>
    `;
    
    return html;
}

export function getAppearanceTabContent() {
    const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
    
    return `
        <div class="settings-section">
            <h3>Appearance Settings</h3>
            
            <div class="setting-group">
                <label class="setting-label">Theme</label>
                <div class="theme-selector">
                    <button class="theme-option ${currentTheme === 'dark' ? 'active' : ''}" 
                            onclick="handleThemeChange('dark')" data-theme="dark">
                        <div class="theme-preview dark-preview"></div>
                        <span>Dark</span>
                    </button>
                    <button class="theme-option ${currentTheme === 'light' ? 'active' : ''}" 
                            onclick="handleThemeChange('light')" data-theme="light">
                        <div class="theme-preview light-preview"></div>
                        <span>Light</span>
                    </button>
                </div>
            </div>
            
            <div class="setting-group">
                <label class="setting-label">Interface Scale</label>
                <select class="form-control" onchange="handleScaleChange(this.value)">
                    <option value="small">Small</option>
                    <option value="medium" selected>Medium</option>
                    <option value="large">Large</option>
                </select>
            </div>
        </div>
    `;
}

export function getLLMTabContent() {
    const state = getState();
    const availableLLMs = state.availableLLMs || {};
    
    let html = `
        <div class="settings-section">
            <h3>LLM Configuration</h3>
            
            <div class="llm-current-config">
                <h4>Current LLM</h4>
                <div id="currentLLMInfo">
                    Loading current LLM configuration...
                </div>
                <div class="llm-actions">
                    <button class="btn-secondary" onclick="refreshLLMSettings()">
                        🔄 Refresh
                    </button>
                    <button class="btn-primary" onclick="testCurrentLLM()">
                        🧪 Test Current LLM
                    </button>
                </div>
            </div>
            
            <div class="llm-selector-section">
                <h4>Switch LLM</h4>
                <select id="llmConfigSelector" class="form-control" onchange="switchLLMConfig(this.value)">
                    <option value="">Select LLM Configuration...</option>
    `;
    
    Object.entries(availableLLMs).forEach(([configId, config]) => {
        html += `<option value="${configId}">${config.display_name || configId}</option>`;
    });
    
    html += `
                </select>
            </div>
            
            <div class="llm-models-list">
                <h4>Available Models</h4>
                <div id="llmModelsList">
                    Loading available models...
                </div>
            </div>
            
            <div class="llm-provider-configs">
                <h4>Provider Configurations</h4>
                <div id="providerConfigsList">
                    Loading provider configurations...
                </div>
            </div>
        </div>
    `;
    
    return html;
}

// Settings Management Functions
export function switchSettingsTab(tabName) {
    setState('activeSettingsTab', tabName);
    
    // Update UI
    refreshSettingsPanel();
}

export function refreshSettingsPanel() {
    const panelContent = document.getElementById('panelContent');
    if (panelContent && getState().activePanel === 'settings') {
        panelContent.innerHTML = getSettingsContent();
        bindSettingsEvents();
    }
}

// Profile Management
export function resetProfileForm() {
    const form = document.getElementById('profileForm');
    if (form) {
        form.reset();
        const state = getState();
        const profile = state.userProfile || {};
        
        // Reset to original values
        Object.keys(profile).forEach(key => {
            const input = form.querySelector(`[name="${key}"]`);
            if (input) {
                input.value = profile[key] || '';
            }
        });
    }
}

export async function saveProfile(formData) {
    try {
        const result = await saveUserProfile(formData);
        
        // Server returns profile object on success, {error: "message"} on error
        if (result.error) {
            showSmartSuggestion(`❌ Error: ${result.error}`);
        } else if (result.id || result.name) {
            showSmartSuggestion('✅ Profile updated successfully');
            // Update local state with new profile data
            setState({ userProfile: result });
            // Refresh the settings panel to show updated values
            triggerUIRefresh('settings');
        } else {
            showSmartSuggestion('❌ Unexpected server response');
        }
    } catch (error) {
        const errorMessage = error.message || 'Network or server error';
        showSmartSuggestion(`❌ Error: ${errorMessage}`);
    }
}


// API Key Management
export async function addApiKey(formData) {
    try {
        const result = await saveApiKey(formData);
        
        if (result.success) {
            showSmartSuggestion('✅ API key added successfully');
            refreshSettingsPanel();
        } else {
            showSmartSuggestion(`❌ Error: ${result.error}`);
        }
    } catch (error) {
        showSmartSuggestion('❌ Error adding API key');
    }
}

export async function editApiKey(keyId) {
    // Implementation for editing API keys
    showNotification('API key editing interface', 'info');
}

export async function removeApiKey(keyId) {
    if (!confirm('Are you sure you want to delete this API key?')) {
        return;
    }
    
    try {
        await deleteApiKey(keyId);
        showSmartSuggestion('🗑️ API key deleted');
        refreshSettingsPanel();
    } catch (error) {
        showSmartSuggestion('❌ Error deleting API key');
    }
}

// LLM Management
export async function refreshLLMSettings() {
    try {
        await loadAvailableLLMs();
        await loadCurrentLLM();
        updateLLMSettingsUI();
        showNotification('LLM settings refreshed', 'success');
    } catch (error) {
        showNotification('Failed to refresh LLM settings', 'error');
    }
}

export async function testCurrentLLM() {
    try {
        const currentInfo = await loadCurrentLLM();
        showNotification(`Testing ${currentInfo.display_name}...`, 'info');
        
        const currentConfigId = Object.keys(getState().availableLLMs)
            .find(id => getState().availableLLMs[id].is_current);
            
        const result = await testLLM(currentConfigId);
        
        if (result.success) {
            showNotification(`✅ ${result.config_name}: ${result.response}`, 'success');
        } else {
            showNotification(`❌ Test failed: ${result.error}`, 'error');
        }
    } catch (error) {
        showNotification('Failed to test LLM', 'error');
    }
}

export async function switchLLMConfig(configId) {
    if (!configId) return;
    
    try {
        await switchLLM(configId);
        showNotification('LLM switched successfully', 'success');
        updateLLMSettingsUI();
    } catch (error) {
        showNotification('Failed to switch LLM', 'error');
    }
}

export function updateLLMSettingsUI() {
    updateLLMSelector();
}


// updateLLMSelector is now in selectors.js

// Theme Management
export function handleThemeChange(selectedTheme) {
    document.documentElement.setAttribute('data-theme', selectedTheme);
    localStorage.setItem('orb-theme', selectedTheme);
    
    // Update theme toggle buttons
    document.querySelectorAll('.theme-option').forEach(button => {
        const buttonTheme = button.dataset.theme;
        if (buttonTheme === selectedTheme) {
            button.classList.add('active');
        } else {
            button.classList.remove('active');
        }
    });
}

export function handleScaleChange(scale) {
    document.documentElement.setAttribute('data-scale', scale);
    localStorage.setItem('orb-scale', scale);
}

// Event Binding
export function bindSettingsEvents() {
    // Profile form
    const profileForm = document.getElementById('profileForm');
    if (profileForm) {
        profileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            try {
                const formData = new FormData(profileForm);
                const data = Object.fromEntries(formData.entries());
                
                // Validate required fields
                if (!data.name || !data.name.trim()) {
                    showSmartSuggestion('❌ Name is required');
                    return;
                }
                
                await saveProfile(data);
            } catch (error) {
                showSmartSuggestion('❌ Error processing form data');
            }
        });
    }
    
    // API Key form
    const apiKeyForm = document.getElementById('apiKeyForm');
    if (apiKeyForm) {
        apiKeyForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(apiKeyForm);
            const data = Object.fromEntries(formData.entries());
            await addApiKey(data);
            apiKeyForm.reset();
        });
    }
}