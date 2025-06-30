// Sidebar functionality
document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const mobileNavToggle = document.getElementById('mobile-nav-toggle');
    const mobileOverlay = document.getElementById('mobile-overlay');
    
    // Desktop sidebar toggle
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            
            // Update main content and footer margins for browsers that don't support :has()
            const mainContent = document.querySelector('.main-content');
            const footer = document.querySelector('footer');
            
            if (sidebar.classList.contains('collapsed')) {
                if (mainContent) mainContent.style.marginLeft = '60px';
                if (footer) footer.style.marginLeft = '60px';
            } else {
                if (mainContent) mainContent.style.marginLeft = '280px';
                if (footer) footer.style.marginLeft = '280px';
            }
        });
    }
    
    // Mobile navigation toggle
    if (mobileNavToggle) {
        mobileNavToggle.addEventListener('click', function() {
            sidebar.classList.toggle('mobile-open');
            mobileOverlay.classList.toggle('active');
            mobileNavToggle.classList.toggle('active');
        });
    }
    
    // Close mobile sidebar when clicking overlay
    if (mobileOverlay) {
        mobileOverlay.addEventListener('click', function() {
            sidebar.classList.remove('mobile-open');
            mobileOverlay.classList.remove('active');
            if (mobileNavToggle) mobileNavToggle.classList.remove('active');
        });
    }
    
    // Close mobile sidebar when clicking on navigation links
    if (sidebar) {
        const navLinks = sidebar.querySelectorAll('a');
        navLinks.forEach(link => {
            link.addEventListener('click', function() {
                if (window.innerWidth <= 1024) {
                    sidebar.classList.remove('mobile-open');
                    mobileOverlay.classList.remove('active');
                    if (mobileNavToggle) mobileNavToggle.classList.remove('active');
                }
            });
        });
    }
    
    // Handle window resize
    window.addEventListener('resize', function() {
        if (window.innerWidth > 1024) {
            if (sidebar) sidebar.classList.remove('mobile-open');
            if (mobileOverlay) mobileOverlay.classList.remove('active');
            if (mobileNavToggle) mobileNavToggle.classList.remove('active');
        }
    });
});