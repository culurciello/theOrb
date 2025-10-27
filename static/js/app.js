// Orvin Application - Rebuilt based on template with migrated features from old/js/
class OrvinApp {
    constructor() {
        this.state = {
            collections: [],
            conversations: [],
            availableAgents: [],
            availableLLMs: {},
            chatMessages: [],
            activeCollectionId: null,
            selectedAgentId: null,
            selectedLLMId: null,
            currentConversationId: null,  // Track current conversation
            activeTab: 'collections',
            currentTheme: 'light', // Will be loaded from user preferences
            pendingFiles: null,
            expandedCollections: new Set(),
            collectionFiles: {},
            isDocsExpanded: false,  // Track docs panel expansion state
            isCollectionsExpanded: false,  // Track collections panel expansion state
            userSettings: {
                profile: {
                    firstName: '',
                    lastName: '',
                    email: ''
                },
                apiKeys: {
                    openai: '',
                    anthropic: ''
                },
                defaultModel: 'gpt-4',
                maxTokens: 4000,
                temperature: 0.7
            }
        };

        // Initialize log refresh interval
        this.logRefreshInterval = null;

        this.init();
    }

    async init() {
        try {
            // Load initial data (includes user info with theme preference)
            await this.loadInitialData();

            // Initialize theme after loading user preferences
            this.initializeTheme();

            // Set up event listeners
            this.setupEventListeners();

            // Set up drag and drop
            this.setupDragAndDrop();

            console.log('Orvin application initialized successfully');
        } catch (error) {
            console.error('Error initializing application:', error);
            this.showNotification('Application initialization failed', 'error');
        }
    }

    // State Management
    setState(key, value) {
        this.state[key] = value;
    }

    getState() {
        return this.state;
    }

    // Theme Management
    initializeTheme() {
        document.documentElement.setAttribute('data-theme', this.state.currentTheme);
        this.updateThemeToggle();
    }

    async toggleTheme() {
        const newTheme = this.state.currentTheme === 'dark' ? 'light' : 'dark';

        try {
            // Save to server
            const response = await fetch('/api/user/theme', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ theme: newTheme })
            });

            if (response.ok) {
                this.state.currentTheme = newTheme;
                document.documentElement.setAttribute('data-theme', newTheme);
                this.updateThemeToggle();
                this.showNotification(`Switched to ${newTheme} theme`, 'success');
            } else {
                throw new Error('Failed to save theme preference');
            }
        } catch (error) {
            console.error('Error updating theme:', error);
            this.showNotification('Failed to save theme preference', 'error');
        }
    }

    updateThemeToggle() {
        const themeIcon = document.getElementById('themeIcon');
        const themeText = document.getElementById('themeText');

        if (themeIcon && themeText) {
            if (this.state.currentTheme === 'dark') {
                // Moon icon for dark mode
                themeIcon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />`;
                themeText.textContent = 'Dark';
            } else {
                // Sun icon for light mode
                themeIcon.innerHTML = `<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />`;
                themeText.textContent = 'Light';
            }
        }
    }

    // API Functions
    async loadInitialData() {
        try {
            await Promise.allSettled([
                this.loadCollections(),
                this.loadAvailableAgents(),
                this.loadAvailableLLMs(),
                this.loadConversations(),
                this.loadSettings(),
                this.loadUserTheme()
            ]);

            this.updateSelectors();
            this.renderCollections();
        } catch (error) {
            console.error('Error loading initial data:', error);
        }
    }

    async loadCollections() {
        try {
            const response = await fetch('/api/collections');
            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const collections = await response.json();
            this.state.collections = collections;
            this.updateActiveCollectionSelector();
            return collections;
        } catch (error) {
            console.error('Error loading collections:', error);
            this.state.collections = [];
            throw error;
        }
    }

    async createCollection(data) {
        const response = await fetch('/api/collections', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Unknown error');
        return result;
    }

    async deleteCollection(collectionId) {
        const response = await fetch(`/api/collections/${collectionId}`, {
            method: 'DELETE'
        });
        if (!response.ok) throw new Error('Failed to delete collection');
        await this.loadCollections();
        this.renderCollections();
    }

    async loadCollectionDocuments(collectionId) {
        try {
            const response = await fetch(`/api/collections/${collectionId}/files`);
            if (!response.ok) {
                if (response.status === 404) return [];
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            return data.files || [];
        } catch (error) {
            console.error('Error loading collection documents:', error);
            return [];
        }
    }

    async uploadFilesToCollection(collectionId, files) {
        let successCount = 0;
        const errors = [];
        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch(`/api/collections/${collectionId}/upload`, {
                    method: 'POST',
                    body: formData
                });

                // Check if response is ok
                if (!response.ok) {
                    // Read response as text first to avoid "body locked" error
                    const text = await response.text();
                    let errorMsg;
                    try {
                        const result = JSON.parse(text);
                        errorMsg = result.error || `Server error (${response.status})`;
                    } catch {
                        // Response is not JSON, use text directly
                        errorMsg = text || `Server error (${response.status})`;
                    }
                    errors.push(`${file.name}: ${errorMsg}`);
                    console.error(`Error uploading ${file.name}:`, errorMsg);
                    continue;
                }

                const result = await response.json();
                if (!result.error) {
                    successCount++;
                    // Check for partial errors (some files succeeded, some failed)
                    if (result.errors && result.errors.length > 0) {
                        errors.push(...result.errors);
                    }
                } else {
                    errors.push(`${file.name}: ${result.error}`);
                    console.error(`Error uploading ${file.name}:`, result.error);
                }
            } catch (error) {
                errors.push(`${file.name}: ${error.message}`);
                console.error(`Error uploading ${file.name}:`, error);
            }
        }
        return { successCount, errors };
    }

    async loadAvailableAgents() {
        try {
            const response = await fetch('/api/agents');
            const agents = await response.json();
            this.state.availableAgents = agents;
            this.updateAgentSelector();
            return agents;
        } catch (error) {
            console.error('Error loading agents:', error);
            this.state.availableAgents = [];
        }
    }

    async loadAvailableLLMs() {
        try {
            const response = await fetch('/api/llm/configs');
            const llms = await response.json();
            this.state.availableLLMs = llms;
            this.updateLLMSelector();
            return llms;
        } catch (error) {
            console.error('Error loading LLMs:', error);
            this.state.availableLLMs = {};
        }
    }

    async loadConversations() {
        try {
            const response = await fetch('/api/conversations');
            const conversations = await response.json();
            this.state.conversations = conversations;

            // Use actual conversations from API only (no mock data)

            return this.state.conversations;
        } catch (error) {
            console.error('Error loading conversations:', error);
            // Set empty conversations array on error
            this.state.conversations = [];
        }
    }


    async sendChatMessage(message, conversationId, collectionId, agentId) {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                conversation_id: conversationId,
                collection_id: collectionId,
                agent_id: agentId
            })
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(errorText);
        }

        return await response.json();
    }

    // UI Functions
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;

        // Sanitize message to prevent XSS
        const sanitizedMessage = Sanitizer.escapeHTML(message);
        notification.innerHTML = `
            <span>${sanitizedMessage}</span>
            <button class="close-btn ml-2 text-white hover:text-gray-200" onclick="this.parentElement.remove()">&times;</button>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    showLoadingOverlay(title = 'Processing...', message = 'Please wait while we process your request', submessage = 'This may take a few moments') {
        const overlay = document.getElementById('loadingOverlay');
        const titleEl = document.getElementById('loadingTitle');
        const messageEl = document.getElementById('loadingMessage');
        const submessageEl = document.getElementById('loadingSubmessage');

        if (overlay) {
            if (titleEl) titleEl.textContent = title;
            if (messageEl) messageEl.textContent = message;
            if (submessageEl) submessageEl.textContent = submessage;
            overlay.classList.add('active');

            // Disable send button and input
            const sendButton = document.querySelector('button[onclick="handleSendMessage()"]');
            const messageInput = document.getElementById('messageInput');
            if (sendButton) sendButton.disabled = true;
            if (messageInput) messageInput.disabled = true;
        }
    }

    hideLoadingOverlay() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.classList.remove('active');

            // Re-enable send button and input
            const sendButton = document.querySelector('button[onclick="handleSendMessage()"]');
            const messageInput = document.getElementById('messageInput');
            if (sendButton) sendButton.disabled = false;
            if (messageInput) messageInput.disabled = false;
        }
    }

    updateLoadingOverlay(title, message, submessage) {
        const titleEl = document.getElementById('loadingTitle');
        const messageEl = document.getElementById('loadingMessage');
        const submessageEl = document.getElementById('loadingSubmessage');

        if (titleEl && title) titleEl.textContent = title;
        if (messageEl && message) messageEl.textContent = message;
        if (submessageEl && submessage) submessageEl.textContent = submessage;
    }

    setActiveTab(tabName) {
        this.state.activeTab = tabName;

        // Update tab buttons
        const tabs = ['collections', 'history', 'log', 'instructions'];
        tabs.forEach(tab => {
            const tabElement = document.getElementById(`${tab}Tab`);
            if (tabElement) {
                tabElement.className =
                    tabName === tab
                        ? 'px-6 py-3 text-sm font-medium text-purple-600 border-b-2 border-purple-600'
                        : 'px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700';
            }
        });

        // Show/hide content
        const contents = ['collectionsContent', 'historyContent', 'logContent', 'instructionsContent'];
        contents.forEach(content => {
            const contentElement = document.getElementById(content);
            if (contentElement) {
                contentElement.style.display = content === `${tabName}Content` ? 'block' : 'none';
            }
        });

        // Load content for specific tabs
        if (tabName === 'history') {
            this.renderConversationHistory();
        } else if (tabName === 'log') {
            this.refreshLogs();
            // Auto-refresh logs every 5 seconds when log tab is active
            if (this.logRefreshInterval) {
                clearInterval(this.logRefreshInterval);
            }
            this.logRefreshInterval = setInterval(() => {
                if (this.state.activeTab === 'log') {
                    this.refreshLogs();
                }
            }, 5000);
        } else {
            // Clear log refresh interval when switching away from log tab
            if (this.logRefreshInterval) {
                clearInterval(this.logRefreshInterval);
                this.logRefreshInterval = null;
            }
        }
    }

    updateSelectors() {
        this.updateActiveCollectionSelector();
        this.updateAgentSelector();
        this.updateLLMSelector();
    }

    updateActiveCollectionSelector() {
        const dropdownList = document.getElementById('collectionsDropdownList');
        if (!dropdownList) return;

        dropdownList.innerHTML = this.state.collections.map(collection => {
            const docCount = collection.document_count || collection.docCount || 0;
            const isActive = this.state.activeCollectionId === collection.id;
            return `
                <button
                    onclick="handleCollectionChange('${collection.id}')"
                    class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100/50 text-xs font-light text-black transition-colors ${isActive ? 'bg-purple-100/50 ring-1 ring-purple-300' : ''}"
                >
                    <div class="font-medium">${collection.name}</div>
                    <div class="text-[10px] text-gray-500">${docCount} documents</div>
                </button>
            `;
        }).join('');
    }

    updateAgentSelector() {
        const dropdownList = document.getElementById('agentDropdownList');
        if (!dropdownList) return;

        const agents = this.state.availableAgents || [];

        if (agents.length === 0) {
            dropdownList.innerHTML = `
                <button
                    onclick="handleAgentChange('')"
                    class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100/50 text-xs font-light text-black transition-colors"
                >
                    Default Agent
                </button>
            `;
            return;
        }

        // Add "Default Agent" option first
        dropdownList.innerHTML = `
            <button
                onclick="handleAgentChange('')"
                class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100/50 text-xs font-light text-black transition-colors ${!this.state.selectedAgentId ? 'bg-purple-100/50 ring-1 ring-purple-300' : ''}"
            >
                Default Agent
            </button>
        ` + agents.map(agent => {
            const isActive = this.state.selectedAgentId === agent.name;
            const displayName = agent.display_name || agent.name;
            return `
                <button
                    onclick="handleAgentChange('${agent.name}')"
                    class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100/50 text-xs font-light text-black transition-colors ${isActive ? 'bg-purple-100/50 ring-1 ring-purple-300' : ''}"
                >
                    ${displayName}
                </button>
            `;
        }).join('');
    }

    updateLLMSelector() {
        const dropdownList = document.getElementById('llmDropdownList');
        if (!dropdownList) return;

        const llmEntries = Object.entries(this.state.availableLLMs);

        if (llmEntries.length === 0) {
            dropdownList.innerHTML = `
                <button
                    onclick="handleLLMChange('')"
                    class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100/50 text-xs font-light text-black transition-colors"
                >
                    Default Model
                </button>
            `;
            return;
        }

        dropdownList.innerHTML = llmEntries.map(([configId, config]) => {
            const isActive = this.state.selectedLLMId === configId;
            const displayName = config.display_name || configId;
            return `
                <button
                    onclick="handleLLMChange('${configId}')"
                    class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100/50 text-xs font-light text-black transition-colors ${isActive ? 'bg-purple-100/50 ring-1 ring-purple-300' : ''}"
                >
                    ${displayName}
                </button>
            `;
        }).join('');
    }


    renderCollections() {
        const container = document.getElementById('collectionsList');
        if (!container) return;

        if (this.state.collections.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-center py-8 text-xs">No collections yet</p>';
            return;
        }

        container.innerHTML = this.state.collections.map(collection => {
            const docCount = collection.document_count || collection.docCount || 0;
            const updatedAt = collection.updated_at || collection.updatedAt || collection.created_at;
            const formattedDate = updatedAt ? new Date(updatedAt).toLocaleDateString() : 'Recently';
            const isExpanded = this.state.expandedCollections.has(collection.id);
            const isActive = this.state.activeCollectionId === collection.id;
            const files = this.state.collectionFiles[collection.id] || [];

            // Generate files list HTML if expanded
            const filesListHTML = isExpanded ? `
                <div class="mt-2 pt-2 border-t border-gray-200/30 space-y-1">
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-[10px] text-gray-500">${files.length} files</span>
                        <button
                            onclick="app.triggerFileUpload(${collection.id}); event.stopPropagation();"
                            class="px-2 py-0.5 bg-purple-500/80 text-white text-[10px] rounded hover:bg-purple-600 transition-colors"
                            title="Upload files"
                        >
                            + Upload
                        </button>
                    </div>
                    ${files.length === 0 ?
                        '<p class="text-[10px] text-gray-400 italic">No files yet</p>' :
                        `<div class="space-y-0.5 max-h-32 overflow-y-auto">
                            ${files.map(file => `
                                <div
                                    class="flex items-center justify-between py-1 px-1.5 bg-white/50 rounded text-[10px] hover:bg-white/80 cursor-pointer transition-colors"
                                    onclick="app.viewDocument(${file.id}, '${(file.filename || file.name).replace(/'/g, "\\'")}', '${file.download_url || ''}'); event.stopPropagation();"
                                    title="Click to view"
                                >
                                    <div class="flex items-center space-x-1 flex-1 min-w-0">
                                        <span class="text-gray-600 text-xs">${this.getFileIcon(this.getFileExtension(file.filename || file.name))}</span>
                                        <span class="text-gray-700 truncate">${file.filename || file.name}</span>
                                    </div>
                                    <span class="text-gray-400 text-[9px] ml-1">${this.formatFileSize(file.file_size || file.content_length || file.size || 0)}</span>
                                </div>
                            `).join('')}
                        </div>`
                    }
                </div>
            ` : '';

            return `
                <div
                    class="p-3 rounded-xl bg-white/70 border border-gray-200/30 hover:bg-white/90 transition-colors cursor-pointer ${isActive ? 'ring-2 ring-purple-400/50' : ''}"
                    data-collection-id="${collection.id}"
                    onclick="app.toggleCollectionDetails(${collection.id})"
                >
                    <div class="flex items-start justify-between mb-1">
                        <div class="flex items-center space-x-2 flex-1 min-w-0">
                            <span class="text-sm font-light text-black truncate">${collection.name}</span>
                            <svg class="w-3 h-3 transition-transform duration-200 flex-shrink-0 ${isExpanded ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                                <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
                            </svg>
                        </div>
                        <div class="flex items-center space-x-1 flex-shrink-0">
                            <div class="w-2 h-2 rounded-full ${isActive ? 'bg-green-500' : 'bg-gray-300'}"></div>
                            <button
                                onclick="app.deleteCollection(${collection.id}); event.stopPropagation();"
                                class="p-0.5 text-gray-400 hover:text-red-600 rounded transition-colors"
                                title="Delete"
                            >
                                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="2">
                                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </button>
                        </div>
                    </div>
                    <div class="text-xs text-gray-500">${docCount} items • ${formattedDate}</div>
                    ${filesListHTML}
                </div>
            `;
        }).join('');
    }

    setActiveCollection(collectionId) {
        this.state.activeCollectionId = collectionId;
        this.updateActiveCollectionSelector();
        this.renderCollections();

        if (collectionId) {
            const collection = this.state.collections.find(c => c.id === collectionId);
            if (collection) {
                this.showNotification(`Collection "${collection.name}" selected for chat`, 'success');
            }
        }
    }

    // Chat Functions
    renderChatMessages() {
        const container = document.getElementById('chatMessages');
        if (!container) return;

        if (this.state.chatMessages.length === 0) {
            container.innerHTML = `
                <div class="text-center text-gray-500 mt-8">
                    <p>Start a conversation about your selected collection</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.state.chatMessages.map((message, idx) => {
            const messageText = message.text || message.content || message.message || '';
            const messageRole = message.role || 'assistant';
            const messageCites = message.cites || message.citations || [];
            const documentRefs = message.documentReferences || [];

            return `
                <div class="message flex ${messageRole === 'user' ? 'justify-end' : 'justify-start'}">
                    <div class="max-w-3/4 p-3 rounded-lg ${
                        messageRole === 'user'
                            ? 'bg-purple-600 text-white'
                            : 'bg-gray-100 text-gray-800'
                    }">
                        <div class="text-sm message-content">${this.formatMessageContent(messageText)}</div>
                        ${messageCites && messageCites.length > 0 ? `
                            <div class="mt-2 flex flex-wrap gap-1">
                                ${messageCites.map(cite => `
                                    <span class="px-2 py-1 bg-white bg-opacity-20 rounded text-xs cursor-pointer hover:bg-opacity-30">
                                        [doc: ${cite}]
                                    </span>
                                `).join('')}
                            </div>
                        ` : ''}
                        ${documentRefs && documentRefs.length > 0 ? `
                            <div class="mt-2 flex flex-wrap gap-1">
                                <span class="text-xs text-gray-600 dark:text-gray-400">Sources:</span>
                                ${documentRefs.map(ref => `
                                    <a href="${window.location.protocol}//${window.location.host}${window.location.pathname.includes('/mynewpage') ? '/mynewpage' : ''}/document-viewer?id=${ref.document_id}&highlight_chunk=${ref.chunk_order}"
                                       target="_blank"
                                       class="px-2 py-1 bg-blue-100 text-blue-800 hover:bg-blue-200 rounded text-xs cursor-pointer inline-flex items-center gap-1"
                                       title="View ${ref.filename}, paragraph ${ref.chunk_order + 1}">
                                        📄 ${ref.filename} (¶${ref.chunk_order + 1})
                                    </a>
                                `).join('')}
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');

        container.scrollTop = container.scrollHeight;
    }

    async handleSendMessage() {
        const messageInput = document.getElementById('messageInput');
        const messageText = messageInput.value.trim();

        if (!messageText) return;

        // Add user message
        const userMessage = { role: 'user', text: messageText };
        this.state.chatMessages.push(userMessage);
        messageInput.value = '';
        this.renderChatMessages();

        // Detect if message might trigger a tool
        const isToolCommand = this.detectToolUsage(messageText);

        if (isToolCommand) {
            this.showLoadingOverlay(
                isToolCommand.title,
                isToolCommand.message,
                isToolCommand.submessage
            );
        } else {
            this.showLoadingOverlay(
                'Processing your message...',
                'The AI is thinking about your question',
                'This usually takes a few seconds'
            );
        }

        try {
            // Get active collection
            const activeCollection = this.state.collections.find(c => c.id === this.state.activeCollectionId);

            // Send message to API with current conversation ID
            const response = await this.sendChatMessage(
                messageText,
                this.state.currentConversationId,
                this.state.activeCollectionId,
                this.state.selectedAgentId
            );

            // Hide loading overlay
            this.hideLoadingOverlay();

            // Update conversation ID from response
            if (response.conversation_id) {
                this.state.currentConversationId = response.conversation_id;
                // Reload conversations to update history
                await this.loadConversations();
            }

            // Add assistant response
            const assistantMessage = {
                role: 'assistant',
                text: response.response || 'Sorry, I could not generate a response at this time.',
                cites: response.citations || [],
                documentReferences: response.document_references || []
            };
            this.state.chatMessages.push(assistantMessage);
            this.renderChatMessages();
        } catch (error) {
            console.error('Error sending message:', error);

            // Hide loading overlay
            this.hideLoadingOverlay();

            // Add error message
            const errorMessage = {
                role: 'assistant',
                text: 'Sorry, there was an error processing your request. Please try again.',
                cites: []
            };
            this.state.chatMessages.push(errorMessage);
            this.renderChatMessages();
        }
    }

    detectToolUsage(message) {
        const messageLower = message.toLowerCase();

        // Detect PubMed search
        if (messageLower.includes('search pubmed') || messageLower.includes('pubmed search') ||
            (messageLower.includes('pubmed') && messageLower.includes('papers'))) {
            return {
                title: 'Searching PubMed...',
                message: 'Searching for research papers and downloading PDFs',
                submessage: 'This may take 1-2 minutes depending on the number of papers'
            };
        }

        // Detect arXiv search
        if (messageLower.includes('search arxiv') || messageLower.includes('arxiv search') ||
            (messageLower.includes('arxiv') && (messageLower.includes('papers') || messageLower.includes('preprints')))) {
            return {
                title: 'Searching arXiv...',
                message: 'Searching for preprints and downloading PDFs',
                submessage: 'This may take 1-2 minutes depending on the number of papers'
            };
        }

        // Detect calculation
        if (messageLower.includes('calculate') || messageLower.includes('compute') ||
            /\d+\s*[\+\-\*\/]\s*\d+/.test(message)) {
            return {
                title: 'Calculating...',
                message: 'Performing mathematical calculation',
                submessage: 'This should only take a moment'
            };
        }

        // Detect time/date requests
        if (messageLower.includes('time') || messageLower.includes('date') ||
            messageLower.includes('what day') || messageLower.includes('current')) {
            return {
                title: 'Getting current time...',
                message: 'Fetching current date and time information',
                submessage: 'Just a moment...'
            };
        }

        return null;
    }


    formatMessageContent(text) {
        if (!text) return '';

        // Simple markdown-like formatting
        let formatted = text;

        // Convert double line breaks to paragraphs
        formatted = formatted.split('\n\n').map(paragraph =>
            paragraph.trim() ? `<p class="mb-3 last:mb-0">${this.processInlineMarkdown(paragraph.replace(/\n/g, '<br>'))}</p>` : ''
        ).filter(p => p).join('');

        // If no double line breaks, treat single line breaks as paragraphs
        if (!formatted.includes('<p>')) {
            formatted = formatted.split('\n').map(line =>
                line.trim() ? `<p class="mb-2 last:mb-0">${this.processInlineMarkdown(line)}</p>` : ''
            ).filter(p => p).join('');
        }

        return formatted || `<p>${this.processInlineMarkdown(text)}</p>`;
    }

    processInlineMarkdown(text) {
        return text
            // Bold text **text** or __text__
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/__(.*?)__/g, '<strong>$1</strong>')

            // Italic text *text* or _text_
            .replace(/(?<!\*)\*([^*]+)\*(?!\*)/g, '<em>$1</em>')
            .replace(/(?<!_)_([^_]+)_(?!_)/g, '<em>$1</em>')

            // Code inline `code`
            .replace(/`([^`]+)`/g, '<code class="bg-gray-200 px-1 rounded text-sm font-mono">$1</code>')

            // Lists - simple detection
            .replace(/^[\s]*[-*+]\s(.+)$/gm, '<li class="ml-4">• $1</li>')
            .replace(/^[\s]*(\d+\.)\s(.+)$/gm, '<li class="ml-4">$1 $2</li>')

            // Links [text](url)
            .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:underline" target="_blank">$1</a>');
    }

    // File Upload Functions
    triggerFileUploadForNewCollection() {
        const fileInput = document.getElementById('fileInput');
        fileInput.onchange = (event) => {
            const files = Array.from(event.target.files);
            if (files.length > 0) {
                this.showNotification(`${files.length} file(s) selected. Create a collection first, then files will be uploaded.`, 'info');
                this.state.pendingFiles = files;
                this.updateNewCollectionUploadArea(files);
            }
            fileInput.value = '';
        };
        fileInput.click();
    }

    triggerFileUpload(collectionId) {
        const fileInput = document.getElementById('fileInput');
        fileInput.onchange = async (event) => {
            const files = Array.from(event.target.files);
            await this.handleFileUpload(files, collectionId);
            fileInput.value = '';
        };
        fileInput.click();
    }

    async handleFileUpload(files, collectionId) {
        // Use streaming upload for better progress feedback
        await this.uploadFilesWithStreaming(collectionId, files);
    }

    updateNewCollectionUploadArea(files) {
        const uploadArea = document.getElementById('newCollectionUploadArea');
        if (!uploadArea) return;

        const filesList = files.slice(0, 3).map(file => {
            const shortName = file.name.length > 30 ? file.name.substring(0, 30) + '...' : file.name;
            return `<div class="text-xs text-gray-600">${this.getFileIcon(this.getFileExtension(file.name))} ${shortName}</div>`;
        }).join('');

        const moreText = files.length > 3 ? `<div class="text-xs text-gray-400">+${files.length - 3} more files</div>` : '';

        uploadArea.innerHTML = `
            <div class="flex flex-col items-center space-y-2">
                <svg class="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                </svg>
                <p class="text-sm text-green-600 font-medium">${files.length} file(s) ready to upload</p>
                <div class="text-left space-y-1">
                    ${filesList}
                    ${moreText}
                </div>
                <p class="text-xs text-gray-500">Create collection to upload these files</p>
            </div>
        `;
    }

    resetNewCollectionUploadArea() {
        const uploadArea = document.getElementById('newCollectionUploadArea');
        if (!uploadArea) return;

        uploadArea.innerHTML = `
            <div class="flex flex-col items-center space-y-2">
                <svg class="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
                <p class="text-sm text-gray-600">
                    Drop files here or
                    <span class="text-purple-600 hover:underline font-medium">choose files</span>
                </p>
                <p class="text-xs text-gray-400">Upload files to add to your new collection</p>
                <p class="text-xs text-gray-400">PDF, DOC, TXT, MD, CSV, XLS, Images, Videos supported</p>
            </div>
        `;
    }

    async toggleCollectionDetails(collectionId) {
        const isExpanded = this.state.expandedCollections.has(collectionId);

        if (isExpanded) {
            // Collapse
            this.state.expandedCollections.delete(collectionId);
        } else {
            // Expand and load files if not already loaded
            this.state.expandedCollections.add(collectionId);
            if (!this.state.collectionFiles[collectionId]) {
                try {
                    const files = await this.loadCollectionDocuments(collectionId);
                    this.state.collectionFiles[collectionId] = files;
                } catch (error) {
                    console.error('Error loading collection files:', error);
                    this.state.collectionFiles[collectionId] = [];
                }
            }
        }

        // Re-render collections to show/hide details
        this.renderCollections();
    }

    formatFileSize(bytes) {
        if (!bytes || bytes === 0) return '0 B';

        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        const size = bytes / Math.pow(1024, i);

        return `${size.toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`;
    }

    handleCreateCollectionClick() {
        const nameInput = document.getElementById('newCollectionName');
        const name = nameInput.value.trim();

        if (!name) {
            // If no name is provided, show notification
            this.showNotification('Please enter a collection name', 'info');
            return;
        }

        // If name is provided, proceed with creation
        this.handleCreateCollection();
    }

    async handleCreateCollection() {
        const nameInput = document.getElementById('newCollectionName');
        const name = nameInput.value.trim();

        if (!name) return;

        try {
            const result = await this.createCollection({ name });
            const newCollectionId = result.id;

            nameInput.value = '';

            this.showNotification(`Collection "${name}" created successfully!`, 'success');

            // Upload pending files if any
            if (this.state.pendingFiles && this.state.pendingFiles.length > 0) {
                const files = this.state.pendingFiles;

                try {
                    // Use streaming upload for better progress feedback
                    await this.uploadFilesWithStreaming(newCollectionId, files);
                } catch (uploadError) {
                    console.error('Error uploading files:', uploadError);
                    this.showNotification(`Error uploading files: ${uploadError.message}`, 'error');
                }

                this.state.pendingFiles = null;
                this.resetNewCollectionUploadArea();
            }

            // Refresh collections list with delay to ensure all operations complete
            setTimeout(async () => {
                await this.loadCollections();
                this.renderCollections();
                this.updateSelectors();
                this.showNotification('Collection list refreshed!', 'success');
            }, 500);

        } catch (error) {
            console.error('Error creating collection:', error);
            this.showNotification(`Error creating collection: ${error.message}`, 'error');
        }
    }


    // Conversation History Functions
    renderConversationHistory() {
        const container = document.getElementById('conversationsList');
        if (!container) return;

        if (this.state.conversations.length === 0) {
            container.innerHTML = '<div class="text-xs font-light text-gray-400 px-2 py-2 italic">No conversations yet</div>';
            return;
        }

        container.innerHTML = this.state.conversations.map(conversation => {
            const messageCount = conversation.message_count || 0;
            const formattedDate = new Date(conversation.created_at || conversation.createdAt).toLocaleDateString();
            const isActive = this.state.currentConversationId === conversation.id;

            // Get first message preview if available
            let preview = 'Click to load';
            if (conversation.messages && conversation.messages.length > 0) {
                preview = conversation.messages[0].content.substring(0, 50) + '...';
            }

            return `
                <button
                    onclick="app.loadConversation(${conversation.id})"
                    class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-100/50 text-xs font-light text-black transition-colors ${isActive ? 'bg-purple-100/50 ring-1 ring-purple-300' : ''}"
                >
                    <div class="flex items-center justify-between mb-1">
                        <span class="font-medium truncate flex-1">${conversation.title || 'Conversation ' + conversation.id}</span>
                        <button
                            onclick="app.deleteConversation(${conversation.id}); event.stopPropagation();"
                            class="p-0.5 text-gray-400 hover:text-red-600 rounded transition-colors"
                            title="Delete"
                        >
                            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                        </button>
                    </div>
                    <div class="text-[10px] text-gray-500">${messageCount} messages • ${formattedDate}</div>
                </button>
            `;
        }).join('');
    }

    async loadConversation(conversationId) {
        try {
            const response = await fetch(`/api/conversations/${conversationId}`);
            if (!response.ok) throw new Error('Failed to load conversation');

            const conversation = await response.json();

            // Process and normalize messages
            const messages = conversation.messages || [];
            this.state.chatMessages = messages.map(msg => {
                // Normalize message format
                return {
                    role: msg.role || (msg.sender === 'user' ? 'user' : 'assistant'),
                    text: msg.content || msg.text || msg.message || '',
                    cites: msg.cites || msg.citations || [],
                    timestamp: msg.timestamp || msg.created_at
                };
            });

            // Set current conversation ID so new messages continue this conversation
            this.state.currentConversationId = conversationId;

            console.log('Loaded conversation:', conversationId, 'with', this.state.chatMessages.length, 'messages');
            this.renderChatMessages();

            // Close the dropdown
            const dropdown = document.getElementById('historyDropdown');
            if (dropdown) dropdown.style.display = 'none';

            // Find conversation title for notification
            const conv = this.state.conversations.find(c => c.id === conversationId);
            const title = conv ? (conv.title || `Conversation ${conversationId}`) : 'Conversation';

            this.showNotification(`Loaded: ${title} (${this.state.chatMessages.length} messages)`, 'success');
        } catch (error) {
            console.error('Error loading conversation:', error);
            this.showNotification(`Failed to load conversation: ${error.message}`, 'error');

            // Clear chat messages on error
            this.state.chatMessages = [];
            this.state.currentConversationId = null;
        }
    }


    async deleteConversation(conversationId) {
        if (!confirm('Are you sure you want to delete this conversation?')) {
            return;
        }

        try {
            const response = await fetch(`/api/conversations/${conversationId}`, {
                method: 'DELETE'
            });
            if (!response.ok) throw new Error('Failed to delete conversation');

            await this.loadConversations();
            this.renderConversationHistory();
            this.showNotification('Conversation deleted', 'success');
        } catch (error) {
            console.error('Error deleting conversation:', error);
            this.showNotification('Failed to delete conversation', 'error');
        }
    }

    startNewConversation() {
        this.state.chatMessages = [];
        this.state.currentConversationId = null;  // Reset conversation ID
        this.renderChatMessages();

        // Close the dropdown
        const dropdown = document.getElementById('historyDropdown');
        if (dropdown) dropdown.style.display = 'none';

        this.showNotification('New conversation started', 'success');
    }

    clearChatHistory() {
        if (!confirm('Are you sure you want to clear all chat history? This will only clear the current session, not saved conversations.')) {
            return;
        }

        this.state.chatMessages = [];
        this.state.currentConversationId = null;  // Reset conversation ID
        this.renderChatMessages();
        this.showNotification('Chat history cleared', 'success');
    }

    exportConversations() {
        const exportData = {
            conversations: this.state.conversations,
            currentChat: this.state.chatMessages,
            exportDate: new Date().toISOString()
        };

        const dataStr = JSON.stringify(exportData, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);

        const link = document.createElement('a');
        link.href = url;
        link.download = `orvin-conversations-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        this.showNotification('Conversations exported successfully', 'success');
    }

    // Log Functions
    async refreshLogs() {
        try {
            const response = await fetch('/api/logs');
            if (!response.ok) throw new Error('Failed to fetch logs');

            const data = await response.json();
            const logOutput = document.getElementById('logOutput');

            if (data.logs && data.logs.length > 0) {
                // Format logs with timestamps
                logOutput.innerHTML = data.logs.map(line => {
                    // Color-code different log levels
                    if (line.includes('ERROR') || line.includes('✗')) {
                        return `<div class="text-red-400">${this.escapeHtml(line)}</div>`;
                    } else if (line.includes('WARNING') || line.includes('⚠️')) {
                        return `<div class="text-yellow-400">${this.escapeHtml(line)}</div>`;
                    } else if (line.includes('INFO') || line.includes('✓')) {
                        return `<div class="text-green-400">${this.escapeHtml(line)}</div>`;
                    } else if (line.includes('DEBUG') || line.includes('🔧')) {
                        return `<div class="text-blue-400">${this.escapeHtml(line)}</div>`;
                    } else {
                        return `<div class="text-gray-400">${this.escapeHtml(line)}</div>`;
                    }
                }).join('');

                // Auto-scroll to bottom
                logOutput.scrollTop = logOutput.scrollHeight;
            } else {
                logOutput.innerHTML = '<p class="text-gray-500">No logs available</p>';
            }
        } catch (error) {
            console.error('Error fetching logs:', error);
            document.getElementById('logOutput').innerHTML =
                `<p class="text-red-400">Error loading logs: ${this.escapeHtml(error.message)}</p>`;
        }
    }

    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Settings Functions
    async loadSettings() {
        try {
            const response = await fetch('/api/settings');
            if (response.ok) {
                const settings = await response.json();
                this.state.userSettings = { ...this.state.userSettings, ...settings };
            }
        } catch (error) {
            console.error('Error loading settings:', error);
        }
    }

    async loadSettingsPanel() {
        // Load user info
        await this.loadCurrentUserInfo();

        // Load settings data
        await this.loadSettings();

        // Populate the UI (now async to load profile data)
        await this.populateSettingsPanel();

        // Update theme toggle
        this.updateThemeToggle();
    }

    async loadCurrentUserInfo() {
        try {
            // Load user info
            const userResponse = await fetch('/api/user/current');
            if (userResponse.ok) {
                const user = await userResponse.json();

                // Update current user display
                const usernameEl = document.getElementById('currentUsername');
                const emailEl = document.getElementById('currentUserEmail');

                if (usernameEl) usernameEl.textContent = user.username || 'User';
                if (emailEl) emailEl.textContent = user.email || '';

                // Store theme preference
                if (user.theme_preference) {
                    this.state.currentTheme = user.theme_preference;
                }
            }

            // Load profile info separately
            const profileResponse = await fetch('/api/user/profile');
            if (profileResponse.ok) {
                const profile = await profileResponse.json();

                const firstNameEl = document.getElementById('firstName');
                const lastNameEl = document.getElementById('lastName');
                const emailInputEl = document.getElementById('email');

                if (firstNameEl) firstNameEl.value = profile.name || '';
                if (lastNameEl) lastNameEl.value = profile.lastname || '';
                if (emailInputEl && !emailInputEl.value) emailInputEl.value = profile.email || '';
            }
        } catch (error) {
            console.error('Error loading user info:', error);
        }
    }

    async populateSettingsPanel() {
        // Load profile data first
        try {
            const profileResponse = await fetch('/api/user/profile');
            if (profileResponse.ok) {
                const profile = await profileResponse.json();

                const firstNameEl = document.getElementById('firstName');
                const lastNameEl = document.getElementById('lastName');
                const emailInputEl = document.getElementById('email');

                if (firstNameEl) firstNameEl.value = profile.name || '';
                if (lastNameEl) lastNameEl.value = profile.lastname || '';
                if (emailInputEl) emailInputEl.value = profile.email || '';
            }
        } catch (error) {
            console.error('Error loading profile data:', error);
        }

        // Populate API keys if available
        const settings = this.state.userSettings;

        const openaiKeyEl = document.getElementById('openaiApiKey');
        const anthropicKeyEl = document.getElementById('anthropicApiKey');
        const maxTokensEl = document.getElementById('maxTokens');
        const temperatureEl = document.getElementById('temperature');
        const temperatureValueEl = document.getElementById('temperatureValue');
        const defaultModelEl = document.getElementById('defaultModel');

        if (settings.apiKeys) {
            if (openaiKeyEl && settings.apiKeys.openai) {
                openaiKeyEl.value = settings.apiKeys.openai;
            }
            if (anthropicKeyEl && settings.apiKeys.anthropic) {
                anthropicKeyEl.value = settings.apiKeys.anthropic;
            }
        }

        if (maxTokensEl && settings.maxTokens) {
            maxTokensEl.value = settings.maxTokens;
        }

        if (temperatureEl && settings.temperature !== undefined) {
            temperatureEl.value = settings.temperature;
            if (temperatureValueEl) {
                temperatureValueEl.textContent = settings.temperature;
            }
        }

        // Update temperature value display on slider change
        if (temperatureEl) {
            temperatureEl.oninput = function() {
                if (temperatureValueEl) {
                    temperatureValueEl.textContent = this.value;
                }
            };
        }

        // Populate LLM dropdown
        if (defaultModelEl) {
            const llmEntries = Object.entries(this.state.availableLLMs);

            if (llmEntries.length === 0) {
                defaultModelEl.innerHTML = '<option value="">No models configured</option>';
            } else {
                defaultModelEl.innerHTML = '<option value="">Select a model</option>' +
                    llmEntries.map(([configId, config]) => {
                        const displayName = config.display_name || configId;
                        return `<option value="${configId}">${displayName}</option>`;
                    }).join('');

                // Set current value
                if (settings.defaultModel) {
                    defaultModelEl.value = settings.defaultModel;
                }
            }
        }
    }

    async saveSettings() {
        try {
            // Collect all form values
            const firstName = document.getElementById('firstName')?.value || '';
            const lastName = document.getElementById('lastName')?.value || '';
            const email = document.getElementById('email')?.value || '';
            const openaiKey = document.getElementById('openaiApiKey')?.value || '';
            const anthropicKey = document.getElementById('anthropicApiKey')?.value || '';
            const maxTokens = parseInt(document.getElementById('maxTokens')?.value) || 4000;
            const temperature = parseFloat(document.getElementById('temperature')?.value) || 0.7;
            const defaultModel = document.getElementById('defaultModel')?.value || '';

            // Update state
            this.state.userSettings = {
                ...this.state.userSettings,
                profile: {
                    firstName: firstName,
                    lastName: lastName,
                    email: email
                },
                apiKeys: {
                    openai: openaiKey,
                    anthropic: anthropicKey
                },
                defaultModel: defaultModel,
                maxTokens: maxTokens,
                temperature: temperature
            };

            // Save profile
            const profileResponse = await fetch('/api/user/profile', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: firstName,
                    lastname: lastName,
                    email: email
                })
            });

            // Save settings
            const settingsResponse = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(this.state.userSettings)
            });

            if (profileResponse.ok && settingsResponse.ok) {
                this.showNotification('Settings saved successfully', 'success');
                // Reload user info to reflect any changes immediately
                await this.loadCurrentUserInfo();
            } else {
                throw new Error('Failed to save settings');
            }
        } catch (error) {
            console.error('Error saving settings:', error);
            this.showNotification('Error saving settings', 'error');
        }
    }

    openSettingsModal() {
        // Load current settings into the modal
        this.populateSettingsModal();
        const modal = document.getElementById('settingsModal');
        modal.style.display = 'flex';

        // Add click outside to close functionality
        modal.onclick = (e) => {
            if (e.target === modal) {
                this.closeSettingsModal();
            }
        };
    }

    closeSettingsModal() {
        document.getElementById('settingsModal').style.display = 'none';
    }

    async populateSettingsModal() {
        // Load fresh settings data from server
        await this.loadSettings();
        const settings = this.state.userSettings;

        // Load and display current user info (updates the header display)
        await this.loadCurrentUserInfo();

        // Populate user profile form fields with the fresh settings data
        document.getElementById('firstName').value = settings.profile?.firstName || '';
        document.getElementById('lastName').value = settings.profile?.lastName || '';
        document.getElementById('email').value = settings.profile?.email || '';

        // Populate API keys
        document.getElementById('openaiApiKey').value = settings.apiKeys?.openai || '';
        document.getElementById('anthropicApiKey').value = settings.apiKeys?.anthropic || '';

        // Populate general settings
        document.getElementById('defaultModel').value = settings.defaultModel || 'gpt-4';
        document.getElementById('maxTokens').value = settings.maxTokens || 4000;
        document.getElementById('temperature').value = settings.temperature || 0.7;
        document.getElementById('temperatureValue').textContent = settings.temperature || 0.7;
    }

    async loadCurrentUserInfo() {
        try {
            const response = await fetch('/api/user/current');
            if (response.ok) {
                const userInfo = await response.json();

                // Update the current user display elements
                const usernameElement = document.getElementById('currentUsername');
                const emailElement = document.getElementById('currentUserEmail');

                if (usernameElement) {
                    usernameElement.textContent = userInfo.username || 'Unknown User';
                }
                if (emailElement) {
                    emailElement.textContent = userInfo.email || 'No email provided';
                }
            } else {
                console.error('Failed to load current user info');
            }
        } catch (error) {
            console.error('Error loading current user info:', error);
        }
    }

    async loadUserTheme() {
        try {
            const response = await fetch('/api/user/current');
            if (response.ok) {
                const userInfo = await response.json();

                // Update theme from user preferences
                if (userInfo.theme_preference) {
                    this.state.currentTheme = userInfo.theme_preference;
                    console.log(`Loaded user theme preference: ${userInfo.theme_preference}`);
                }
            } else {
                console.error('Failed to load user theme preference');
            }
        } catch (error) {
            console.error('Error loading user theme:', error);
        }
    }

    async handleLogout() {
        try {
            // Show confirmation dialog
            const confirmLogout = confirm('Are you sure you want to sign out?');
            if (!confirmLogout) {
                return;
            }

            // Close settings modal first
            this.closeSettingsModal();

            // Show loading state
            this.showNotification('Signing out...', 'info');

            // Call logout API
            const response = await fetch('/logout', {
                method: 'GET',
                credentials: 'same-origin'
            });

            if (response.ok) {
                // Theme preference stays with user account

                // Redirect to login page
                window.location.href = '/login';
            } else {
                throw new Error('Logout failed');
            }
        } catch (error) {
            console.error('Error during logout:', error);
            this.showNotification('Error signing out. Please try again.', 'error');
        }
    }

    collectSettingsFromModal() {
        // Collect user profile
        this.state.userSettings.profile = {
            firstName: document.getElementById('firstName').value.trim(),
            lastName: document.getElementById('lastName').value.trim(),
            email: document.getElementById('email').value.trim()
        };

        // Collect API keys
        this.state.userSettings.apiKeys = {
            openai: document.getElementById('openaiApiKey').value.trim(),
            anthropic: document.getElementById('anthropicApiKey').value.trim()
        };

        // Collect general settings
        this.state.userSettings.defaultModel = document.getElementById('defaultModel').value;
        this.state.userSettings.maxTokens = parseInt(document.getElementById('maxTokens').value) || 4000;
        this.state.userSettings.temperature = parseFloat(document.getElementById('temperature').value) || 0.7;
    }

    handleSaveSettings() {
        this.collectSettingsFromModal();
        this.saveSettings();
    }

    togglePasswordVisibility(inputId) {
        const input = document.getElementById(inputId);
        const isPassword = input.type === 'password';
        input.type = isPassword ? 'text' : 'password';

        // Update the eye icon (optional - we can add this later)
    }

    updateTemperatureDisplay() {
        const temperatureInput = document.getElementById('temperature');
        const temperatureValue = document.getElementById('temperatureValue');
        if (temperatureInput && temperatureValue) {
            temperatureValue.textContent = temperatureInput.value;
        }
    }

    // Enhanced file handling with progress
    async handleFileUploadWithProgress(files, collectionId) {
        const collection = this.state.collections.find(c => c.id === collectionId);
        if (!collection) return;

        const progressNotification = this.showProgressNotification(`Uploading ${files.length} file(s) to ${collection.name}...`);

        try {
            let successCount = 0;
            const errors = [];
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const formData = new FormData();
                formData.append('file', file);

                try {
                    const response = await fetch(`/api/collections/${collectionId}/upload`, {
                        method: 'POST',
                        body: formData
                    });

                    // Check if response is ok
                    if (!response.ok) {
                        // Read response as text first to avoid "body locked" error
                        const text = await response.text();
                        let errorMsg;
                        try {
                            const result = JSON.parse(text);
                            errorMsg = result.error || `Server error (${response.status})`;
                        } catch {
                            // Response is not JSON, use text directly
                            errorMsg = text || `Server error (${response.status})`;
                        }
                        errors.push(`${file.name}: ${errorMsg}`);
                        console.error(`Error uploading ${file.name}:`, errorMsg);
                    } else {
                        const result = await response.json();
                        if (!result.error) {
                            successCount++;
                            // Check for partial errors (some files succeeded, some failed)
                            if (result.errors && result.errors.length > 0) {
                                errors.push(...result.errors);
                            }
                        } else {
                            errors.push(`${file.name}: ${result.error}`);
                            console.error(`Error uploading ${file.name}:`, result.error);
                        }
                    }

                    // Update progress
                    const progress = ((i + 1) / files.length) * 100;
                    this.updateProgressNotification(progressNotification, progress, `Processing ${file.name}...`);
                } catch (error) {
                    errors.push(`${file.name}: ${error.message}`);
                    console.error(`Error uploading ${file.name}:`, error);
                }
            }

            this.closeProgressNotification(progressNotification);

            if (successCount > 0) {
                // Clear cached files for this collection to force refresh
                delete this.state.collectionFiles[collectionId];

                await this.loadCollections();
                this.renderCollections();
                this.updateSelectors();
                const successMsg = `Successfully uploaded ${successCount} file(s) to ${collection.name}`;
                if (errors.length > 0) {
                    const errorDetails = `\n\nWarning - Some files failed:\n${errors.join('\n')}`;
                    this.showNotification(successMsg + errorDetails, 'warning');
                } else {
                    this.showNotification(successMsg, 'success');
                }
            } else {
                const errorDetails = errors.length > 0 ? `\n${errors.join('\n')}` : '';
                this.showNotification(`No files were uploaded successfully${errorDetails}`, 'error');
            }
        } catch (error) {
            this.closeProgressNotification(progressNotification);
            console.error('Error uploading files:', error);
            this.showNotification(`Error uploading files: ${error.message}`, 'error');
        }
    }

    showProgressNotification(message) {
        const notification = document.createElement('div');
        notification.className = 'notification info';
        notification.innerHTML = `
            <div class="flex items-center space-x-3">
                <div class="progress-spinner"></div>
                <div>
                    <div class="font-medium">${message}</div>
                    <div class="progress-bar mt-1">
                        <div class="progress-fill" style="width: 0%"></div>
                    </div>
                    <div class="text-xs mt-1 progress-text">Starting...</div>
                </div>
            </div>
        `;

        document.body.appendChild(notification);
        return notification;
    }

    updateProgressNotification(notification, progress, text) {
        const progressFill = notification.querySelector('.progress-fill');
        const progressText = notification.querySelector('.progress-text');

        if (progressFill) {
            progressFill.style.width = progress + '%';
        }
        if (progressText) {
            progressText.textContent = text;
        }
    }

    async uploadFilesWithStreaming(collectionId, files) {
        const collection = this.state.collections.find(c => c.id === collectionId);
        if (!collection) return;

        const progressNotification = this.showProgressNotification(`Uploading ${files.length} file(s) to ${collection.name}...`);

        try {
            const formData = new FormData();
            files.forEach((file, index) => {
                formData.append('file', file);
            });

            const response = await fetch(`/api/collections/${collectionId}/upload-stream`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let successCount = 0;
            const errors = [];
            const stepMessages = {
                'start': 'Starting upload',
                'extracting': 'Extracting text',
                'summarizing': 'Generating summary',
                'embedding': 'Creating embeddings',
                'indexing': 'Indexing documents',
                'complete': 'Complete',
                'error': 'Error'
            };

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep incomplete line in buffer

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));

                            if (data.error) {
                                errors.push(data.error);
                                continue;
                            }

                            if (data.success) {
                                successCount = data.processed_documents;
                                if (data.errors) {
                                    errors.push(...data.errors);
                                }
                                continue;
                            }

                            if (data.step && data.file) {
                                const stepMsg = stepMessages[data.step] || data.step;
                                const fileName = data.file.length > 30
                                    ? data.file.substring(0, 30) + '...'
                                    : data.file;

                                this.updateProgressNotification(
                                    progressNotification,
                                    data.progress || 0,
                                    `${stepMsg}: ${fileName}`
                                );

                                if (data.step === 'complete') {
                                    successCount++;
                                } else if (data.step === 'error' && data.error) {
                                    errors.push(`${data.file}: ${data.error}`);
                                }
                            }
                        } catch (e) {
                            console.error('Error parsing SSE data:', e);
                        }
                    }
                }
            }

            this.closeProgressNotification(progressNotification);

            // Clear cached files and refresh
            if (successCount > 0) {
                delete this.state.collectionFiles[collectionId];
                await this.loadCollections();
                this.renderCollections();
                this.updateSelectors();

                const successMsg = `Successfully uploaded ${successCount} file(s) to ${collection.name}`;
                if (errors.length > 0) {
                    const errorDetails = `\n\nWarning - Some files failed:\n${errors.join('\n')}`;
                    this.showNotification(successMsg + errorDetails, 'warning');
                } else {
                    this.showNotification(successMsg, 'success');
                }
            } else {
                const errorDetails = errors.length > 0 ? `\n${errors.join('\n')}` : '';
                this.showNotification(`No files were uploaded successfully${errorDetails}`, 'error');
            }

        } catch (error) {
            this.closeProgressNotification(progressNotification);
            console.error('Error uploading files:', error);
            this.showNotification(`Error uploading files: ${error.message}`, 'error');
        }
    }

    closeProgressNotification(notification) {
        if (notification && notification.parentElement) {
            setTimeout(() => {
                notification.remove();
            }, 2000);
        }
    }

    // Utility Functions
    getFileIcon(fileType) {
        const iconMap = {
            'pdf': '📄', 'doc': '📝', 'docx': '📝', 'txt': '📄', 'md': '📄',
            'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️',
            'mp4': '🎬', 'avi': '🎬', 'mov': '🎬',
            'mp3': '🎵', 'wav': '🎵',
            'zip': '📦', 'rar': '📦',
            'csv': '📊', 'xlsx': '📊',
            'py': '🐍', 'js': '📜', 'html': '🌐', 'css': '🎨'
        };
        return iconMap[fileType?.toLowerCase()] || '📄';
    }

    getFileExtension(filename) {
        return filename.split('.').pop()?.toLowerCase() || '';
    }

    // View Document Function
    viewDocument(documentId, filename, downloadUrl) {
        try {
            // Determine the file type
            const extension = this.getFileExtension(filename).toLowerCase();
            const isPDF = extension === 'pdf';

            // Build the URL
            let viewUrl;

            if (isPDF) {
                // For PDFs, use the document viewer with the document ID
                viewUrl = `/document-viewer?id=${documentId}`;
            } else if (downloadUrl) {
                // For other files, open directly via the download URL
                viewUrl = downloadUrl;
            } else {
                // Fallback: try to construct download URL from document ID
                this.showNotification('Unable to open document: URL not available', 'error');
                return;
            }

            // Open in new window
            const width = 1000;
            const height = 800;
            const left = (screen.width - width) / 2;
            const top = (screen.height - height) / 2;

            window.open(
                viewUrl,
                '_blank',
                `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes,toolbar=no,menubar=no,location=no,status=yes`
            );

            console.log(`Opening document: ${filename} at ${viewUrl}`);
        } catch (error) {
            console.error('Error opening document:', error);
            this.showNotification('Error opening document', 'error');
        }
    }

    // Collections Refresh Function
    async refreshCollectionsList() {
        try {
            this.showNotification('Refreshing collections...', 'info');
            await this.loadCollections();
            this.renderCollections();
            this.updateSelectors();
            this.showNotification('Collections refreshed successfully!', 'success');
        } catch (error) {
            console.error('Error refreshing collections:', error);
            this.showNotification('Error refreshing collections', 'error');
        }
    }

    // PubMed Search Modal Functions
    openPubmedSearchModal() {
        const modal = document.getElementById('pubmedSearchModal');
        if (modal) {
            modal.style.display = 'flex';
            // Add click outside to close
            modal.onclick = (e) => {
                if (e.target === modal) {
                    this.closePubmedSearchModal();
                }
            };
        }
    }

    closePubmedSearchModal() {
        const modal = document.getElementById('pubmedSearchModal');
        if (modal) {
            modal.style.display = 'none';
            // Clear form
            document.getElementById('pubmedQuery').value = '';
            document.getElementById('pubmedCollectionName').value = '';
            document.getElementById('pubmedMaxResults').value = '10';
        }
    }

    async submitPubmedSearch() {
        const query = document.getElementById('pubmedQuery').value.trim();
        const collectionName = document.getElementById('pubmedCollectionName').value.trim();
        const maxResults = parseInt(document.getElementById('pubmedMaxResults').value) || 10;

        if (!query) {
            this.showNotification('Please enter a search query', 'error');
            return;
        }

        // Close modal
        this.closePubmedSearchModal();

        // Build message to send to agent
        let message = `Search PubMed for "${query}" with max_results ${maxResults}`;
        if (collectionName) {
            message += ` and save to collection named "${collectionName}"`;
        }

        // Add to chat as user message
        const userMessage = { role: 'user', text: message };
        this.state.chatMessages.push(userMessage);
        this.renderChatMessages();

        // Show loading overlay
        this.showLoadingOverlay(
            'Searching PubMed...',
            'Searching for research papers and downloading PDFs',
            'This may take 1-2 minutes depending on the number of papers'
        );

        try {
            // Send message to agent
            const response = await this.sendChatMessage(
                message,
                this.state.currentConversationId,
                this.state.activeCollectionId,
                this.state.selectedAgentId
            );

            this.hideLoadingOverlay();

            // Update conversation ID
            if (response.conversation_id) {
                this.state.currentConversationId = response.conversation_id;
                await this.loadConversations();
            }

            // Add agent response
            const assistantMessage = {
                role: 'assistant',
                text: response.response || 'PubMed search completed.',
                cites: response.citations || [],
                documentReferences: response.document_references || []
            };
            this.state.chatMessages.push(assistantMessage);
            this.renderChatMessages();

            // Reload collections to show the new one
            // Add small delay to ensure backend DB operations complete
            this.showNotification('Refreshing collection list...', 'info');
            setTimeout(async () => {
                await this.loadCollections();
                this.renderCollections();
                this.updateSelectors();
                this.showNotification('Collection list updated! Check the collections tab.', 'success');
            }, 1000);

        } catch (error) {
            this.hideLoadingOverlay();
            console.error('Error in PubMed search:', error);
            this.showNotification(`Error: ${error.message}`, 'error');

            const errorMessage = {
                role: 'assistant',
                text: 'Sorry, there was an error with the PubMed search. Please try again.',
                cites: []
            };
            this.state.chatMessages.push(errorMessage);
            this.renderChatMessages();
        }
    }

    // arXiv Search Modal Functions
    openArxivSearchModal() {
        const modal = document.getElementById('arxivSearchModal');
        if (modal) {
            modal.style.display = 'flex';
            // Add click outside to close
            modal.onclick = (e) => {
                if (e.target === modal) {
                    this.closeArxivSearchModal();
                }
            };
        }
    }

    closeArxivSearchModal() {
        const modal = document.getElementById('arxivSearchModal');
        if (modal) {
            modal.style.display = 'none';
            // Clear form
            document.getElementById('arxivQuery').value = '';
            document.getElementById('arxivCollectionName').value = '';
            document.getElementById('arxivMaxResults').value = '10';
            document.getElementById('arxivSortBy').value = 'relevance';
        }
    }

    async submitArxivSearch() {
        const query = document.getElementById('arxivQuery').value.trim();
        const collectionName = document.getElementById('arxivCollectionName').value.trim();
        const maxResults = parseInt(document.getElementById('arxivMaxResults').value) || 10;
        const sortBy = document.getElementById('arxivSortBy').value;

        if (!query) {
            this.showNotification('Please enter a search query', 'error');
            return;
        }

        // Close modal
        this.closeArxivSearchModal();

        // Build message to send to agent
        let message = `Search arXiv for "${query}" with max_results ${maxResults} and sort_by ${sortBy}`;
        if (collectionName) {
            message += ` and save to collection named "${collectionName}"`;
        }

        // Add to chat as user message
        const userMessage = { role: 'user', text: message };
        this.state.chatMessages.push(userMessage);
        this.renderChatMessages();

        // Show loading overlay
        this.showLoadingOverlay(
            'Searching arXiv...',
            'Searching for preprints and downloading PDFs',
            'This may take 1-2 minutes depending on the number of papers'
        );

        try {
            // Send message to agent
            const response = await this.sendChatMessage(
                message,
                this.state.currentConversationId,
                this.state.activeCollectionId,
                this.state.selectedAgentId
            );

            this.hideLoadingOverlay();

            // Update conversation ID
            if (response.conversation_id) {
                this.state.currentConversationId = response.conversation_id;
                await this.loadConversations();
            }

            // Add agent response
            const assistantMessage = {
                role: 'assistant',
                text: response.response || 'arXiv search completed.',
                cites: response.citations || [],
                documentReferences: response.document_references || []
            };
            this.state.chatMessages.push(assistantMessage);
            this.renderChatMessages();

            // Reload collections to show the new one
            // Add small delay to ensure backend DB operations complete
            this.showNotification('Refreshing collection list...', 'info');
            setTimeout(async () => {
                await this.loadCollections();
                this.renderCollections();
                this.updateSelectors();
                this.showNotification('Collection list updated! Check the collections tab.', 'success');
            }, 1000);

        } catch (error) {
            this.hideLoadingOverlay();
            console.error('Error in arXiv search:', error);
            this.showNotification(`Error: ${error.message}`, 'error');

            const errorMessage = {
                role: 'assistant',
                text: 'Sorry, there was an error with the arXiv search. Please try again.',
                cites: []
            };
            this.state.chatMessages.push(errorMessage);
            this.renderChatMessages();
        }
    }

    // LII Search Modal Functions
    openLIISearchModal() {
        const modal = document.getElementById('liiSearchModal');
        if (modal) {
            modal.style.display = 'flex';
            // Add click outside to close
            modal.onclick = (e) => {
                if (e.target === modal) {
                    this.closeLIISearchModal();
                }
            };
        }
    }

    closeLIISearchModal() {
        const modal = document.getElementById('liiSearchModal');
        if (modal) {
            modal.style.display = 'none';
            // Clear form
            document.getElementById('liiQuery').value = '';
            document.getElementById('liiCollectionName').value = '';
            document.getElementById('liiMaxResults').value = '5';
        }
    }

    async submitLIISearch() {
        const query = document.getElementById('liiQuery').value.trim();
        const collectionName = document.getElementById('liiCollectionName').value.trim();
        const maxResults = parseInt(document.getElementById('liiMaxResults').value) || 5;

        if (!query) {
            this.showNotification('Please enter a search query', 'error');
            return;
        }

        // Close modal
        this.closeLIISearchModal();

        // Build message to send to agent
        let message = `Search LII for "${query}" with max_results ${maxResults}`;
        if (collectionName) {
            message += ` and save to collection named "${collectionName}"`;
        }

        // Add to chat as user message
        const userMessage = { role: 'user', text: message };
        this.state.chatMessages.push(userMessage);
        this.renderChatMessages();

        // Show loading overlay
        this.showLoadingOverlay(
            'Searching LII...',
            'Searching Legal Information Institute for legal resources',
            'This may take 1-2 minutes'
        );

        try {
            // Send message to agent
            const response = await this.sendChatMessage(
                message,
                this.state.currentConversationId,
                this.state.activeCollectionId,
                this.state.selectedAgentId
            );

            this.hideLoadingOverlay();

            // Update conversation ID
            if (response.conversation_id) {
                this.state.currentConversationId = response.conversation_id;
                await this.loadConversations();
            }

            // Add agent response
            const assistantMessage = {
                role: 'assistant',
                text: response.response || 'LII search completed.',
                cites: response.citations || [],
                documentReferences: response.document_references || []
            };
            this.state.chatMessages.push(assistantMessage);
            this.renderChatMessages();

            // Reload collections to show the new one
            this.showNotification('Refreshing collection list...', 'info');
            setTimeout(async () => {
                await this.loadCollections();
                this.renderCollections();
                this.updateSelectors();
                this.showNotification('Collection list updated! Check the collections tab.', 'success');
            }, 1000);

        } catch (error) {
            this.hideLoadingOverlay();
            console.error('Error in LII search:', error);
            this.showNotification(`Error: ${error.message}`, 'error');

            const errorMessage = {
                role: 'assistant',
                text: 'Sorry, there was an error with the LII search. Please try again.',
                cites: []
            };
            this.state.chatMessages.push(errorMessage);
            this.renderChatMessages();
        }
    }

    // DOAJ Search Modal Functions
    openDOAJSearchModal() {
        const modal = document.getElementById('doajSearchModal');
        if (modal) {
            modal.style.display = 'flex';
            // Add click outside to close
            modal.onclick = (e) => {
                if (e.target === modal) {
                    this.closeDOAJSearchModal();
                }
            };
        }
    }

    closeDOAJSearchModal() {
        const modal = document.getElementById('doajSearchModal');
        if (modal) {
            modal.style.display = 'none';
            // Clear form
            document.getElementById('doajQuery').value = '';
            document.getElementById('doajCollectionName').value = '';
            document.getElementById('doajSearchType').value = 'articles';
            document.getElementById('doajMaxResults').value = '10';
        }
    }

    async submitDOAJSearch() {
        const query = document.getElementById('doajQuery').value.trim();
        const collectionName = document.getElementById('doajCollectionName').value.trim();
        const searchType = document.getElementById('doajSearchType').value;
        const maxResults = parseInt(document.getElementById('doajMaxResults').value) || 10;

        if (!query) {
            this.showNotification('Please enter a search query', 'error');
            return;
        }

        // Close modal
        this.closeDOAJSearchModal();

        // Build message to send to agent
        let message = `Search DOAJ for "${query}" with search_type ${searchType} and max_results ${maxResults}`;
        if (collectionName) {
            message += ` and save to collection named "${collectionName}"`;
        }

        // Add to chat as user message
        const userMessage = { role: 'user', text: message };
        this.state.chatMessages.push(userMessage);
        this.renderChatMessages();

        // Show loading overlay
        this.showLoadingOverlay(
            'Searching DOAJ...',
            `Searching Directory of Open Access Journals for ${searchType}`,
            'This may take 1-2 minutes'
        );

        try {
            // Send message to agent
            const response = await this.sendChatMessage(
                message,
                this.state.currentConversationId,
                this.state.activeCollectionId,
                this.state.selectedAgentId
            );

            this.hideLoadingOverlay();

            // Update conversation ID
            if (response.conversation_id) {
                this.state.currentConversationId = response.conversation_id;
                await this.loadConversations();
            }

            // Add agent response
            const assistantMessage = {
                role: 'assistant',
                text: response.response || 'DOAJ search completed.',
                cites: response.citations || [],
                documentReferences: response.document_references || []
            };
            this.state.chatMessages.push(assistantMessage);
            this.renderChatMessages();

            // Reload collections to show the new one
            this.showNotification('Refreshing collection list...', 'info');
            setTimeout(async () => {
                await this.loadCollections();
                this.renderCollections();
                this.updateSelectors();
                this.showNotification('Collection list updated! Check the collections tab.', 'success');
            }, 1000);

        } catch (error) {
            this.hideLoadingOverlay();
            console.error('Error in DOAJ search:', error);
            this.showNotification(`Error: ${error.message}`, 'error');

            const errorMessage = {
                role: 'assistant',
                text: 'Sorry, there was an error with the DOAJ search. Please try again.',
                cites: []
            };
            this.state.chatMessages.push(errorMessage);
            this.renderChatMessages();
        }
    }

    // Event Listeners
    setupEventListeners() {
        // Message input enter key
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.handleSendMessage();
                }
            });
        }

        // Auto-resize message input
        if (messageInput) {
            messageInput.addEventListener('input', function() {
                this.style.height = 'auto';
                this.style.height = Math.min(this.scrollHeight, 120) + 'px';
            });
        }

        // Collection selector changes
        const activeCollectionSelector = document.getElementById('activeCollectionSelector');
        if (activeCollectionSelector) {
            activeCollectionSelector.addEventListener('change', (e) => {
                this.setActiveCollection(parseInt(e.target.value) || null);
            });
        }

        // Agent selector changes
        const agentSelector = document.getElementById('agentSelector');
        if (agentSelector) {
            agentSelector.addEventListener('change', (e) => {
                this.state.selectedAgentId = e.target.value || null;
            });
        }

        // LLM selector changes
        const llmSelector = document.getElementById('llmSelector');
        if (llmSelector) {
            llmSelector.addEventListener('change', (e) => {
                this.state.selectedLLMId = e.target.value || null;
            });
        }

        // Settings modal temperature slider
        document.addEventListener('input', (e) => {
            if (e.target.id === 'temperature') {
                this.updateTemperatureDisplay();
            }
        });
    }

    setupDragAndDrop() {
        const body = document.body;

        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            body.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            }, false);
        });

        body.addEventListener('drop', async (e) => {
            const files = Array.from(e.dataTransfer.files);
            if (files.length === 0) return;

            // Check if dropped on a specific collection
            const collectionItem = e.target.closest('.collection-item');
            let targetCollectionId = null;

            if (collectionItem) {
                targetCollectionId = parseInt(collectionItem.getAttribute('data-collection-id'));
            }

            // Use target collection, or active collection, or prepare for new collection
            if (targetCollectionId) {
                await this.handleFileUpload(files, targetCollectionId);
            } else if (this.state.activeCollectionId) {
                await this.handleFileUpload(files, this.state.activeCollectionId);
            } else {
                // Otherwise, prepare for new collection
                this.state.pendingFiles = files;
                this.updateNewCollectionUploadArea(files);
                this.showNotification(`${files.length} file(s) ready. Create a collection to upload them.`, 'info');
                this.setActiveTab('collections');
            }
        }, false);
    }

    // Orb-based UI Management
    toggleOrbExpansion() {
        const orbContainer = document.getElementById('orbContainer');
        const isExpanded = orbContainer.classList.contains('orb-expanded');

        if (isExpanded) {
            orbContainer.classList.remove('orb-expanded');
            orbContainer.classList.add('orb-collapsed');
        } else {
            orbContainer.classList.add('orb-expanded');
            orbContainer.classList.remove('orb-collapsed');
        }
    }

    togglePanel(panelName, event) {
        if (event) {
            event.stopPropagation();
        }

        const panelId = `${panelName}Panel`;
        const panel = document.getElementById(panelId);
        const allPanels = ['docsPanel', 'collectionsPanel', 'voicePanel', 'meetingPanel', 'settingsPanel'];
        const allButtons = ['docsBtn', 'collectionsBtn', 'voiceBtn', 'meetingBtn', 'settingsBtn'];

        // Close all other panels
        allPanels.forEach(id => {
            if (id !== panelId) {
                document.getElementById(id).style.display = 'none';
            }
        });

        // Remove active class from all buttons
        allButtons.forEach(id => {
            document.getElementById(id)?.classList.remove('active');
        });

        // Toggle the selected panel
        if (panel.style.display === 'none' || !panel.style.display) {
            panel.style.display = 'block';
            document.getElementById(`${panelName}Btn`)?.classList.add('active');

            // If opening docs or collections panel, load their data
            if (panelName === 'docs') {
                // Chat is already initialized, just ensure collections are loaded in dropdown
                this.updateSelectors();
            } else if (panelName === 'collections') {
                this.loadCollections();
                this.renderCollections();
            } else if (panelName === 'settings') {
                // Load settings when opening settings panel
                this.loadSettingsPanel();
            }
        } else {
            panel.style.display = 'none';
            document.getElementById(`${panelName}Btn`)?.classList.remove('active');
        }
    }

    toggleDropdown(dropdownName) {
        const dropdownId = `${dropdownName}Dropdown`;
        const dropdown = document.getElementById(dropdownId);
        const allDropdowns = ['historyDropdown', 'collectionsDropdown', 'agentDropdown', 'llmDropdown'];

        // Close all other dropdowns
        allDropdowns.forEach(id => {
            if (id !== dropdownId) {
                const elem = document.getElementById(id);
                if (elem) elem.style.display = 'none';
            }
        });

        // Toggle the selected dropdown
        if (dropdown) {
            const isOpening = dropdown.style.display === 'none' || !dropdown.style.display;
            dropdown.style.display = isOpening ? 'block' : 'none';

            // Load data when opening dropdowns
            if (isOpening) {
                if (dropdownName === 'history') {
                    this.loadConversations().then(() => {
                        this.renderConversationHistory();
                    });
                } else if (dropdownName === 'collections') {
                    this.updateActiveCollectionSelector();
                } else if (dropdownName === 'agent') {
                    this.updateAgentSelector();
                } else if (dropdownName === 'llm') {
                    this.updateLLMSelector();
                }
            }
        }
    }

    handleCollectionChange(collectionId) {
        const value = collectionId || null;
        this.state.activeCollectionId = value ? parseInt(value) : null;

        // Update the displayed text
        const selectedText = document.getElementById('selectedCollectionText');
        if (selectedText) {
            if (this.state.activeCollectionId) {
                const collection = this.state.collections.find(c => c.id === this.state.activeCollectionId);
                selectedText.textContent = collection ? collection.name : 'All Collections';
            } else {
                selectedText.textContent = 'All Collections';
            }
        }

        // Close the dropdown
        const dropdown = document.getElementById('collectionsDropdown');
        if (dropdown) dropdown.style.display = 'none';

        // Re-render to update active state
        this.updateActiveCollectionSelector();

        this.showNotification(
            this.state.activeCollectionId
                ? `Collection "${this.state.collections.find(c => c.id === this.state.activeCollectionId)?.name}" activated`
                : 'All collections selected',
            'info'
        );
    }

    handleLLMChange(llmId) {
        this.state.selectedLLMId = llmId || null;

        // Update the displayed text
        const selectedText = document.getElementById('selectedLLMText');
        if (selectedText) {
            if (this.state.selectedLLMId && this.state.availableLLMs[this.state.selectedLLMId]) {
                const llm = this.state.availableLLMs[this.state.selectedLLMId];
                selectedText.textContent = llm.display_name || this.state.selectedLLMId;
            } else {
                selectedText.textContent = 'AI Model';
            }
        }

        // Close the dropdown
        const dropdown = document.getElementById('llmDropdown');
        if (dropdown) dropdown.style.display = 'none';

        // Re-render to update active state
        this.updateLLMSelector();

        this.showNotification(
            this.state.selectedLLMId
                ? `AI Model "${this.state.availableLLMs[this.state.selectedLLMId]?.display_name || this.state.selectedLLMId}" selected`
                : 'Default AI Model selected',
            'info'
        );
    }

    handleAgentChange(agentId) {
        this.state.selectedAgentId = agentId || null;

        // Update the displayed text
        const selectedText = document.getElementById('selectedAgentText');
        if (selectedText) {
            if (this.state.selectedAgentId) {
                const agent = this.state.availableAgents.find(a => a.name === this.state.selectedAgentId);
                selectedText.textContent = agent ? (agent.display_name || agent.name) : 'Agent';
            } else {
                selectedText.textContent = 'Agent';
            }
        }

        // Close the dropdown
        const dropdown = document.getElementById('agentDropdown');
        if (dropdown) dropdown.style.display = 'none';

        // Re-render to update active state
        this.updateAgentSelector();

        this.showNotification(
            this.state.selectedAgentId
                ? `Agent "${this.state.availableAgents.find(a => a.name === this.state.selectedAgentId)?.display_name || this.state.selectedAgentId}" selected`
                : 'Default Agent selected',
            'info'
        );
    }

    toggleDocsExpand() {
        this.state.isDocsExpanded = !this.state.isDocsExpanded;
        const panel = document.getElementById('docsPanel');
        const expandBtn = document.getElementById('docsExpandBtn');

        if (!panel) return;

        if (this.state.isDocsExpanded) {
            // Expanded state
            panel.style.bottom = '110px';
            panel.style.left = '110px';
            panel.style.right = '4%';
            panel.style.width = 'auto';
            panel.style.height = 'calc(100vh - 240px)';
            panel.style.minHeight = 'calc(100vh - 240px)';

            // Update button icon to collapse icon
            if (expandBtn) {
                expandBtn.innerHTML = `
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25" />
                    </svg>
                `;
                expandBtn.title = 'Collapse';
            }
        } else {
            // Collapsed state
            panel.style.bottom = '110px';
            panel.style.left = '110px';
            panel.style.right = 'auto';
            panel.style.width = '580px';
            panel.style.height = 'auto';
            panel.style.minHeight = '520px';

            // Update button icon to expand icon
            if (expandBtn) {
                expandBtn.innerHTML = `
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                    </svg>
                `;
                expandBtn.title = 'Expand';
            }
        }
    }

    toggleCollectionsExpand() {
        this.state.isCollectionsExpanded = !this.state.isCollectionsExpanded;
        const panel = document.getElementById('collectionsPanel');
        const expandBtn = document.getElementById('collectionsExpandBtn');

        if (!panel) return;

        if (this.state.isCollectionsExpanded) {
            // Expanded state
            panel.style.bottom = '110px';
            panel.style.left = '110px';
            panel.style.right = '4%';
            panel.style.width = 'auto';
            panel.style.height = 'calc(100vh - 240px)';
            panel.style.maxHeight = 'calc(100vh - 240px)';

            // Update button icon to collapse icon
            if (expandBtn) {
                expandBtn.innerHTML = `
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M9 15v4.5M9 15H4.5M9 15l-5.25 5.25M15 9h4.5M15 9V4.5M15 9l5.25-5.25M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25" />
                    </svg>
                `;
                expandBtn.title = 'Collapse';
            }
        } else {
            // Collapsed state
            panel.style.bottom = '110px';
            panel.style.left = '110px';
            panel.style.right = 'auto';
            panel.style.width = '400px';
            panel.style.height = 'auto';
            panel.style.maxHeight = 'calc(100vh - 240px)';

            // Update button icon to expand icon
            if (expandBtn) {
                expandBtn.innerHTML = `
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
                    </svg>
                `;
                expandBtn.title = 'Expand';
            }
        }
    }
}

// Initialize app when DOM is ready
let app;
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        app = new OrvinApp();
    });
} else {
    app = new OrvinApp();
}

// Global functions for HTML onclick handlers
window.app = app;
window.toggleTheme = () => app.toggleTheme();
window.setActiveTab = (tab) => app.setActiveTab(tab);
window.handleCreateCollection = () => app.handleCreateCollection();
window.handleCreateCollectionClick = () => app.handleCreateCollectionClick();
window.handleSendMessage = () => app.handleSendMessage();
window.triggerFileUploadForNewCollection = () => app.triggerFileUploadForNewCollection();
window.toggleCollectionDetails = (id) => app.toggleCollectionDetails(id);
window.openSettingsModal = () => app.openSettingsModal();
window.closeSettingsModal = () => app.closeSettingsModal();
window.saveSettings = () => app.handleSaveSettings();
window.togglePasswordVisibility = (id) => app.togglePasswordVisibility(id);
window.handleLogout = () => app.handleLogout();
window.refreshLogs = () => app.refreshLogs();
window.openPubmedSearchModal = () => app.openPubmedSearchModal();
window.closePubmedSearchModal = () => app.closePubmedSearchModal();
window.submitPubmedSearch = () => app.submitPubmedSearch();
window.openArxivSearchModal = () => app.openArxivSearchModal();
window.closeArxivSearchModal = () => app.closeArxivSearchModal();
window.submitArxivSearch = () => app.submitArxivSearch();
window.openLIISearchModal = () => app.openLIISearchModal();
window.closeLIISearchModal = () => app.closeLIISearchModal();
window.submitLIISearch = () => app.submitLIISearch();
window.openDOAJSearchModal = () => app.openDOAJSearchModal();
window.closeDOAJSearchModal = () => app.closeDOAJSearchModal();
window.submitDOAJSearch = () => app.submitDOAJSearch();
window.refreshCollectionsList = () => app.refreshCollectionsList();
window.viewDocument = (docId, filename, url) => app.viewDocument(docId, filename, url);

// New orb-based UI functions
window.toggleOrbExpansion = () => app.toggleOrbExpansion();
window.togglePanel = (panelName, event) => app.togglePanel(panelName, event);
window.toggleDropdown = (dropdownName) => app.toggleDropdown(dropdownName);
window.handleCollectionChange = (collectionId) => app.handleCollectionChange(collectionId);
window.toggleDocsExpand = () => app.toggleDocsExpand();
window.toggleCollectionsExpand = () => app.toggleCollectionsExpand();
window.startNewConversation = () => app.startNewConversation();
window.handleLLMChange = (llmId) => app.handleLLMChange(llmId);
window.handleAgentChange = (agentId) => app.handleAgentChange(agentId);
window.saveSettings = () => app.saveSettings();
