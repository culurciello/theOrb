// Event Management Module
import { elements } from './dom.js';
import { getState, setExpanded, setActivePanel, setSelectedCollection, setSelectedAgent, setSelectedLLM } from './state.js';
import { showPanel, collapseAll, showSmartSuggestion, bindPanelEvents } from './ui.js';
import { sendMessage, startNewConversation, openChatAndSendMessage, showSaveToCollectionModal } from './chat.js';
import { handleFileUpload } from './uploads.js';
import { bindCollectionEvents, updateSelectedFilesDisplay } from './collections.js';
import { bindChatEvents } from './chat.js';
import { bindSettingsEvents } from './settings.js';
import { switchLLM } from './api.js';

export function setupEventListeners() {
    setupMainOrbEvents();
    setupVerticalButtonEvents();
    setupHorizontalButtonEvents();
    setupChatEvents();
    setupCommandInputEvents();
    setupSelectorEvents();
    setupFileUploadEvents();
    setupGlobalEvents();
    setupKeyboardShortcuts();
}

function setupMainOrbEvents() {
    if (!elements.mainOrb) return;
    
    elements.mainOrb.addEventListener('click', function() {
        const state = getState();
        const isExpanded = !state.isExpanded;
        setExpanded(isExpanded);
        
        if (isExpanded) {
            elements.mainOrb.classList.add('expanded');
            elements.verticalButtons.classList.add('show');
            elements.horizontalButtons.classList.add('show');
        } else {
            collapseAll();
        }
    });
}

function setupVerticalButtonEvents() {
    document.querySelectorAll('.vertical-button').forEach(button => {
        button.addEventListener('click', function() {
            const panel = this.dataset.panel;
            const state = getState();
            
            // If clicking the same active panel, close it
            if (state.activePanel === panel && elements.expandedPanel.classList.contains('show')) {
                elements.expandedPanel.classList.remove('show');
                this.classList.remove('active');
                setActivePanel(null);
            } else {
                showPanel(panel);
            }
        });
    });
}

function setupHorizontalButtonEvents() {
    document.querySelectorAll('.horizontal-button').forEach(button => {
        button.addEventListener('click', function() {
            const action = this.dataset.action;
            executeAction(action);
        });
    });
}

function setupChatEvents() {
    bindChatEvents();
}

function setupCommandInputEvents() {
    if (!elements.commandInput) return;
    
    elements.commandInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleCommandInput(this.value);
            this.value = '';
            this.classList.remove('show');
        }
    });
}

function setupSelectorEvents() {
    // Collection selector
    if (elements.collectionSelector) {
        elements.collectionSelector.addEventListener('change', function() {
            const collectionId = this.value;
            if (collectionId) {
                const collectionIdInt = parseInt(collectionId);
                setSelectedCollection(collectionIdInt);
                const state = getState();
                const collection = state.collections.find(c => c.id == collectionIdInt);
                elements.collectionStatus.textContent = `Using "${collection?.name}" collection`;
                console.log('Selected collection:', collection?.name, 'ID:', collectionIdInt);
            } else {
                setSelectedCollection(null);
                elements.collectionStatus.textContent = 'Select a collection to search your documents';
                console.log('Cleared collection selection');
            }
        });
    }

    // Agent selector
    if (elements.agentSelector) {
        elements.agentSelector.addEventListener('change', function() {
            const agentId = this.value;
            if (agentId) {
                setSelectedAgent(agentId);
                const state = getState();
                const agent = state.availableAgents.find(a => a.name === agentId);
                elements.agentStatus.textContent = `Using ${agent?.display_name || agentId} agent`;
                console.log('Selected agent:', agent?.display_name || agentId);
            } else {
                setSelectedAgent(null);
                elements.agentStatus.textContent = 'Choose an AI agent for processing';
                console.log('Cleared agent selection');
            }
        });
    }

    // LLM selector
    if (elements.llmSelector) {
        elements.llmSelector.addEventListener('change', function() {
            const llmId = this.value;
            const state = getState();
            if (llmId && llmId !== state.selectedLLMId) {
                setSelectedLLM(llmId);
                switchLLM(llmId);
                console.log('Selected LLM:', llmId);
            } else if (!llmId) {
                setSelectedLLM(null);
                console.log('Cleared LLM selection');
            }
        });
    }
}

function setupFileUploadEvents() {
    if (!elements.fileInput) return;
    
    elements.fileInput.addEventListener('change', function() {
        const state = getState();
        if (state.collectionsView === 'create') {
            updateSelectedFilesDisplay();
        } else {
            handleFileUpload();
        }
    });
}

function setupGlobalEvents() {
    // Click outside to collapse
    document.addEventListener('click', function(e) {
        const state = getState();
        
        // Don't collapse if clicking on interactive elements
        const interactiveSelectors = [
            '.orvin-orb', '.vertical-buttons', '.horizontal-buttons', '.expanded-panel',
            '.command-input', '.smart-suggestion', '.chat-messages-display',
            'button', '.btn-primary', '.btn-secondary', '.btn-small',
            '.collection-item', '.collection-main', '.collection-actions',
            'input', 'select', 'textarea', 'form', '.modal'
        ];
        
        const isInteractive = interactiveSelectors.some(selector => 
            e.target.closest(selector)
        );
        
        if (!isInteractive && state.isExpanded) {
            collapseAll();
        }
    });

    // Save to collection button (delegated event)
    document.addEventListener('click', function(e) {
        if (e.target.id === 'saveToCollectionBtn') {
            e.preventDefault();
            e.stopPropagation();
            showSaveToCollectionModal();
        }
    });
}

function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        const state = getState();
        
        // Escape key - close everything
        if (e.key === 'Escape') {
            collapseAll();
            if (elements.chatMessagesDisplay) {
                elements.chatMessagesDisplay.classList.remove('show');
            }
        }
        
        // Ctrl+K - open command palette
        if (e.ctrlKey && e.key === 'k') {
            e.preventDefault();
            if (!state.isExpanded) {
                elements.mainOrb.click();
            }
            setTimeout(() => {
                executeAction('command');
            }, 100);
        }
        
        // Ctrl+N - new conversation
        if (e.ctrlKey && e.key === 'n') {
            e.preventDefault();
            executeAction('new-chat');
        }
        
        // Ctrl+O - open collections
        if (e.ctrlKey && e.key === 'o') {
            e.preventDefault();
            if (!state.isExpanded) {
                elements.mainOrb.click();
            }
            setTimeout(() => {
                showPanel('collections');
            }, 100);
        }
    });
}

// Action handlers
export function executeAction(action) {
    switch (action) {
        case 'command':
            showCommandInput();
            break;
        case 'upload':
            elements.fileInput.click();
            showSmartSuggestion('📁 File upload dialog opened');
            break;
        case 'new-chat':
            startNewConversation();
            break;
        case 'voice':
            handleVoiceInput();
            break;
        default:
            console.log(`Unknown action: ${action}`);
    }
}

function showCommandInput() {
    if (elements.commandInput) {
        elements.commandInput.classList.add('show');
        elements.commandInput.focus();
    }
}

function handleCommandInput(command) {
    const lowerCommand = command.toLowerCase().trim();
    
    // Simple command routing
    if (lowerCommand.includes('conversation') || lowerCommand.includes('chat')) {
        showPanel('conversations');
        showSmartSuggestion('💬 Opened conversations panel');
    } else if (lowerCommand.includes('collection') || lowerCommand.includes('document')) {
        showPanel('collections');
        showSmartSuggestion('💾 Opened collections panel');
    } else if (lowerCommand.includes('setting')) {
        showPanel('settings');
        showSmartSuggestion('⚙️ Opened settings panel');
    } else if (lowerCommand.includes('upload') || lowerCommand.includes('file')) {
        elements.fileInput.click();
        showSmartSuggestion('📁 File upload dialog opened');
    } else {
        // Send as message
        openChatAndSendMessage(command);
    }
}


// This function is now imported from ui.js

// Utility functions for dynamic event binding
export function addEventListener(element, event, handler) {
    if (element && typeof element.addEventListener === 'function') {
        element.addEventListener(event, handler);
    }
}

export function removeEventListener(element, event, handler) {
    if (element && typeof element.removeEventListener === 'function') {
        element.removeEventListener(event, handler);
    }
}

// Delegated event handling for dynamic content
export function delegateEvent(container, selector, event, handler) {
    if (!container) return;
    
    container.addEventListener(event, function(e) {
        const target = e.target.closest(selector);
        if (target) {
            handler.call(target, e);
        }
    });
}