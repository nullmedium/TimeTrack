// Sub-task Management Functions

// Global variable to track subtasks
let currentSubtasks = [];

// Initialize subtasks when loading a task
function initializeSubtasks(taskId) {
    currentSubtasks = [];
    const subtasksContainer = document.getElementById('subtasks-container');
    if (!subtasksContainer) return;
    
    subtasksContainer.innerHTML = '<div class="loading">Loading subtasks...</div>';
    
    if (taskId) {
        // Fetch existing subtasks
        fetch(`/api/tasks/${taskId}`)
            .then(response => response.json())
            .then(task => {
                if (task.subtasks) {
                    currentSubtasks = task.subtasks;
                    renderSubtasks();
                } else {
                    subtasksContainer.innerHTML = '<p class="no-subtasks">No subtasks yet</p>';
                }
            })
            .catch(error => {
                console.error('Error loading subtasks:', error);
                subtasksContainer.innerHTML = '<p class="error">Error loading subtasks</p>';
            });
    } else {
        renderSubtasks();
    }
}

// Render subtasks in the modal
function renderSubtasks() {
    const container = document.getElementById('subtasks-container');
    if (!container) return;
    
    if (currentSubtasks.length === 0) {
        container.innerHTML = '<p class="no-subtasks">No subtasks yet</p>';
        return;
    }
    
    container.innerHTML = currentSubtasks.map((subtask, index) => `
        <div class="subtask-item" data-subtask-id="${subtask.id || ''}" data-index="${index}">
            <input type="checkbox" 
                   class="subtask-checkbox" 
                   ${subtask.status === 'COMPLETED' ? 'checked' : ''}
                   onchange="toggleSubtaskStatus(${index})"
                   ${subtask.id ? '' : 'disabled'}>
            <input type="text" 
                   class="subtask-name" 
                   value="${escapeHtml(subtask.name)}" 
                   placeholder="Subtask name"
                   onchange="updateSubtaskName(${index}, this.value)">
            <select class="subtask-priority" onchange="updateSubtaskPriority(${index}, this.value)">
                <option value="LOW" ${subtask.priority === 'LOW' ? 'selected' : ''}>Low</option>
                <option value="MEDIUM" ${subtask.priority === 'MEDIUM' ? 'selected' : ''}>Medium</option>
                <option value="HIGH" ${subtask.priority === 'HIGH' ? 'selected' : ''}>High</option>
                <option value="URGENT" ${subtask.priority === 'URGENT' ? 'selected' : ''}>Urgent</option>
            </select>
            <select class="subtask-assignee" onchange="updateSubtaskAssignee(${index}, this.value)">
                <option value="">Unassigned</option>
                ${renderAssigneeOptions(subtask.assigned_to_id)}
            </select>
            <button type="button" class="btn btn-danger btn-xs" onclick="removeSubtask(${index})">Remove</button>
        </div>
    `).join('');
}

// Add a new subtask
function addSubtask() {
    const newSubtask = {
        name: '',
        status: 'TODO',
        priority: 'MEDIUM',
        assigned_to_id: null,
        isNew: true
    };
    
    currentSubtasks.push(newSubtask);
    renderSubtasks();
    
    // Focus on the new subtask input
    setTimeout(() => {
        const inputs = document.querySelectorAll('.subtask-name');
        if (inputs.length > 0) {
            inputs[inputs.length - 1].focus();
        }
    }, 50);
}

// Remove a subtask
function removeSubtask(index) {
    const subtask = currentSubtasks[index];
    
    if (subtask.id) {
        // If it has an ID, it exists in the database
        if (confirm('Are you sure you want to delete this subtask?')) {
            fetch(`/api/subtasks/${subtask.id}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (response.ok) {
                    currentSubtasks.splice(index, 1);
                    renderSubtasks();
                    showNotification('Subtask deleted successfully', 'success');
                } else {
                    throw new Error('Failed to delete subtask');
                }
            })
            .catch(error => {
                console.error('Error deleting subtask:', error);
                showNotification('Error deleting subtask', 'error');
            });
        }
    } else {
        // Just remove from array if not saved yet
        currentSubtasks.splice(index, 1);
        renderSubtasks();
    }
}

// Update subtask name
function updateSubtaskName(index, name) {
    currentSubtasks[index].name = name;
}

// Update subtask priority
function updateSubtaskPriority(index, priority) {
    currentSubtasks[index].priority = priority;
}

// Update subtask assignee
function updateSubtaskAssignee(index, assigneeId) {
    currentSubtasks[index].assigned_to_id = assigneeId || null;
}

// Toggle subtask status
function toggleSubtaskStatus(index) {
    const subtask = currentSubtasks[index];
    const newStatus = subtask.status === 'DONE' ? 'TODO' : 'DONE';
    
    if (subtask.id) {
        // Update in database
        fetch(`/api/subtasks/${subtask.id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ status: newStatus })
        })
        .then(response => response.json())
        .then(updatedSubtask => {
            currentSubtasks[index] = updatedSubtask;
            renderSubtasks();
            updateTaskProgress();
        })
        .catch(error => {
            console.error('Error updating subtask status:', error);
            showNotification('Error updating subtask status', 'error');
            renderSubtasks(); // Re-render to revert checkbox
        });
    } else {
        currentSubtasks[index].status = newStatus;
    }
}

// Save all subtasks for a task
function saveSubtasks(taskId) {
    const promises = [];
    
    currentSubtasks.forEach(subtask => {
        if (subtask.isNew && subtask.name.trim()) {
            // Create new subtask
            promises.push(
                fetch('/api/subtasks', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        task_id: taskId,
                        name: subtask.name,
                        priority: subtask.priority,
                        assigned_to_id: subtask.assigned_to_id,
                        status: subtask.status
                    })
                })
                .then(response => response.json())
            );
        } else if (subtask.id && !subtask.isNew) {
            // Update existing subtask
            promises.push(
                fetch(`/api/subtasks/${subtask.id}`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        name: subtask.name,
                        priority: subtask.priority,
                        assigned_to_id: subtask.assigned_to_id,
                        status: subtask.status
                    })
                })
                .then(response => response.json())
            );
        }
    });
    
    return Promise.all(promises);
}

// Update task progress based on subtasks
function updateTaskProgress() {
    const taskId = document.getElementById('task-id').value;
    if (!taskId) return;
    
    // Refresh the task card in the board
    if (typeof refreshTaskCard === 'function') {
        refreshTaskCard(taskId);
    }
}

// Render assignee options
function renderAssigneeOptions(selectedId) {
    // This should be populated from the global team members list
    const teamMembers = window.teamMembers || [];
    return teamMembers.map(member => 
        `<option value="${member.id}" ${member.id == selectedId ? 'selected' : ''}>${escapeHtml(member.username)}</option>`
    ).join('');
}

// Helper function to escape HTML
function escapeHtml(unsafe) {
    return unsafe
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Display subtasks in task cards
function renderSubtasksInCard(subtasks) {
    if (!subtasks || subtasks.length === 0) return '';
    
    const completedCount = subtasks.filter(s => s.status === 'COMPLETED').length;
    const totalCount = subtasks.length;
    const percentage = Math.round((completedCount / totalCount) * 100);
    
    return `
        <div class="task-subtasks">
            <div class="subtask-progress">
                <div class="subtask-progress-bar">
                    <div class="subtask-progress-fill" style="width: ${percentage}%"></div>
                </div>
                <span class="subtask-count">${completedCount}/${totalCount} subtasks</span>
            </div>
        </div>
    `;
}

// Add subtask styles
const subtaskStyles = `
<style>
/* Subtask Styles - Compact */
.subtask-item {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    margin-bottom: 0.4rem;
    padding: 0.4rem 0.5rem;
    background: #f8f9fa;
    border-radius: 4px;
    border: 1px solid #e9ecef;
}

.subtask-checkbox {
    cursor: pointer;
    width: 18px;
    height: 18px;
}

.subtask-name {
    flex: 2;
    padding: 0.3rem 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.85rem;
}

.subtask-priority {
    flex: 0.8;
    padding: 0.3rem 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.8rem;
}

.subtask-assignee {
    flex: 1.2;
    padding: 0.3rem 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.8rem;
}

.no-subtasks {
    color: #6c757d;
    font-style: italic;
    text-align: center;
    padding: 1rem;
}

/* Subtask progress in task cards */
.task-subtasks {
    margin-top: 0.75rem;
    padding-top: 0.75rem;
    border-top: 1px solid #e9ecef;
}

.subtask-progress {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.subtask-progress-bar {
    flex: 1;
    height: 6px;
    background: #e9ecef;
    border-radius: 3px;
    overflow: hidden;
}

.subtask-progress-fill {
    height: 100%;
    background: #28a745;
    transition: width 0.3s ease;
}

.subtask-count {
    font-size: 0.75rem;
    color: #6c757d;
    white-space: nowrap;
}
</style>
`;

// Inject styles when document is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        document.head.insertAdjacentHTML('beforeend', subtaskStyles);
    });
} else {
    document.head.insertAdjacentHTML('beforeend', subtaskStyles);
}