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
        const lightIcon = document.getElementById('lightIcon');
        const darkIcon = document.getElementById('darkIcon');
        const themeText = document.getElementById('themeText');

        if (lightIcon && darkIcon && themeText) {
            if (this.state.currentTheme === 'dark') {
                // Show moon icon, hide sun icon
                lightIcon.classList.add('hidden');
                darkIcon.classList.remove('hidden');
                themeText.textContent = 'Dark';
            } else {
                // Show sun icon, hide moon icon
                lightIcon.classList.remove('hidden');
                darkIcon.classList.add('hidden');
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
        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch(`/api/collections/${collectionId}/upload`, {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                if (!result.error) successCount++;
            } catch (error) {
                console.error(`Error uploading ${file.name}:`, error);
            }
        }
        return successCount;
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
        notification.innerHTML = `
            <span>${message}</span>
            <button class="close-btn ml-2 text-white hover:text-gray-200" onclick="this.parentElement.remove()">&times;</button>
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
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
        const selector = document.getElementById('activeCollectionSelector');
        if (!selector) return;

        selector.innerHTML = '<option value="">None selected</option>' +
            this.state.collections.map(collection => {
                const docCount = collection.document_count || collection.docCount || 0;
                return `<option value="${collection.id}">${collection.name} (${docCount} documents)</option>`;
            }).join('');

        if (this.state.activeCollectionId) {
            selector.value = this.state.activeCollectionId;
        }
    }

    updateAgentSelector() {
        const selector = document.getElementById('agentSelector');
        if (!selector) return;

        selector.innerHTML = '<option value="">Default Agent</option>' +
            this.state.availableAgents.map(agent =>
                `<option value="${agent.name}">${agent.display_name || agent.name}</option>`
            ).join('');

        if (this.state.selectedAgentId) {
            selector.value = this.state.selectedAgentId;
        }
    }

    updateLLMSelector() {
        const selector = document.getElementById('llmSelector');
        if (!selector) return;

        selector.innerHTML = '<option value="">Default LLM</option>';

        Object.entries(this.state.availableLLMs).forEach(([configId, config]) => {
            const option = document.createElement('option');
            option.value = configId;
            option.textContent = config.display_name || configId;
            selector.appendChild(option);
        });

        if (this.state.selectedLLMId) {
            selector.value = this.state.selectedLLMId;
        }
    }


    renderCollections() {
        const container = document.getElementById('collectionsList');
        if (!container) return;

        if (this.state.collections.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-center py-8">No collections yet</p>';
            return;
        }

        container.innerHTML = this.state.collections.map(collection => {
            const docCount = collection.document_count || collection.docCount || 0;
            const updatedAt = collection.updated_at || collection.updatedAt || collection.created_at;
            const formattedDate = updatedAt ? new Date(updatedAt).toLocaleDateString() : 'Recently';
            const isExpanded = this.state.expandedCollections.has(collection.id);
            const files = this.state.collectionFiles[collection.id] || [];

            // Generate files list HTML
            const filesListHTML = isExpanded ? `
                <div class="mt-3 border-t border-gray-200 pt-3">
                    <div class="flex items-center justify-between mb-2">
                        <h5 class="text-sm font-medium text-gray-700">Files in this collection:</h5>
                        <div class="flex items-center space-x-2">
                            <span class="text-xs text-gray-500">${files.length} files</span>
                            <button
                                onclick="app.triggerFileUpload(${collection.id}); event.stopPropagation();"
                                class="px-2 py-1 bg-purple-600 text-white text-xs rounded hover:bg-purple-700 transition-colors"
                                title="Upload files to this collection"
                            >
                                + Upload
                            </button>
                        </div>
                    </div>
                    ${files.length === 0 ?
                        '<p class="text-xs text-gray-500 italic">No files uploaded yet</p>' :
                        `<div class="space-y-1 max-h-40 overflow-y-auto">
                            ${files.map(file => `
                                <div class="flex items-center justify-between py-1 px-2 bg-white rounded text-xs">
                                    <div class="flex items-center space-x-2">
                                        <span class="text-gray-600">${this.getFileIcon(this.getFileExtension(file.filename || file.name))}</span>
                                        <span class="text-gray-900 truncate max-w-32" title="${file.filename || file.name}">${file.filename || file.name}</span>
                                    </div>
                                    <span class="text-gray-500 font-mono">${this.formatFileSize(file.size || file.file_size || 0)}</span>
                                </div>
                            `).join('')}
                        </div>`
                    }
                </div>
            ` : '';

            return `
                <div class="collection-item bg-gray-50 rounded-lg p-4" data-collection-id="${collection.id}">
                    <div class="flex items-start justify-between mb-2">
                        <h4 class="font-medium text-gray-900 cursor-pointer hover:text-purple-600 flex items-center space-x-2" onclick="app.toggleCollectionDetails(${collection.id})">
                            <span>${collection.name}</span>
                            <svg class="w-4 h-4 transition-transform duration-200 ${isExpanded ? 'rotate-90' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                            </svg>
                        </h4>
                        <div class="flex items-center space-x-2">
                            <button
                                onclick="app.setActiveCollection(${collection.id})"
                                class="px-3 py-1 rounded text-sm transition-colors ${
                                    this.state.activeCollectionId === collection.id
                                        ? 'bg-purple-600 text-white'
                                        : 'bg-white text-gray-700 hover:bg-gray-100'
                                }"
                            >
                                ${this.state.activeCollectionId === collection.id ? 'Active' : 'Select'}
                            </button>
                            <button
                                onclick="app.deleteCollection(${collection.id})"
                                class="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                                title="Delete collection"
                            >
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </button>
                        </div>
                    </div>

                    <p class="text-sm text-gray-600 mb-3">
                        ${docCount} documents • Updated ${formattedDate}
                    </p>

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
        const collection = this.state.collections.find(c => c.id === collectionId);
        if (!collection) return;

        try {
            this.showNotification(`Uploading ${files.length} file(s) to ${collection.name}...`, 'info');

            const successCount = await this.uploadFilesToCollection(collectionId, files);

            if (successCount > 0) {
                // Clear cached files for this collection to force refresh
                delete this.state.collectionFiles[collectionId];

                await this.loadCollections();
                this.renderCollections();
                this.updateSelectors();
                this.showNotification(`Successfully uploaded ${successCount} file(s) to ${collection.name}`, 'success');
            } else {
                this.showNotification('No files were uploaded successfully', 'error');
            }
        } catch (error) {
            console.error('Error uploading files:', error);
            this.showNotification(`Error uploading files: ${error.message}`, 'error');
        }
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

    showUploadArea() {
        const uploadArea = document.getElementById('newCollectionUploadArea');
        if (uploadArea) {
            uploadArea.style.display = 'block';
        }
    }

    hideUploadArea() {
        const uploadArea = document.getElementById('newCollectionUploadArea');
        if (uploadArea) {
            uploadArea.style.display = 'none';
        }
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
            // If no name is provided, show the upload area to prompt user
            this.showUploadArea();
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
            await this.loadCollections();
            this.renderCollections();
            this.updateSelectors();

            this.showNotification(`Collection "${name}" created successfully!`, 'success');

            // Upload pending files if any
            if (this.state.pendingFiles && this.state.pendingFiles.length > 0) {
                const files = this.state.pendingFiles;
                this.showNotification(`Uploading ${files.length} file(s) to ${name}...`, 'info');

                try {
                    const successCount = await this.uploadFilesToCollection(newCollectionId, files);

                    if (successCount > 0) {
                        await this.loadCollections();
                        this.renderCollections();
                        this.updateSelectors();
                        this.showNotification(`Successfully uploaded ${successCount} file(s) to ${name}`, 'success');
                    } else {
                        this.showNotification('No files were uploaded successfully', 'error');
                    }
                } catch (uploadError) {
                    console.error('Error uploading files:', uploadError);
                    this.showNotification(`Error uploading files: ${uploadError.message}`, 'error');
                }

                this.state.pendingFiles = null;
                this.resetNewCollectionUploadArea();
            }

            // Hide upload area after successful creation
            this.hideUploadArea();
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
            container.innerHTML = '<p class="text-gray-500 text-center py-8">No conversations yet</p>';
            return;
        }

        container.innerHTML = this.state.conversations.map(conversation => {
            const preview = conversation.messages && conversation.messages.length > 0
                ? conversation.messages[0].content.substring(0, 100) + '...'
                : 'No messages';
            const messageCount = conversation.messages ? conversation.messages.length : 0;
            const formattedDate = new Date(conversation.created_at).toLocaleDateString();

            return `
                <div class="conversation-item bg-gray-50 rounded-lg p-4 hover-lift cursor-pointer">
                    <div class="flex items-start justify-between mb-2">
                        <h4 class="font-medium text-gray-900">
                            ${conversation.title || `Conversation ${conversation.id}`}
                        </h4>
                        <div class="flex items-center space-x-2">
                            <button
                                onclick="app.loadConversation(${conversation.id})"
                                class="px-3 py-1 bg-purple-600 text-white rounded text-xs hover:bg-purple-700 transition-colors"
                            >
                                Load
                            </button>
                            <button
                                onclick="app.deleteConversation(${conversation.id})"
                                class="p-1 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors"
                            >
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                            </button>
                        </div>
                    </div>
                    <p class="text-sm text-gray-600 mb-2">${preview}</p>
                    <div class="flex items-center justify-between text-xs text-gray-500">
                        <span>${messageCount} messages</span>
                        <span>${formattedDate}</span>
                    </div>
                </div>
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
            this.setActiveTab('collections'); // Switch back to main chat view
            this.showNotification(`Conversation loaded with ${this.state.chatMessages.length} messages`, 'success');
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
        this.setActiveTab('collections');
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

    async saveSettings() {
        try {
            const settings = this.state.userSettings;
            const response = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settings)
            });

            if (response.ok) {
                this.showNotification('Settings saved successfully', 'success');
                // Reload user info to reflect any changes immediately
                await this.loadCurrentUserInfo();
                this.closeSettingsModal();
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
            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const formData = new FormData();
                formData.append('file', file);

                try {
                    const response = await fetch(`/api/collections/${collectionId}/upload`, {
                        method: 'POST',
                        body: formData
                    });
                    const result = await response.json();
                    if (!result.error) successCount++;

                    // Update progress
                    const progress = ((i + 1) / files.length) * 100;
                    this.updateProgressNotification(progressNotification, progress, `Processing ${file.name}...`);
                } catch (error) {
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
                this.showNotification(`Successfully uploaded ${successCount} file(s) to ${collection.name}`, 'success');
            } else {
                this.showNotification('No files were uploaded successfully', 'error');
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
