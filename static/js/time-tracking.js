// Time Tracking JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Project/Task Selection
    const projectSelect = document.getElementById('project-select');
    const taskSelect = document.getElementById('task-select');
    const manualProjectSelect = document.getElementById('manual-project');
    const manualTaskSelect = document.getElementById('manual-task');
    
    // Update task dropdown when project is selected
    function updateTaskDropdown(projectSelectElement, taskSelectElement) {
        const projectId = projectSelectElement.value;
        
        if (!projectId) {
            taskSelectElement.disabled = true;
            taskSelectElement.innerHTML = '<option value="">Select a project first</option>';
            return;
        }
        
        // Fetch tasks for the selected project
        fetch(`/api/projects/${projectId}/tasks`)
            .then(response => {
                if (!response.ok) {
                    return response.json().then(data => {
                        throw new Error(data.error || `HTTP error! status: ${response.status}`);
                    });
                }
                return response.json();
            })
            .then(data => {
                taskSelectElement.disabled = false;
                taskSelectElement.innerHTML = '<option value="">No specific task</option>';
                
                if (data.tasks && data.tasks.length > 0) {
                    data.tasks.forEach(task => {
                        const option = document.createElement('option');
                        option.value = task.id;
                        option.textContent = `${task.title} (${task.status})`;
                        taskSelectElement.appendChild(option);
                    });
                } else {
                    taskSelectElement.innerHTML = '<option value="">No tasks available</option>';
                }
            })
            .catch(error => {
                console.error('Error fetching tasks:', error);
                taskSelectElement.disabled = true;
                taskSelectElement.innerHTML = `<option value="">Error: ${error.message}</option>`;
            });
    }
    
    if (projectSelect) {
        projectSelect.addEventListener('change', () => updateTaskDropdown(projectSelect, taskSelect));
    }
    
    if (manualProjectSelect) {
        manualProjectSelect.addEventListener('change', () => updateTaskDropdown(manualProjectSelect, manualTaskSelect));
    }
    
    // Start Work Form
    const startWorkForm = document.getElementById('start-work-form');
    if (startWorkForm) {
        startWorkForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const projectId = document.getElementById('project-select').value;
            const taskId = document.getElementById('task-select').value;
            const notes = document.getElementById('work-notes').value;
            
            fetch('/api/arrive', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    project_id: projectId || null,
                    task_id: taskId || null,
                    notes: notes || null
                }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    showNotification('Error: ' + data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('An error occurred while starting work', 'error');
            });
        });
    }
    
    // View Toggle
    const viewToggleBtns = document.querySelectorAll('.toggle-btn');
    const listView = document.getElementById('list-view');
    const gridView = document.getElementById('grid-view');
    
    viewToggleBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const view = this.getAttribute('data-view');
            
            // Update button states
            viewToggleBtns.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Show/hide views
            if (view === 'list') {
                listView.classList.add('active');
                gridView.classList.remove('active');
            } else {
                listView.classList.remove('active');
                gridView.classList.add('active');
            }
            
            // Save preference
            localStorage.setItem('timeTrackingView', view);
        });
    });
    
    // Restore view preference
    const savedView = localStorage.getItem('timeTrackingView') || 'list';
    if (savedView === 'grid') {
        document.querySelector('[data-view="grid"]').click();
    }
    
    // Modal Functions
    function openModal(modalId) {
        document.getElementById(modalId).style.display = 'block';
        document.body.style.overflow = 'hidden';
    }
    
    function closeModal(modalId) {
        document.getElementById(modalId).style.display = 'none';
        document.body.style.overflow = 'auto';
    }
    
    // Modal close buttons
    document.querySelectorAll('.modal-close, .modal-cancel').forEach(btn => {
        btn.addEventListener('click', function() {
            const modal = this.closest('.modal');
            closeModal(modal.id);
        });
    });
    
    // Close modal on overlay click
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', function() {
            const modal = this.closest('.modal');
            closeModal(modal.id);
        });
    });
    
    // Manual Entry
    const manualEntryBtn = document.getElementById('manual-entry-btn');
    if (manualEntryBtn) {
        manualEntryBtn.addEventListener('click', function() {
            // Set default dates to today
            const today = new Date().toISOString().split('T')[0];
            document.getElementById('manual-start-date').value = today;
            document.getElementById('manual-end-date').value = today;
            openModal('manual-modal');
        });
    }
    
    // Manual Entry Form Submission
    const manualEntryForm = document.getElementById('manual-entry-form');
    if (manualEntryForm) {
        manualEntryForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const startDate = document.getElementById('manual-start-date').value;
            const startTime = document.getElementById('manual-start-time').value;
            const endDate = document.getElementById('manual-end-date').value;
            const endTime = document.getElementById('manual-end-time').value;
            const projectId = document.getElementById('manual-project').value;
            const taskId = document.getElementById('manual-task').value;
            const breakMinutes = parseInt(document.getElementById('manual-break').value) || 0;
            const notes = document.getElementById('manual-notes').value;
            
            // Validate end time is after start time
            const startDateTime = new Date(`${startDate}T${startTime}`);
            const endDateTime = new Date(`${endDate}T${endTime}`);
            
            if (endDateTime <= startDateTime) {
                showNotification('End time must be after start time', 'error');
                return;
            }
            
            fetch('/api/manual-entry', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    start_date: startDate,
                    start_time: startTime,
                    end_date: endDate,
                    end_time: endTime,
                    project_id: projectId || null,
                    task_id: taskId || null,
                    break_minutes: breakMinutes,
                    notes: notes || null
                }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    closeModal('manual-modal');
                    location.reload();
                } else {
                    showNotification('Error: ' + data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('An error occurred while adding the manual entry', 'error');
            });
        });
    }
    
    // Edit Entry
    document.querySelectorAll('.edit-entry-btn').forEach(button => {
        button.addEventListener('click', function() {
            const entryId = this.getAttribute('data-id');
            
            // Fetch entry details
            fetch(`/api/time-entry/${entryId}`)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        const entry = data.entry;
                        
                        // Parse dates and times
                        const arrivalDate = new Date(entry.arrival_time);
                        const departureDate = entry.departure_time ? new Date(entry.departure_time) : null;
                        
                        // Set form values
                        document.getElementById('edit-entry-id').value = entry.id;
                        document.getElementById('edit-arrival-date').value = arrivalDate.toISOString().split('T')[0];
                        document.getElementById('edit-arrival-time').value = arrivalDate.toTimeString().substring(0, 5);
                        
                        if (departureDate) {
                            document.getElementById('edit-departure-date').value = departureDate.toISOString().split('T')[0];
                            document.getElementById('edit-departure-time').value = departureDate.toTimeString().substring(0, 5);
                        } else {
                            document.getElementById('edit-departure-date').value = '';
                            document.getElementById('edit-departure-time').value = '';
                        }
                        
                        document.getElementById('edit-project').value = entry.project_id || '';
                        document.getElementById('edit-notes').value = entry.notes || '';
                        
                        openModal('edit-modal');
                    } else {
                        showNotification('Error loading entry details', 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showNotification('An error occurred while loading entry details', 'error');
                });
        });
    });
    
    // Edit Entry Form Submission
    const editEntryForm = document.getElementById('edit-entry-form');
    if (editEntryForm) {
        editEntryForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const entryId = document.getElementById('edit-entry-id').value;
            const arrivalDate = document.getElementById('edit-arrival-date').value;
            const arrivalTime = document.getElementById('edit-arrival-time').value;
            const departureDate = document.getElementById('edit-departure-date').value;
            const departureTime = document.getElementById('edit-departure-time').value;
            const projectId = document.getElementById('edit-project').value;
            const notes = document.getElementById('edit-notes').value;
            
            // Format datetime strings
            const arrivalDateTime = `${arrivalDate}T${arrivalTime}:00`;
            let departureDateTime = null;
            
            if (departureDate && departureTime) {
                departureDateTime = `${departureDate}T${departureTime}:00`;
            }
            
            fetch(`/api/update/${entryId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    arrival_time: arrivalDateTime,
                    departure_time: departureDateTime,
                    project_id: projectId || null,
                    notes: notes || null
                }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    closeModal('edit-modal');
                    location.reload();
                } else {
                    showNotification('Error: ' + data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('An error occurred while updating the entry', 'error');
            });
        });
    }
    
    // Delete Entry
    document.querySelectorAll('.delete-entry-btn').forEach(button => {
        button.addEventListener('click', function() {
            const entryId = this.getAttribute('data-id');
            document.getElementById('delete-entry-id').value = entryId;
            openModal('delete-modal');
        });
    });
    
    // Confirm Delete
    const confirmDeleteBtn = document.getElementById('confirm-delete');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', function() {
            const entryId = document.getElementById('delete-entry-id').value;
            
            fetch(`/api/delete/${entryId}`, {
                method: 'DELETE',
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    closeModal('delete-modal');
                    // Remove the row/card from the DOM
                    const row = document.querySelector(`tr[data-entry-id="${entryId}"]`);
                    const card = document.querySelector(`.entry-card[data-entry-id="${entryId}"]`);
                    if (row) row.remove();
                    if (card) card.remove();
                    showNotification('Entry deleted successfully', 'success');
                } else {
                    showNotification('Error: ' + data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('An error occurred while deleting the entry', 'error');
            });
        });
    }
    
    // Resume Work
    document.querySelectorAll('.resume-work-btn').forEach(button => {
        button.addEventListener('click', function() {
            // Skip if button is disabled
            if (this.disabled) {
                return;
            }
            
            const entryId = this.getAttribute('data-id');
            
            fetch(`/api/resume/${entryId}`, {
                method: 'POST',
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    location.reload();
                } else {
                    showNotification('Error: ' + data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('An error occurred while resuming work', 'error');
            });
        });
    });
    
    // Notification function
    function showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Add to page
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => notification.classList.add('show'), 10);
        
        // Remove after 5 seconds
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
});

// Add notification styles
const style = document.createElement('style');
style.textContent = `
.notification {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 1rem 1.5rem;
    border-radius: 8px;
    background: white;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    transform: translateX(400px);
    transition: transform 0.3s ease;
    z-index: 9999;
    max-width: 350px;
}

.notification.show {
    transform: translateX(0);
}

.notification-success {
    background: #d1fae5;
    color: #065f46;
    border: 1px solid #6ee7b7;
}

.notification-error {
    background: #fee2e2;
    color: #991b1b;
    border: 1px solid #fca5a5;
}

.notification-info {
    background: #dbeafe;
    color: #1e40af;
    border: 1px solid #93c5fd;
}
`;
document.head.appendChild(style);