// User dropdown context menu functionality
document.addEventListener('DOMContentLoaded', function() {
    const userDropdownToggle = document.getElementById('user-dropdown-toggle');
    const userDropdownModal = document.getElementById('user-dropdown-modal');
    
    // Toggle dropdown context menu
    if (userDropdownToggle && userDropdownModal) {
        userDropdownToggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Toggle active class
            const isActive = userDropdownModal.classList.contains('active');
            userDropdownModal.classList.toggle('active');
            
            // Position the dropdown relative to the toggle button
            if (!isActive) {
                const toggleRect = userDropdownToggle.getBoundingClientRect();
                const sidebarHeader = userDropdownToggle.closest('.sidebar-header');
                const sidebarHeaderRect = sidebarHeader.getBoundingClientRect();
                
                // Position relative to sidebar header
                userDropdownModal.style.position = 'absolute';
                userDropdownModal.style.top = (toggleRect.bottom - sidebarHeaderRect.top + 5) + 'px';
                userDropdownModal.style.right = '10px';
                userDropdownModal.style.left = 'auto';
            }
        });
    }
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (userDropdownModal && !userDropdownModal.contains(e.target) && !userDropdownToggle.contains(e.target)) {
            userDropdownModal.classList.remove('active');
        }
    });
    
    // Close dropdown when pressing Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && userDropdownModal && userDropdownModal.classList.contains('active')) {
            userDropdownModal.classList.remove('active');
        }
    });
    
    // Close dropdown when clicking on menu items
    if (userDropdownModal) {
        const menuLinks = userDropdownModal.querySelectorAll('a');
        menuLinks.forEach(link => {
            link.addEventListener('click', function() {
                userDropdownModal.classList.remove('active');
            });
        });
    }
});