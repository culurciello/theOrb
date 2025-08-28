// State management
let isExpanded = false;
let activePanel = null;
let isRecording = false;
let currentConversationId = null;
let selectedCollectionId = null;
let selectedAgentId = null;
let selectedLLMId = null;
let collections = [];
let conversations = [];
let availableAgents = [];
let availableLLMs = {};
let currentDocuments = [];
let isInDocumentView = false;
let collectionsView = 'list'; // 'list', 'detail', 'create'
let selectedCollectionForView = null;
let userProfile = null;
let apiKeys = [];
let activeSettingsTab = 'profile';
let currentTheme = 'dark';

// Elements
const mainOrb = document.getElementById('mainOrb');
const verticalButtons = document.getElementById('verticalButtons');
const horizontalButtons = document.getElementById('horizontalButtons');
const expandedPanel = document.getElementById('expandedPanel');
const panelHeader = document.getElementById('panelHeader');
const panelContent = document.getElementById('panelContent');
const smartSuggestion = document.getElementById('smartSuggestion');
const commandInput = document.getElementById('commandInput');
const chatMessagesDisplay = document.getElementById('chatMessagesDisplay');
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const chatTitle = document.getElementById('chatTitle');
const closeChatBtn = document.getElementById('closeChatBtn');
const collectionSelector = document.getElementById('collectionSelector');
const collectionStatus = document.getElementById('collectionStatus');
const agentSelector = document.getElementById('agentSelector');
const agentStatus = document.getElementById('agentStatus');
const llmSelector = document.getElementById('llmSelector');
const llmStatus = document.getElementById('llmStatus');
const fileInput = document.getElementById('fileInput');
const chatInputContainer = document.getElementById('chatInputContainer');

// Initialize the app
document.addEventListener('DOMContentLoaded', function() {
    loadCollections();
    loadConversations();
    loadUserProfile();
    loadApiKeys();
    loadAvailableAgents();
    loadAvailableLLMs();
    initializeTheme();
    setupEventListeners();
    showWelcomeMessage();
});

function setupEventListeners() {
    // Main orb click handler
    mainOrb.addEventListener('click', function() {
        isExpanded = !isExpanded;
        
        if (isExpanded) {
            mainOrb.classList.add('expanded');
            verticalButtons.classList.add('show');
            horizontalButtons.classList.add('show');
        } else {
            collapseAll();
        }
    });

    // Vertical button handlers
    document.querySelectorAll('.vertical-button').forEach(button => {
        button.addEventListener('click', function() {
            const panel = this.dataset.panel;
            
            // If clicking the same active panel, close it
            if (activePanel === panel && expandedPanel.classList.contains('show')) {
                expandedPanel.classList.remove('show');
                this.classList.remove('active');
                activePanel = null;
            } else {
                showPanel(panel);
            }
        });
    });

    // Horizontal button handlers
    document.querySelectorAll('.horizontal-button').forEach(button => {
        button.addEventListener('click', function() {
            const action = this.dataset.action;
            executeAction(action);
        });
    });

    // Chat input handlers
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Command input handler
    commandInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleCommandInput(this.value);
            this.value = '';
            this.classList.remove('show');
        }
    });

    // Close chat button
    closeChatBtn.addEventListener('click', function() {
        chatMessagesDisplay.classList.remove('show');
    });

    // Save to collection button
    document.addEventListener('click', function(e) {
        if (e.target.id === 'saveToCollectionBtn') {
            showSaveToCollectionModal();
        }
    });

    // Collection selector change handler
    collectionSelector.addEventListener('change', function() {
        const collectionId = this.value;
        if (collectionId) {
            selectedCollectionId = parseInt(collectionId);
            const collection = collections.find(c => c.id == collectionId);
            collectionStatus.textContent = `Using "${collection?.name}" collection`;
        } else {
            selectedCollectionId = null;
            collectionStatus.textContent = 'Select a collection to search your documents';
        }
    });

    // Agent selector change handler
    agentSelector.addEventListener('change', function() {
        const agentId = this.value;
        if (agentId) {
            selectedAgentId = agentId;
            const agent = availableAgents.find(a => a.name === agentId);
            agentStatus.textContent = `Using ${agent?.display_name || agentId} agent`;
        } else {
            selectedAgentId = null;
            agentStatus.textContent = 'Choose an AI agent for processing';
        }
    });

    // LLM selector change handler
    llmSelector.addEventListener('change', function() {
        const llmId = this.value;
        if (llmId && llmId !== selectedLLMId) {
            switchLLM(llmId);
        }
    });

    // File upload
    fileInput.addEventListener('change', function() {
        if (collectionsView === 'create') {
            updateSelectedFilesDisplay();
        } else {
            handleFileUpload();
        }
    });

    // Add drag/drop functionality to chat input
    setupDragDropImageCaption();

    // Click outside to collapse
    document.addEventListener('click', function(e) {
        // Don't collapse if clicking on buttons within the panel content or interactive elements
        if (!e.target.closest('.orvin-orb, .vertical-buttons, .horizontal-buttons, .expanded-panel, .command-input, .smart-suggestion, .chat-messages-display') && 
            !e.target.closest('button') && !e.target.closest('.btn-primary') && !e.target.closest('.btn-secondary') && !e.target.closest('.btn-small') &&
            !e.target.closest('.collection-item') && !e.target.closest('.collection-main') && !e.target.closest('.collection-actions') &&
            !e.target.closest('input') && !e.target.closest('select') && !e.target.closest('textarea') && !e.target.closest('form')) {
            if (isExpanded) {
                collapseAll();
            }
        }
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            collapseAll();
            chatMessagesDisplay.classList.remove('show');
        }
        if (e.ctrlKey && e.key === 'k') {
            e.preventDefault();
            if (!isExpanded) {
                mainOrb.click();
            }
            setTimeout(() => {
                executeAction('command');
            }, 100);
        }
    });
}

function showPanel(panelType) {
    activePanel = panelType;
    
    // Update active state
    document.querySelectorAll('.vertical-button').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector(`[data-panel="${panelType}"]`).classList.add('active');

    // Show the panel
    expandedPanel.classList.add('show');

    // Update panel content
    const panelData = getPanelData(panelType);
    panelHeader.textContent = panelData.title;
    panelContent.innerHTML = panelData.content;

    // Bind panel-specific events
    bindPanelEvents(panelType);
}

function getPanelData(panelType) {
    const panels = {
        voice: {
            title: '🎤 Voice Capture',
            content: `
                <div class="voice-content">
                    <div class="mic-button" id="micButton">🎤</div>
                    <div class="voice-status" id="voiceStatus">Click to start recording</div>
                    <div class="voice-text" id="voiceText">Voice-to-text will appear here...</div>
                </div>
            `
        },
        collections: {
            title: '💾 Data Collections',
            content: getCollectionsContent()
        },
        chat: {
            title: '💬 Conversations',
            content: getConversationsContent()
        },
        documents: {
            title: '📋 Documents',
            content: getDocumentsContent()
        },
        settings: {
            title: '⚙️ Settings',
            content: getSettingsContent()
        }
    };

    return panels[panelType] || { title: 'Orb', content: '<div class="panel-text">Panel content</div>' };
}

function getCollectionsContent() {
    switch (collectionsView) {
        case 'detail':
            return getCollectionDetailContent();
        case 'create':
            return getCreateCollectionContent();
        default:
            return getCollectionsListContent();
    }
}

function getCollectionsListContent() {
    let content = `
        <div class="collections-content">
            <div class="collections-header">
                <h4 style="margin: 0; font-size: 14px;">My Collections</h4>
                <button class="btn-primary btn-small" onclick="showCreateCollection()">+ New Collection</button>
            </div>
            
            <div class="collections-list" id="collectionsList">
    `;

    if (collections.length === 0) {
        content += `
            <div class="empty-state">
                <div style="text-align: center; padding: 30px; opacity: 0.7;">
                    <div style="font-size: 48px; margin-bottom: 15px;">📚</div>
                    <div style="font-size: 16px; margin-bottom: 10px;">No collections yet</div>
                    <div style="font-size: 12px; opacity: 0.8;">Create your first collection to organize your documents</div>
                </div>
            </div>
        `;
    } else {
        collections.forEach(collection => {
            content += `
                <div class="collection-item ${selectedCollectionId === collection.id ? 'selected' : ''}" data-collection-id="${collection.id}">
                    <div class="collection-main" onclick="event.stopPropagation(); viewCollectionDetails(${collection.id})">
                        <div class="collection-name">${collection.name}</div>
                        <div class="collection-info">${collection.document_count} documents</div>
                        <div class="collection-meta">Created: ${formatDate(collection.created_at)}</div>
                    </div>
                    <div class="collection-actions">
                        <button class="btn-small btn-secondary" onclick="event.stopPropagation(); selectCollectionForChat(${collection.id})" title="Use for chat">💬</button>
                        <button class="btn-small btn-edit" onclick="event.stopPropagation(); editCollection(${collection.id})" title="Edit">✏️</button>
                        <button class="btn-small btn-delete" onclick="event.stopPropagation(); deleteCollection(${collection.id})" title="Delete">🗑️</button>
                    </div>
                </div>
            `;
        });
    }

    content += `
            </div>
        </div>
    `;

    return content;
}

function getCollectionDetailContent() {
    const collection = collections.find(c => c.id === selectedCollectionForView);
    if (!collection) {
        collectionsView = 'list';
        return getCollectionsListContent();
    }

    let content = `
        <div class="collections-content">
            <div class="collection-detail-header">
                <button class="btn-secondary btn-small" onclick="backToCollectionsList()">← Back</button>
                <div class="collection-detail-title">
                    <h4 style="margin: 0; font-size: 16px;">${collection.name}</h4>
                    <div style="font-size: 12px; opacity: 0.7;">${collection.document_count} documents</div>
                </div>
                <button class="btn-primary btn-small" onclick="addFilesToCollection(${collection.id})">+ Add Files</button>
                <button class="import-directory-btn btn-small" onclick="showDirectoryImport()" title="Import Directory">📁 Import Directory</button>
            </div>
            
            <div class="collection-documents-list" id="collectionDocumentsList">
    `;

    if (currentDocuments.length === 0) {
        content += `
            <div class="empty-state">
                <div style="text-align: center; padding: 30px; opacity: 0.7;">
                    <div style="font-size: 32px; margin-bottom: 10px;">📄</div>
                    <div style="font-size: 14px; margin-bottom: 8px;">No documents in this collection</div>
                    <div style="font-size: 12px; opacity: 0.8;">Add some files to get started</div>
                </div>
            </div>
        `;
    } else {
        currentDocuments.forEach(doc => {
            content += `
                <div class="document-item-detailed" data-document-id="${doc.id}">
                    <div class="document-icon">📄</div>
                    <div class="document-info-detailed">
                        <div class="document-name-detailed">${doc.filename}</div>
                        <div class="document-meta">
                            <span class="file-type-badge">${doc.file_type.toUpperCase()}</span>
                            <span>${formatFileSize(doc.content_length)}</span>
                            <span>${doc.chunk_count} chunks</span>
                            <span>Added: ${formatDate(doc.created_at)}</span>
                        </div>
                        <div class="document-preview-detailed">${doc.content_preview}</div>
                    </div>
                    <div class="document-actions">
                        <button class="btn-small btn-secondary" onclick="viewDocument(${doc.id})" title="View">👁️</button>
                        <button class="btn-small btn-delete" onclick="removeDocumentFromCollection(${doc.id})" title="Remove">🗑️</button>
                    </div>
                </div>
            `;
        });
    }

    content += `
            </div>
            
            <div class="collection-file-links-section" style="margin-top: 20px;">
                <div class="section-header" style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px;">
                    <h5 style="margin: 0; font-size: 14px; opacity: 0.8;">📎 File Links</h5>
                    <button class="btn-small btn-secondary" onclick="loadCollectionFileLinks(${collection.id})" title="Refresh links">🔄</button>
                </div>
                <div class="file-links-container" id="fileLinksContainer-${collection.id}">
                    <div style="text-align: center; padding: 15px; opacity: 0.6; font-size: 12px;">
                        Click refresh to load file links
                    </div>
                </div>
            </div>
        </div>
    `;

    return content;
}

function getCreateCollectionContent() {
    return `
        <div class="collections-content">
            <div class="create-collection-header">
                <button class="btn-secondary btn-small" onclick="backToCollectionsList()">← Back</button>
                <h4 style="margin: 0; font-size: 16px;">Create New Collection</h4>
            </div>
            
            <form class="create-collection-form" id="createCollectionForm">
                <div class="form-group">
                    <label class="form-label">Collection Name</label>
                    <input type="text" class="form-input" name="name" placeholder="Enter collection name" required>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Add Files or Folders (Optional)</label>
                    <div class="simple-upload">
                        <input type="file" id="collectionFilesInput" multiple style="display:none;">
                        <button type="button" class="btn-primary" onclick="selectContent()">📁 Choose Files/Folders</button>
                    </div>
                    <div id="selectionInfo" class="selection-info"></div>
                </div>
                
                <div class="form-actions">
                    <button type="submit" class="btn-primary">Create Collection</button>
                    <button type="button" class="btn-secondary" onclick="backToCollectionsList()">Cancel</button>
                </div>
            </form>
        </div>
    `;
}

function selectContent() {
    // Create a simple popup menu to choose between files or folders
    const menu = document.createElement('div');
    menu.className = 'selection-menu';
    menu.innerHTML = `
        <div class="selection-menu-content">
            <div class="selection-menu-header">Choose what to add:</div>
            <button class="selection-option" onclick="selectFiles(); closeSelectionMenu();">📄 Select Individual Files</button>
            <button class="selection-option" onclick="selectFolder(); closeSelectionMenu();">📁 Select Entire Folder</button>
            <button class="selection-cancel" onclick="closeSelectionMenu();">Cancel</button>
        </div>
    `;
    
    // Style the menu
    menu.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;
    
    document.body.appendChild(menu);
    window.currentSelectionMenu = menu;
}

function closeSelectionMenu() {
    if (window.currentSelectionMenu) {
        document.body.removeChild(window.currentSelectionMenu);
        window.currentSelectionMenu = null;
    }
}

function selectFiles() {
    const input = document.getElementById('collectionFilesInput');
    
    // Remove webkitdirectory for file selection
    input.removeAttribute('webkitdirectory');
    input.setAttribute('multiple', '');
    
    input.onchange = function() {
        const files = Array.from(this.files);
        const info = document.getElementById('selectionInfo');
        
        if (files.length > 0) {
            info.innerHTML = `
                <div class="selected-info">
                    ✅ Selected: ${files.length} individual file${files.length > 1 ? 's' : ''}
                    <div class="file-preview">${files.slice(0, 5).map(f => f.name).join(', ')}${files.length > 5 ? '...' : ''}</div>
                </div>
            `;
        }
    };
    
    input.click();
}

function selectFolder() {
    const input = document.getElementById('collectionFilesInput');
    
    // Set webkitdirectory for folder selection
    input.setAttribute('webkitdirectory', '');
    input.setAttribute('multiple', '');
    
    input.onchange = function() {
        const files = Array.from(this.files);
        const info = document.getElementById('selectionInfo');
        
        if (files.length > 0) {
            const folderPath = files[0].webkitRelativePath.split('/')[0];
            info.innerHTML = `
                <div class="selected-info">
                    ✅ Selected folder: <strong>${folderPath}</strong>
                    <div class="file-preview">${files.length} files found</div>
                </div>
            `;
        }
    };
    
    input.click();
}

function getConversationsContent() {
    let content = `
        <div class="chat-content">
            <div class="conversations-header">
                <h4 style="margin: 0; font-size: 14px;">Conversations</h4>
                <button class="new-conversation-btn" onclick="startNewConversation()">+ New</button>
            </div>
            <div class="conversations-list" id="conversationsList">
    `;

    if (conversations.length === 0) {
        content += '<div style="text-align: center; padding: 20px; opacity: 0.7;">No conversations yet. Start chatting!</div>';
    } else {
        conversations.forEach(conv => {
            content += `
                <div class="conversation-item ${currentConversationId === conv.id ? 'active' : ''}" data-conversation-id="${conv.id}">
                    <div>
                        <div style="font-weight: 500; margin-bottom: 2px;">${conv.title}</div>
                        <div style="font-size: 11px; opacity: 0.7;">${conv.message_count} messages</div>
                    </div>
                    <button class="delete-conversation-btn" onclick="deleteConversation('${conv.id}')">×</button>
                </div>
            `;
        });
    }

    content += `
            </div>
            <input type="text" class="chat-input" id="quickChatInput" placeholder="Quick message...">
        </div>
    `;

    return content;
}

function getDocumentsContent() {
    if (!selectedCollectionId && !isInDocumentView) {
        return `
            <div class="documents-content">
                <div style="text-align: center; padding: 40px; opacity: 0.7;">
                    Select a collection first to view its documents.
                </div>
            </div>
        `;
    }

    let content = `
        <div class="documents-content">
            <div class="documents-header">
                <h4 style="margin: 0; font-size: 14px;">Documents</h4>
                <button class="back-to-collections-btn" onclick="backToCollections()">← Back</button>
            </div>
            <div class="documents-list" id="documentsList">
    `;

    if (currentDocuments.length === 0) {
        content += '<div style="text-align: center; padding: 20px; opacity: 0.7;">No documents in this collection</div>';
    } else {
        currentDocuments.forEach(doc => {
            content += `
                <div class="document-item" data-document-id="${doc.id}">
                    <div class="document-name">
                        <span>${doc.filename}</span>
                        <button class="delete-document-btn" onclick="deleteDocument('${doc.id}')">×</button>
                    </div>
                    <div class="document-info">
                        ${doc.file_type.toUpperCase()} • ${formatFileSize(doc.content_length)} • ${doc.chunk_count} chunks
                    </div>
                    <div class="document-info">
                        Added: ${formatDate(doc.created_at)}
                    </div>
                    <div class="document-preview">${doc.content_preview}</div>
                </div>
            `;
        });
    }

    content += `
            </div>
        </div>
    `;

    return content;
}

function bindPanelEvents(panelType) {
    if (panelType === 'voice') {
        const micButton = document.getElementById('micButton');
        const voiceStatus = document.getElementById('voiceStatus');
        const voiceText = document.getElementById('voiceText');

        if (micButton) {
            micButton.addEventListener('click', function() {
                isRecording = !isRecording;
                
                if (isRecording) {
                    this.classList.add('recording');
                    voiceStatus.textContent = 'Recording... Click to stop';
                    voiceText.textContent = 'Listening for your voice...';
                    
                    setTimeout(() => {
                        if (isRecording) {
                            voiceText.textContent = 'Sample voice input: "Show me my work documents"';
                        }
                    }, 3000);
                } else {
                    this.classList.remove('recording');
                    voiceStatus.textContent = 'Click to start recording';
                    voiceText.textContent = 'Voice recording stopped. Processing...';
                }
            });
        }
    }

    if (panelType === 'collections') {
        // Handle create collection form
        const createCollectionForm = document.getElementById('createCollectionForm');
        if (createCollectionForm) {
            createCollectionForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const formData = new FormData(this);
                const data = Object.fromEntries(formData);
                createNewCollection(data);
            });
        }

        // Set up drag and drop functionality for the drop zone
        setupDropZone();

        // Update file input display for create collection
        updateSelectedFilesDisplay();
    }

    if (panelType === 'chat') {
        const conversationItems = document.querySelectorAll('.conversation-item');
        conversationItems.forEach(item => {
            item.addEventListener('click', function() {
                const conversationId = this.dataset.conversationId;
                loadConversation(conversationId);
            });
        });

        const quickChatInput = document.getElementById('quickChatInput');
        if (quickChatInput) {
            quickChatInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    const message = this.value.trim();
                    if (message) {
                        openChatAndSendMessage(message);
                        this.value = '';
                    }
                }
            });
        }
    }

    if (panelType === 'settings') {
        // Settings tab switching
        const settingsTabs = document.querySelectorAll('.settings-tab');
        settingsTabs.forEach(tab => {
            tab.addEventListener('click', function() {
                const tabName = this.dataset.tab;
                switchSettingsTab(tabName);
            });
        });

        // Profile form submission
        const profileForm = document.getElementById('profileForm');
        if (profileForm) {
            profileForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const formData = new FormData(this);
                const data = Object.fromEntries(formData);
                saveUserProfile(data);
            });
        }

        // API key form submission
        const apiKeyForm = document.getElementById('apiKeyForm');
        if (apiKeyForm) {
            apiKeyForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const formData = new FormData(this);
                const data = Object.fromEntries(formData);
                saveApiKey(data);
                this.reset();
            });
        }
    }
}

function executeAction(action) {
    switch(action) {
        case 'command':
            commandInput.classList.add('show');
            commandInput.focus();
            break;
        case 'suggest':
            showSmartSuggestion('💡 Try: "Show me my latest documents" or "Start a new conversation"');
            break;
        case 'upload':
            fileInput.click();
            break;
    }
}

async function loadCollections() {
    try {
        const response = await fetch('/api/collections');
        collections = await response.json();
        updateCollectionSelector();
        if (activePanel === 'collections') {
            showPanel('collections');
        }
    } catch (error) {
        console.error('Error loading collections:', error);
    }
}

async function loadConversations() {
    try {
        const response = await fetch('/api/conversations');
        conversations = await response.json();
        if (activePanel === 'chat') {
            showPanel('chat');
        }
    } catch (error) {
        console.error('Error loading conversations:', error);
    }
}

async function loadAvailableAgents() {
    try {
        const response = await fetch('/api/agents');
        availableAgents = await response.json();
        updateAgentSelector();
    } catch (error) {
        console.error('Error loading agents:', error);
        // Set default agents if API fails
        availableAgents = [
            { name: 'basic', display_name: 'Basic Agent', description: 'Fast single-pass responses without verification', is_default: true },
            { name: 'verification', display_name: 'Verification Agent', description: 'Verifies information accuracy', is_default: false },
            { name: 'deep_research', display_name: 'Deep Research Agent', description: 'Performs comprehensive research', is_default: false }
        ];
        updateAgentSelector();
    }
}

async function loadAvailableLLMs() {
    try {
        const response = await fetch('/api/llm/configs');
        availableLLMs = await response.json();
        updateLLMSelector();
        loadCurrentLLM();
    } catch (error) {
        console.error('Error loading LLMs:', error);
        llmSelector.innerHTML = '<option value="">Error loading LLMs</option>';
        llmStatus.textContent = 'Error loading language models';
    }
}

async function loadCurrentLLM() {
    try {
        const response = await fetch('/api/llm/current');
        const currentLLM = await response.json();
        if (currentLLM.provider) {
            updateLLMStatus(currentLLM);
        }
    } catch (error) {
        console.error('Error loading current LLM:', error);
    }
}

function updateLLMSelector() {
    llmSelector.innerHTML = '';
    
    if (Object.keys(availableLLMs).length === 0) {
        llmSelector.innerHTML = '<option value="">No LLMs configured</option>';
        return;
    }
    
    // Group by provider
    const providers = { anthropic: [], ollama: [], vllm: [] };
    
    Object.entries(availableLLMs).forEach(([id, config]) => {
        if (config.is_active) {
            providers[config.provider].push({ id, ...config });
        }
    });
    
    // Add options grouped by provider
    Object.entries(providers).forEach(([provider, configs]) => {
        if (configs.length > 0) {
            const group = document.createElement('optgroup');
            group.label = provider.toUpperCase();
            
            configs.forEach(config => {
                const option = document.createElement('option');
                option.value = config.id;
                option.textContent = `${config.display_name} (${config.size})`;
                option.selected = config.is_current;
                
                if (config.is_current) {
                    selectedLLMId = config.id;
                }
                
                // Add status indicator
                if (!config.has_api_key && config.provider === 'anthropic') {
                    option.textContent += ' - No API Key';
                    option.disabled = true;
                }
                
                group.appendChild(option);
            });
            
            llmSelector.appendChild(group);
        }
    });
    
    if (llmSelector.children.length === 0) {
        llmSelector.innerHTML = '<option value="">No active LLMs</option>';
    }
}

function updateLLMStatus(llmInfo) {
    if (!llmInfo || !llmInfo.provider) {
        llmStatus.textContent = 'No LLM selected';
        llmStatus.className = 'llm-status error';
        return;
    }
    
    const statusText = `${llmInfo.display_name} - ${llmInfo.is_available ? 'Available' : 'Unavailable'}`;
    llmStatus.textContent = statusText;
    llmStatus.className = `llm-status ${llmInfo.is_available ? 'success' : 'error'}`;
}

async function switchLLM(configId) {
    try {
        const response = await fetch('/api/llm/current', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config_id: configId })
        });
        
        if (response.ok) {
            selectedLLMId = configId;
            loadCurrentLLM(); // Refresh status
            showNotification('LLM switched successfully', 'success');
        } else {
            const error = await response.json();
            showNotification(error.error || 'Failed to switch LLM', 'error');
        }
    } catch (error) {
        console.error('Error switching LLM:', error);
        showNotification('Error switching LLM', 'error');
    }
}

function showNotification(message, type = 'info') {
    // Simple notification using browser alert for now
    // In production, you might want to implement a proper notification system
    console.log(`${type.toUpperCase()}: ${message}`);
    
    // Create a temporary notification element
    const notification = document.createElement('div');
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 8px;
        color: white;
        font-size: 14px;
        z-index: 10000;
        transition: opacity 0.3s ease;
        background: ${type === 'success' ? 'var(--success-color)' : type === 'error' ? 'var(--error-color)' : 'var(--accent-color)'};
    `;
    
    document.body.appendChild(notification);
    
    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

function selectCollection(collectionId) {
    selectedCollectionId = collectionId;
    
    document.querySelectorAll('.collection-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    if (collectionId) {
        document.querySelector(`[data-collection-id="${collectionId}"]`).classList.add('selected');
        loadCollectionDocuments(collectionId);
    }
}

async function loadCollectionDocuments(collectionId) {
    try {
        const response = await fetch(`/api/collections/${collectionId}/documents`);
        currentDocuments = await response.json();
        isInDocumentView = true;
        
        if (activePanel === 'documents') {
            showPanel('documents');
        }
    } catch (error) {
        console.error('Error loading documents:', error);
    }
}

async function loadCollectionFileLinks(collectionId) {
    try {
        const container = document.getElementById(`fileLinksContainer-${collectionId}`);
        if (!container) return;
        
        // Show loading state
        container.innerHTML = `
            <div style="text-align: center; padding: 15px; opacity: 0.6; font-size: 12px;">
                Loading file links...
            </div>
        `;
        
        const response = await fetch(`/api/collections/${collectionId}/file-links`);
        const data = await response.json();
        
        if (data.file_links && data.file_links.length > 0) {
            let linksHTML = `
                <div class="file-links-header" style="font-size: 12px; opacity: 0.7; margin-bottom: 8px;">
                    ${data.total_files} file${data.total_files !== 1 ? 's' : ''} available
                </div>
            `;
            
            data.file_links.forEach(file => {
                const fileIcon = getFileIcon(file.file_type);
                const fileSize = formatFileSize(file.file_size || 0);
                
                linksHTML += `
                    <div class="file-link-item" style="display: flex; align-items: center; padding: 8px; margin-bottom: 4px; background: rgba(255,255,255,0.05); border-radius: 4px; transition: background 0.2s;">
                        <div class="file-icon" style="margin-right: 8px; font-size: 16px;">${fileIcon}</div>
                        <div class="file-info" style="flex: 1; min-width: 0;">
                            <div class="file-name" style="font-size: 12px; font-weight: 500; margin-bottom: 2px; word-break: break-all;">
                                <a href="${file.url}" target="_blank" style="color: var(--primary-color); text-decoration: none;">${file.filename}</a>
                            </div>
                            <div class="file-meta" style="font-size: 10px; opacity: 0.6;">
                                ${file.file_type.toUpperCase()} • ${fileSize}
                                ${file.categories && file.categories.length > 0 ? ' • ' + file.categories.slice(0, 2).join(', ') : ''}
                            </div>
                        </div>
                        <div class="file-actions" style="margin-left: 8px;">
                            <a href="${file.url}" target="_blank" class="btn-tiny" title="Open file" style="padding: 4px 6px; font-size: 10px; text-decoration: none;">🔗</a>
                        </div>
                    </div>
                `;
            });
            
            container.innerHTML = linksHTML;
        } else {
            container.innerHTML = `
                <div style="text-align: center; padding: 15px; opacity: 0.6; font-size: 12px;">
                    No accessible files found
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading file links:', error);
        const container = document.getElementById(`fileLinksContainer-${collectionId}`);
        if (container) {
            container.innerHTML = `
                <div style="text-align: center; padding: 15px; opacity: 0.6; font-size: 12px; color: #ff6b6b;">
                    Error loading file links
                </div>
            `;
        }
    }
}

function getFileIcon(fileType) {
    const icons = {
        'image': '🖼️',
        'video': '🎥',
        'text': '📄',
        'audio': '🔊',
        'pdf': '📕',
        'doc': '📘',
        'docx': '📘',
        'xls': '📊',
        'xlsx': '📊',
        'ppt': '📺',
        'pptx': '📺'
    };
    return icons[fileType.toLowerCase()] || '📄';
}

function backToCollections() {
    isInDocumentView = false;
    showPanel('collections');
}

async function handleFileUpload() {
    const files = fileInput.files;
    if (files.length === 0) return;

    const collectionNameInput = document.getElementById('collectionNameInput');
    let collectionName = collectionNameInput ? collectionNameInput.value.trim() : '';
    
    if (!collectionName) {
        collectionName = prompt('Enter collection name:');
        if (!collectionName) return;
    }

    // Find or create collection
    let collection = collections.find(c => c.name === collectionName);
    if (!collection) {
        try {
            const response = await fetch('/api/collections', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: collectionName })
            });
            collection = await response.json();
            collections.push(collection);
        } catch (error) {
            showSmartSuggestion(`❌ Error creating collection: ${error.message}`);
            return;
        }
    }

    // Upload files
    let successCount = 0;
    for (const file of files) {
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`/api/collections/${collection.id}/upload`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            if (!result.error) {
                successCount++;
            }
        } catch (error) {
            console.error(`Error uploading ${file.name}:`, error);
        }
    }

    // Clear inputs and refresh
    fileInput.value = '';
    if (collectionNameInput) {
        collectionNameInput.value = '';
    }
    
    loadCollections();
    showSmartSuggestion(`✅ Successfully uploaded ${successCount} of ${files.length} files to "${collectionName}"`);
}

function openChatAndSendMessage(message) {
    chatMessagesDisplay.classList.add('show');
    messageInput.value = message;
    setTimeout(() => {
        sendMessage();
    }, 300);
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    // Clear input
    messageInput.value = '';
    
    // Add user message to chat
    addMessage('user', message);
    
    // Add status message for AI processing
    const statusMessageDiv = addStatusMessage('Processing...');
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                conversation_id: currentConversationId,
                collection_id: selectedCollectionId,
                agent_id: selectedAgentId
            })
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`${response.status} ${response.statusText}: ${errorText}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        removeStatusMessage(statusMessageDiv);
        
        if (!currentConversationId) {
            currentConversationId = data.conversation_id;
            const shortTitle = message.length > 50 ? message.substring(0, 50) + '...' : message;
            chatTitle.textContent = shortTitle;
            loadConversations();
        }
        
        console.log('Response data:', data); // Debug log
        addMessage('assistant', data.response, data.verified, data.images);
        
    } catch (error) {
        removeStatusMessage(statusMessageDiv);
        addMessage('assistant', `Error: ${error.message}`, false);
    }
}

function addMessage(role, content, verified = null, images = null) {
    console.log(`Adding message: role=${role}, verified=${verified}`); // Debug log
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    let verificationBadge = '';
    if (role === 'assistant' && verified !== null) {
        const badgeClass = verified ? 'verified' : 'unverified';
        const badgeText = verified ? '✓ Verified' : '⚠ Unverified';
        console.log(`Creating badge: ${badgeClass} - ${badgeText}`); // Debug log
        verificationBadge = `<div class="verification-badge ${badgeClass}">${badgeText}</div>`;
    }
    
    // Build images gallery if images are provided
    let imagesGallery = '';
    if (images && images.length > 0) {
        imagesGallery = '<div class="message-images-gallery">';
        for (const image of images) {
            // Use the provided URL, or fallback to constructing from file_path
            let imageUrl = image.url;
            let urlForModal = image.url;
            
            if (!imageUrl && image.metadata?.file_path) {
                // Fallback: construct URL from file_path
                const imagePath = image.metadata.file_path;
                const encodedPath = imagePath.split('/').map(part => encodeURIComponent(part)).join('/');
                imageUrl = `/api/images/${encodedPath}`;
                urlForModal = encodedPath;
            } else if (imageUrl) {
                // For modal, just use the full URL
                urlForModal = imageUrl;
            }
            
            if (imageUrl) {
                const escapedDescription = image.content.replace(/'/g, '&#39;').replace(/"/g, '&quot;');
                const escapedUrlForModal = urlForModal.replace(/'/g, '&#39;');
                
                imagesGallery += `
                    <div class="message-image-item">
                        <img src="${imageUrl}" 
                             alt="${escapedDescription}" 
                             class="message-image" 
                             onclick="openImageModal('${escapedUrlForModal}', '${escapedDescription}')"
                             onerror="this.onerror=null; this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTUwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjNmNGY2Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxMiIgZmlsbD0iIzZiNzI4MCIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIG5vdCBmb3VuZDwvdGV4dD48L3N2Zz4='; this.title='Image not found: ${imageUrl}';"/>
                        <div class="image-caption">${escapedDescription}</div>
                    </div>
                `;
            }
        }
        imagesGallery += '</div>';
    }
    
    messageDiv.innerHTML = `
        <div class="message-content">${content}</div>
        ${imagesGallery}
        ${verificationBadge}
    `;
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function openImageModal(imageUrl, description) {
    // Create modal for full-size image viewing
    const modal = document.createElement('div');
    modal.className = 'image-modal';
    
    // If imageUrl doesn't start with /, assume it's an encoded path for /api/images/
    const fullImageUrl = imageUrl.startsWith('/') ? imageUrl : `/api/images/${imageUrl}`;
    
    modal.innerHTML = `
        <div class="image-modal-content">
            <span class="image-modal-close" onclick="closeImageModal()">&times;</span>
            <img src="${fullImageUrl}" 
                 alt="${description}" 
                 class="image-modal-img" 
                 onerror="this.onerror=null; this.style.display='none'; this.nextElementSibling.style.display='block';" />
            <div class="image-modal-error" style="display:none; color:white; text-align:center; padding:50px;">
                <div style="font-size:48px; margin-bottom:20px;">❌</div>
                <div>Image could not be loaded</div>
                <div style="font-size:12px; margin-top:10px; opacity:0.7;">${imageUrl.replace(/&#39;/g, "'")}</div>
            </div>
            <div class="image-modal-caption">${description}</div>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.onclick = function(e) {
        if (e.target === modal) {
            closeImageModal();
        }
    };
    
    // Add escape key handler
    const escapeHandler = function(e) {
        if (e.key === 'Escape') {
            closeImageModal();
        }
    };
    document.addEventListener('keydown', escapeHandler);
    modal.escapeHandler = escapeHandler;
}

function closeImageModal() {
    const modal = document.querySelector('.image-modal');
    if (modal) {
        // Remove escape key handler if it exists
        if (modal.escapeHandler) {
            document.removeEventListener('keydown', modal.escapeHandler);
        }
        document.body.removeChild(modal);
    }
}

function addStatusMessage(statusText) {
    const statusDiv = document.createElement('div');
    statusDiv.className = 'message assistant status-message';
    statusDiv.innerHTML = `
        <div class="message-content">
            <div class="loading" style="display: inline-block; margin-right: 10px;"></div>
            <span class="status-text">${statusText}</span>
        </div>
    `;
    chatMessages.appendChild(statusDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return statusDiv;
}

function removeStatusMessage(statusDiv) {
    if (statusDiv && statusDiv.parentNode) {
        statusDiv.parentNode.removeChild(statusDiv);
    }
}

async function loadConversation(conversationId) {
    try {
        const response = await fetch(`/api/conversations/${conversationId}`);
        const conversation = await response.json();
        
        currentConversationId = conversationId;
        
        // Update chat title
        chatTitle.textContent = conversation.title;
        
        // Clear current messages
        chatMessages.innerHTML = '';
        
        // Load messages
        conversation.messages.forEach(msg => {
            // For assistant messages, try to extract images if they were included in the original response
            const images = msg.role === 'assistant' && msg.images ? msg.images : null;
            addMessage(msg.role, msg.content, msg.role === 'assistant' ? msg.verified : null, images);
        });
        
        // Show chat display
        chatMessagesDisplay.classList.add('show');
        
        // Update conversations list
        loadConversations();
        
    } catch (error) {
        console.error('Error loading conversation:', error);
    }
}

function startNewConversation() {
    // Clear current conversation
    currentConversationId = null;
    
    // Clear chat messages
    chatMessages.innerHTML = '';
    
    // Update chat title
    chatTitle.textContent = 'New Conversation';
    
    // Show chat display
    chatMessagesDisplay.classList.add('show');
    
    // Update conversations list
    loadConversations();
    
    // Focus on message input
    messageInput.focus();
}

async function deleteConversation(conversationId) {
    if (!confirm('Are you sure you want to delete this conversation?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/conversations/${conversationId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            // Remove from conversations array
            conversations = conversations.filter(c => c.id !== conversationId);
            
            // If this was the current conversation, start a new one
            if (currentConversationId === conversationId) {
                chatMessagesDisplay.classList.remove('show');
                currentConversationId = null;
            }
            
            loadConversations();
            showSmartSuggestion('🗑️ Conversation deleted');
        } else {
            showSmartSuggestion('❌ Failed to delete conversation');
        }
    } catch (error) {
        showSmartSuggestion('❌ Error deleting conversation');
    }
}

async function deleteDocument(documentId) {
    if (!confirm('Are you sure you want to delete this document?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/documents/${documentId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            // Reload documents list
            if (selectedCollectionId) {
                loadCollectionDocuments(selectedCollectionId);
            }
            // Refresh collections to update document count
            loadCollections();
            showSmartSuggestion('🗑️ Document deleted');
        } else {
            showSmartSuggestion('❌ Failed to delete document');
        }
    } catch (error) {
        showSmartSuggestion('❌ Error deleting document');
    }
}

function handleCommandInput(command) {
    command = command.toLowerCase().trim();
    
    if (command.includes('chat') || command.includes('conversation')) {
        showPanel('chat');
        showSmartSuggestion('💬 Opened conversations panel');
    } else if (command.includes('upload') || command.includes('file')) {
        executeAction('upload');
        showSmartSuggestion('📁 File upload dialog opened');
    } else if (command.includes('collection') || command.includes('data')) {
        showPanel('collections');
        showSmartSuggestion('💾 Opened collections panel');
    } else if (command.includes('document')) {
        showPanel('documents');
        showSmartSuggestion('📋 Opened documents panel');
    } else {
        // Treat as a chat message
        openChatAndSendMessage(command);
    }
}

function showSmartSuggestion(message) {
    smartSuggestion.innerHTML = `<div>${message}</div>`;
    smartSuggestion.classList.add('show');
    setTimeout(() => {
        smartSuggestion.classList.remove('show');
    }, 4000);
}

function hideSuggestion() {
    smartSuggestion.classList.remove('show');
}

function collapseAll() {
    isExpanded = false;
    activePanel = null;
    
    mainOrb.classList.remove('expanded');
    verticalButtons.classList.remove('show');
    horizontalButtons.classList.remove('show');
    expandedPanel.classList.remove('show');
    commandInput.classList.remove('show');
    smartSuggestion.classList.remove('show');
    
    document.querySelectorAll('.vertical-button').forEach(btn => {
        btn.classList.remove('active');
    });
}

function showWelcomeMessage() {
    setTimeout(() => {
        showSmartSuggestion('👋 Welcome! Click the orb to get started');
    }, 1000);
}

// Settings functions
function getSettingsContent() {
    return `
        <div class="settings-content">
            <div class="settings-tabs">
                <button class="settings-tab ${activeSettingsTab === 'profile' ? 'active' : ''}" data-tab="profile">Profile</button>
                <button class="settings-tab ${activeSettingsTab === 'api-keys' ? 'active' : ''}" data-tab="api-keys">API Keys</button>
                <button class="settings-tab ${activeSettingsTab === 'llm' ? 'active' : ''}" data-tab="llm">LLM Models</button>
                <button class="settings-tab ${activeSettingsTab === 'appearance' ? 'active' : ''}" data-tab="appearance">Appearance</button>
            </div>
            
            <div class="settings-tab-content ${activeSettingsTab === 'profile' ? 'active' : ''}" id="profile-tab">
                ${getProfileTabContent()}
            </div>
            
            <div class="settings-tab-content ${activeSettingsTab === 'api-keys' ? 'active' : ''}" id="api-keys-tab">
                ${getApiKeysTabContent()}
            </div>
            
            <div class="settings-tab-content ${activeSettingsTab === 'llm' ? 'active' : ''}" id="llm-tab">
                ${getLLMTabContent()}
            </div>
            
            <div class="settings-tab-content ${activeSettingsTab === 'appearance' ? 'active' : ''}" id="appearance-tab">
                ${getAppearanceTabContent()}
            </div>
        </div>
    `;
}

function getProfileTabContent() {
    const profile = userProfile || {
        name: '',
        lastname: '',
        email: '',
        phone: '',
        address: ''
    };

    return `
        <form class="settings-form" id="profileForm">
            <div class="form-group">
                <label class="form-label">First Name</label>
                <input type="text" class="form-input" name="name" value="${profile.name}" placeholder="Enter your first name">
            </div>
            
            <div class="form-group">
                <label class="form-label">Last Name</label>
                <input type="text" class="form-input" name="lastname" value="${profile.lastname}" placeholder="Enter your last name">
            </div>
            
            <div class="form-group">
                <label class="form-label">Email</label>
                <input type="email" class="form-input" name="email" value="${profile.email}" placeholder="Enter your email">
            </div>
            
            <div class="form-group">
                <label class="form-label">Phone</label>
                <input type="tel" class="form-input" name="phone" value="${profile.phone || ''}" placeholder="Enter your phone number">
            </div>
            
            <div class="form-group">
                <label class="form-label">Address</label>
                <textarea class="form-input form-textarea" name="address" placeholder="Enter your address">${profile.address || ''}</textarea>
            </div>
            
            <div class="form-actions">
                <button type="submit" class="btn-primary">Save Profile</button>
                <button type="button" class="btn-secondary" onclick="resetProfileForm()">Reset</button>
            </div>
        </form>
    `;
}

function getApiKeysTabContent() {
    let content = `
        <div class="api-keys-list" id="apiKeysList">
    `;

    if (apiKeys.length === 0) {
        content += '<div style="text-align: center; padding: 20px; opacity: 0.7;">No API keys configured</div>';
    } else {
        apiKeys.forEach(key => {
            const statusClass = key.is_active ? 'status-active' : 'status-inactive-badge';
            const statusText = key.is_active ? 'Active' : 'Inactive';
            
            content += `
                <div class="api-key-item ${key.is_active ? '' : 'status-inactive'}">
                    <div class="api-key-info">
                        <div class="api-key-service">
                            ${key.service_name}
                            <span class="status-badge ${statusClass}">${statusText}</span>
                        </div>
                        <div class="api-key-value">${key.key_value}</div>
                    </div>
                    <div class="api-key-actions">
                        <button class="btn-small btn-edit" onclick="editApiKey(${key.id})">Edit</button>
                        <button class="btn-small btn-delete" onclick="deleteApiKey(${key.id})">Delete</button>
                    </div>
                </div>
            `;
        });
    }

    content += `
        </div>
        
        <div class="add-api-key-form">
            <h4 style="margin: 0 0 15px 0; font-size: 14px;">Add New API Key</h4>
            <form id="apiKeyForm">
                <div class="form-row">
                    <div class="form-group">
                        <label class="form-label">Service</label>
                        <select class="form-input" name="service_name" required>
                            <option value="">Select service...</option>
                            <option value="openai">OpenAI</option>
                            <option value="anthropic">Anthropic</option>
                            <option value="google">Google</option>
                            <option value="azure">Azure</option>
                            <option value="other">Other</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">API Key</label>
                        <input type="password" class="form-input" name="key_value" placeholder="Enter API key" required>
                    </div>
                </div>
                <div class="form-actions">
                    <button type="submit" class="btn-primary">Add API Key</button>
                </div>
            </form>
        </div>
    `;

    return content;
}

function getAppearanceTabContent() {
    return `
        <div class="appearance-settings">
            <div class="setting-group">
                <label class="setting-label">Theme</label>
                <div class="theme-selector-group">
                    <select class="form-input" id="themeSelector" onchange="handleThemeChange(this.value)">
                        <option value="dark" ${currentTheme === 'dark' ? 'selected' : ''}>Dark Mode</option>
                        <option value="light" ${currentTheme === 'light' ? 'selected' : ''}>Light Mode</option>
                    </select>
                    <button class="theme-toggle-btn theme-preview-btn" onclick="toggleTheme()" title="Preview Theme Toggle">${currentTheme === 'dark' ? '☀️' : '🌙'}</button>
                </div>
                <div class="setting-description">
                    Choose between dark and light mode for the interface. Dark mode is easier on the eyes in low-light conditions.
                </div>
            </div>
            
            <div class="setting-group">
                <label class="setting-label">Interface Scale</label>
                <select class="form-input" disabled>
                    <option value="normal">Normal (100%)</option>
                    <option value="large">Large (125%)</option>
                </select>
                <div class="setting-description">
                    Adjust the size of interface elements. <span class="coming-soon">(Coming Soon)</span>
                </div>
            </div>
            
            <div class="setting-group">
                <label class="setting-label">Animation Effects</label>
                <select class="form-input" disabled>
                    <option value="enabled">Enabled</option>
                    <option value="reduced">Reduced Motion</option>
                    <option value="disabled">Disabled</option>
                </select>
                <div class="setting-description">
                    Control interface animations and transitions. <span class="coming-soon">(Coming Soon)</span>
                </div>
            </div>
        </div>
    `;
}

function getLLMTabContent() {
    return `
        <div class="llm-settings">
            <div class="setting-group">
                <label class="setting-label">Current Language Model</label>
                <div class="current-llm-info" id="currentLLMInfo">
                    <div class="loading">Loading...</div>
                </div>
                <div class="setting-description">
                    This is the currently active language model used for AI responses.
                </div>
            </div>
            
            <div class="setting-group">
                <label class="setting-label">Default Model Selection</label>
                <select class="form-input" id="defaultLLMSelector">
                    <option value="">Loading models...</option>
                </select>
                <div class="setting-description">
                    Choose your preferred default language model. This will be used for all new conversations.
                </div>
            </div>
            
            <div class="setting-group">
                <label class="setting-label">Available Models</label>
                <div class="llm-models-list" id="llmModelsList">
                    <div class="loading">Loading available models...</div>
                </div>
                <div class="setting-description">
                    All available language models and their status. Green indicates the model is available and ready to use.
                </div>
            </div>
            
            <div class="setting-group">
                <label class="setting-label">Provider Configuration</label>
                <div class="provider-configs" id="providerConfigs">
                    <div class="loading">Loading provider configurations...</div>
                </div>
                <div class="setting-description">
                    Configure API keys and settings for different LLM providers.
                </div>
            </div>
            
            <div class="setting-actions">
                <button class="btn-primary" onclick="refreshLLMSettings()">🔄 Refresh Models</button>
                <button class="btn-secondary" onclick="testCurrentLLM()">🧪 Test Current Model</button>
            </div>
        </div>
    `;
}

// User Profile API functions
async function loadUserProfile() {
    try {
        const response = await fetch('/api/user/profile');
        userProfile = await response.json();
        if (activePanel === 'settings') {
            showPanel('settings');
        }
    } catch (error) {
        console.error('Error loading user profile:', error);
    }
}

async function loadApiKeys() {
    try {
        const response = await fetch('/api/user/api-keys');
        apiKeys = await response.json();
        if (activePanel === 'settings') {
            showPanel('settings');
        }
    } catch (error) {
        console.error('Error loading API keys:', error);
    }
}

async function saveUserProfile(formData) {
    try {
        const response = await fetch('/api/user/profile', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            userProfile = result;
            showSmartSuggestion('✅ Profile updated successfully');
            showPanel('settings'); // Refresh the panel
        } else {
            showSmartSuggestion(`❌ Error: ${result.error}`);
        }
    } catch (error) {
        showSmartSuggestion('❌ Error updating profile');
    }
}

async function saveApiKey(formData) {
    try {
        const response = await fetch('/api/user/api-keys', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            await loadApiKeys();
            showSmartSuggestion('✅ API key added successfully');
            showPanel('settings'); // Refresh the panel
        } else {
            showSmartSuggestion(`❌ Error: ${result.error}`);
        }
    } catch (error) {
        showSmartSuggestion('❌ Error adding API key');
    }
}

async function deleteApiKey(keyId) {
    if (!confirm('Are you sure you want to delete this API key?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/user/api-keys/${keyId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            await loadApiKeys();
            showSmartSuggestion('🗑️ API key deleted');
            showPanel('settings'); // Refresh the panel
        } else {
            showSmartSuggestion('❌ Error deleting API key');
        }
    } catch (error) {
        showSmartSuggestion('❌ Error deleting API key');
    }
}

function editApiKey(keyId) {
    // For now, just show a simple prompt - could be enhanced with a modal
    const key = apiKeys.find(k => k.id === keyId);
    if (!key) return;
    
    const newValue = prompt(`Edit API key for ${key.service_name}:`, '');
    if (newValue && newValue.trim()) {
        updateApiKey(keyId, { key_value: newValue.trim() });
    }
}

async function updateApiKey(keyId, data) {
    try {
        const response = await fetch(`/api/user/api-keys/${keyId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            await loadApiKeys();
            showSmartSuggestion('✅ API key updated');
            showPanel('settings'); // Refresh the panel
        } else {
            showSmartSuggestion('❌ Error updating API key');
        }
    } catch (error) {
        showSmartSuggestion('❌ Error updating API key');
    }
}

function resetProfileForm() {
    if (confirm('Reset form to original values?')) {
        showPanel('settings'); // This will reload the form with original data
    }
}

function switchSettingsTab(tabName) {
    activeSettingsTab = tabName;
    showPanel('settings'); // Refresh the entire settings panel with the new active tab
    
    // Load specific data for the LLM tab
    if (tabName === 'llm') {
        setTimeout(() => {
            updateLLMSettingsUI();
        }, 100); // Small delay to ensure DOM is ready
    }
}

// Collection Management Functions
function showCreateCollection() {
    collectionsView = 'create';
    showPanel('collections');
}

function backToCollectionsList() {
    collectionsView = 'list';
    selectedCollectionForView = null;
    showPanel('collections');
}

function viewCollectionDetails(collectionId) {
    selectedCollectionForView = collectionId;
    collectionsView = 'detail';
    loadCollectionDocuments(collectionId);
    showPanel('collections');
    
    // Auto-load file links after a brief delay to let the panel render
    setTimeout(() => {
        loadCollectionFileLinks(collectionId);
    }, 100);
}

function selectCollectionForChat(collectionId) {
    selectedCollectionId = collectionId;
    
    // Update collection items visual state
    document.querySelectorAll('.collection-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    const collectionItem = document.querySelector(`[data-collection-id="${collectionId}"]`);
    if (collectionItem) {
        collectionItem.classList.add('selected');
    }
    
    // Update the collection selector in chat
    if (collectionSelector) {
        collectionSelector.value = collectionId;
        const collection = collections.find(c => c.id == collectionId);
        collectionStatus.textContent = `Using "${collection?.name}" collection`;
    }
    
    showSmartSuggestion(`💾 Collection "${collections.find(c => c.id == collectionId)?.name}" selected for chat`);
}

async function createNewCollection(data) {
    try {
        // Create collection first
        const response = await fetch('/api/collections', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name: data.name })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            // Check if files were selected
            const input = document.getElementById('collectionFilesInput');
            let filesToUpload = [];
            
            if (input && input.files.length > 0) {
                filesToUpload = Array.from(input.files);
            }
            
            if (filesToUpload.length > 0) {
                // Upload files to the new collection
                await uploadFilesToCollection(result.id, filesToUpload);
                showSmartSuggestion(`✅ Collection "${data.name}" created with ${filesToUpload.length} files`);
            } else {
                showSmartSuggestion(`✅ Collection "${data.name}" created successfully`);
            }
            
            // Clear input and go back to collections list
            if (input) input.value = '';
            
            await loadCollections();
            collectionsView = 'list';
            showPanel('collections');
        } else {
            showSmartSuggestion(`❌ Error: ${result.error}`);
        }
    } catch (error) {
        showSmartSuggestion('❌ Error creating collection');
    }
}

async function uploadFilesToCollection(collectionId, files) {
    console.log(`Uploading ${files.length} files to collection ${collectionId}`);
    let successCount = 0;
    
    for (const file of files) {
        console.log(`Processing file: ${file.name}, size: ${file.size}, type: ${file.type}`);
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`/api/collections/${collectionId}/upload`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            console.log(`Upload response for ${file.name}:`, result);
            
            if (response.ok && !result.error) {
                successCount++;
            } else {
                console.error(`Upload failed for ${file.name}:`, result.error || 'Unknown error');
            }
        } catch (error) {
            console.error(`Error uploading ${file.name}:`, error);
        }
    }
    
    console.log(`Upload complete: ${successCount} of ${files.length} files successful`);
    
    if (successCount > 0) {
        showSmartSuggestion(`✅ Uploaded ${successCount} of ${files.length} files`);
    } else if (files.length > 0) {
        showSmartSuggestion(`❌ Failed to upload files. Check console for details.`);
    }
}

function addFilesToCollection(collectionId) {
    // Store the collection ID for when files are selected
    fileInput.dataset.collectionId = collectionId;
    fileInput.click();
}

async function handleFileUpload() {
    const files = fileInput.files;
    if (files.length === 0) return;

    // Check if this is for adding to an existing collection
    const collectionId = fileInput.dataset.collectionId;
    if (collectionId) {
        await uploadFilesToCollection(parseInt(collectionId), files);
        
        // Refresh the collection details view
        await loadCollectionDocuments(parseInt(collectionId));
        await loadCollections();
        showPanel('collections');
        
        // Clear the dataset
        delete fileInput.dataset.collectionId;
        fileInput.value = '';
        return;
    }

    // Legacy behavior for creating new collections
    const collectionNameInput = document.getElementById('collectionNameInput');
    let collectionName = collectionNameInput ? collectionNameInput.value.trim() : '';
    
    if (!collectionName) {
        collectionName = prompt('Enter collection name:');
        if (!collectionName) return;
    }

    // Find or create collection
    let collection = collections.find(c => c.name === collectionName);
    if (!collection) {
        try {
            const response = await fetch('/api/collections', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ name: collectionName })
            });
            collection = await response.json();
            collections.push(collection);
        } catch (error) {
            showSmartSuggestion(`❌ Error creating collection: ${error.message}`);
            return;
        }
    }

    await uploadFilesToCollection(collection.id, files);

    // Clear inputs and refresh
    fileInput.value = '';
    if (collectionNameInput) {
        collectionNameInput.value = '';
    }
    
    loadCollections();
}

function updateSelectedFilesDisplay() {
    const selectedFilesDiv = document.getElementById('selectedFiles');
    if (!selectedFilesDiv) return;

    const files = fileInput.files;
    if (files.length === 0) {
        selectedFilesDiv.innerHTML = '';
        return;
    }

    let content = '';
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        content += `
            <div class="selected-file-item">
                <span>${file.name} (${formatFileSize(file.size)})</span>
                <button type="button" class="file-remove-btn" onclick="removeFile(${i})">×</button>
            </div>
        `;
    }
    selectedFilesDiv.innerHTML = content;
}

function removeFile(index) {
    const dt = new DataTransfer();
    const files = fileInput.files;
    
    for (let i = 0; i < files.length; i++) {
        if (i !== index) {
            dt.items.add(files[i]);
        }
    }
    
    fileInput.files = dt.files;
    updateSelectedFilesDisplay();
}

async function editCollection(collectionId) {
    const collection = collections.find(c => c.id === collectionId);
    if (!collection) return;
    
    const newName = prompt(`Edit collection name:`, collection.name);
    if (newName && newName.trim() && newName.trim() !== collection.name) {
        // Note: We'd need to add an API endpoint for updating collection names
        showSmartSuggestion('💡 Collection editing will be implemented in a future update');
    }
}

async function deleteCollection(collectionId) {
    const collection = collections.find(c => c.id === collectionId);
    if (!collection) return;
    
    if (!confirm(`Are you sure you want to delete "${collection.name}" and all its documents?`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/collections/${collectionId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            await loadCollections();
            if (selectedCollectionId === collectionId) {
                selectedCollectionId = null;
            }
            showSmartSuggestion('🗑️ Collection deleted');
            showPanel('collections');
        } else {
            showSmartSuggestion('❌ Error deleting collection');
        }
    } catch (error) {
        showSmartSuggestion('❌ Error deleting collection');
    }
}

async function removeDocumentFromCollection(documentId) {
    if (!confirm('Are you sure you want to remove this document?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/documents/${documentId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            // Reload documents list
            if (selectedCollectionForView) {
                await loadCollectionDocuments(selectedCollectionForView);
            }
            // Refresh collections to update document count
            await loadCollections();
            showSmartSuggestion('🗑️ Document removed');
            showPanel('collections');
        } else {
            showSmartSuggestion('❌ Error removing document');
        }
    } catch (error) {
        showSmartSuggestion('❌ Error removing document');
    }
}

function viewDocument(documentId) {
    const doc = currentDocuments.find(d => d.id === documentId);
    if (!doc) return;
    
    // For now, show an alert with document content
    // This could be enhanced with a modal in the future
    alert(`Document: ${doc.filename}\n\nContent:\n${doc.content_preview}...\n\nFile Type: ${doc.file_type.toUpperCase()}\nSize: ${formatFileSize(doc.content_length)}\nChunks: ${doc.chunk_count}`);
}

// Utility functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
}

function updateCollectionSelector() {
    if (!collectionSelector) return;
    
    // Clear existing options except the first one
    collectionSelector.innerHTML = '<option value="">No collection selected</option>';
    
    // Add collections as options
    collections.forEach(collection => {
        const option = document.createElement('option');
        option.value = collection.id;
        option.textContent = `${collection.name} (${collection.document_count} docs)`;
        collectionSelector.appendChild(option);
    });
    
    // Restore selected collection if any
    if (selectedCollectionId) {
        collectionSelector.value = selectedCollectionId;
        const collection = collections.find(c => c.id == selectedCollectionId);
        if (collection) {
            collectionStatus.textContent = `Using "${collection.name}" collection`;
        }
    }
}

function updateAgentSelector() {
    if (!agentSelector) return;
    
    // Clear existing options
    agentSelector.innerHTML = '<option value="">Auto-detect agent</option>';
    
    // Add agents as options
    availableAgents.forEach(agent => {
        const option = document.createElement('option');
        option.value = agent.name;
        option.textContent = `${agent.display_name}${agent.is_default ? ' (Default)' : ''}`;
        option.title = agent.description;
        agentSelector.appendChild(option);
    });
    
    // Set default agent if available and none selected
    if (!selectedAgentId) {
        const defaultAgent = availableAgents.find(a => a.is_default);
        if (defaultAgent) {
            selectedAgentId = defaultAgent.name;
            agentSelector.value = defaultAgent.name;
            agentStatus.textContent = `Using ${defaultAgent.display_name} agent`;
        } else {
            agentStatus.textContent = 'Agent will be auto-detected from your message';
        }
    } else {
        // Restore selected agent
        agentSelector.value = selectedAgentId;
        const agent = availableAgents.find(a => a.name === selectedAgentId);
        if (agent) {
            agentStatus.textContent = `Using ${agent.display_name} agent`;
        }
    }
}

// Directory Drop Zone Setup
function setupDropZone() {
    const dropZone = document.getElementById('dropZone');
    if (!dropZone) return;

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop zone when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files/directories
    dropZone.addEventListener('drop', handleDrop, false);

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight() {
        dropZone.classList.add('dragover');
    }

    function unhighlight() {
        dropZone.classList.remove('dragover');
    }

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const items = dt.items;

        if (items) {
            // Check if we're dropping directories by looking for directory entries
            for (let i = 0; i < items.length; i++) {
                const item = items[i];
                if (item.kind === 'file') {
                    const entry = item.webkitGetAsEntry();
                    if (entry && entry.isDirectory) {
                        // For web security reasons, we can't get the full path
                        // We'll need to show a message asking user to manually enter path
                        showDirectoryDropMessage(entry.name);
                        return;
                    }
                }
            }
        }

        // If no directory, handle as regular files
        const files = dt.files;
        if (files.length > 0) {
            // Create a new DataTransfer object to properly set files
            const dataTransfer = new DataTransfer();
            for (let i = 0; i < files.length; i++) {
                dataTransfer.items.add(files[i]);
            }
            fileInput.files = dataTransfer.files;
            updateSelectedFilesDisplay();
        }
    }

    function showDirectoryDropMessage(dirName) {
        const selectedDirectoryDiv = document.getElementById('selectedDirectory');
        selectedDirectoryDiv.innerHTML = `
            <div class="directory-dropped">
                <div class="directory-info">
                    <span class="directory-icon">📁</span>
                    <span class="directory-name">Directory "${dirName}" detected</span>
                </div>
                <div class="directory-path-input">
                    <input type="text" placeholder="Enter full path to ${dirName}" class="form-input" id="directoryPathInput">
                    <button type="button" class="btn-secondary btn-small" onclick="confirmDirectoryPath()">✓</button>
                    <button type="button" class="btn-secondary btn-small" onclick="clearDirectorySelection()">✗</button>
                </div>
                <div class="directory-help">
                    <small>For security reasons, please enter the full path to the directory you dropped</small>
                </div>
            </div>
        `;
    }
}

function confirmDirectoryPath() {
    const pathInput = document.getElementById('directoryPathInput');
    const selectedDirectoryDiv = document.getElementById('selectedDirectory');
    
    if (pathInput && pathInput.value.trim()) {
        const path = pathInput.value.trim();
        selectedDirectoryDiv.dataset.path = path;
        selectedDirectoryDiv.innerHTML = `
            <div class="directory-selected">
                <span class="directory-icon">📁</span>
                <span class="directory-path">${path}</span>
                <button type="button" class="btn-secondary btn-small" onclick="clearDirectorySelection()">Remove</button>
            </div>
        `;
    }
}

function clearDirectorySelection() {
    const selectedDirectoryDiv = document.getElementById('selectedDirectory');
    selectedDirectoryDiv.innerHTML = '';
    selectedDirectoryDiv.dataset.path = '';
}

function selectFilesOrDirectory() {
    // Create a simple dialog to let user choose between files or directory
    if (confirm('Click OK to select individual files, or Cancel to select a directory')) {
        // User chose files
        const fileInput = document.getElementById('fileInput');
        fileInput.click();
    } else {
        // User chose directory
        const directoryInput = document.getElementById('directoryInput');
        directoryInput.click();
        
        // Add event listener for when directory is selected
        directoryInput.onchange = function() {
            if (this.files.length > 0) {
                showSelectedDirectory(this.files);
            }
        };
    }
}

// Keep the old function for backward compatibility if needed elsewhere
function selectDirectory() {
    const directoryInput = document.getElementById('directoryInput');
    directoryInput.click();
    
    // Add event listener for when directory is selected
    directoryInput.onchange = function() {
        if (this.files.length > 0) {
            showSelectedDirectory(this.files);
        }
    };
}

function showSelectedDirectory(files) {
    const selectedDirectoryDiv = document.getElementById('selectedDirectory');
    const directoryName = files[0].webkitRelativePath.split('/')[0];
    
    selectedDirectoryDiv.innerHTML = `
        <div class="directory-selected">
            <span class="directory-icon">📁</span>
            <span class="directory-name">${directoryName} (${files.length} files)</span>
            <button type="button" class="btn-secondary btn-small" onclick="clearDirectoryInput()">Remove</button>
        </div>
    `;
}

function clearDirectoryInput() {
    const directoryInput = document.getElementById('directoryInput');
    const selectedDirectoryDiv = document.getElementById('selectedDirectory');
    
    directoryInput.value = '';
    selectedDirectoryDiv.innerHTML = '';
}

async function handleDirectoryFilesImport(collectionId, files, collectionName) {
    try {
        showSmartSuggestion('🔄 Processing directory files...');
        console.log(`Processing ${files.length} directory files for collection ${collectionId}`);
        
        // Prepare form data with all files
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            formData.append('files', file);
            
            // Add relative path information if available
            if (file.webkitRelativePath) {
                formData.append(`relativePath_${i}`, file.webkitRelativePath);
            }
            
            console.log(`Added file: ${file.name}, path: ${file.webkitRelativePath || file.name}, size: ${file.size}, type: ${file.type}`);
        }
        
        // Upload all files to the new multiple files endpoint
        const response = await fetch(`/api/collections/${collectionId}/upload-files`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        console.log('Directory upload response:', result);
        
        if (response.ok && result.success) {
            await loadCollections();
            collectionsView = 'list';
            showPanel('collections');
            
            const stats = result.statistics || {};
            const fileTypesStr = Object.keys(stats.file_types || {}).join(', ');
            const categoriesStr = Object.keys(stats.categories || {}).join(', ');
            
            showSmartSuggestion(`✅ Collection "${collectionName}" created! Processed ${result.processed_documents} files. Types: ${fileTypesStr}. Categories: ${categoriesStr}`);
        } else {
            throw new Error(result.error || 'Failed to process directory files');
        }
        
    } catch (error) {
        console.error('Directory files import error:', error);
        showSmartSuggestion(`❌ Directory import failed: ${error.message}`);
    }
}

async function performDirectoryImportForNewCollection(collectionId, directoryPath, collectionName) {
    try {
        // Show progress indication
        showSmartSuggestion('🔄 Starting directory import...');
        
        const response = await fetch(`/api/collections/${collectionId}/upload-directory`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                directory_path: directoryPath
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to import directory');
        }
        
        // Show success and reload
        await loadCollections();
        collectionsView = 'list';
        showPanel('collections');
        
        const successMessage = `✅ Collection "${collectionName}" created! Imported ${data.processed_documents || 0} documents from directory.`;
        showSmartSuggestion(successMessage);
        
    } catch (error) {
        console.error('Directory import error:', error);
        showSmartSuggestion(`❌ Directory import failed: ${error.message}`);
    }
}

// Directory Import Functions
function showDirectoryImport() {
    const modal = document.getElementById('directoryModal');
    modal.classList.add('show');
}

function closeDirectoryModal() {
    const modal = document.getElementById('directoryModal');
    modal.classList.remove('show');
    // Clear the input
    document.getElementById('directoryPath').value = '';
}

function startDirectoryImport() {
    const directoryPath = document.getElementById('directoryPath').value.trim();
    
    if (!directoryPath) {
        alert('Please enter a directory path');
        return;
    }
    
    if (!selectedCollectionForView) {
        alert('Please select a collection first');
        return;
    }
    
    // Close the directory modal
    closeDirectoryModal();
    
    // Show progress modal
    showImportProgress();
    
    // Start the import process
    performDirectoryImport(directoryPath, selectedCollectionForView.id);
}

function showImportProgress() {
    const modal = document.getElementById('importProgressModal');
    modal.classList.add('show');
    
    // Reset progress
    updateImportProgress(0, 'Starting import...', '');
}

function closeImportProgress() {
    const modal = document.getElementById('importProgressModal');
    modal.classList.remove('show');
}

function updateImportProgress(percentage, status, details) {
    const progressFill = document.getElementById('progressFill');
    const importStatus = document.getElementById('importStatus');
    const importDetails = document.getElementById('importDetails');
    
    if (progressFill) progressFill.style.width = percentage + '%';
    if (importStatus) importStatus.textContent = status;
    if (importDetails) importDetails.textContent = details;
}

async function performDirectoryImport(directoryPath, collectionId) {
    try {
        updateImportProgress(10, 'Analyzing directory...', 'Scanning for supported files');
        
        const response = await fetch(`/api/collections/${collectionId}/upload-directory`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                directory_path: directoryPath
            })
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to import directory');
        }
        
        // Simulate progress updates
        updateImportProgress(50, 'Processing files...', 'Extracting text and analyzing content');
        
        // Wait a bit to show progress
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        updateImportProgress(80, 'Creating embeddings...', 'Generating vector representations');
        
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        updateImportProgress(100, 'Import completed!', 
            `Successfully processed ${data.processed_documents} documents`);
        
        // Show success details
        if (data.statistics) {
            const stats = data.statistics;
            const details = [
                `Total files: ${stats.total_documents}`,
                `Total chunks: ${stats.total_chunks}`,
                `File types: ${Object.keys(stats.file_types).join(', ')}`,
                `Categories: ${Object.keys(stats.categories).join(', ')}`
            ].join(' | ');
            
            updateImportProgress(100, 'Import completed!', details);
        }
        
        // Close progress modal after a delay
        setTimeout(() => {
            closeImportProgress();
            // Reload collections and documents
            loadCollections();
            if (collectionsView === 'detail' && selectedCollectionForView) {
                loadCollectionDocuments(selectedCollectionForView.id);
            }
            showSuccessMessage('Directory imported successfully!');
        }, 2000);
        
    } catch (error) {
        console.error('Directory import error:', error);
        updateImportProgress(0, 'Import failed', error.message);
        
        // Show error and close modal after delay
        setTimeout(() => {
            closeImportProgress();
            showErrorMessage('Import failed: ' + error.message);
        }, 3000);
    }
}

function showSuccessMessage(message) {
    // You can implement a toast notification here
    // For now, just use alert
    alert(message);
}

function showErrorMessage(message) {
    // You can implement a toast notification here
    // For now, just use alert
    alert('Error: ' + message);
}

// Theme Management Functions
function initializeTheme() {
    // Load saved theme from localStorage or use default
    const savedTheme = localStorage.getItem('orb-theme') || 'dark';
    setTheme(savedTheme);
    
    // Ensure icon is set correctly on initial load
    updateOrbIcon(savedTheme);
}

function setTheme(theme) {
    currentTheme = theme;
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('orb-theme', theme);
    
    // Update any theme toggle buttons
    updateThemeToggleButtons();
    
    // Update the orb icon
    updateOrbIcon(theme);
}

function updateOrbIcon(theme) {
    const orbIcon = document.getElementById('orbIcon');
    if (orbIcon) {
        if (theme === 'dark') {
            orbIcon.src = '/static/icon-dark.png';
        } else {
            orbIcon.src = '/static/icon-light.png';
        }
    }
}

function toggleTheme() {
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
}

function updateThemeToggleButtons() {
    const themeButtons = document.querySelectorAll('.theme-toggle-btn');
    themeButtons.forEach(btn => {
        if (currentTheme === 'dark') {
            btn.innerHTML = '☀️';
            btn.title = 'Switch to Light Mode';
        } else {
            btn.innerHTML = '🌙';
            btn.title = 'Switch to Dark Mode';
        }
    });
    
    // Update theme selector in settings if it exists
    const themeSelector = document.getElementById('themeSelector');
    if (themeSelector) {
        themeSelector.value = currentTheme;
    }
}

function handleThemeChange(selectedTheme) {
    setTheme(selectedTheme);
}

// Image upload functions for chat
function setupDragDropImageCaption() {
    const container = chatInputContainer;
    const input = messageInput;
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        container.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    // Highlight drop zone on drag enter/over
    ['dragenter', 'dragover'].forEach(eventName => {
        container.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        container.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight(e) {
        container.classList.add('drag-over');
    }
    
    function unhighlight(e) {
        container.classList.remove('drag-over');
    }
    
    // Handle dropped files
    container.addEventListener('drop', handleDrop, false);
    
    async function handleDrop(e) {
        const files = e.dataTransfer.files;
        
        if (files.length === 0) return;
        
        const file = files[0];
        
        // Validate image file
        if (!file.type.startsWith('image/')) {
            showSmartSuggestion('❌ Please drop an image file');
            return;
        }
        
        // Check file size (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
            showSmartSuggestion('❌ Image file is too large. Please select a file smaller than 10MB');
            return;
        }
        
        showSmartSuggestion('🎯 Converting image to caption...');
        
        try {
            const caption = await convertImageToCaption(file);
            
            // Add caption to input
            const currentText = input.value;
            const newText = currentText ? `${currentText}\n\n[Image: ${caption}]` : `[Image: ${caption}]`;
            input.value = newText;
            
            showSmartSuggestion(`✅ Image converted to caption: "${caption}"`);
            input.focus();
            
        } catch (error) {
            showSmartSuggestion(`❌ Error converting image: ${error.message}`);
        }
    }
}

async function convertImageToCaption(file) {
    const formData = new FormData();
    formData.append('image', file);
    
    const response = await fetch('/api/image-caption', {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`${response.status}: ${errorText}`);
    }
    
    const data = await response.json();
    
    if (data.error) {
        throw new Error(data.error);
    }
    
    return data.caption;
}

// LLM Settings Functions
async function refreshLLMSettings() {
    try {
        await loadAvailableLLMs();
        await loadCurrentLLM();
        if (activeSettingsTab === 'llm') {
            updateLLMSettingsUI();
        }
        showNotification('LLM settings refreshed', 'success');
    } catch (error) {
        console.error('Error refreshing LLM settings:', error);
        showNotification('Failed to refresh LLM settings', 'error');
    }
}

async function testCurrentLLM() {
    try {
        const currentInfo = await fetch('/api/llm/current').then(r => r.json());
        showNotification(`Testing ${currentInfo.display_name}...`, 'info');
        
        // Find current config ID
        let currentConfigId = selectedLLMId;
        if (!currentConfigId) {
            currentConfigId = Object.keys(availableLLMs).find(id => availableLLMs[id].is_current) || 'anthropic_large';
        }
        
        const testResponse = await fetch('/api/llm/test/' + currentConfigId, {
            method: 'POST'
        });
        
        const result = await testResponse.json();
        
        if (result.success) {
            showNotification(`✅ ${result.config_name}: ${result.response}`, 'success');
        } else {
            showNotification(`❌ Test failed: ${result.error}`, 'error');
        }
    } catch (error) {
        console.error('Error testing LLM:', error);
        showNotification('Failed to test LLM', 'error');
    }
}

function updateLLMSettingsUI() {
    updateCurrentLLMInfo();
    updateDefaultLLMSelector();
    updateLLMModelsList();
    updateProviderConfigs();
}

function updateCurrentLLMInfo() {
    const infoElement = document.getElementById('currentLLMInfo');
    if (!infoElement) return;
    
    if (!selectedLLMId || !availableLLMs[selectedLLMId]) {
        // Find current model from available LLMs
        const currentConfigId = Object.keys(availableLLMs).find(id => availableLLMs[id].is_current);
        if (!currentConfigId) {
            infoElement.innerHTML = '<div class="no-data">No model selected</div>';
            return;
        }
        selectedLLMId = currentConfigId;
    }
    
    const config = availableLLMs[selectedLLMId];
    const statusClass = config.has_api_key || config.provider !== 'anthropic' ? 'available' : 'unavailable';
    
    infoElement.innerHTML = `
        <div class="current-llm-card">
            <div class="llm-header">
                <span class="llm-name">${config.display_name}</span>
                <span class="llm-status ${statusClass}">●</span>
            </div>
            <div class="llm-details">
                <span class="llm-provider">${config.provider.toUpperCase()}</span>
                <span class="llm-size">${config.size}</span>
                <span class="llm-model">${config.model}</span>
            </div>
        </div>
    `;
}

// Save to Collection Modal Functions
function showSaveToCollectionModal() {
    if (!currentConversationId) {
        showSmartSuggestion('❌ No active conversation to save');
        return;
    }
    
    const modal = document.getElementById('saveToCollectionModal');
    const existingCollectionSelect = document.getElementById('existingCollectionSelect');
    
    // Populate existing collections dropdown
    existingCollectionSelect.innerHTML = '<option value="">Choose a collection...</option>';
    collections.forEach(collection => {
        const option = document.createElement('option');
        option.value = collection.id;
        option.textContent = collection.name;
        existingCollectionSelect.appendChild(option);
    });
    
    // Reset modal state
    document.getElementById('existingCollectionSection').style.display = 'none';
    document.getElementById('newCollectionSection').style.display = 'none';
    document.getElementById('saveConfirmBtn').disabled = true;
    document.getElementById('newCollectionNameInput').value = '';
    
    // Reset button states
    document.getElementById('existingCollectionBtn').classList.remove('active');
    document.getElementById('newCollectionBtn').classList.remove('active');
    
    modal.style.display = 'block';
}

function closeSaveToCollectionModal() {
    document.getElementById('saveToCollectionModal').style.display = 'none';
}

function selectExistingCollection() {
    document.getElementById('existingCollectionSection').style.display = 'block';
    document.getElementById('newCollectionSection').style.display = 'none';
    document.getElementById('existingCollectionBtn').classList.add('active');
    document.getElementById('newCollectionBtn').classList.remove('active');
    
    // Enable save button if collection is selected
    const select = document.getElementById('existingCollectionSelect');
    document.getElementById('saveConfirmBtn').disabled = !select.value;
    
    // Add change listener for validation
    select.addEventListener('change', function() {
        document.getElementById('saveConfirmBtn').disabled = !this.value;
    });
}

function selectNewCollection() {
    document.getElementById('newCollectionSection').style.display = 'block';
    document.getElementById('existingCollectionSection').style.display = 'none';
    document.getElementById('newCollectionBtn').classList.add('active');
    document.getElementById('existingCollectionBtn').classList.remove('active');
    
    // Enable save button if name is entered
    const input = document.getElementById('newCollectionNameInput');
    document.getElementById('saveConfirmBtn').disabled = !input.value.trim();
    
    // Add input listener for validation
    input.addEventListener('input', function() {
        document.getElementById('saveConfirmBtn').disabled = !this.value.trim();
    });
    
    // Focus the input
    input.focus();
}

async function saveChatToCollection() {
    if (!currentConversationId) {
        showSmartSuggestion('❌ No active conversation to save');
        return;
    }
    
    const existingCollectionSelect = document.getElementById('existingCollectionSelect');
    const newCollectionNameInput = document.getElementById('newCollectionNameInput');
    const saveConfirmBtn = document.getElementById('saveConfirmBtn');
    
    // Determine which option is selected
    let collection_id = null;
    let collection_name = null;
    
    if (document.getElementById('existingCollectionSection').style.display === 'block') {
        collection_id = parseInt(existingCollectionSelect.value);
        if (!collection_id) {
            showSmartSuggestion('❌ Please select a collection');
            return;
        }
    } else if (document.getElementById('newCollectionSection').style.display === 'block') {
        collection_name = newCollectionNameInput.value.trim();
        if (!collection_name) {
            showSmartSuggestion('❌ Please enter a collection name');
            return;
        }
    } else {
        showSmartSuggestion('❌ Please select an option');
        return;
    }
    
    // Disable button and show loading
    saveConfirmBtn.disabled = true;
    saveConfirmBtn.textContent = 'Saving...';
    
    try {
        const response = await fetch(`/api/conversations/${currentConversationId}/save-to-collection`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                collection_id: collection_id,
                collection_name: collection_name
            })
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            closeSaveToCollectionModal();
            showSmartSuggestion(`✅ Chat saved to collection "${result.collection.name}" successfully!`);
            
            // Refresh collections list to include new collection if created
            if (collection_name) {
                await loadCollections();
            }
        } else {
            throw new Error(result.error || 'Failed to save chat');
        }
    } catch (error) {
        console.error('Error saving chat to collection:', error);
        showSmartSuggestion(`❌ Error saving chat: ${error.message}`);
    } finally {
        saveConfirmBtn.disabled = false;
        saveConfirmBtn.textContent = 'Save Chat';
    }
}