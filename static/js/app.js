// Main Application - Refactored and Modular
// Import all modules
import { initializeState } from './state.js';
import { loadCollections, loadConversations, loadUserProfile, loadApiKeys, loadAvailableAgents, loadAvailableLLMs } from './api.js';
import { initializeTheme, showWelcomeMessage } from './ui.js';
import { setupEventListeners } from './events.js';
import { setupDropZone, addFilesToCollection } from './uploads.js';
import { updateCollectionSelector, updateAgentSelector, updateLLMSelector } from './selectors.js';

// Global functions that need to be accessible from HTML
// These will be attached to window object for backward compatibility
import { showPanel, collapseAll, showNotification, showSmartSuggestion, toggleTheme } from './ui.js';

import { showCreateCollection, backToCollectionsList, viewCollectionDetails, selectCollectionForChat, editCollection, removeCollection, removeDocumentFromCollection, viewDocument, selectFiles, selectFolder, removeFile, updateSelectedFilesDisplay, clearSelectedFiles } from './collections.js';

import { startNewConversation, openConversation, removeConversation, openChatAndSendMessage, sendMessage, showSaveToCollectionModal, closeSaveToCollectionModal, selectExistingCollection, selectNewCollection, performSaveChatToCollection as saveChatToCollection, openImageModal, closeImageModal, saveMessageToCollection, closeSaveMessageModal, performSaveMessage } from './chat.js';

import { switchSettingsTab, resetProfileForm, editApiKey, removeApiKey, refreshLLMSettings, testCurrentLLM, switchLLMConfig, handleThemeChange } from './settings.js';

import { executeAction } from './events.js';

// Application Initialization
class OrbApp {
    constructor() {
        this.initialized = false;
    }

    async init() {
        if (this.initialized) return;

        try {
            // Initialize state management
            initializeState();

            // Load initial data
            await this.loadInitialData();

            // Set up UI
            initializeTheme();
            setupEventListeners();
            setupDropZone();

            // Show welcome message
            showWelcomeMessage();

            // Expose global functions for HTML compatibility
            this.exposeGlobalFunctions();

            this.initialized = true;
            console.log('Orb application initialized successfully');

        } catch (error) {
            console.error('Error initializing application:', error);
            showNotification('Application initialization failed', 'error');
        }
    }

    async loadInitialData() {
        const loadPromises = [
            loadCollections().catch(e => console.warn('Failed to load collections:', e)),
            loadConversations().catch(e => console.warn('Failed to load conversations:', e)),
            loadUserProfile().catch(e => console.warn('Failed to load user profile:', e)),
            loadApiKeys().catch(e => console.warn('Failed to load API keys:', e)),
            loadAvailableAgents().catch(e => console.warn('Failed to load agents:', e)),
            loadAvailableLLMs().catch(e => console.warn('Failed to load LLMs:', e))
        ];

        await Promise.allSettled(loadPromises);
        
        // Update selectors after all data is loaded
        updateCollectionSelector();
        updateAgentSelector();
        updateLLMSelector();
    }

    exposeGlobalFunctions() {
        // UI Functions
        window.showPanel = showPanel;
        window.collapseAll = collapseAll;
        window.showNotification = showNotification;
        window.showSmartSuggestion = showSmartSuggestion;
        window.toggleTheme = toggleTheme;
        window.handleThemeChange = handleThemeChange;
        window.executeAction = executeAction;

        // Collections Functions
        window.showCreateCollection = showCreateCollection;
        window.backToCollectionsList = backToCollectionsList;
        window.viewCollectionDetails = viewCollectionDetails;
        window.selectCollectionForChat = selectCollectionForChat;
        window.editCollection = editCollection;
        window.deleteCollection = removeCollection;
        window.removeDocumentFromCollection = removeDocumentFromCollection;
        window.viewDocument = viewDocument;
        window.selectFiles = selectFiles;
        window.selectFolder = selectFolder;
        window.removeFile = removeFile;
        window.updateSelectedFilesDisplay = updateSelectedFilesDisplay;
        window.clearSelectedFiles = clearSelectedFiles;
        window.addFilesToCollection = addFilesToCollection;

        // Chat Functions
        window.startNewConversation = startNewConversation;
        window.openConversation = openConversation;
        window.deleteConversation = removeConversation;
        window.openChatAndSendMessage = openChatAndSendMessage;
        window.sendMessage = sendMessage;
        window.showSaveToCollectionModal = showSaveToCollectionModal;
        window.closeSaveToCollectionModal = closeSaveToCollectionModal;
        window.selectExistingCollection = selectExistingCollection;
        window.selectNewCollection = selectNewCollection;
        window.saveChatToCollection = saveChatToCollection;
        window.openImageModal = openImageModal;
        window.closeImageModal = closeImageModal;
        window.saveMessageToCollection = saveMessageToCollection;
        window.closeSaveMessageModal = closeSaveMessageModal;
        window.performSaveMessage = performSaveMessage;

        // Settings Functions
        window.switchSettingsTab = switchSettingsTab;
        window.resetProfileForm = resetProfileForm;
        window.editApiKey = editApiKey;
        window.deleteApiKey = removeApiKey;
        window.refreshLLMSettings = refreshLLMSettings;
        window.testCurrentLLM = testCurrentLLM;
        window.switchLLMConfig = switchLLMConfig;
        window.setTheme = handleThemeChange;
    }

    // Utility methods for debugging
    getModuleInfo() {
        return {
            modules: [
                'state.js - State management',
                'api.js - API services', 
                'dom.js - DOM utilities',
                'ui.js - UI components',
                'collections.js - Collection management',
                'chat.js - Chat functionality',
                'uploads.js - File upload handling',
                'settings.js - Settings management',
                'events.js - Event handling'
            ],
            initialized: this.initialized
        };
    }
}

// Create and initialize app instance
const app = new OrbApp();

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => app.init());
} else {
    app.init();
}

// Export for debugging
window.OrbApp = app;