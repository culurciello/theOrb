// Collections Module
import { getState, setState, setSelectedCollection } from './state.js';
import { elements, createElement, setHTML } from './dom.js';
import { 
    loadCollections, 
    loadCollectionDocuments, 
    loadCollectionFileLinks,
    createCollection,
    uploadFilesToCollection,
    deleteCollection,
    deleteDocument
} from './api.js';
import { showNotification, showSmartSuggestion, formatFileSize, formatDate, getFileIcon } from './ui.js';
import { triggerUIRefresh } from './refresh.js';

export function getCollectionsContent() {
    const state = getState();
    
    switch (state.collectionsView) {
        case 'list':
            return getCollectionsListContent();
        case 'detail':
            return getCollectionDetailContent();
        case 'create':
            return getCreateCollectionContent();
        default:
            return getCollectionsListContent();
    }
}

export function getCollectionsListContent() {
    const state = getState();
    const collections = state.collections;

    if (collections.length === 0) {
        return `
            <div class="empty-state">
                <h3>No Collections Found</h3>
                <p>Create your first collection to organize your documents</p>
                <button class="btn-primary" onclick="showCreateCollection()">
                    Create Collection
                </button>
            </div>
        `;
    }

    let html = `
        <div class="collections-header">
            <h3>Your Collections</h3>
            <button class="btn-primary" onclick="showCreateCollection()">
                + New Collection
            </button>
        </div>
        <div class="collections-grid">
    `;

    collections.forEach(collection => {
        html += `
            <div class="collection-item" data-id="${collection.id}">
                <div class="collection-main" onclick="viewCollectionDetails(${collection.id})">
                    <div class="collection-icon">📁</div>
                    <div class="collection-info">
                        <div class="collection-name">${collection.name}</div>
                        <div class="collection-meta">${collection.document_count || 0} documents</div>
                        <div class="collection-date">Created ${formatDate(collection.created_at)}</div>
                    </div>
                </div>
                <div class="collection-actions">
                    <button class="btn-small" onclick="selectCollectionForChat(${collection.id})" title="Use in Chat">
                        💬
                    </button>
                    <button class="btn-small" onclick="editCollection(${collection.id})" title="Edit">
                        ✏️
                    </button>
                    <button class="btn-small delete-btn" onclick="deleteCollection(${collection.id})" title="Delete">
                        🗑️
                    </button>
                </div>
            </div>
        `;
    });

    html += '</div>';
    return html;
}

export function getCollectionDetailContent() {
    const state = getState();
    const collection = state.selectedCollectionForView;
    
    if (!collection) return '<p>Collection not found</p>';

    const documents = Array.isArray(state.currentDocuments) ? state.currentDocuments : [];

    let html = `
        <div class="collection-detail-header">
            <button class="btn-secondary" onclick="backToCollectionsList()">
                ← Back to Collections
            </button>
            <h3>${collection.name}</h3>
            <div class="collection-actions">
                <button class="btn-primary" onclick="addFilesToCollection(${collection.id})">
                    + Add Files
                </button>
            </div>
        </div>
        
        <div class="collection-stats">
            <div class="stat">
                <span class="stat-number">${documents.length}</span>
                <span class="stat-label">Documents</span>
            </div>
        </div>
    `;
    
    if (documents.length === 0) {
        html += `
            <div class="empty-state">
                <h4>No documents in this collection</h4>
                <p>Add some files to get started</p>
                <button class="btn-primary" onclick="addFilesToCollection(${collection.id})">
                    Add Files
                </button>
            </div>
        `;
    } else {
        html += '<div class="documents-list">';
        
        documents.forEach(doc => {
            const fileType = doc.file_type || 'unknown';
            const icon = getFileIcon(fileType);
            
            html += `
                <div class="document-item">
                    <div class="document-icon">${icon}</div>
                    <div class="document-info">
                        <div class="document-name">${doc.filename}</div>
                        <div class="document-meta">
                            ${formatFileSize(doc.file_size || 0)} • 
                            ${formatDate(doc.created_at)}
                        </div>
                    </div>
                    <div class="document-actions">
                        <button class="btn-small" onclick="viewDocument(${doc.id})" title="View">
                            👁️
                        </button>
                        <button class="btn-small delete-btn" onclick="removeDocumentFromCollection(${doc.id})" title="Remove">
                            🗑️
                        </button>
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
    }

    return html;
}

export function getCreateCollectionContent() {
    return `
        <div class="create-collection-form">
            <div class="form-header">
                <button class="btn-secondary" onclick="backToCollectionsList()">
                    ← Back to Collections
                </button>
                <h3>Create New Collection</h3>
            </div>
            
            <form id="createCollectionForm">
                <div class="form-group">
                    <label for="collectionName">Collection Name</label>
                    <input type="text" id="collectionName" name="collectionName" required placeholder="Enter collection name">
                </div>
                
                <div class="form-group">
                    <label for="collectionDescription">Description (Optional)</label>
                    <textarea id="collectionDescription" name="collectionDescription" placeholder="Describe your collection"></textarea>
                </div>
                
                <div class="content-selection">
                    <h4>Add Content</h4>
                    <div class="selection-options">
                        <button type="button" class="selection-btn" onclick="selectFiles()">
                            📄 Select Files
                        </button>
                        <button type="button" class="selection-btn" onclick="selectFolder()">
                            📁 Select Folder
                        </button>
                    </div>
                    
                    <div id="selectedFilesContainer" style="display: none;">
                        <h5>Selected Files</h5>
                        <div id="selectedFilesList"></div>
                        <button type="button" class="btn-small" onclick="clearSelectedFiles()">
                            Clear Selection
                        </button>
                    </div>
                </div>
                
                <div class="form-actions">
                    <button type="button" class="btn-secondary" onclick="backToCollectionsList()">
                        Cancel
                    </button>
                    <button type="submit" class="btn-primary">
                        Create Collection
                    </button>
                </div>
            </form>
        </div>
    `;
}

// Collection Management Functions
export function showCreateCollection() {
    setState('collectionsView', 'create');
    // Trigger panel refresh
    const panelContent = elements.panelContent;
    if (panelContent) {
        setHTML(panelContent, getCollectionsContent());
        bindCollectionEvents();
    }
}

export function backToCollectionsList() {
    setState('collectionsView', 'list');
    setState('selectedCollectionForView', null);
    // Trigger panel refresh
    const panelContent = elements.panelContent;
    if (panelContent) {
        setHTML(panelContent, getCollectionsContent());
        bindCollectionEvents();
    }
}

export async function viewCollectionDetails(collectionId) {
    const state = getState();
    const collection = state.collections.find(c => c.id === collectionId);
    
    if (!collection) return;
    
    setState('selectedCollectionForView', collection);
    setState('collectionsView', 'detail');
    
    try {
        await loadCollectionDocuments(collectionId);
    } catch (error) {
        console.warn('Could not load collection documents:', error);
        showNotification('Collection loaded but documents unavailable', 'warning');
    }
    
    // Always refresh the panel, even if documents failed to load
    const panelContent = elements.panelContent;
    if (panelContent) {
        setHTML(panelContent, getCollectionsContent());
        bindCollectionEvents();
    }
}

export function selectCollectionForChat(collectionId) {
    const state = getState();
    const collection = state.collections.find(c => c.id === collectionId);
    
    if (!collection) return;
    
    setSelectedCollection(collectionId);
    
    // Update collection selector
    const selector = elements.collectionSelector;
    if (selector) {
        selector.value = collectionId;
    }
    
    // Update status
    const status = elements.collectionStatus;
    if (status) {
        status.textContent = `Using "${collection.name}" collection`;
    }
    
    showSmartSuggestion(`💾 Collection "${collection.name}" selected for chat`);
}

export async function createNewCollection(formData) {
    try {
        const result = await createCollection(formData);
        
        if (formData.files && formData.files.length > 0) {
            // Handle file uploads
            await uploadFilesToCollection(result.id, formData.files);
        }
        
        await loadCollections();
        backToCollectionsList();
        
        showNotification(`Collection "${formData.name}" created successfully`, 'success');
    } catch (error) {
        showNotification(`Error creating collection: ${error.message}`, 'error');
    }
}

export async function editCollection(collectionId) {
    showNotification('Collection editing will be implemented in a future update', 'info');
}

export async function removeCollection(collectionId) {
    if (!confirm('Are you sure you want to delete this collection? This action cannot be undone.')) {
        return;
    }
    
    try {
        await deleteCollection(collectionId);
        showNotification('Collection deleted', 'success');
        
        // If we're viewing this collection, go back to list
        const state = getState();
        if (state.selectedCollectionForView?.id === collectionId) {
            backToCollectionsList();
        } else {
            // Refresh the collections list view
            triggerUIRefresh('collections');
        }
    } catch (error) {
        showNotification('Error deleting collection', 'error');
    }
}


export async function removeDocumentFromCollection(documentId) {
    if (!confirm('Are you sure you want to remove this document?')) {
        return;
    }
    
    try {
        await deleteDocument(documentId);
        
        const state = getState();
        if (state.selectedCollectionForView) {
            await loadCollectionDocuments(state.selectedCollectionForView.id);
            // Refresh view
            const panelContent = elements.panelContent;
            if (panelContent) {
                setHTML(panelContent, getCollectionsContent());
                bindCollectionEvents();
            }
        }
        
        await loadCollections();
        showNotification('Document removed', 'success');
    } catch (error) {
        showNotification('Error removing document', 'error');
    }
}

export function viewDocument(documentId) {
    const state = getState();
    const document = state.currentDocuments.find(d => d.id === documentId);
    
    if (!document) return;
    
    // Open document viewer - this would be implemented based on document type
    showNotification('Document viewer will be implemented in a future update', 'info');
}

// Event binding for collection-specific interactions
export function bindCollectionEvents() {
    const createForm = document.getElementById('createCollectionForm');
    if (createForm) {
        createForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(createForm);
            const collectionData = {
                name: formData.get('collectionName'),
                description: formData.get('collectionDescription')
            };
            
            // Add selected files if any
            const fileInput = elements.fileInput;
            if (fileInput && fileInput.files.length > 0) {
                collectionData.files = Array.from(fileInput.files);
            }
            
            await createNewCollection(collectionData);
        });
    }
}

// File selection utilities
export function selectFiles() {
    elements.fileInput.click();
}

export function selectFolder() {
    // Modern browsers support directory selection
    const input = elements.fileInput;
    input.webkitdirectory = true;
    input.click();
}

export function clearSelectedFiles() {
    elements.fileInput.value = '';
    const container = document.getElementById('selectedFilesContainer');
    if (container) {
        container.style.display = 'none';
    }
}

export function updateSelectedFilesDisplay() {
    const files = elements.fileInput.files;
    const container = document.getElementById('selectedFilesContainer');
    const filesList = document.getElementById('selectedFilesList');
    
    if (files.length === 0) {
        if (container) container.style.display = 'none';
        return;
    }
    
    if (container) container.style.display = 'block';
    
    if (filesList) {
        let html = '';
        Array.from(files).forEach((file, index) => {
            const icon = getFileIcon(file.name.split('.').pop());
            html += `
                <div class="selected-file">
                    <span class="file-icon">${icon}</span>
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">${formatFileSize(file.size)}</span>
                    <button type="button" class="remove-file" onclick="removeFile(${index})">
                        ×
                    </button>
                </div>
            `;
        });
        filesList.innerHTML = html;
    }
}

export function removeFile(index) {
    // Note: Can't directly remove from FileList, would need to reconstruct
    // For now, just clear and let user re-select
    clearSelectedFiles();
    showNotification('Please re-select files to remove specific items', 'info');
}