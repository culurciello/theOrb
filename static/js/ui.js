// UI Components and Utilities
import { elements, addClass, removeClass, setTextContent, setHTML } from './dom.js';
import { getState, setActivePanel, setExpanded } from './state.js';
import { getCollectionsContent, bindCollectionEvents } from './collections.js';
import { getConversationsContent, bindChatEvents } from './chat.js';
import { getSettingsContent, bindSettingsEvents } from './settings.js';

// Panel Management
export function showPanel(panelType) {
    const state = getState();
    
    // Remove active class from all vertical buttons
    document.querySelectorAll('.vertical-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Add active class to clicked button
    const activeButton = document.querySelector(`.vertical-button[data-panel="${panelType}"]`);
    if (activeButton) {
        activeButton.classList.add('active');
    }
    
    // Show expanded panel
    elements.expandedPanel.classList.add('show');
    setActivePanel(panelType);
    
    // Update panel content
    const panelData = getPanelData(panelType);
    setTextContent(elements.panelHeader, panelData.title);
    setHTML(elements.panelContent, panelData.content);
    
    // Bind panel-specific events
    bindPanelEvents(panelType);
}

export function getPanelData(panelType) {
    switch (panelType) {
        case 'collections':
            return {
                title: 'Collections',
                content: '<div id="collectionsContainer">Loading collections...</div>'
            };
        case 'conversations':
        case 'chat':
            return {
                title: 'Conversations', 
                content: '<div id="conversationsContainer">Loading conversations...</div>'
            };
        case 'documents':
            return {
                title: 'Documents',
                content: '<div id="documentsContainer">Loading documents...</div>'
            };
        case 'settings':
            return {
                title: 'Settings',
                content: '<div id="settingsContainer">Loading settings...</div>'
            };
        default:
            return {
                title: 'Panel',
                content: '<p>Panel content not found</p>'
            };
    }
}

export function collapseAll() {
    setExpanded(false);
    removeClass(elements.mainOrb, 'expanded');
    removeClass(elements.verticalButtons, 'show');
    removeClass(elements.horizontalButtons, 'show');
    removeClass(elements.expandedPanel, 'show');
    
    document.querySelectorAll('.vertical-button').forEach(btn => {
        removeClass(btn, 'active');
    });
    
    setActivePanel(null);
}

// Notification System
export function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button class="close-btn">&times;</button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
    
    // Manual close
    notification.querySelector('.close-btn').addEventListener('click', () => {
        notification.remove();
    });
}

export function showSmartSuggestion(message) {
    setTextContent(elements.smartSuggestion, message);
    addClass(elements.smartSuggestion, 'show');
    
    setTimeout(() => {
        hideSuggestion();
    }, 3000);
}

export function hideSuggestion() {
    removeClass(elements.smartSuggestion, 'show');
}

// Theme Management
export function initializeTheme() {
    const savedTheme = localStorage.getItem('orb-theme') || 'dark';
    setTheme(savedTheme);
}

export function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('orb-theme', theme);
    updateOrbIcon(theme);
    updateThemeToggleButtons();
}

export function updateOrbIcon(theme) {
    const orbIcon = elements.mainOrb.querySelector('.orb-icon');
    if (orbIcon) {
        if (theme === 'dark') {
            orbIcon.innerHTML = '🌙';
        } else {
            orbIcon.innerHTML = '☀️';
        }
    }
}

export function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
}

export function updateThemeToggleButtons() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    
    document.querySelectorAll('.theme-toggle').forEach(button => {
        const buttonTheme = button.dataset.theme;
        if (buttonTheme === currentTheme) {
            addClass(button, 'active');
        } else {
            removeClass(button, 'active');
        }
    });
}

// Welcome Message
export function showWelcomeMessage() {
    if (!getState().currentConversationId) {
        showSmartSuggestion('👋 Welcome! Click the orb to get started');
    }
}

// File Size and Date Utilities
export function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

export function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString();
}

export function getFileIcon(fileType) {
    const iconMap = {
        'pdf': '📄',
        'doc': '📝', 'docx': '📝',
        'txt': '📄', 'md': '📄',
        'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️',
        'mp4': '🎬', 'avi': '🎬', 'mov': '🎬',
        'mp3': '🎵', 'wav': '🎵',
        'zip': '📦', 'rar': '📦',
        'csv': '📊', 'xlsx': '📊',
        'py': '🐍', 'js': '📜', 'html': '🌐', 'css': '🎨'
    };
    
    return iconMap[fileType?.toLowerCase()] || '📄';
}

export function bindPanelEvents(panelType) {
    // Load actual content and bind events
    if (panelType === 'collections' || panelType === 'documents') {
        const content = getCollectionsContent();
        setHTML(elements.panelContent, content);
        bindCollectionEvents();
    }
    
    if (panelType === 'conversations' || panelType === 'chat') {
        const content = getConversationsContent();
        setHTML(elements.panelContent, content);
        bindChatEvents();
    }
    
    if (panelType === 'settings') {
        const content = getSettingsContent();
        setHTML(elements.panelContent, content);
        bindSettingsEvents();
    }
}