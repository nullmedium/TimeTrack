// Mobile Table Enhancements for TimeTrack
document.addEventListener('DOMContentLoaded', function() {
    
    // Configuration
    const MOBILE_BREAKPOINT = 768;
    const CARD_VIEW_BREAKPOINT = 576;
    
    // Initialize all data tables
    function initMobileTables() {
        const tables = document.querySelectorAll('.data-table, table');
        
        tables.forEach(table => {
            // Wrap tables in responsive container
            if (!table.closest('.table-responsive')) {
                const wrapper = document.createElement('div');
                wrapper.className = 'table-responsive';
                table.parentNode.insertBefore(wrapper, table);
                wrapper.appendChild(table);
                
                // Check if table is scrollable
                checkTableScroll(wrapper);
            }
            
            // Add mobile-specific attributes
            if (window.innerWidth <= CARD_VIEW_BREAKPOINT) {
                convertTableToCards(table);
            }
        });
    }
    
    // Check if table needs horizontal scroll
    function checkTableScroll(wrapper) {
        const table = wrapper.querySelector('table');
        if (table.scrollWidth > wrapper.clientWidth) {
            wrapper.classList.add('scrollable');
            addScrollIndicator(wrapper);
        } else {
            wrapper.classList.remove('scrollable');
        }
    }
    
    // Add visual scroll indicator
    function addScrollIndicator(wrapper) {
        if (!wrapper.querySelector('.scroll-indicator')) {
            const indicator = document.createElement('div');
            indicator.className = 'scroll-indicator';
            indicator.innerHTML = '<i class="ti ti-arrow-right"></i> Scroll for more';
            wrapper.appendChild(indicator);
            
            // Hide indicator when scrolled to end
            wrapper.addEventListener('scroll', function() {
                const maxScroll = this.scrollWidth - this.clientWidth;
                if (this.scrollLeft >= maxScroll - 10) {
                    indicator.style.opacity = '0';
                } else {
                    indicator.style.opacity = '1';
                }
            });
        }
    }
    
    // Convert table to card layout for mobile
    function convertTableToCards(table) {
        // Skip if already converted or marked to skip
        if (table.classList.contains('no-card-view') || table.dataset.mobileCards === 'true') {
            return;
        }
        
        const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
        const rows = table.querySelectorAll('tbody tr');
        
        // Create card container
        const cardContainer = document.createElement('div');
        cardContainer.className = 'mobile-card-view';
        cardContainer.setAttribute('role', 'list');
        
        rows.forEach((row, rowIndex) => {
            const card = createCardFromRow(row, headers);
            cardContainer.appendChild(card);
        });
        
        // Insert card view before table
        table.parentNode.insertBefore(cardContainer, table);
        
        // Add classes for toggling
        table.classList.add('desktop-table-view');
        table.dataset.mobileCards = 'true';
    }
    
    // Create a card element from table row
    function createCardFromRow(row, headers) {
        const cells = row.querySelectorAll('td');
        const card = document.createElement('div');
        card.className = 'table-card';
        card.setAttribute('role', 'listitem');
        
        // Check for special data attributes
        const primaryField = row.dataset.primaryField || 0;
        const secondaryField = row.dataset.secondaryField || 1;
        
        // Create card header with primary info
        if (cells[primaryField]) {
            const cardHeader = document.createElement('div');
            cardHeader.className = 'table-card-header';
            cardHeader.innerHTML = cells[primaryField].innerHTML;
            card.appendChild(cardHeader);
        }
        
        // Create card body with other fields
        const cardBody = document.createElement('div');
        cardBody.className = 'table-card-body';
        
        cells.forEach((cell, index) => {
            // Skip primary field as it's in header
            if (index === primaryField) return;
            
            const field = document.createElement('div');
            field.className = 'table-card-field';
            
            const label = document.createElement('span');
            label.className = 'table-card-label';
            label.textContent = headers[index] || '';
            
            const value = document.createElement('span');
            value.className = 'table-card-value';
            value.innerHTML = cell.innerHTML;
            
            field.appendChild(label);
            field.appendChild(value);
            cardBody.appendChild(field);
        });
        
        card.appendChild(cardBody);
        
        // Copy any data attributes from row
        Array.from(row.attributes).forEach(attr => {
            if (attr.name.startsWith('data-')) {
                card.setAttribute(attr.name, attr.value);
            }
        });
        
        // Copy click handlers if any
        if (row.onclick) {
            card.onclick = row.onclick;
            card.style.cursor = 'pointer';
        }
        
        return card;
    }
    
    // Time entry table specific enhancements
    function enhanceTimeEntryTable() {
        const timeTable = document.querySelector('.time-entries-table');
        if (!timeTable) return;
        
        if (window.innerWidth <= MOBILE_BREAKPOINT) {
            // Add swipe actions for time entries
            addSwipeActions(timeTable);
            
            // Compact view for mobile
            timeTable.classList.add('mobile-compact');
        }
    }
    
    // Add swipe gestures to table rows
    function addSwipeActions(table) {
        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            let startX = 0;
            let currentX = 0;
            let isDragging = false;
            
            row.addEventListener('touchstart', handleTouchStart, { passive: true });
            row.addEventListener('touchmove', handleTouchMove, { passive: true });
            row.addEventListener('touchend', handleTouchEnd);
            
            function handleTouchStart(e) {
                startX = e.touches[0].clientX;
                isDragging = true;
                row.style.transition = 'none';
            }
            
            function handleTouchMove(e) {
                if (!isDragging) return;
                
                currentX = e.touches[0].clientX;
                const diffX = currentX - startX;
                
                // Limit swipe distance
                const maxSwipe = 100;
                const swipeX = Math.max(-maxSwipe, Math.min(maxSwipe, diffX));
                
                row.style.transform = `translateX(${swipeX}px)`;
                
                // Show action indicators
                if (swipeX < -50) {
                    row.classList.add('swipe-delete');
                } else if (swipeX > 50) {
                    row.classList.add('swipe-edit');
                } else {
                    row.classList.remove('swipe-delete', 'swipe-edit');
                }
            }
            
            function handleTouchEnd(e) {
                if (!isDragging) return;
                
                const diffX = currentX - startX;
                row.style.transition = 'transform 0.3s ease';
                row.style.transform = '';
                
                // Trigger actions based on swipe distance
                if (diffX < -80) {
                    // Delete action
                    const deleteBtn = row.querySelector('.delete-btn');
                    if (deleteBtn) deleteBtn.click();
                } else if (diffX > 80) {
                    // Edit action
                    const editBtn = row.querySelector('.edit-btn');
                    if (editBtn) editBtn.click();
                }
                
                row.classList.remove('swipe-delete', 'swipe-edit');
                isDragging = false;
            }
        });
    }
    
    // Handle responsive table on window resize
    function handleResize() {
        const tables = document.querySelectorAll('.table-responsive');
        tables.forEach(wrapper => {
            checkTableScroll(wrapper);
        });
        
        // Re-initialize tables if crossing breakpoint
        if (window.innerWidth <= CARD_VIEW_BREAKPOINT) {
            initMobileTables();
        }
        
        // Update time entry table
        enhanceTimeEntryTable();
    }
    
    // Add CSS for card view
    function injectCardStyles() {
        if (document.getElementById('mobile-table-styles')) return;
        
        const styles = `
            <style id="mobile-table-styles">
                .table-card {
                    background: var(--bg-light);
                    border: 1px solid var(--border-color);
                    border-radius: 8px;
                    padding: 16px;
                    margin-bottom: 12px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                    transition: transform 0.2s ease, box-shadow 0.2s ease;
                }
                
                .table-card:hover {
                    transform: translateY(-2px);
                    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                }
                
                .table-card-header {
                    font-weight: 600;
                    font-size: 16px;
                    margin-bottom: 12px;
                    color: var(--text-primary);
                }
                
                .table-card-body {
                    display: grid;
                    gap: 8px;
                }
                
                .table-card-field {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 4px 0;
                }
                
                .table-card-label {
                    font-size: 13px;
                    color: var(--text-muted);
                    flex-shrink: 0;
                    margin-right: 12px;
                }
                
                .table-card-value {
                    text-align: right;
                    font-size: 14px;
                    color: var(--text-secondary);
                }
                
                .scroll-indicator {
                    position: absolute;
                    right: 0;
                    top: 50%;
                    transform: translateY(-50%);
                    background: linear-gradient(to right, transparent, rgba(255,255,255,0.9));
                    padding: 8px 16px 8px 32px;
                    pointer-events: none;
                    transition: opacity 0.3s ease;
                    font-size: 13px;
                    color: var(--text-muted);
                }
                
                /* Swipe action styles */
                .swipe-delete {
                    background-color: rgba(255, 59, 48, 0.1);
                }
                
                .swipe-edit {
                    background-color: rgba(52, 199, 89, 0.1);
                }
                
                /* Mobile compact view */
                .mobile-compact td {
                    padding: 8px 6px;
                    font-size: 13px;
                }
                
                .mobile-compact .btn-sm {
                    padding: 4px 8px;
                    font-size: 12px;
                }
            </style>
        `;
        
        document.head.insertAdjacentHTML('beforeend', styles);
    }
    
    // Initialize on load
    injectCardStyles();
    initMobileTables();
    enhanceTimeEntryTable();
    
    // Handle window resize
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(handleResize, 250);
    });
    
    // Export functions for external use
    window.MobileTables = {
        init: initMobileTables,
        convertToCards: convertTableToCards,
        enhanceTimeEntry: enhanceTimeEntryTable
    };
});