// UI Refresh System
import { getState } from './state.js';
import { elements, setHTML } from './dom.js';
import { getCollectionsContent, bindCollectionEvents } from './collections.js';
import { getConversationsContent, bindChatEvents } from './chat.js';
import { getSettingsContent, bindSettingsEvents } from './settings.js';

// Centralized UI refresh system
export function triggerUIRefresh(dataType) {
    const state = getState();
    
    switch (dataType) {
        case 'collections':
            refreshCollectionsUI();
            break;
        case 'conversations':
            refreshConversationsUI();
            break;
        case 'settings':
            refreshSettingsUI();
            break;
        case 'all':
            refreshCollectionsUI();
            refreshConversationsUI();
            refreshSettingsUI();
            break;
    }
}

function refreshCollectionsUI() {
    const state = getState();
    const panelContent = elements.panelContent;
    
    if (panelContent && (state.activePanel === 'collections' || state.activePanel === 'documents')) {
        setHTML(panelContent, getCollectionsContent());
        bindCollectionEvents();
    }
}

function refreshConversationsUI() {
    const state = getState();
    const panelContent = elements.panelContent;
    
    if (panelContent && (state.activePanel === 'conversations' || state.activePanel === 'chat')) {
        setHTML(panelContent, getConversationsContent());
        bindChatEvents();
    }
}

function refreshSettingsUI() {
    const state = getState();
    const panelContent = elements.panelContent;
    
    if (panelContent && state.activePanel === 'settings') {
        setHTML(panelContent, getSettingsContent());
        bindSettingsEvents();
    }
}