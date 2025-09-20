// Global State Management
export const state = {
    // UI State
    isExpanded: false,
    activePanel: null,
    isRecording: false,
    isInDocumentView: false,
    collectionsView: 'list', // 'list', 'detail', 'create'
    activeSettingsTab: 'profile',
    currentTheme: 'dark',
    
    // Data State
    currentConversationId: null,
    selectedCollectionId: null,
    selectedAgentId: null,
    selectedLLMId: null,
    selectedCollectionForView: null,
    
    // Collections and data
    collections: [],
    conversations: [],
    availableAgents: [],
    availableLLMs: {},
    currentDocuments: [],
    userProfile: null,
    apiKeys: []
};

// State getters
export const getState = () => state;

// State setters with validation
export const setState = (key, value) => {
    if (key in state) {
        state[key] = value;
    } else {
        console.warn(`Unknown state key: ${key}`);
    }
};

// Specific state management functions
export const setActivePanel = (panel) => {
    state.activePanel = panel;
};

export const setExpanded = (expanded) => {
    state.isExpanded = expanded;
};

export const setCurrentConversation = (id) => {
    state.currentConversationId = id;
};

export const setSelectedCollection = (id) => {
    state.selectedCollectionId = id;
};

export const setSelectedAgent = (id) => {
    state.selectedAgentId = id;
};

export const setSelectedLLM = (id) => {
    state.selectedLLMId = id;
};

// Data management
export const setCollections = (collections) => {
    state.collections = collections;
};

export const addCollection = (collection) => {
    state.collections.push(collection);
};

export const setConversations = (conversations) => {
    state.conversations = conversations;
};

export const setAvailableAgents = (agents) => {
    state.availableAgents = agents;
};

export const setAvailableLLMs = (llms) => {
    state.availableLLMs = llms;
};

export const setCurrentDocuments = (documents) => {
    state.currentDocuments = Array.isArray(documents) ? documents : [];
};

export const setUserProfile = (profile) => {
    state.userProfile = profile;
};

export const setApiKeys = (keys) => {
    state.apiKeys = keys;
};

export const setTheme = (theme) => {
    state.currentTheme = theme;
    localStorage.setItem('orb-theme', theme);
};

// Initialize state on app startup
export const initializeState = () => {
    // Load saved theme
    const savedTheme = localStorage.getItem('orb-theme') || 'dark';
    state.currentTheme = savedTheme;
    
    console.log('State initialized');
};