// Chat Module
import { getState, setCurrentConversation, setState } from './state.js';
import { elements, createElement, addClass, removeClass, setHTML } from './dom.js';
import { 
    loadConversations, 
    loadConversation, 
    deleteConversation,
    sendChatMessage,
    saveChatToCollection 
} from './api.js';
import { showNotification, showSmartSuggestion, formatDate, showPanel } from './ui.js';
import { triggerUIRefresh } from './refresh.js';

export function getConversationsContent() {
    const state = getState();
    const conversations = state.conversations;

    let html = `
        <div class="conversations-header">
            <h3>Your Conversations</h3>
            <button class="btn-primary" onclick="startNewConversation()">
                + New Chat
            </button>
        </div>
        <div class="conversations-list">
    `;

    if (conversations.length === 0) {
        html += '</div>';
        return html;
    }

    conversations.forEach(conversation => {
        const preview = conversation.messages && conversation.messages.length > 0 
            ? conversation.messages[0].content.substring(0, 100) + '...'
            : 'No messages';
            
        html += `
            <div class="conversation-item" onclick="openConversation(${conversation.id})">
                <div class="conversation-info">
                    <div class="conversation-title">
                        ${conversation.title || `Conversation ${conversation.id}`}
                    </div>
                    <div class="conversation-preview">${preview}</div>
                    <div class="conversation-date">${formatDate(conversation.created_at)}</div>
                </div>
                <div class="conversation-actions" onclick="event.stopPropagation()">
                    <button class="btn-small delete-btn" onclick="deleteConversation(${conversation.id})" title="Delete">
                        🗑️
                    </button>
                </div>
            </div>
        `;
    });

    html += '</div>';
    return html;
}

export function startNewConversation() {
    setCurrentConversation(null);
    clearChatMessages();
    hideSaveToCollectionOption();
    openChatInterface();
    showSmartSuggestion('💬 New conversation started! Ask me anything.');
}

export async function openConversation(conversationId) {
    try {
        const conversation = await loadConversation(conversationId);
        setCurrentConversation(conversationId);
        
        // Update chat title
        const titleElement = elements.chatTitle;
        if (titleElement) {
            titleElement.textContent = conversation.title || `Conversation ${conversationId}`;
        }
        
        // Load messages
        displayMessages(conversation.messages || []);
        showSaveToCollectionOption();
        openChatInterface();
        
        await loadConversations();
        triggerUIRefresh('conversations');
    } catch (error) {
        showNotification('Error loading conversation', 'error');
    }
}

export async function removeConversation(conversationId) {
    if (!confirm('Are you sure you want to delete this conversation?')) {
        return;
    }
    
    try {
        await deleteConversation(conversationId);
        await loadConversations();
        triggerUIRefresh('conversations');
        
        // If this was the current conversation, clear it
        const state = getState();
        if (state.currentConversationId === conversationId) {
            setCurrentConversation(null);
            clearChatMessages();
        }
        
        showSmartSuggestion('🗑️ Conversation deleted');
        
        // Refresh conversations panel if visible  
        triggerUIRefresh('conversations');
    } catch (error) {
        showSmartSuggestion('❌ Failed to delete conversation');
    }
}

export function openChatInterface() {
    addClass(elements.chatMessagesDisplay, 'show');
}

export function closeChatInterface() {
    removeClass(elements.chatMessagesDisplay, 'show');
    showPanel('chat');
}

export function clearChatMessages() {
    if (elements.chatMessages) {
        elements.chatMessages.innerHTML = '';
    }
    if (elements.chatTitle) {
        elements.chatTitle.textContent = 'New Conversation';
    }
    hideSaveToCollectionOption();
}

export function displayMessages(messages) {
    if (!elements.chatMessages) return;
    
    elements.chatMessages.innerHTML = '';
    
    messages.forEach(message => {
        addMessage(message.role, message.content, message.verified, message.images);
    });
    
    // Scroll to bottom
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

export function addMessage(role, content, verified = null, images = null) {
    if (!elements.chatMessages) return;
    
    const messageDiv = createElement('div', `message ${role}`);
    const messageId = Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    
    let messageContent = `
        <div class="message-header">
            <div class="message-role">${role === 'user' ? '👤 You' : '🤖 Assistant'}</div>
            <div class="message-actions">
                <button class="message-save-btn" onclick="saveMessageToCollection('${messageId}', '${role}')" title="Save to collection">
                    📁
                </button>
            </div>
        </div>
        <div class="message-content" data-message-id="${messageId}">${formatMessageContent(content)}</div>
    `;
    
    if (images && images.length > 0) {
        messageContent += '<div class="message-images">';
        images.forEach((image) => {
            messageContent += `
                <img src="${image.url}" 
                     alt="${image.description || 'Image'}" 
                     class="message-image" 
                     onclick="openImageModal('${image.url}', '${image.description || ''}')"
                     style="max-width: 200px; max-height: 200px; margin: 5px; border-radius: 8px; cursor: pointer;">
            `;
        });
        messageContent += '</div>';
    }
    
    if (verified !== null) {
        const verifiedIcon = verified ? '✅' : '❌';
        messageContent += `<div class="message-verified">${verifiedIcon} ${verified ? 'Verified' : 'Unverified'}</div>`;
    }
    
    messageDiv.innerHTML = messageContent;
    elements.chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

export function formatMessageContent(content) {
    // Basic markdown-like formatting
    return content
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}

export function addStatusMessage(statusText) {
    const statusDiv = createElement('div', 'message-status');
    statusDiv.textContent = statusText;
    
    if (elements.chatMessages) {
        elements.chatMessages.appendChild(statusDiv);
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    }
    
    return statusDiv;
}

export function removeStatusMessage(statusDiv) {
    if (statusDiv && statusDiv.parentNode) {
        statusDiv.parentNode.removeChild(statusDiv);
    }
}

export async function sendMessage() {
    const messageText = elements.messageInput?.value.trim();
    if (!messageText) return;
    
    const state = getState();
    
    // Add user message to display
    addMessage('user', messageText);
    
    // Clear input
    if (elements.messageInput) {
        elements.messageInput.value = '';
    }
    
    // Show typing status with context
    let statusText = '🤖 Assistant is thinking...';
    if (state.selectedCollectionId) {
        const collection = state.collections.find(c => c.id === state.selectedCollectionId);
        statusText = `🤖 Assistant is searching "${collection?.name}" collection...`;
    }
    const statusDiv = addStatusMessage(statusText);
    
    try {
        // Log what data we're sending
        console.log('Sending chat message with context:', {
            message: messageText,
            conversationId: state.currentConversationId,
            collectionId: state.selectedCollectionId,
            agentId: state.selectedAgentId,
            collectionName: state.selectedCollectionId ? state.collections.find(c => c.id === state.selectedCollectionId)?.name : null
        });
        
        const data = await sendChatMessage(
            messageText,
            state.currentConversationId,
            state.selectedCollectionId,
            state.selectedAgentId
        );
        
        // Remove status message
        removeStatusMessage(statusDiv);
        
        // Add assistant response with collection context indicator
        let responseContent = data.response;
        if (state.selectedCollectionId && data.sources_used) {
            // If the API response indicates sources were used, we could add a note
            responseContent += `\n\n*✓ Answer based on documents from "${state.collections.find(c => c.id === state.selectedCollectionId)?.name}" collection*`;
        }
        addMessage('assistant', responseContent, data.verified, data.images);
        
        // Update conversation ID if it's new
        if (!state.currentConversationId && data.conversation_id) {
            setCurrentConversation(data.conversation_id);
            
            // Update chat title
            if (elements.chatTitle) {
                elements.chatTitle.textContent = `Conversation ${data.conversation_id}`;
            }
            
            await loadConversations();
        triggerUIRefresh('conversations');
        }
        
        // Show save to collection button if there's an active conversation
        if (state.currentConversationId) {
            showSaveToCollectionOption();
        }
        
    } catch (error) {
        removeStatusMessage(statusDiv);
        addMessage('system', `Error: ${error.message}`);
        showNotification('Failed to send message', 'error');
    }
}

export function openChatAndSendMessage(message) {
    openChatInterface();
    if (elements.messageInput) {
        elements.messageInput.value = message;
    }
    
    setTimeout(() => {
        sendMessage();
    }, 100);
}

export function showSaveToCollectionOption() {
    const state = getState();
    const existingBtn = document.getElementById('saveToCollectionBtn');
    if (existingBtn && state.currentConversationId) {
        existingBtn.style.display = 'flex';
    }
}

export function hideSaveToCollectionOption() {
    const existingBtn = document.getElementById('saveToCollectionBtn');
    if (existingBtn) {
        existingBtn.style.display = 'none';
    }
}

export function saveMessageToCollection(messageId, role) {
    const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
    if (!messageElement) {
        showSmartSuggestion('❌ Message not found');
        return;
    }
    
    const messageText = messageElement.textContent.trim();
    showSaveMessageToCollectionModal(messageText, role, messageId);
}

export function showSaveMessageToCollectionModal(messageText, role, messageId) {
    const state = getState();
    const collections = state.collections || [];
    
    const modal = createElement('div', 'modal');
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>Save Message to Collection</h3>
                <button class="close-btn" onclick="closeSaveMessageModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div class="message-preview">
                    <strong>${role === 'user' ? 'Your message' : 'Assistant response'}:</strong>
                    <p class="message-text">${messageText.substring(0, 200)}${messageText.length > 200 ? '...' : ''}</p>
                </div>
                <div class="save-options">
                    <label>
                        <input type="radio" name="messageSaveOption" value="existing" checked>
                        Save to existing collection
                    </label>
                    <div id="existingMessageCollectionSection" class="save-section">
                        <select id="existingMessageCollectionSelect">
                            <option value="">Select a collection...</option>
                            ${collections.map(c => `<option value="${c.id}">${c.name}</option>`).join('')}
                        </select>
                    </div>
                    
                    <label>
                        <input type="radio" name="messageSaveOption" value="new">
                        Create new collection
                    </label>
                    <div id="newMessageCollectionSection" class="save-section" style="display: none;">
                        <input type="text" id="newMessageCollectionNameInput" 
                               placeholder="Enter collection name (letters, numbers, spaces, -, _, .)"
                               maxlength="100"
                               pattern="[a-zA-Z0-9\s\-_\.]+"
                               title="Only letters, numbers, spaces, hyphens, underscores, and periods allowed">
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-secondary" onclick="closeSaveMessageModal()">Cancel</button>
                <button class="btn-primary" onclick="performSaveMessage('${messageId}', '${role}')">Save Message</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.id = 'saveMessageModal';
    
    // Add event listeners for radio buttons
    const radioButtons = modal.querySelectorAll('input[name="messageSaveOption"]');
    radioButtons.forEach(radio => {
        radio.addEventListener('change', function() {
            const existingSection = document.getElementById('existingMessageCollectionSection');
            const newSection = document.getElementById('newMessageCollectionSection');
            
            if (this.value === 'existing') {
                existingSection.style.display = 'block';
                newSection.style.display = 'none';
            } else {
                existingSection.style.display = 'none';
                newSection.style.display = 'block';
            }
        });
    });
}

export function closeSaveMessageModal() {
    const modal = document.getElementById('saveMessageModal');
    if (modal) {
        modal.remove();
    }
}

export async function performSaveMessage(messageId, role) {
    const messageElement = document.querySelector(`[data-message-id="${messageId}"]`);
    if (!messageElement) {
        showSmartSuggestion('❌ Message not found');
        return;
    }
    
    const messageText = messageElement.textContent.trim();
    const existingSelect = document.getElementById('existingMessageCollectionSelect');
    const newNameInput = document.getElementById('newMessageCollectionNameInput');
    const selectedOption = document.querySelector('input[name="messageSaveOption"]:checked')?.value;
    
    let collectionId = null;
    let collectionName = null;
    
    if (selectedOption === 'existing') {
        collectionId = parseInt(existingSelect?.value);
        if (!collectionId) {
            showSmartSuggestion('❌ Please select a collection');
            return;
        }
    } else {
        collectionName = newNameInput?.value.trim();
        if (!collectionName) {
            showSmartSuggestion('❌ Please enter a collection name');
            return;
        }
    }
    
    try {
        // Create the message document
        const messageDoc = {
            title: `${role === 'user' ? 'User' : 'Assistant'} Message`,
            content: messageText,
            type: 'message',
            source: role,
            timestamp: new Date().toISOString()
        };
        
        // Save to collection by creating a text document
        await saveMessageAsDocument(messageDoc, collectionId, collectionName);
        
        closeSaveMessageModal();
        showSmartSuggestion('✅ Message saved to collection successfully!');
        
    } catch (error) {
        showSmartSuggestion(`❌ Error saving message: ${error.message}`);
    }
}

async function saveMessageAsDocument(messageDoc, collectionId, collectionName) {
    // Import required functions
    const { createCollection } = await import('./api.js');
    
    // If creating new collection, create it first
    if (collectionName && !collectionId) {
        const newCollection = await createCollection({ name: collectionName });
        collectionId = newCollection.id;
    }
    
    // Create a temporary file with the message content
    const messageContent = `${messageDoc.title}\n\nContent: ${messageDoc.content}\n\nSource: ${messageDoc.source}\nTimestamp: ${messageDoc.timestamp}`;
    
    // Create a blob and form data to upload as document
    const blob = new Blob([messageContent], { type: 'text/plain' });
    const file = new File([blob], `${messageDoc.title.replace(/[^a-z0-9]/gi, '_')}.txt`, { type: 'text/plain' });
    
    const formData = new FormData();
    formData.append('files', file);
    
    // Upload to collection
    const response = await fetch(`/api/collections/${collectionId}/upload`, {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        throw new Error('Failed to save message to collection');
    }
    
    return response.json();
}

export function showSaveToCollectionModal() {
    const state = getState();
    
    if (!state.currentConversationId) {
        // Check if there are any messages in the current chat
        const chatMessages = elements.chatMessages;
        if (chatMessages && chatMessages.children.length > 0) {
            // If there are messages but no conversation ID, it means the conversation hasn't been saved yet
            // Let's offer to save the current chat as a new conversation first
            if (confirm('This chat hasn\'t been saved yet. Would you like to save it as a new conversation first?')) {
                // Trigger a new message to create the conversation, then retry
                showSmartSuggestion('💡 Send any message to create a conversation, then you can save it to a collection.');
            }
        } else {
            showSmartSuggestion('❌ Start a conversation first, then you can save it to a collection');
        }
        return;
    }
    
    // Use the existing HTML modal
    const modal = document.getElementById('saveToCollectionModal');
    if (!modal) {
        showSmartSuggestion('❌ Modal not found. Please refresh the page.');
        return;
    }
    
    // Populate the existing collection dropdown
    const existingCollectionSelect = document.getElementById('existingCollectionSelect');
    if (existingCollectionSelect) {
        existingCollectionSelect.innerHTML = `
            <option value="">Choose a collection...</option>
            ${state.collections.map(c => 
                `<option value="${c.id}">${c.name}</option>`
            ).join('')}
        `;
    }
    
    // Reset form state
    const existingRadio = modal.querySelector('input[value="existing"]');
    const newRadio = modal.querySelector('input[value="new"]');
    const existingSection = document.getElementById('existingCollectionSection');
    const newSection = document.getElementById('newCollectionSection');
    const newCollectionInput = document.getElementById('newCollectionNameInput');
    const saveBtn = document.getElementById('saveConfirmBtn');
    
    if (existingRadio) existingRadio.checked = true;
    if (newRadio) newRadio.checked = false;
    if (existingSection) existingSection.style.display = 'block';
    if (newSection) newSection.style.display = 'none';
    if (newCollectionInput) newCollectionInput.value = '';
    if (saveBtn) saveBtn.disabled = false;
    
    // Show the modal
    modal.style.display = 'flex';
}

export function closeSaveToCollectionModal() {
    const modal = document.getElementById('saveToCollectionModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

export function selectExistingCollection() {
    const existingBtn = document.getElementById('existingCollectionBtn');
    const newBtn = document.getElementById('newCollectionBtn');
    const existingSection = document.getElementById('existingCollectionSection');
    const newSection = document.getElementById('newCollectionSection');
    const saveBtn = document.getElementById('saveConfirmBtn');
    
    // Toggle button states
    if (existingBtn) existingBtn.classList.add('active');
    if (newBtn) newBtn.classList.remove('active');
    
    // Show/hide sections
    if (existingSection) existingSection.style.display = 'block';
    if (newSection) newSection.style.display = 'none';
    
    // Enable save button if a collection is selected
    const existingSelect = document.getElementById('existingCollectionSelect');
    if (saveBtn && existingSelect) {
        saveBtn.disabled = !existingSelect.value;
    }
}

export function selectNewCollection() {
    const existingBtn = document.getElementById('existingCollectionBtn');
    const newBtn = document.getElementById('newCollectionBtn');
    const existingSection = document.getElementById('existingCollectionSection');
    const newSection = document.getElementById('newCollectionSection');
    const saveBtn = document.getElementById('saveConfirmBtn');
    
    // Toggle button states
    if (existingBtn) existingBtn.classList.remove('active');
    if (newBtn) newBtn.classList.add('active');
    
    // Show/hide sections
    if (existingSection) existingSection.style.display = 'none';
    if (newSection) newSection.style.display = 'block';
    
    // Enable save button if collection name is entered
    const newInput = document.getElementById('newCollectionNameInput');
    if (saveBtn && newInput) {
        saveBtn.disabled = !newInput.value.trim();
        
        // Add input listener for real-time validation
        newInput.addEventListener('input', function() {
            saveBtn.disabled = !this.value.trim();
        });
    }
}

export async function performSaveChatToCollection() {
    const state = getState();
    
    if (!state.currentConversationId) {
        showSmartSuggestion('❌ No active conversation to save');
        return;
    }
    
    const existingSelect = document.getElementById('existingCollectionSelect');
    const newNameInput = document.getElementById('newCollectionNameInput');
    const saveBtn = document.getElementById('saveConfirmBtn');
    
    let collectionId = null;
    let collectionName = null;
    
    const selectedOption = document.querySelector('input[name="saveOption"]:checked')?.value;
    
    if (selectedOption === 'existing') {
        collectionId = parseInt(existingSelect?.value);
        if (!collectionId) {
            showSmartSuggestion('❌ Please select a collection');
            return;
        }
    } else {
        collectionName = newNameInput?.value.trim();
        if (!collectionName) {
            showSmartSuggestion('❌ Please enter a collection name');
            return;
        }
    }
    
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = 'Saving...';
    }
    
    try {
        const result = await saveChatToCollection(
            state.currentConversationId,
            collectionId,
            collectionName
        );
        
        closeSaveToCollectionModal();
        showSmartSuggestion(`✅ Chat saved to collection "${result.collection.name}" successfully!`);
        
        // Refresh collections if we created a new one
        if (collectionName) {
            await loadCollections();
        }
        
    } catch (error) {
        showSmartSuggestion(`❌ Error saving chat: ${error.message}`);
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.textContent = 'Save Chat';
        }
    }
}

// Image modal functions
export function openImageModal(imageUrl, description) {
    const modal = createElement('div', 'image-modal');
    modal.innerHTML = `
        <div class="image-modal-content">
            <button class="close-btn" onclick="closeImageModal()">&times;</button>
            <img src="${imageUrl}" alt="${description}" class="modal-image">
            <div class="image-description">${description}</div>
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.id = 'imageModal';
    
    // Close on background click
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeImageModal();
        }
    });
}

export function closeImageModal() {
    const modal = document.getElementById('imageModal');
    if (modal) {
        modal.remove();
    }
}


// Event handlers for chat interface
export function bindChatEvents() {
    // Message input enter key
    if (elements.messageInput) {
        elements.messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }
    
    // Close chat button
    if (elements.closeChatBtn) {
        elements.closeChatBtn.addEventListener('click', closeChatInterface);
    }
}