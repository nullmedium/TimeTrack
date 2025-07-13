// Mobile Performance Optimizations
(function() {
    'use strict';
    
    // Lazy Loading for Images
    class LazyLoader {
        constructor() {
            this.imageObserver = null;
            this.init();
        }
        
        init() {
            // Check for IntersectionObserver support
            if ('IntersectionObserver' in window) {
                this.imageObserver = new IntersectionObserver((entries, observer) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            this.loadImage(entry.target);
                            observer.unobserve(entry.target);
                        }
                    });
                }, {
                    rootMargin: '50px 0px',
                    threshold: 0.01
                });
                
                // Start observing images
                this.observeImages();
            } else {
                // Fallback for older browsers
                this.loadAllImages();
            }
        }
        
        observeImages() {
            const images = document.querySelectorAll('img[data-src]');
            images.forEach(img => this.imageObserver.observe(img));
        }
        
        loadImage(img) {
            const src = img.dataset.src;
            if (!src) return;
            
            // Create new image to preload
            const newImg = new Image();
            newImg.onload = () => {
                img.src = src;
                img.classList.add('loaded');
                delete img.dataset.src;
            };
            newImg.src = src;
        }
        
        loadAllImages() {
            const images = document.querySelectorAll('img[data-src]');
            images.forEach(img => this.loadImage(img));
        }
    }
    
    // Virtual Scrolling for Long Lists
    class VirtualScroller {
        constructor(container, options = {}) {
            this.container = container;
            this.itemHeight = options.itemHeight || 80;
            this.bufferSize = options.bufferSize || 5;
            this.items = [];
            this.visibleItems = [];
            
            if (this.container) {
                this.init();
            }
        }
        
        init() {
            // Set up container
            this.container.style.position = 'relative';
            this.container.style.overflow = 'auto';
            
            // Create spacer for scrollbar
            this.spacer = document.createElement('div');
            this.spacer.style.position = 'absolute';
            this.spacer.style.top = '0';
            this.spacer.style.left = '0';
            this.spacer.style.width = '1px';
            this.container.appendChild(this.spacer);
            
            // Set up scroll listener
            this.container.addEventListener('scroll', this.onScroll.bind(this));
            
            // Initial render
            this.render();
        }
        
        setItems(items) {
            this.items = items;
            this.spacer.style.height = `${items.length * this.itemHeight}px`;
            this.render();
        }
        
        onScroll() {
            cancelAnimationFrame(this.scrollFrame);
            this.scrollFrame = requestAnimationFrame(() => this.render());
        }
        
        render() {
            const scrollTop = this.container.scrollTop;
            const containerHeight = this.container.clientHeight;
            
            // Calculate visible range
            const startIndex = Math.max(0, Math.floor(scrollTop / this.itemHeight) - this.bufferSize);
            const endIndex = Math.min(
                this.items.length - 1,
                Math.ceil((scrollTop + containerHeight) / this.itemHeight) + this.bufferSize
            );
            
            // Update visible items
            this.updateVisibleItems(startIndex, endIndex);
        }
        
        updateVisibleItems(startIndex, endIndex) {
            // Implementation depends on specific use case
            // This is a simplified example
            console.log(`Rendering items ${startIndex} to ${endIndex}`);
        }
    }
    
    // Request Idle Callback Polyfill
    window.requestIdleCallback = window.requestIdleCallback || function(cb) {
        const start = Date.now();
        return setTimeout(function() {
            cb({
                didTimeout: false,
                timeRemaining: function() {
                    return Math.max(0, 50 - (Date.now() - start));
                }
            });
        }, 1);
    };
    
    // Debounce function for performance
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
    
    // Optimize form inputs
    function optimizeInputs() {
        // Debounce search inputs
        const searchInputs = document.querySelectorAll('input[type="search"], .search-input');
        searchInputs.forEach(input => {
            const originalHandler = input.oninput;
            if (originalHandler) {
                input.oninput = debounce(originalHandler, 300);
            }
        });
        
        // Lazy load select options for large dropdowns
        const largeSelects = document.querySelectorAll('select[data-lazy]');
        largeSelects.forEach(select => {
            select.addEventListener('focus', function loadOptions() {
                // Load options on first focus
                if (this.dataset.loaded) return;
                
                const endpoint = this.dataset.lazy;
                fetch(endpoint)
                    .then(response => response.json())
                    .then(options => {
                        options.forEach(opt => {
                            const option = document.createElement('option');
                            option.value = opt.value;
                            option.textContent = opt.label;
                            this.appendChild(option);
                        });
                        this.dataset.loaded = 'true';
                    });
            }, { once: true });
        });
    }
    
    // Reduce motion for users who prefer it
    function respectReducedMotion() {
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
        
        if (prefersReducedMotion.matches) {
            document.documentElement.classList.add('reduce-motion');
        }
        
        prefersReducedMotion.addEventListener('change', (e) => {
            if (e.matches) {
                document.documentElement.classList.add('reduce-motion');
            } else {
                document.documentElement.classList.remove('reduce-motion');
            }
        });
    }
    
    // Optimize animations
    function optimizeAnimations() {
        // Use CSS containment
        const cards = document.querySelectorAll('.card, .entry-card');
        cards.forEach(card => {
            card.style.contain = 'layout style paint';
        });
        
        // Use will-change sparingly
        document.addEventListener('touchstart', (e) => {
            const target = e.target.closest('.btn, .card, [data-animate]');
            if (target) {
                target.style.willChange = 'transform';
                
                // Remove after animation
                setTimeout(() => {
                    target.style.willChange = 'auto';
                }, 300);
            }
        });
    }
    
    // Memory management
    function setupMemoryManagement() {
        // Clean up event listeners on page hide
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Pause non-critical operations
                if (window.pauseBackgroundOperations) {
                    window.pauseBackgroundOperations();
                }
            } else {
                // Resume operations
                if (window.resumeBackgroundOperations) {
                    window.resumeBackgroundOperations();
                }
            }
        });
        
        // Clean up on navigation
        window.addEventListener('pagehide', () => {
            // Cancel pending requests
            if (window.pendingRequests) {
                window.pendingRequests.forEach(request => request.abort());
            }
        });
    }
    
    // Battery-aware features
    function setupBatteryAwareness() {
        if ('getBattery' in navigator) {
            navigator.getBattery().then(battery => {
                function updateBatteryStatus() {
                    if (battery.level < 0.2 && !battery.charging) {
                        document.documentElement.classList.add('low-battery');
                        // Reduce animations and background operations
                    } else {
                        document.documentElement.classList.remove('low-battery');
                    }
                }
                
                battery.addEventListener('levelchange', updateBatteryStatus);
                battery.addEventListener('chargingchange', updateBatteryStatus);
                updateBatteryStatus();
            });
        }
    }
    
    // Network-aware loading
    function setupNetworkAwareness() {
        if ('connection' in navigator) {
            const connection = navigator.connection;
            
            function updateNetworkStatus() {
                const effectiveType = connection.effectiveType;
                document.documentElement.dataset.networkSpeed = effectiveType;
                
                // Adjust quality based on connection
                if (effectiveType === 'slow-2g' || effectiveType === '2g') {
                    document.documentElement.classList.add('low-quality');
                } else {
                    document.documentElement.classList.remove('low-quality');
                }
            }
            
            connection.addEventListener('change', updateNetworkStatus);
            updateNetworkStatus();
        }
    }
    
    // Initialize all optimizations
    function init() {
        // Only run on mobile
        if (window.innerWidth > 768) return;
        
        requestIdleCallback(() => {
            new LazyLoader();
            optimizeInputs();
            respectReducedMotion();
            optimizeAnimations();
            setupMemoryManagement();
            setupBatteryAwareness();
            setupNetworkAwareness();
        });
    }
    
    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Export for use in other modules
    window.MobilePerformance = {
        LazyLoader,
        VirtualScroller,
        debounce
    };
})();