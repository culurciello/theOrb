// File Upload Module
import { getState } from './state.js';
import { elements } from './dom.js';
import { uploadFilesToCollection, createCollection, convertImageToCaption, loadCollectionDocuments, loadCollections } from './api.js';
import { showNotification, showSmartSuggestion, showPanel } from './ui.js';

export async function handleFileUpload() {
    const files = elements.fileInput.files;
    if (files.length === 0) return;

    // Check if this is for adding to an existing collection
    const collectionId = elements.fileInput.dataset.collectionId;
    if (collectionId) {
        await uploadFilesToCollection(parseInt(collectionId), files);
        
        // Refresh the collection details view
        await loadCollectionDocuments(parseInt(collectionId));
        await loadCollections();
        showPanel('collections');
        
        // Clear the dataset
        delete elements.fileInput.dataset.collectionId;
        elements.fileInput.value = '';
        return;
    }

    // Legacy behavior for creating new collections
    const collectionNameInput = document.getElementById('collectionNameInput');
    let collectionName = collectionNameInput ? collectionNameInput.value.trim() : '';
    
    if (!collectionName) {
        collectionName = prompt('Enter collection name:');
        if (!collectionName) return;
    }

    // Find or create collection
    const state = getState();
    let collection = state.collections.find(c => c.name === collectionName);
    if (!collection) {
        try {
            collection = await createCollection({ name: collectionName });
        } catch (error) {
            showSmartSuggestion(`❌ Error creating collection: ${error.message}`);
            return;
        }
    }

    await uploadFilesToCollection(collection.id, files);

    // Clear inputs and refresh
    elements.fileInput.value = '';
    if (collectionNameInput) {
        collectionNameInput.value = '';
    }
    
    await loadCollections();
}

export function addFilesToCollection(collectionId) {
    elements.fileInput.dataset.collectionId = collectionId;
    elements.fileInput.click();
}

export function setupDropZone() {
    const container = elements.chatInputContainer;
    if (!container) return;

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        container.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop area when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        container.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        container.addEventListener(eventName, unhighlight, false);
    });
    
    function highlight() {
        container.classList.add('drag-over');
    }
    
    function unhighlight() {
        container.classList.remove('drag-over');
    }
    
    // Handle dropped files
    container.addEventListener('drop', handleDrop, false);

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    async function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length === 0) return;
        
        // Handle image files for captioning
        const imageFile = Array.from(files).find(file => 
            file.type.startsWith('image/')
        );
        
        if (imageFile) {
            if (!imageFile.type.startsWith('image/')) {
                showSmartSuggestion('❌ Please drop an image file');
                return;
            }
            
            // Check file size (10MB limit)
            if (imageFile.size > 10 * 1024 * 1024) {
                showSmartSuggestion('❌ Image file is too large. Please select a file smaller than 10MB');
                return;
            }
            
            showSmartSuggestion('🎯 Converting image to caption...');
            
            try {
                const caption = await convertImageToCaption(imageFile);
                
                // Add caption to message input
                if (elements.messageInput) {
                    const currentValue = elements.messageInput.value;
                    const newValue = currentValue ? `${currentValue}\n\n${caption}` : caption;
                    elements.messageInput.value = newValue;
                    elements.messageInput.focus();
                }
                
                showSmartSuggestion(`✅ Image converted to caption: "${caption}"`);
                
            } catch (error) {
                console.error('Error converting image:', error);
                showSmartSuggestion(`❌ Error converting image: ${error.message}`);
            }
        }
    }
}

// Directory Import Functions

export function closeDirectoryModal() {
    const modal = document.getElementById('directoryModal');
    if (modal) {
        modal.remove();
    }
}

export async function performDirectoryImport(directoryPath, collectionId) {
    try {
        showImportProgress();
        updateImportProgress(10, 'Starting import', 'Preparing to import directory...');
        
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
        
        if (!response.ok) {
            throw new Error(data.error || 'Import failed');
        }
        
        updateImportProgress(50, 'Processing files', 'Reading and categorizing documents...');
        
        // Simulate progress updates
        await new Promise(resolve => setTimeout(resolve, 1000));
        updateImportProgress(80, 'Almost done', 'Finalizing import...');
        
        await new Promise(resolve => setTimeout(resolve, 1000));
        updateImportProgress(100, 'Import complete!', `Processed ${data.processed_documents} documents`);
        
        // Show success and close modal after delay
        setTimeout(() => {
            closeImportProgress();
            // Reload collections and documents
            loadCollections();
            const state = getState();
            if (state.collectionsView === 'detail' && state.selectedCollectionForView) {
                loadCollectionDocuments(state.selectedCollectionForView.id);
            }
            showNotification('Directory imported successfully!', 'success');
        }, 2000);
        
    } catch (error) {
        console.error('Directory import error:', error);
        updateImportProgress(0, 'Import failed', error.message);
        
        // Show error and close modal after delay
        setTimeout(() => {
            closeImportProgress();
            showNotification('Import failed: ' + error.message, 'error');
        }, 3000);
    }
}

export function showImportProgress() {
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'importProgressModal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h3>Importing Directory</h3>
            </div>
            <div class="modal-body">
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill" id="progressFill" style="width: 0%"></div>
                    </div>
                    <div class="progress-text">
                        <div id="progressStatus">Starting import...</div>
                        <div id="progressDetails"></div>
                    </div>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

export function closeImportProgress() {
    const modal = document.getElementById('importProgressModal');
    if (modal) {
        modal.remove();
    }
}

export function updateImportProgress(percentage, status, details) {
    const progressFill = document.getElementById('progressFill');
    const progressStatus = document.getElementById('progressStatus');
    const progressDetails = document.getElementById('progressDetails');
    
    if (progressFill) {
        progressFill.style.width = percentage + '%';
    }
    
    if (progressStatus) {
        progressStatus.textContent = status;
    }
    
    if (progressDetails) {
        progressDetails.textContent = details || '';
    }
}