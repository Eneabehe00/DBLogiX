/**
 * DBLogiX - Sidebar Functionality
 * Handles sidebar interactions, mobile responsiveness, and dropdown menus
 */
document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main-content');
    const mobileMenuToggle = document.getElementById('mobile-menu-toggle');
    const sidebarClose = document.getElementById('sidebar-close');
    const sidebarOverlay = document.getElementById('sidebar-overlay');
    
    // Get ALL submenu toggles, including nested ones
    const submenuToggles = document.querySelectorAll('.submenu-toggle');
    
    // Utility Functions
    function isMobile() {
        return window.innerWidth < 768;
    }
    
    /**
     * Toggle mobile sidebar visibility
     */
    function toggleMobileSidebar() {
        sidebar.classList.toggle('active');
        sidebarOverlay.classList.toggle('active');
        document.body.classList.toggle('sidebar-open');
    }
    
    /**
     * Toggle desktop sidebar collapse state
     */
    function toggleDesktopSidebar() {
        if (!isMobile()) {
            sidebar.classList.toggle('collapsed');
            
            // Save preference to localStorage
            const isCollapsed = sidebar.classList.contains('collapsed');
            localStorage.setItem('sidebarCollapsed', isCollapsed.toString());
        }
    }
    
    /**
     * Handle submenu toggling
     * @param {Event} e - Click event
     */
    function toggleSubmenu(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const parentItem = this.closest('.has-submenu');
        
        // Check if this is a nested submenu
        const isNestedSubmenu = parentItem.parentElement.closest('.has-submenu') !== null;
        
        // Get all parent submenus if this is a nested menu
        const parentSubmenus = [];
        if (isNestedSubmenu) {
            let currentParent = parentItem.parentElement.closest('.has-submenu');
            while (currentParent) {
                parentSubmenus.push(currentParent);
                currentParent = currentParent.parentElement.closest('.has-submenu');
            }
        }
        
        // If this is a top-level submenu (not nested)
        if (!isNestedSubmenu) {
            // Close other top-level submenus that aren't ancestors of this item
            const topLevelSubmenus = sidebar.querySelectorAll('.sidebar-nav > .has-submenu');
            topLevelSubmenus.forEach(function(item) {
                if (item !== parentItem && !item.contains(parentItem)) {
                    item.classList.remove('open');
                }
            });
        } else {
            // This is a nested submenu
            // Only close sibling submenus at the same level
            const siblingSubmenus = parentItem.parentElement.querySelectorAll(':scope > .has-submenu');
            siblingSubmenus.forEach(function(item) {
                if (item !== parentItem) {
                    item.classList.remove('open');
                }
            });
        }
        
        // Toggle current submenu
        parentItem.classList.toggle('open');
        
        // For both mobile and desktop, ensure all parent submenus stay open
        if (isNestedSubmenu) {
            parentSubmenus.forEach(function(parent) {
                parent.classList.add('open');
            });
        }
    }
    
    /**
     * Initialize sidebar state from saved preferences
     */
    function initSidebarState() {
        // Restore sidebar collapsed state on desktop
        if (!isMobile()) {
            const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
            if (isCollapsed) {
                sidebar.classList.add('collapsed');
            }
        }
        
        // On mobile, ensure sidebar is closed initially
        if (isMobile()) {
            sidebar.classList.remove('active');
            sidebarOverlay.classList.remove('active');
        }
        
        // Initialize open state for active submenu items
        const activeSubmenuItems = sidebar.querySelectorAll('.has-submenu .active');
        activeSubmenuItems.forEach(function(item) {
            let parent = item.parentElement;
            
            // Navigate up to find all parent submenu containers
            while (parent && parent !== sidebar) {
                if (parent.classList.contains('has-submenu')) {
                    parent.classList.add('open');
                }
                parent = parent.parentElement;
            }
        });
    }
    
    /**
     * Fix the layout issues when window is resized
     */
    function adjustLayout() {
        if (isMobile()) {
            // Ensure proper mobile layout
            sidebar.classList.remove('collapsed');
            mainContent.style.width = '100%';
            mainContent.style.marginLeft = '0';
        } else {
            // Ensure proper desktop layout
            if (sidebar.classList.contains('collapsed')) {
                mainContent.style.width = `calc(100% - ${getComputedStyle(document.documentElement).getPropertyValue('--sidebar-width-collapsed').trim()})`;
                mainContent.style.marginLeft = getComputedStyle(document.documentElement).getPropertyValue('--sidebar-width-collapsed').trim();
            } else {
                mainContent.style.width = `calc(100% - ${getComputedStyle(document.documentElement).getPropertyValue('--sidebar-width').trim()})`;
                mainContent.style.marginLeft = getComputedStyle(document.documentElement).getPropertyValue('--sidebar-width').trim();
            }
            
            // Ensure sidebar is visible on desktop
            sidebar.classList.remove('active');
            sidebarOverlay.classList.remove('active');
        }
    }
    
    /**
     * Attach event listeners to all submenu toggles including nested ones
     */
    function attachSubmenuListeners() {
        // Get ALL submenu toggles, including nested ones
        const allSubmenuToggles = document.querySelectorAll('.submenu-toggle');
        
        // Attach event listeners to all submenu toggles
        allSubmenuToggles.forEach(function(toggle) {
            toggle.addEventListener('click', toggleSubmenu);
        });
    }
    
    // Event Listeners
    
    // Mobile menu toggle
    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', toggleMobileSidebar);
    }
    
    // Mobile sidebar close button
    if (sidebarClose) {
        sidebarClose.addEventListener('click', toggleMobileSidebar);
    }
    
    // Overlay click to close sidebar on mobile
    if (sidebarOverlay) {
        sidebarOverlay.addEventListener('click', toggleMobileSidebar);
    }
    
    // Add desktop sidebar toggle button if needed
    const addDesktopToggle = function() {
        // If toggle button already exists, don't add another one
        if (document.getElementById('desktop-sidebar-toggle')) {
            return;
        }
        
        const toggleBtn = document.createElement('button');
        toggleBtn.id = 'desktop-sidebar-toggle';
        toggleBtn.className = 'sidebar-toggle-btn d-none d-md-block';
        toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
        toggleBtn.title = 'Toggle Sidebar';
        
        // Add to sidebar header
        const sidebarHeader = document.querySelector('.sidebar-header');
        if (sidebarHeader) {
            sidebarHeader.appendChild(toggleBtn);
            
            // Add event listener
            toggleBtn.addEventListener('click', toggleDesktopSidebar);
        }
    };
    
    // Uncomment to add a desktop toggle button
    // addDesktopToggle();
    
    // Attach event listeners to all submenu toggles
    attachSubmenuListeners();
    
    // Handle resize events
    window.addEventListener('resize', function() {
        adjustLayout();
        
        if (isMobile()) {
            // On mobile view, close sidebar when resizing from desktop
            if (sidebar.classList.contains('collapsed')) {
                sidebar.classList.remove('collapsed');
            }
        } else {
            // On desktop view, remove mobile classes
            sidebar.classList.remove('active');
            sidebarOverlay.classList.remove('active');
            document.body.classList.remove('sidebar-open');
        }
    });
    
    // Close sidebar submenu when clicking outside on mobile
    document.addEventListener('click', function(event) {
        if (isMobile() && !sidebar.contains(event.target) && !mobileMenuToggle.contains(event.target)) {
            const openSubmenus = sidebar.querySelectorAll('.has-submenu.open');
            if (openSubmenus.length > 0 && sidebar.classList.contains('active')) {
                openSubmenus.forEach(function(item) {
                    item.classList.remove('open');
                });
            }
        } else if (!isMobile() && !sidebar.contains(event.target)) {
            // On desktop, close submenus when clicking outside the sidebar
            const openSubmenus = sidebar.querySelectorAll('.has-submenu.open');
            if (openSubmenus.length > 0) {
                openSubmenus.forEach(function(item) {
                    // Only close top-level submenus when clicking outside
                    if (item.parentElement.classList.contains('sidebar-nav')) {
                        item.classList.remove('open');
                    }
                });
            }
        }
    });
    
    // Initialize sidebar state and adjust layout
    initSidebarState();
    adjustLayout();
}); 