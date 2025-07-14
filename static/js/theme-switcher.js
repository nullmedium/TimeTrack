// Dark Mode Theme Switcher
(function() {
    // Theme constants
    const THEME_KEY = 'timetrack-theme';
    const LIGHT_THEME = 'light';
    const DARK_THEME = 'dark';
    const DEFAULT_THEME = LIGHT_THEME;
    
    // Icons for theme toggle
    const LIGHT_ICON = '<i class="ti ti-sun"></i>';
    const DARK_ICON = '<i class="ti ti-moon"></i>';
    
    // Get saved theme or default
    function getSavedTheme() {
        return localStorage.getItem(THEME_KEY) || DEFAULT_THEME;
    }
    
    // Save theme preference
    function saveTheme(theme) {
        localStorage.setItem(THEME_KEY, theme);
    }
    
    // Apply theme to document
    function applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        updateToggleButton(theme);
        
        // Update meta theme-color for mobile browsers
        const metaThemeColor = document.querySelector('meta[name="theme-color"]');
        if (metaThemeColor) {
            metaThemeColor.content = theme === DARK_THEME ? '#0f0f0f' : '#ffffff';
        }
    }
    
    // Update toggle button icon
    function updateToggleButton(theme) {
        const toggleButton = document.querySelector('.theme-toggle');
        if (toggleButton) {
            toggleButton.innerHTML = theme === DARK_THEME ? LIGHT_ICON : DARK_ICON;
            toggleButton.setAttribute('title', theme === DARK_THEME ? 'Switch to Light Mode' : 'Switch to Dark Mode');
        }
    }
    
    // Toggle theme
    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme') || DEFAULT_THEME;
        const newTheme = currentTheme === DARK_THEME ? LIGHT_THEME : DARK_THEME;
        
        applyTheme(newTheme);
        saveTheme(newTheme);
        
        // Dispatch custom event for other components to react
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: newTheme } }));
    }
    
    // Create theme toggle button
    function createToggleButton() {
        const button = document.createElement('button');
        button.className = 'theme-toggle';
        button.setAttribute('aria-label', 'Toggle theme');
        button.innerHTML = getSavedTheme() === DARK_THEME ? LIGHT_ICON : DARK_ICON;
        button.addEventListener('click', toggleTheme);
        
        // Add to body
        document.body.appendChild(button);
        
        return button;
    }
    
    // Initialize theme system
    function initTheme() {
        // Apply saved theme immediately to prevent flash
        const savedTheme = getSavedTheme();
        applyTheme(savedTheme);
        
        // Create toggle button when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', createToggleButton);
        } else {
            createToggleButton();
        }
        
        // Listen for system theme changes
        if (window.matchMedia) {
            const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
            
            // Check if no saved preference, use system preference
            if (!localStorage.getItem(THEME_KEY)) {
                applyTheme(darkModeQuery.matches ? DARK_THEME : LIGHT_THEME);
            }
            
            // Listen for system theme changes
            darkModeQuery.addEventListener('change', (e) => {
                // Only apply if user hasn't set a preference
                if (!localStorage.getItem(THEME_KEY)) {
                    const newTheme = e.matches ? DARK_THEME : LIGHT_THEME;
                    applyTheme(newTheme);
                }
            });
        }
        
        // Add keyboard shortcut (Ctrl/Cmd + Shift + D)
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'D') {
                e.preventDefault();
                toggleTheme();
            }
        });
    }
    
    // Handle theme for specific components that might need updates
    window.addEventListener('themeChanged', (e) => {
        const theme = e.detail.theme;
        
        // Update Chart.js charts if present
        if (window.Chart) {
            Chart.defaults.color = theme === DARK_THEME ? '#a8a8a8' : '#666';
            Chart.defaults.borderColor = theme === DARK_THEME ? '#333333' : '#e5e7eb';
            Chart.defaults.plugins.legend.labels.color = theme === DARK_THEME ? '#a8a8a8' : '#666';
            
            // Update all existing charts
            Object.keys(Chart.instances).forEach(key => {
                const chart = Chart.instances[key];
                chart.options.scales.x.ticks.color = theme === DARK_THEME ? '#a8a8a8' : '#666';
                chart.options.scales.y.ticks.color = theme === DARK_THEME ? '#a8a8a8' : '#666';
                chart.options.scales.x.grid.color = theme === DARK_THEME ? '#333333' : '#e5e7eb';
                chart.options.scales.y.grid.color = theme === DARK_THEME ? '#333333' : '#e5e7eb';
                chart.update();
            });
        }
        
        // Update Ace editor theme if present
        if (window.ace) {
            const editors = document.querySelectorAll('.ace_editor');
            editors.forEach(editorEl => {
                const editor = ace.edit(editorEl);
                editor.setTheme(theme === DARK_THEME ? 'ace/theme/monokai' : 'ace/theme/github');
            });
        }
    });
    
    // Prevent flash of incorrect theme
    document.documentElement.style.visibility = 'hidden';
    document.addEventListener('DOMContentLoaded', () => {
        requestAnimationFrame(() => {
            document.documentElement.style.visibility = '';
        });
    });
    
    // Initialize immediately
    initTheme();
    
    // Export functions for use in other scripts
    window.ThemeSwitcher = {
        toggle: toggleTheme,
        getTheme: () => document.documentElement.getAttribute('data-theme') || DEFAULT_THEME,
        setTheme: (theme) => {
            applyTheme(theme);
            saveTheme(theme);
        },
        isDark: () => (document.documentElement.getAttribute('data-theme') || DEFAULT_THEME) === DARK_THEME
    };
})();