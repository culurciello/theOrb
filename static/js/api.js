// API Services Module
import { setCollections, setConversations, setAvailableAgents, setAvailableLLMs, setCurrentDocuments, setUserProfile, setApiKeys } from './state.js';
import { updateCollectionSelector, updateAgentSelector, updateLLMSelector } from './selectors.js';
import { triggerUIRefresh } from './refresh.js';

// Collections API
export async function loadCollections() {
    try {
        const response = await fetch('/api/collections');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const collections = await response.json();
        setCollections(collections);
        updateCollectionSelector();
        return collections;
    } catch (error) {
        console.error('Error loading collections:', error);
        setCollections([]);
        updateCollectionSelector();
        throw error;
    }
}

export async function createCollection(data) {
    // Validate collection name
    if (!data.name || !data.name.trim()) {
        throw new Error('Collection name is required');
    }
    
    // Trim and validate length
    const trimmedName = data.name.trim();
    if (trimmedName.length > 100) {
        throw new Error('Collection name must be 100 characters or less');
    }
    
    // Validate characters - allow letters, numbers, spaces, hyphens, underscores, periods
    const validNamePattern = /^[a-zA-Z0-9\s\-_\.]+$/;
    if (!validNamePattern.test(trimmedName)) {
        throw new Error('Collection name can only contain letters, numbers, spaces, hyphens, underscores, and periods');
    }
    
    // Clean the data
    const cleanData = {
        name: trimmedName
    };
    
    const response = await fetch('/api/collections', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(cleanData)
    });
    
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Unknown error');
    return result;
}

export async function deleteCollection(collectionId) {
    const response = await fetch(`/api/collections/${collectionId}`, {
        method: 'DELETE'
    });
    if (!response.ok) throw new Error('Failed to delete collection');
    await loadCollections();
    // Trigger UI refresh after data change
    triggerUIRefresh('collections');
}

export async function loadCollectionDocuments(collectionId) {
    try {
        const response = await fetch(`/api/collections/${collectionId}/files`);
        
        if (!response.ok) {
            if (response.status === 404) {
                console.warn(`Files endpoint not found for collection ${collectionId}`);
                setCurrentDocuments([]);
                return [];
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        const documents = data.files || [];
        setCurrentDocuments(documents);
        return documents;
    } catch (error) {
        console.error('Error loading collection documents:', error);
        setCurrentDocuments([]);
        throw error;
    }
}

export async function loadCollectionFileLinks(collectionId) {
    try {
        const response = await fetch(`/api/collections/${collectionId}/file-links`);
        const data = await response.json();
        return data.file_links || [];
    } catch (error) {
        console.error('Error loading collection file links:', error);
        return [];
    }
}

// File Upload API
export async function uploadFilesToCollection(collectionId, files) {
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
            if (!result.error) {
                successCount++;
            }
        } catch (error) {
            console.error(`Error uploading ${file.name}:`, error);
        }
    }
    return successCount;
}

export async function uploadDirectoryToCollection(collectionId, directoryPath) {
    const response = await fetch(`/api/collections/${collectionId}/upload-directory`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            directory_path: directoryPath
        })
    });
    
    const data = await response.json();
    if (!response.ok) throw new Error(data.error);
    return data;
}

// Conversations API
export async function loadConversations() {
    try {
        const response = await fetch('/api/conversations');
        const conversations = await response.json();
        setConversations(conversations);
        return conversations;
    } catch (error) {
        console.error('Error loading conversations:', error);
        throw error;
    }
}

export async function loadConversation(conversationId) {
    const response = await fetch(`/api/conversations/${conversationId}`);
    const conversation = await response.json();
    if (!response.ok) throw new Error('Failed to load conversation');
    return conversation;
}

export async function deleteConversation(conversationId) {
    const response = await fetch(`/api/conversations/${conversationId}`, {
        method: 'DELETE'
    });
    if (!response.ok) throw new Error('Failed to delete conversation');
}

export async function saveChatToCollection(conversationId, collectionId, collectionName) {
    const response = await fetch(`/api/conversations/${conversationId}/save-to-collection`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            collection_id: collectionId,
            collection_name: collectionName
        })
    });
    
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    return result;
}

// Chat API
export async function sendChatMessage(message, conversationId, collectionId, agentId) {
    const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
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
    
    const data = await response.json();
    return data;
}

// Documents API
export async function deleteDocument(documentId) {
    const response = await fetch(`/api/documents/${documentId}`, {
        method: 'DELETE'
    });
    if (!response.ok) throw new Error('Failed to delete document');
}

// Agent API
export async function loadAvailableAgents() {
    try {
        const response = await fetch('/api/agents');
        const agents = await response.json();
        setAvailableAgents(agents);
        updateAgentSelector();
        return agents;
    } catch (error) {
        console.error('Error loading agents:', error);
        throw error;
    }
}

// LLM API
export async function loadAvailableLLMs() {
    try {
        const response = await fetch('/api/llm/configs');
        const llms = await response.json();
        setAvailableLLMs(llms);
        updateLLMSelector();
        return llms;
    } catch (error) {
        console.error('Error loading LLMs:', error);
        throw error;
    }
}

export async function loadCurrentLLM() {
    const response = await fetch('/api/llm/current');
    const currentLLM = await response.json();
    if (!response.ok) throw new Error('Failed to load current LLM');
    return currentLLM;
}

export async function switchLLM(configId) {
    const response = await fetch('/api/llm/current', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            config_id: configId
        })
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error);
    }
    
    const result = await response.json();
    updateLLMSelector();
    return result;
}

export async function testLLM(configId) {
    const testResponse = await fetch('/api/llm/test/' + configId, {
        method: 'POST'
    });
    const result = await testResponse.json();
    if (!testResponse.ok) throw new Error(result.error);
    return result;
}

// User Profile API
export async function loadUserProfile() {
    const response = await fetch('/api/user/profile');
    const profile = await response.json();
    setUserProfile(profile);
    return profile;
}

export async function saveUserProfile(formData) {
    try {
        const response = await fetch('/api/user/profile', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData)
        });
        
        if (!response.ok) {
            // Try to get error message from response
            try {
                const errorResult = await response.json();
                throw new Error(errorResult.error || `Server error: ${response.status}`);
            } catch (jsonError) {
                throw new Error(`Server error: ${response.status} ${response.statusText}`);
            }
        }
        
        return await response.json();
    } catch (error) {
        // Handle network errors
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            throw new Error('Network error: Could not connect to server');
        }
        throw error;
    }
}

// API Keys API
export async function loadApiKeys() {
    const response = await fetch('/api/user/api-keys');
    const keys = await response.json();
    setApiKeys(keys);
    return keys;
}

export async function saveApiKey(formData) {
    const response = await fetch('/api/user/api-keys', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData)
    });
    
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    await loadApiKeys();
    return result;
}

export async function deleteApiKey(keyId) {
    const response = await fetch(`/api/user/api-keys/${keyId}`, {
        method: 'DELETE'
    });
    
    if (!response.ok) throw new Error('Failed to delete API key');
    await loadApiKeys();
}

export async function updateApiKey(keyId, data) {
    const response = await fetch(`/api/user/api-keys/${keyId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data)
    });
    
    if (!response.ok) throw new Error('Failed to update API key');
    await loadApiKeys();
}

// Image API
export async function convertImageToCaption(file) {
    const formData = new FormData();
    formData.append('image', file);

    const response = await fetch('/api/image-caption', {
        method: 'POST',
        body: formData
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText);
    }

    const data = await response.json();
    return data.caption;
}