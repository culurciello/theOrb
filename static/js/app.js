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
            activeTab: 'collections',
            currentTheme: localStorage.getItem('orb-theme') || 'light',
            validationFindings: [],
            selectedValidationCollection: null,
            draftText: '',
            pendingFiles: null
        };

        this.init();
    }

    async init() {
        try {
            // Initialize theme
            this.initializeTheme();

            // Load initial data
            await this.loadInitialData();

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

    toggleTheme() {
        const newTheme = this.state.currentTheme === 'dark' ? 'light' : 'dark';
        this.state.currentTheme = newTheme;
        localStorage.setItem('orb-theme', newTheme);
        document.documentElement.setAttribute('data-theme', newTheme);
        this.updateThemeToggle();
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
                this.loadConversations()
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
            this.updateValidationCollectionSelector();
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

            // If no conversations from API, add some mock data for demo
            if (conversations.length === 0) {
                this.addMockConversations();
            }

            return this.state.conversations;
        } catch (error) {
            console.error('Error loading conversations:', error);
            // Add mock conversations for demo when API is not available
            this.addMockConversations();
        }
    }

    // Add mock conversations for testing/demo
    addMockConversations() {
        this.state.conversations = [
            {
                id: 1,
                title: "Legal Document Analysis",
                created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(), // 2 days ago
                messages: [
                    { role: 'user', content: 'What are the key points in this legal document?' },
                    { role: 'assistant', content: 'Based on the documents in your collection, here are the key considerations...' }
                ]
            },
            {
                id: 2,
                title: "Contract Review Session",
                created_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(), // 5 days ago
                messages: [
                    { role: 'user', content: 'Can you review this contract for potential issues?' },
                    { role: 'assistant', content: 'I\'ve reviewed the contract and found several areas that need attention...' }
                ]
            },
            {
                id: 3,
                title: "Research Discussion",
                created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(), // 1 week ago
                messages: [
                    { role: 'user', content: 'Help me understand the methodology in this research paper' },
                    { role: 'assistant', content: 'The research methodology follows a comprehensive approach...' }
                ]
            }
        ];
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
        document.getElementById('collectionsTab').className =
            tabName === 'collections'
                ? 'px-6 py-3 text-sm font-medium text-purple-600 border-b-2 border-purple-600'
                : 'px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700';

        document.getElementById('validateTab').className =
            tabName === 'validate'
                ? 'px-6 py-3 text-sm font-medium text-purple-600 border-b-2 border-purple-600'
                : 'px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700';

        document.getElementById('historyTab').className =
            tabName === 'history'
                ? 'px-6 py-3 text-sm font-medium text-purple-600 border-b-2 border-purple-600'
                : 'px-6 py-3 text-sm font-medium text-gray-500 hover:text-gray-700';

        // Show/hide content
        document.getElementById('collectionsContent').style.display =
            tabName === 'collections' ? 'block' : 'none';
        document.getElementById('validateContent').style.display =
            tabName === 'validate' ? 'block' : 'none';
        document.getElementById('historyContent').style.display =
            tabName === 'history' ? 'block' : 'none';

        // Load content for history tab
        if (tabName === 'history') {
            this.renderConversationHistory();
        }
    }

    updateSelectors() {
        this.updateActiveCollectionSelector();
        this.updateAgentSelector();
        this.updateLLMSelector();
        this.updateValidationCollectionSelector();
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

    updateValidationCollectionSelector() {
        const selector = document.getElementById('validationCollectionSelector');
        if (!selector) return;

        selector.innerHTML = '<option value="">Choose a collection...</option>' +
            this.state.collections.map(collection =>
                `<option value="${collection.id}">${collection.name} (${collection.document_count || 0} documents)</option>`
            ).join('');
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

            return `
                <div class="collection-item bg-gray-50 rounded-lg p-4" data-collection-id="${collection.id}">
                    <div class="flex items-start justify-between mb-2">
                        <h4 class="font-medium text-gray-900">${collection.name}</h4>
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

                    <!-- Upload Area -->
                    <div onclick="app.triggerFileUpload(${collection.id})" class="upload-area border-2 border-dashed border-gray-300 rounded-lg p-4 text-center hover:border-purple-400 hover:bg-purple-50 transition-colors cursor-pointer">
                        <div class="flex flex-col items-center space-y-2">
                            <svg class="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                            </svg>
                            <p class="text-sm text-gray-500">
                                Drop files here or
                                <span class="text-purple-600 hover:underline">choose files</span>
                            </p>
                            <p class="text-xs text-gray-400">PDF, DOC, TXT, MD supported</p>
                        </div>
                    </div>
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

            return `
                <div class="message flex ${messageRole === 'user' ? 'justify-end' : 'justify-start'}">
                    <div class="max-w-3/4 p-3 rounded-lg ${
                        messageRole === 'user'
                            ? 'bg-purple-600 text-white'
                            : 'bg-gray-100 text-gray-800'
                    }">
                        <p class="text-sm">${messageText}</p>
                        ${messageCites && messageCites.length > 0 ? `
                            <div class="mt-2 flex flex-wrap gap-1">
                                ${messageCites.map(cite => `
                                    <span class="px-2 py-1 bg-white bg-opacity-20 rounded text-xs cursor-pointer hover:bg-opacity-30">
                                        [doc: ${cite}]
                                    </span>
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

            // Send message to API or use mock response
            const response = await this.sendChatMessage(
                messageText,
                null,
                this.state.activeCollectionId,
                this.state.selectedAgentId
            );

            // Add assistant response
            const assistantMessage = {
                role: 'assistant',
                text: response.response || this.mockAssistantReply(messageText, activeCollection),
                cites: response.citations || []
            };
            this.state.chatMessages.push(assistantMessage);
            this.renderChatMessages();
        } catch (error) {
            console.error('Error sending message:', error);

            // Add error message with mock response as fallback
            const activeCollection = this.state.collections.find(c => c.id === this.state.activeCollectionId);
            const errorMessage = {
                role: 'assistant',
                text: this.mockAssistantReply(messageText, activeCollection),
                cites: activeCollection ? [`${activeCollection.name}_document.pdf p.1`] : []
            };
            this.state.chatMessages.push(errorMessage);
            this.renderChatMessages();
        }
    }

    mockAssistantReply(userMsg, activeCollection) {
        const responses = [
            "Based on the documents in your collection, here are the key considerations:",
            "According to the legal precedents in your files, the standard approach is:",
            "The contracts documentation suggests that you should review:",
            "From the case law analysis, it appears that:"
        ];

        const baseReply = responses[Math.floor(Math.random() * responses.length)];
        return `${baseReply} This aligns with established practices and precedents.`;
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
        } catch (error) {
            console.error('Error creating collection:', error);
            this.showNotification(`Error creating collection: ${error.message}`, 'error');
        }
    }

    // Validation Functions
    handleValidate() {
        const draftText = document.getElementById('draftText').value.trim();
        const selectedCollectionId = document.getElementById('validationCollectionSelector').value;

        if (!draftText || !selectedCollectionId) {
            this.showNotification('Please enter text and select a collection', 'warning');
            return;
        }

        const validationCollection = this.state.collections.find(c => c.id == selectedCollectionId);
        const findings = this.mockValidate(draftText, validationCollection);
        this.state.validationFindings = findings;
        this.renderValidationResults();
    }

    mockValidate(text, activeCollection) {
        if (!text.trim() || !activeCollection) return [];

        const sentences = text.split('.').filter(s => s.trim().length > 10);
        if (sentences.length === 0) return [];

        const findings = [];
        const issueTypes = ['Needs Citation', 'Likely Misquote', 'Outdated Reference'];
        const selectedSentences = sentences.sort(() => 0.5 - Math.random()).slice(0, Math.min(3, sentences.length));

        selectedSentences.forEach((sentence, idx) => {
            const type = issueTypes[idx % issueTypes.length];
            const mockSources = [
                `Document_${Math.floor(Math.random() * 100)}.pdf`,
                `Reference_${Math.floor(Math.random() * 50)}.docx`
            ];

            findings.push({
                id: Date.now() + idx,
                type,
                excerpt: sentence.trim() + '.',
                suggestion: type === 'Likely Misquote' ? 'Consider revising this statement' : 'Add supporting documentation',
                sources: mockSources
            });
        });

        return findings;
    }

    renderValidationResults() {
        const resultsContainer = document.getElementById('validationResults');
        const findingsContainer = document.getElementById('validationFindings');

        if (this.state.validationFindings.length === 0) {
            resultsContainer.style.display = 'none';
            return;
        }

        resultsContainer.style.display = 'block';
        findingsContainer.innerHTML = this.state.validationFindings.map(finding => `
            <div class="border border-gray-200 rounded-lg p-4">
                <div class="flex items-start space-x-3 mb-3">
                    <span class="px-2 py-1 rounded text-xs font-medium ${
                        finding.type === 'Needs Citation' ? 'bg-blue-100 text-blue-800' :
                        finding.type === 'Likely Misquote' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                    }">
                        ${finding.type}
                    </span>
                </div>

                <p class="text-sm text-gray-900 bg-yellow-50 p-2 rounded mb-3">
                    "${finding.excerpt}"
                </p>

                <div class="space-y-2">
                    <div class="flex items-center space-x-2">
                        <select class="flex-1 text-sm border border-gray-300 rounded p-1">
                            ${finding.sources.map(source => `<option>${source}</option>`).join('')}
                        </select>
                        <button
                            onclick="app.insertCitation('${finding.id}', '${finding.sources[0]}')"
                            class="px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 transition-colors"
                        >
                            Insert citation
                        </button>
                    </div>

                    <button
                        onclick="app.fixSuggestion('${finding.id}')"
                        class="px-3 py-1 bg-purple-600 text-white rounded text-xs hover:bg-purple-700 transition-colors"
                    >
                        Fix suggestion
                    </button>
                </div>
            </div>
        `).join('');
    }

    insertCitation(findingId, source) {
        const page = Math.floor(Math.random() * 50) + 1;
        const citation = `[source: ${source} p.${page}]`;
        const draftTextArea = document.getElementById('draftText');
        draftTextArea.value += ' ' + citation;
        this.showNotification('Citation inserted', 'success');
    }

    fixSuggestion(findingId) {
        const finding = this.state.validationFindings.find(f => f.id == findingId);
        if (!finding) return;

        const fixes = {
            'Needs Citation': (text) => text.replace(/\.$/, ' (as established in legal precedent).'),
            'Likely Misquote': (text) => text.replace(/\b(always|never|all|none)\b/g, 'typically'),
            'Outdated Reference': (text) => text.replace(/\b\d{4}\b/, '2024')
        };

        const fixFunction = fixes[finding.type];
        if (fixFunction) {
            const draftTextArea = document.getElementById('draftText');
            const newExcerpt = fixFunction(finding.excerpt);
            draftTextArea.value = draftTextArea.value.replace(finding.excerpt, newExcerpt);
            this.showNotification('Suggestion applied', 'success');
        }
    }

    copyDraftText() {
        const draftText = document.getElementById('draftText').value;
        navigator.clipboard.writeText(draftText).then(() => {
            this.showNotification('Draft text copied to clipboard', 'success');
        });
    }

    copyCitations() {
        const draftText = document.getElementById('draftText').value;
        const citations = draftText.match(/\[source:[^\]]+\]/g) || [];
        navigator.clipboard.writeText(citations.join('\n')).then(() => {
            this.showNotification('Citations copied to clipboard', 'success');
        });
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

            console.log('Loaded conversation:', conversationId, 'with', this.state.chatMessages.length, 'messages');
            this.renderChatMessages();
            this.setActiveTab('collections'); // Switch back to main chat view
            this.showNotification(`Conversation loaded with ${this.state.chatMessages.length} messages`, 'success');
        } catch (error) {
            console.error('Error loading conversation:', error);
            this.showNotification(`Failed to load conversation: ${error.message}`, 'error');

            // For testing purposes, load some mock data if API fails
            this.loadMockConversation(conversationId);
        }
    }

    // Mock conversation for testing when API is not available
    loadMockConversation(conversationId) {
        this.state.chatMessages = [
            {
                role: 'user',
                text: 'What are the key points in this legal document?',
                timestamp: new Date().toISOString()
            },
            {
                role: 'assistant',
                text: 'Based on the documents in your collection, here are the key considerations: The contract outlines several important clauses regarding liability and termination procedures.',
                cites: [`Document_${conversationId}.pdf p.1`, `Legal_Brief_${conversationId}.docx p.3`],
                timestamp: new Date().toISOString()
            },
            {
                role: 'user',
                text: 'Can you elaborate on the liability clauses?',
                timestamp: new Date().toISOString()
            },
            {
                role: 'assistant',
                text: 'The liability clauses establish clear boundaries for responsibility distribution between parties. Section 4.2 specifically addresses limitation of damages and indemnification procedures.',
                cites: [`Document_${conversationId}.pdf p.4`],
                timestamp: new Date().toISOString()
            }
        ];
        this.renderChatMessages();
        this.showNotification(`Mock conversation ${conversationId} loaded for demo`, 'info');
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
        this.renderChatMessages();
        this.setActiveTab('collections');
        this.showNotification('New conversation started', 'success');
    }

    clearChatHistory() {
        if (!confirm('Are you sure you want to clear all chat history? This will only clear the current session, not saved conversations.')) {
            return;
        }

        this.state.chatMessages = [];
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

            // If we have an active collection, upload to it
            if (this.state.activeCollectionId) {
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
window.handleSendMessage = () => app.handleSendMessage();
window.triggerFileUploadForNewCollection = () => app.triggerFileUploadForNewCollection();
window.handleValidate = () => app.handleValidate();
window.copyDraftText = () => app.copyDraftText();
window.copyCitations = () => app.copyCitations();