// Pull-to-Refresh implementation for mobile
(function() {
    'use strict';
    
    class PullToRefresh {
        constructor(options = {}) {
            this.container = options.container || document.querySelector('.content');
            this.onRefresh = options.onRefresh || (() => location.reload());
            this.threshold = options.threshold || 80;
            this.max = options.max || 120;
            
            this.startY = 0;
            this.currentY = 0;
            this.pulling = false;
            this.refreshing = false;
            
            if (this.container && this.isMobile()) {
                this.init();
            }
        }
        
        isMobile() {
            return window.innerWidth <= 768 || 
                   /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        }
        
        init() {
            // Create pull-to-refresh indicator
            this.createIndicator();
            
            // Add touch event listeners
            this.container.addEventListener('touchstart', this.onTouchStart.bind(this), { passive: true });
            this.container.addEventListener('touchmove', this.onTouchMove.bind(this), { passive: false });
            this.container.addEventListener('touchend', this.onTouchEnd.bind(this));
        }
        
        createIndicator() {
            this.indicator = document.createElement('div');
            this.indicator.className = 'pull-refresh-indicator';
            this.indicator.innerHTML = `
                <div class="pull-refresh-spinner">
                    <i class="ti ti-refresh"></i>
                </div>
                <div class="pull-refresh-text">Pull to refresh</div>
            `;
            
            // Insert at the beginning of container
            this.container.insertBefore(this.indicator, this.container.firstChild);
            
            // Add styles
            this.addStyles();
        }
        
        addStyles() {
            if (document.getElementById('pull-refresh-styles')) return;
            
            const styles = `
                <style id="pull-refresh-styles">
                    .pull-refresh-indicator {
                        position: absolute;
                        top: -60px;
                        left: 0;
                        right: 0;
                        height: 60px;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        opacity: 0;
                        transform: scale(0.8);
                        transition: opacity 0.2s, transform 0.2s;
                    }
                    
                    .pull-refresh-indicator.visible {
                        opacity: 1;
                        transform: scale(1);
                    }
                    
                    .pull-refresh-indicator.refreshing {
                        position: fixed;
                        top: 20px;
                        z-index: 1000;
                    }
                    
                    .pull-refresh-spinner {
                        width: 40px;
                        height: 40px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        background: white;
                        border-radius: 50%;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                    }
                    
                    .pull-refresh-spinner i {
                        font-size: 24px;
                        color: var(--primary-color, #667eea);
                        transition: transform 0.3s ease;
                    }
                    
                    .pull-refresh-indicator.pulling .pull-refresh-spinner i {
                        transform: rotate(180deg);
                    }
                    
                    .pull-refresh-indicator.refreshing .pull-refresh-spinner i {
                        animation: spin 1s linear infinite;
                    }
                    
                    .pull-refresh-text {
                        margin-top: 4px;
                        font-size: 12px;
                        color: var(--text-muted, #999);
                    }
                    
                    @keyframes spin {
                        from { transform: rotate(0deg); }
                        to { transform: rotate(360deg); }
                    }
                    
                    /* Container adjustments */
                    .content {
                        position: relative;
                        overflow-y: auto;
                        -webkit-overflow-scrolling: touch;
                    }
                    
                    .content.pulling {
                        overflow-y: hidden;
                    }
                </style>
            `;
            
            document.head.insertAdjacentHTML('beforeend', styles);
        }
        
        onTouchStart(e) {
            if (this.refreshing) return;
            
            // Only activate at the top of the page
            if (this.container.scrollTop === 0) {
                this.startY = e.touches[0].clientY;
                this.pulling = true;
            }
        }
        
        onTouchMove(e) {
            if (!this.pulling || this.refreshing) return;
            
            this.currentY = e.touches[0].clientY;
            const diff = this.currentY - this.startY;
            
            if (diff > 0) {
                e.preventDefault();
                
                // Calculate pull distance with resistance
                const pullDistance = Math.min(diff * 0.5, this.max);
                
                // Update container transform
                this.container.style.transform = `translateY(${pullDistance}px)`;
                
                // Update indicator
                this.indicator.classList.add('visible');
                
                if (pullDistance >= this.threshold) {
                    this.indicator.classList.add('pulling');
                    this.updateText('Release to refresh');
                } else {
                    this.indicator.classList.remove('pulling');
                    this.updateText('Pull to refresh');
                }
            }
        }
        
        onTouchEnd() {
            if (!this.pulling || this.refreshing) return;
            
            const diff = this.currentY - this.startY;
            const pullDistance = Math.min(diff * 0.5, this.max);
            
            this.pulling = false;
            this.container.style.transition = 'transform 0.3s ease';
            
            if (pullDistance >= this.threshold) {
                // Trigger refresh
                this.refresh();
            } else {
                // Reset
                this.reset();
            }
        }
        
        refresh() {
            this.refreshing = true;
            this.container.style.transform = 'translateY(60px)';
            this.indicator.classList.add('refreshing');
            this.updateText('Refreshing...');
            
            // Add haptic feedback if available
            if (navigator.vibrate) {
                navigator.vibrate(10);
            }
            
            // Call refresh callback
            Promise.resolve(this.onRefresh()).then(() => {
                setTimeout(() => {
                    this.reset();
                }, 500);
            });
        }
        
        reset() {
            this.container.style.transform = '';
            this.indicator.classList.remove('visible', 'pulling', 'refreshing');
            
            setTimeout(() => {
                this.container.style.transition = '';
                this.refreshing = false;
                this.currentY = 0;
            }, 300);
        }
        
        updateText(text) {
            const textEl = this.indicator.querySelector('.pull-refresh-text');
            if (textEl) textEl.textContent = text;
        }
    }
    
    // Auto-initialize on common containers
    document.addEventListener('DOMContentLoaded', function() {
        // Time tracking page
        if (document.querySelector('.time-tracking-container')) {
            new PullToRefresh({
                container: document.querySelector('.time-tracking-container'),
                onRefresh: () => {
                    // Refresh time entries
                    if (window.loadTimeEntries) {
                        return window.loadTimeEntries();
                    }
                }
            });
        }
        
        // Notes list
        if (document.querySelector('.notes-container')) {
            new PullToRefresh({
                container: document.querySelector('.notes-container'),
                onRefresh: () => {
                    // Refresh notes
                    if (window.refreshNotes) {
                        return window.refreshNotes();
                    }
                }
            });
        }
    });
    
    // Expose globally
    window.PullToRefresh = PullToRefresh;
})();