// DOM Element Management
export const elements = {
    // Main UI elements
    mainOrb: document.getElementById('mainOrb'),
    verticalButtons: document.getElementById('verticalButtons'),
    horizontalButtons: document.getElementById('horizontalButtons'),
    expandedPanel: document.getElementById('expandedPanel'),
    panelHeader: document.getElementById('panelHeader'),
    panelContent: document.getElementById('panelContent'),
    
    // Smart suggestion and command input
    smartSuggestion: document.getElementById('smartSuggestion'),
    commandInput: document.getElementById('commandInput'),
    
    // Chat elements
    chatMessagesDisplay: document.getElementById('chatMessagesDisplay'),
    chatMessages: document.getElementById('chatMessages'),
    messageInput: document.getElementById('messageInput'),
    chatTitle: document.getElementById('chatTitle'),
    closeChatBtn: document.getElementById('closeChatBtn'),
    chatInputContainer: document.getElementById('chatInputContainer'),
    
    // Selectors and status
    collectionSelector: document.getElementById('collectionSelector'),
    collectionStatus: document.getElementById('collectionStatus'),
    agentSelector: document.getElementById('agentSelector'),
    agentStatus: document.getElementById('agentStatus'),
    llmSelector: document.getElementById('llmSelector'),
    llmStatus: document.getElementById('llmStatus'),
    
    // File input
    fileInput: document.getElementById('fileInput')
};

// Utility functions for DOM manipulation
export function createElement(tag, className = '', textContent = '') {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (textContent) element.textContent = textContent;
    return element;
}

export function clearElement(element) {
    if (element) {
        element.innerHTML = '';
    }
}

export function toggleClass(element, className) {
    if (element) {
        element.classList.toggle(className);
    }
}

export function addClass(element, className) {
    if (element) {
        element.classList.add(className);
    }
}

export function removeClass(element, className) {
    if (element) {
        element.classList.remove(className);
    }
}

export function hasClass(element, className) {
    return element ? element.classList.contains(className) : false;
}

export function setTextContent(element, text) {
    if (element) {
        element.textContent = text;
    }
}

export function setHTML(element, html) {
    if (element) {
        element.innerHTML = html;
    }
}

export function show(element) {
    if (element) {
        element.style.display = '';
    }
}

export function hide(element) {
    if (element) {
        element.style.display = 'none';
    }
}

// Query selectors with error handling
export function $(selector) {
    return document.querySelector(selector);
}

export function $$(selector) {
    return document.querySelectorAll(selector);
}