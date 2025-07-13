// Date Picker Enhancer - Makes date/time inputs respect user preferences
(function() {
    'use strict';
    
    // Enhanced date input that shows user's preferred format
    class EnhancedDateInput {
        constructor(input) {
            this.nativeInput = input;
            this.userPrefs = DateFormatter.getUserPreferences();
            this.isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) || window.innerWidth <= 768;
            
            // Only enhance date and datetime-local inputs
            if (input.type !== 'date' && input.type !== 'datetime-local') {
                return;
            }
            
            // Check if already enhanced
            if (input.dataset.enhanced === 'true') {
                return;
            }
            
            this.enhance();
        }
        
        enhance() {
            // Skip if already in a hybrid date input structure
            if (this.nativeInput.classList.contains('date-input-native') || 
                this.nativeInput.closest('.hybrid-date-input')) {
                return;
            }
            
            // Mark as enhanced
            this.nativeInput.dataset.enhanced = 'true';
            
            // Create wrapper
            const wrapper = document.createElement('div');
            wrapper.className = 'enhanced-date-wrapper';
            
            // Create formatted text input
            this.textInput = document.createElement('input');
            this.textInput.type = 'text';
            this.textInput.className = this.nativeInput.className + ' date-text-input';
            this.textInput.placeholder = this.getPlaceholder();
            this.textInput.required = this.nativeInput.required;
            
            // Copy other attributes
            if (this.nativeInput.id) {
                this.textInput.id = this.nativeInput.id + '-text';
            }
            
            // Hide native input but keep it functional
            this.nativeInput.style.position = 'absolute';
            this.nativeInput.style.opacity = '0';
            this.nativeInput.style.pointerEvents = 'none';
            this.nativeInput.style.zIndex = '-1';
            this.nativeInput.tabIndex = -1;
            
            // Insert wrapper
            this.nativeInput.parentNode.insertBefore(wrapper, this.nativeInput);
            wrapper.appendChild(this.nativeInput);
            wrapper.appendChild(this.textInput);
            
            // Add calendar icon button
            const calendarBtn = document.createElement('button');
            calendarBtn.type = 'button';
            calendarBtn.className = 'calendar-btn';
            calendarBtn.innerHTML = '<i class="ti ti-calendar"></i>';
            calendarBtn.title = 'Open date picker';
            calendarBtn.setAttribute('aria-label', 'Open date picker');
            wrapper.appendChild(calendarBtn);
            
            // Add mobile hint
            if (this.isMobile) {
                this.textInput.placeholder = this.textInput.placeholder + ' (tap to select)';
            }
            
            // Set initial value if exists
            if (this.nativeInput.value) {
                this.updateTextInput();
            }
            
            // Event listeners
            this.setupEventListeners(calendarBtn);
        }
        
        getPlaceholder() {
            const format = this.userPrefs.dateFormat;
            const isDateTime = this.nativeInput.type === 'datetime-local';
            
            const datePlaceholder = {
                'ISO': 'YYYY-MM-DD',
                'US': 'MM/DD/YYYY',
                'EU': 'DD/MM/YYYY',
                'UK': 'DD/MM/YYYY',
                'Readable': 'Jan 01, 2024',
                'Full': 'January 01, 2024'
            }[format] || 'YYYY-MM-DD';
            
            if (isDateTime) {
                const timePlaceholder = this.userPrefs.timeFormat24h ? 'HH:MM' : 'HH:MM AM';
                return `${datePlaceholder} ${timePlaceholder}`;
            }
            
            return datePlaceholder;
        }
        
        setupEventListeners(calendarBtn) {
            // On mobile, make the entire input area clickable for date picker
            if (this.isMobile) {
                this.textInput.addEventListener('focus', (e) => {
                    e.preventDefault();
                    // Trigger calendar button click
                    calendarBtn.click();
                    this.textInput.blur();
                });
                
                // Make text input read-only on mobile to prevent keyboard
                this.textInput.readOnly = true;
                this.textInput.style.cursor = 'pointer';
            } else {
                // Desktop behavior - allow typing
                this.textInput.addEventListener('blur', () => {
                    this.parseUserInput();
                });
                
                // Allow Enter key to trigger parsing
                this.textInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        this.parseUserInput();
                    }
                });
            }
            
            // When native input changes, update text input
            this.nativeInput.addEventListener('change', () => {
                this.updateTextInput();
            });
            
            // Calendar button shows native picker
            calendarBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                
                // On mobile, we need different handling
                if (window.innerWidth <= 768) {
                    // For mobile, overlay the native input over the button temporarily
                    this.nativeInput.style.position = 'absolute';
                    this.nativeInput.style.top = '0';
                    this.nativeInput.style.left = '0';
                    this.nativeInput.style.width = '100%';
                    this.nativeInput.style.height = '100%';
                    this.nativeInput.style.opacity = '0.01'; // Almost invisible but interactive
                    this.nativeInput.style.pointerEvents = 'auto';
                    this.nativeInput.style.zIndex = '100';
                    
                    // Trigger the native picker
                    this.nativeInput.focus();
                    this.nativeInput.click();
                    
                    // Some mobile browsers need showPicker()
                    if (this.nativeInput.showPicker) {
                        try {
                            this.nativeInput.showPicker();
                        } catch (e) {
                            // Fallback if showPicker is not supported
                        }
                    }
                } else {
                    // Desktop behavior
                    this.nativeInput.style.opacity = '1';
                    this.nativeInput.style.pointerEvents = 'auto';
                    this.nativeInput.focus();
                    this.nativeInput.click();
                }
                
                // Hide native input after interaction
                const hideNative = () => {
                    this.nativeInput.style.opacity = '0';
                    this.nativeInput.style.pointerEvents = 'none';
                    this.nativeInput.style.position = 'absolute';
                    this.nativeInput.style.zIndex = '-1';
                    this.nativeInput.removeEventListener('blur', hideNative);
                    this.nativeInput.removeEventListener('change', hideNative);
                };
                
                // Use timeout for mobile to ensure picker has opened
                if (window.innerWidth <= 768) {
                    setTimeout(() => {
                        this.nativeInput.addEventListener('blur', hideNative);
                        this.nativeInput.addEventListener('change', hideNative);
                    }, 100);
                } else {
                    this.nativeInput.addEventListener('blur', hideNative);
                    this.nativeInput.addEventListener('change', hideNative);
                }
            });
        }
        
        updateTextInput() {
            const value = this.nativeInput.value;
            if (!value) {
                this.textInput.value = '';
                return;
            }
            
            if (this.nativeInput.type === 'datetime-local') {
                // Format datetime
                const dt = new Date(value);
                this.textInput.value = DateFormatter.formatDateTime(dt);
            } else {
                // Format date only
                const dt = new Date(value + 'T00:00:00');
                this.textInput.value = DateFormatter.formatDate(dt);
            }
        }
        
        parseUserInput() {
            const input = this.textInput.value.trim();
            if (!input) {
                this.nativeInput.value = '';
                return;
            }
            
            try {
                const parsed = this.parseDate(input);
                if (parsed) {
                    // Convert to ISO format for native input
                    const year = parsed.getFullYear();
                    const month = String(parsed.getMonth() + 1).padStart(2, '0');
                    const day = String(parsed.getDate()).padStart(2, '0');
                    
                    if (this.nativeInput.type === 'datetime-local') {
                        const hours = String(parsed.getHours()).padStart(2, '0');
                        const minutes = String(parsed.getMinutes()).padStart(2, '0');
                        this.nativeInput.value = `${year}-${month}-${day}T${hours}:${minutes}`;
                    } else {
                        this.nativeInput.value = `${year}-${month}-${day}`;
                    }
                    
                    // Update text input with properly formatted value
                    this.updateTextInput();
                    
                    // Trigger change event on native input
                    this.nativeInput.dispatchEvent(new Event('change', { bubbles: true }));
                } else {
                    // Invalid input - restore previous value
                    this.updateTextInput();
                    this.textInput.classList.add('error');
                    setTimeout(() => this.textInput.classList.remove('error'), 2000);
                }
            } catch (e) {
                console.error('Date parsing error:', e);
                this.updateTextInput();
            }
        }
        
        parseDate(input) {
            // Remove extra spaces
            input = input.replace(/\s+/g, ' ').trim();
            
            // Try different parsing strategies based on user's format
            const format = this.userPrefs.dateFormat;
            let date = null;
            
            // Extract time if present
            let timeMatch = null;
            let dateStr = input;
            
            if (this.nativeInput.type === 'datetime-local') {
                // Look for time patterns
                const time24Match = input.match(/(\d{1,2}):(\d{2})(?::(\d{2}))?$/);
                const time12Match = input.match(/(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM|am|pm)$/i);
                
                if (time12Match) {
                    timeMatch = time12Match;
                    dateStr = input.substring(0, input.lastIndexOf(time12Match[0])).trim();
                } else if (time24Match) {
                    timeMatch = time24Match;
                    dateStr = input.substring(0, input.lastIndexOf(time24Match[0])).trim();
                }
            }
            
            // Parse date part based on format
            switch (format) {
                case 'US': // MM/DD/YYYY
                    const usMatch = dateStr.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/);
                    if (usMatch) {
                        date = new Date(usMatch[3], usMatch[1] - 1, usMatch[2]);
                    }
                    break;
                    
                case 'EU':
                case 'UK': // DD/MM/YYYY
                    const euMatch = dateStr.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})$/);
                    if (euMatch) {
                        date = new Date(euMatch[3], euMatch[2] - 1, euMatch[1]);
                    }
                    break;
                    
                case 'ISO': // YYYY-MM-DD
                    const isoMatch = dateStr.match(/^(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})$/);
                    if (isoMatch) {
                        date = new Date(isoMatch[1], isoMatch[2] - 1, isoMatch[3]);
                    }
                    break;
                    
                case 'Readable': // Jan 01, 2024
                case 'Full': // January 01, 2024
                    // Try to parse natural language dates
                    date = new Date(dateStr);
                    if (isNaN(date.getTime())) {
                        date = null;
                    }
                    break;
            }
            
            // If no specific format matched, try generic parsing
            if (!date) {
                date = new Date(dateStr);
                if (isNaN(date.getTime())) {
                    return null;
                }
            }
            
            // Add time if present
            if (timeMatch && date) {
                let hours = parseInt(timeMatch[1]);
                const minutes = parseInt(timeMatch[2]);
                const seconds = timeMatch[3] ? parseInt(timeMatch[3]) : 0;
                
                // Handle 12-hour format
                if (timeMatch[4]) {
                    const isPM = timeMatch[4].toUpperCase() === 'PM';
                    if (hours === 12 && !isPM) hours = 0;
                    else if (hours !== 12 && isPM) hours += 12;
                }
                
                date.setHours(hours, minutes, seconds);
            }
            
            return date;
        }
    }
    
    // Enhanced time input for 12/24 hour format
    class EnhancedTimeInput {
        constructor(input) {
            this.nativeInput = input;
            this.userPrefs = DateFormatter.getUserPreferences();
            
            if (input.type !== 'time' || input.dataset.enhanced === 'true') {
                return;
            }
            
            // Only enhance if user prefers 12-hour format
            if (this.userPrefs.timeFormat24h) {
                return; // Native time input already uses 24-hour format
            }
            
            this.enhance();
        }
        
        enhance() {
            // Similar enhancement for time inputs to show AM/PM
            // This is simpler since time inputs are already somewhat flexible
            
            // Add helper text
            const helper = document.createElement('small');
            helper.className = 'time-format-helper';
            helper.textContent = '12-hour format (use AM/PM)';
            this.nativeInput.parentNode.insertBefore(helper, this.nativeInput.nextSibling);
            
            this.nativeInput.dataset.enhanced = 'true';
        }
    }
    
    // Auto-enhance all date/time inputs
    function enhanceAllInputs() {
        // Enhance date and datetime-local inputs
        document.querySelectorAll('input[type="date"], input[type="datetime-local"]').forEach(input => {
            new EnhancedDateInput(input);
        });
        
        // Enhance time inputs
        document.querySelectorAll('input[type="time"]').forEach(input => {
            new EnhancedTimeInput(input);
        });
    }
    
    // CSS injection for styling
    function injectStyles() {
        if (document.getElementById('date-picker-enhancer-styles')) return;
        
        const styles = `
            <style id="date-picker-enhancer-styles">
                .enhanced-date-wrapper {
                    position: relative;
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                .date-text-input {
                    flex: 1;
                }
                
                .date-text-input.error {
                    border-color: var(--danger, #dc3545);
                    animation: shake 0.3s;
                }
                
                @keyframes shake {
                    0%, 100% { transform: translateX(0); }
                    25% { transform: translateX(-5px); }
                    75% { transform: translateX(5px); }
                }
                
                .calendar-btn {
                    padding: 8px 12px;
                    border: 1px solid var(--border-color, #dee2e6);
                    background: white;
                    border-radius: 4px;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                
                .calendar-btn:hover {
                    background: var(--bg-light, #f8f9fa);
                    border-color: var(--primary-color, #667eea);
                }
                
                .calendar-btn i {
                    font-size: 18px;
                    color: var(--primary-color, #667eea);
                }
                
                .time-format-helper {
                    display: block;
                    margin-top: 4px;
                    color: var(--text-muted, #6c757d);
                    font-size: 0.875em;
                }
                
                /* Mobile adjustments */
                @media (max-width: 768px) {
                    .enhanced-date-wrapper {
                        position: relative;
                        display: block;
                        width: 100%;
                    }
                    
                    .calendar-btn {
                        position: absolute;
                        right: 8px;
                        top: 50%;
                        transform: translateY(-50%);
                        padding: 12px;
                        min-width: 44px;
                        min-height: 44px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        z-index: 10;
                        background: white;
                        border: 1px solid var(--border-color, #dee2e6);
                    }
                    
                    .date-text-input {
                        padding-right: 56px;
                        width: 100%;
                        min-height: 48px;
                        font-size: 16px; /* Prevent zoom on iOS */
                        -webkit-appearance: none;
                        appearance: none;
                    }
                    
                    /* Read-only style on mobile */
                    .date-text-input[readonly] {
                        background-color: white;
                        cursor: pointer;
                        -webkit-tap-highlight-color: rgba(0,0,0,0.1);
                    }
                    
                    /* Larger tap target for wrapper */
                    .enhanced-date-wrapper {
                        min-height: 48px;
                    }
                    
                    /* Better touch targets */
                    .enhanced-date-wrapper input[type="date"],
                    .enhanced-date-wrapper input[type="datetime-local"] {
                        min-height: 48px;
                        width: 100%;
                    }
                }
            </style>
        `;
        
        document.head.insertAdjacentHTML('beforeend', styles);
    }
    
    // Initialize
    document.addEventListener('DOMContentLoaded', function() {
        // Make sure DateFormatter is loaded
        if (typeof DateFormatter === 'undefined') {
            console.error('DateFormatter not found. Make sure date-formatter.js is loaded first.');
            return;
        }
        
        injectStyles();
        enhanceAllInputs();
        
        // Re-enhance when new content is added dynamically
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) { // Element node
                        if (node.matches && (node.matches('input[type="date"]') || 
                            node.matches('input[type="time"]') || 
                            node.matches('input[type="datetime-local"]'))) {
                            new EnhancedDateInput(node);
                            new EnhancedTimeInput(node);
                        }
                        // Check children
                        const inputs = node.querySelectorAll('input[type="date"], input[type="time"], input[type="datetime-local"]');
                        inputs.forEach(input => {
                            new EnhancedDateInput(input);
                            new EnhancedTimeInput(input);
                        });
                    }
                });
            });
        });
        
        observer.observe(document.body, { childList: true, subtree: true });
    });
    
    // Expose for manual enhancement
    window.DatePickerEnhancer = {
        enhanceInput: function(input) {
            if (input.type === 'date' || input.type === 'datetime-local') {
                return new EnhancedDateInput(input);
            } else if (input.type === 'time') {
                return new EnhancedTimeInput(input);
            }
        },
        enhanceAll: enhanceAllInputs
    };
})();