// Selector Update Functions
import { getState } from './state.js';
import { elements } from './dom.js';

export function updateCollectionSelector() {
    const state = getState();
    const selector = elements.collectionSelector;
    
    if (!selector) return;
    
    // Clear existing options
    selector.innerHTML = '<option value="">No Collection</option>';
    
    // Add collections as options
    state.collections.forEach(collection => {
        const option = document.createElement('option');
        option.value = collection.id;
        option.textContent = collection.name;
        selector.appendChild(option);
    });
}

export function updateAgentSelector() {
    const state = getState();
    const selector = elements.agentSelector;
    
    if (!selector) return;
    
    // Clear existing options
    selector.innerHTML = '<option value="">Default Agent</option>';
    
    // Add agents as options
    state.availableAgents.forEach(agent => {
        const option = document.createElement('option');
        option.value = agent.name;
        option.textContent = agent.display_name || agent.name;
        selector.appendChild(option);
    });
}

export function updateLLMSelector() {
    const state = getState();
    const selector = elements.llmSelector;
    
    if (!selector) return;
    
    // Clear existing options
    selector.innerHTML = '<option value="">Default LLM</option>';
    
    // Add LLM configurations as options
    Object.entries(state.availableLLMs).forEach(([configId, config]) => {
        const option = document.createElement('option');
        option.value = configId;
        option.textContent = config.display_name || configId;
        
        // Mark current LLM as selected
        if (config.is_current) {
            option.selected = true;
        }
        
        selector.appendChild(option);
    });
}