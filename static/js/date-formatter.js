// Date and Time Formatting Utility
// This file provides client-side date/time formatting that matches user preferences

(function() {
    'use strict';
    
    // Get user preferences from data attributes or localStorage
    function getUserPreferences() {
        // Check if preferences are stored in the DOM
        const prefsElement = document.getElementById('user-preferences');
        if (prefsElement) {
            return {
                dateFormat: prefsElement.dataset.dateFormat || 'ISO',
                timeFormat24h: prefsElement.dataset.timeFormat24h === 'true'
            };
        }
        
        // Fallback to localStorage
        return {
            dateFormat: localStorage.getItem('dateFormat') || 'ISO',
            timeFormat24h: localStorage.getItem('timeFormat24h') === 'true'
        };
    }
    
    // Format date according to user preference
    function formatDate(date) {
        if (!date) return '';
        
        const d = date instanceof Date ? date : new Date(date);
        if (isNaN(d.getTime())) return '';
        
        const prefs = getUserPreferences();
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        
        switch (prefs.dateFormat) {
            case 'US':
                return `${month}/${day}/${year}`;
            case 'EU':
            case 'UK':
                return `${day}/${month}/${year}`;
            case 'Readable':
                return d.toLocaleDateString('en-US', { 
                    year: 'numeric', 
                    month: 'short', 
                    day: 'numeric' 
                });
            case 'Full':
                return d.toLocaleDateString('en-US', { 
                    year: 'numeric', 
                    month: 'long', 
                    day: 'numeric' 
                });
            case 'ISO':
            default:
                return `${year}-${month}-${day}`;
        }
    }
    
    // Format time according to user preference
    function formatTime(date, includeSeconds = true) {
        if (!date) return '';
        
        const d = date instanceof Date ? date : new Date(date);
        if (isNaN(d.getTime())) return '';
        
        const prefs = getUserPreferences();
        const hours = d.getHours();
        const minutes = String(d.getMinutes()).padStart(2, '0');
        const seconds = String(d.getSeconds()).padStart(2, '0');
        
        if (prefs.timeFormat24h) {
            const h24 = String(hours).padStart(2, '0');
            return includeSeconds ? `${h24}:${minutes}:${seconds}` : `${h24}:${minutes}`;
        } else {
            const h12 = hours === 0 ? 12 : hours > 12 ? hours - 12 : hours;
            const ampm = hours >= 12 ? 'PM' : 'AM';
            const timeStr = includeSeconds ? 
                `${h12}:${minutes}:${seconds}` : 
                `${h12}:${minutes}`;
            return `${timeStr} ${ampm}`;
        }
    }
    
    // Format datetime according to user preference
    function formatDateTime(date) {
        if (!date) return '';
        
        const d = date instanceof Date ? date : new Date(date);
        if (isNaN(d.getTime())) return '';
        
        return `${formatDate(d)} ${formatTime(d)}`;
    }
    
    // Format duration (seconds to HH:MM:SS)
    function formatDuration(seconds) {
        if (seconds == null || seconds < 0) return '00:00:00';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        return [hours, minutes, secs]
            .map(v => String(v).padStart(2, '0'))
            .join(':');
    }
    
    // Update all elements with data-format attributes
    function updateFormattedDates() {
        // Update date elements
        document.querySelectorAll('[data-format-date]').forEach(el => {
            const dateStr = el.dataset.formatDate;
            if (dateStr) {
                el.textContent = formatDate(dateStr);
            }
        });
        
        // Update time elements
        document.querySelectorAll('[data-format-time]').forEach(el => {
            const timeStr = el.dataset.formatTime;
            const includeSeconds = el.dataset.includeSeconds !== 'false';
            if (timeStr) {
                el.textContent = formatTime(timeStr, includeSeconds);
            }
        });
        
        // Update datetime elements
        document.querySelectorAll('[data-format-datetime]').forEach(el => {
            const datetimeStr = el.dataset.formatDatetime;
            if (datetimeStr) {
                el.textContent = formatDateTime(datetimeStr);
            }
        });
        
        // Update duration elements
        document.querySelectorAll('[data-format-duration]').forEach(el => {
            const seconds = parseInt(el.dataset.formatDuration);
            if (!isNaN(seconds)) {
                el.textContent = formatDuration(seconds);
            }
        });
    }
    
    // Store preferences in localStorage when they change
    function storePreferences(dateFormat, timeFormat24h) {
        localStorage.setItem('dateFormat', dateFormat);
        localStorage.setItem('timeFormat24h', timeFormat24h);
    }
    
    // Initialize on DOM ready
    document.addEventListener('DOMContentLoaded', function() {
        updateFormattedDates();
        
        // Listen for preference changes
        window.addEventListener('preferenceChanged', function(e) {
            if (e.detail) {
                storePreferences(e.detail.dateFormat, e.detail.timeFormat24h);
                updateFormattedDates();
            }
        });
    });
    
    // Expose functions globally
    window.DateFormatter = {
        formatDate: formatDate,
        formatTime: formatTime,
        formatDateTime: formatDateTime,
        formatDuration: formatDuration,
        updateFormattedDates: updateFormattedDates,
        getUserPreferences: getUserPreferences
    };
})();