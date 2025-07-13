// Enhanced Mobile Gesture Support
(function() {
    'use strict';
    
    class MobileGestures {
        constructor() {
            this.touchStartX = 0;
            this.touchStartY = 0;
            this.touchEndX = 0;
            this.touchEndY = 0;
            this.longPressTimer = null;
            
            this.init();
        }
        
        init() {
            // Only initialize on mobile
            if (!this.isMobile()) return;
            
            // Add swipe to navigate back
            this.initSwipeBack();
            
            // Add long press for context menus
            this.initLongPress();
            
            // Add swipe actions for list items
            this.initSwipeActions();
            
            // Add pinch to zoom for images/charts
            this.initPinchZoom();
        }
        
        isMobile() {
            return window.innerWidth <= 768 || 'ontouchstart' in window;
        }
        
        // Swipe from left edge to go back
        initSwipeBack() {
            let startX = 0;
            let startY = 0;
            let startTime = 0;
            
            document.addEventListener('touchstart', (e) => {
                const touch = e.touches[0];
                startX = touch.clientX;
                startY = touch.clientY;
                startTime = Date.now();
                
                // Only track if starting from left edge
                if (startX > 30) return;
                
                // Add visual indicator
                this.showSwipeIndicator();
            }, { passive: true });
            
            document.addEventListener('touchmove', (e) => {
                if (startX > 30) return;
                
                const touch = e.touches[0];
                const diffX = touch.clientX - startX;
                const diffY = Math.abs(touch.clientY - startY);
                
                // Horizontal swipe detection
                if (diffX > 50 && diffY < 50) {
                    this.updateSwipeIndicator(diffX);
                }
            }, { passive: true });
            
            document.addEventListener('touchend', (e) => {
                if (startX > 30) return;
                
                const endTime = Date.now();
                const timeDiff = endTime - startTime;
                const touch = e.changedTouches[0];
                const diffX = touch.clientX - startX;
                
                this.hideSwipeIndicator();
                
                // Quick swipe from edge
                if (timeDiff < 300 && diffX > 100) {
                    this.navigateBack();
                }
            });
        }
        
        // Long press for context actions
        initLongPress() {
            const longPressElements = document.querySelectorAll('[data-long-press]');
            
            longPressElements.forEach(element => {
                element.addEventListener('touchstart', (e) => {
                    this.longPressTimer = setTimeout(() => {
                        this.showContextMenu(element, e);
                        
                        // Haptic feedback
                        if (navigator.vibrate) {
                            navigator.vibrate(50);
                        }
                    }, 500);
                }, { passive: true });
                
                element.addEventListener('touchend', () => {
                    clearTimeout(this.longPressTimer);
                });
                
                element.addEventListener('touchmove', () => {
                    clearTimeout(this.longPressTimer);
                });
            });
        }
        
        // Swipe actions on list items
        initSwipeActions() {
            const swipeElements = document.querySelectorAll('[data-swipe-actions]');
            
            swipeElements.forEach(element => {
                let startX = 0;
                let currentX = 0;
                let startTime = 0;
                
                element.addEventListener('touchstart', (e) => {
                    startX = e.touches[0].clientX;
                    startTime = Date.now();
                    element.style.transition = 'none';
                }, { passive: true });
                
                element.addEventListener('touchmove', (e) => {
                    currentX = e.touches[0].clientX;
                    const diffX = currentX - startX;
                    
                    // Limit swipe distance
                    const maxSwipe = 100;
                    const swipeX = Math.max(-maxSwipe, Math.min(maxSwipe, diffX));
                    
                    element.style.transform = `translateX(${swipeX}px)`;
                    
                    // Show action hints
                    if (swipeX < -50) {
                        element.classList.add('swipe-left');
                        element.classList.remove('swipe-right');
                    } else if (swipeX > 50) {
                        element.classList.add('swipe-right');
                        element.classList.remove('swipe-left');
                    } else {
                        element.classList.remove('swipe-left', 'swipe-right');
                    }
                }, { passive: true });
                
                element.addEventListener('touchend', (e) => {
                    const endTime = Date.now();
                    const timeDiff = endTime - startTime;
                    const diffX = currentX - startX;
                    
                    element.style.transition = 'transform 0.3s ease';
                    element.style.transform = '';
                    
                    // Quick swipe actions
                    if (timeDiff < 300) {
                        if (diffX < -80) {
                            this.triggerSwipeAction(element, 'left');
                        } else if (diffX > 80) {
                            this.triggerSwipeAction(element, 'right');
                        }
                    }
                    
                    element.classList.remove('swipe-left', 'swipe-right');
                });
            });
        }
        
        // Pinch to zoom for images
        initPinchZoom() {
            const zoomElements = document.querySelectorAll('[data-zoomable]');
            
            zoomElements.forEach(element => {
                let initialDistance = 0;
                let currentScale = 1;
                
                element.addEventListener('touchstart', (e) => {
                    if (e.touches.length === 2) {
                        initialDistance = this.getDistance(e.touches[0], e.touches[1]);
                    }
                }, { passive: true });
                
                element.addEventListener('touchmove', (e) => {
                    if (e.touches.length === 2) {
                        e.preventDefault();
                        const currentDistance = this.getDistance(e.touches[0], e.touches[1]);
                        currentScale = currentDistance / initialDistance;
                        currentScale = Math.max(0.5, Math.min(3, currentScale));
                        
                        element.style.transform = `scale(${currentScale})`;
                    }
                }, { passive: false });
                
                element.addEventListener('touchend', () => {
                    if (currentScale < 0.8 || currentScale > 2.5) {
                        element.style.transition = 'transform 0.3s ease';
                        element.style.transform = 'scale(1)';
                        currentScale = 1;
                    }
                });
            });
        }
        
        // Helper methods
        getDistance(touch1, touch2) {
            const dx = touch1.clientX - touch2.clientX;
            const dy = touch1.clientY - touch2.clientY;
            return Math.sqrt(dx * dx + dy * dy);
        }
        
        showSwipeIndicator() {
            if (!this.swipeIndicator) {
                this.swipeIndicator = document.createElement('div');
                this.swipeIndicator.className = 'swipe-back-indicator';
                this.swipeIndicator.innerHTML = '<i class="ti ti-chevron-right"></i>';
                document.body.appendChild(this.swipeIndicator);
            }
            this.swipeIndicator.classList.add('visible');
        }
        
        updateSwipeIndicator(progress) {
            if (this.swipeIndicator) {
                const opacity = Math.min(1, progress / 100);
                const scale = 0.8 + (0.2 * opacity);
                this.swipeIndicator.style.opacity = opacity;
                this.swipeIndicator.style.transform = `translateX(${progress * 0.3}px) scale(${scale})`;
            }
        }
        
        hideSwipeIndicator() {
            if (this.swipeIndicator) {
                this.swipeIndicator.classList.remove('visible');
            }
        }
        
        navigateBack() {
            // Check if there's a back button
            const backBtn = document.querySelector('.btn-back, [href*="javascript:history.back"]');
            if (backBtn) {
                backBtn.click();
            } else {
                history.back();
            }
        }
        
        showContextMenu(element, event) {
            const actions = element.dataset.longPress.split(',');
            
            // Create context menu
            const menu = document.createElement('div');
            menu.className = 'mobile-context-menu';
            menu.style.top = `${event.touches[0].clientY}px`;
            menu.style.left = `${event.touches[0].clientX}px`;
            
            actions.forEach(action => {
                const [label, handler] = action.split(':');
                const item = document.createElement('button');
                item.textContent = label;
                item.onclick = () => {
                    if (window[handler]) {
                        window[handler](element);
                    }
                    menu.remove();
                };
                menu.appendChild(item);
            });
            
            document.body.appendChild(menu);
            
            // Remove on outside click
            setTimeout(() => {
                document.addEventListener('touchstart', () => menu.remove(), { once: true });
            }, 100);
        }
        
        triggerSwipeAction(element, direction) {
            const action = element.dataset[`swipe${direction.charAt(0).toUpperCase() + direction.slice(1)}`];
            if (action && window[action]) {
                window[action](element);
            }
        }
    }
    
    // Add CSS for gestures
    function addGestureStyles() {
        if (document.getElementById('gesture-styles')) return;
        
        const styles = `
            <style id="gesture-styles">
                /* Swipe back indicator */
                .swipe-back-indicator {
                    position: fixed;
                    left: 0;
                    top: 50%;
                    transform: translateY(-50%);
                    width: 40px;
                    height: 40px;
                    background: rgba(0,0,0,0.8);
                    border-radius: 0 20px 20px 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    opacity: 0;
                    transition: opacity 0.2s;
                    z-index: 1000;
                    pointer-events: none;
                }
                
                .swipe-back-indicator.visible {
                    opacity: 1;
                }
                
                /* Swipe actions */
                [data-swipe-actions] {
                    position: relative;
                    overflow: hidden;
                }
                
                [data-swipe-actions]::before,
                [data-swipe-actions]::after {
                    content: '';
                    position: absolute;
                    top: 0;
                    bottom: 0;
                    width: 100px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    opacity: 0;
                    transition: opacity 0.2s;
                }
                
                [data-swipe-actions]::before {
                    left: 0;
                    background: linear-gradient(to right, #4CAF50, transparent);
                }
                
                [data-swipe-actions]::after {
                    right: 0;
                    background: linear-gradient(to left, #F44336, transparent);
                }
                
                [data-swipe-actions].swipe-right::before,
                [data-swipe-actions].swipe-left::after {
                    opacity: 0.3;
                }
                
                /* Context menu */
                .mobile-context-menu {
                    position: fixed;
                    background: white;
                    border-radius: 8px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.2);
                    padding: 8px 0;
                    z-index: 1000;
                    min-width: 150px;
                    transform: scale(0.8);
                    animation: contextMenuIn 0.2s ease forwards;
                }
                
                @keyframes contextMenuIn {
                    to {
                        transform: scale(1);
                    }
                }
                
                .mobile-context-menu button {
                    display: block;
                    width: 100%;
                    padding: 12px 16px;
                    border: none;
                    background: none;
                    text-align: left;
                    font-size: 16px;
                    cursor: pointer;
                }
                
                .mobile-context-menu button:hover {
                    background: #f5f5f5;
                }
                
                /* Pinch zoom */
                [data-zoomable] {
                    touch-action: pinch-zoom;
                    transition: transform 0.3s ease;
                }
            </style>
        `;
        
        document.head.insertAdjacentHTML('beforeend', styles);
    }
    
    // Initialize
    document.addEventListener('DOMContentLoaded', function() {
        addGestureStyles();
        new MobileGestures();
    });
    
    window.MobileGestures = MobileGestures;
})();