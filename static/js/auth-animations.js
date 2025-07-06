// Authentication Page Animations and Interactions

document.addEventListener('DOMContentLoaded', function() {
    // Add loading state to submit button
    const form = document.querySelector('.auth-form');
    const submitBtn = document.querySelector('.btn-primary');
    
    if (form && submitBtn) {
        form.addEventListener('submit', function(e) {
            // Check if form is valid
            if (form.checkValidity()) {
                submitBtn.classList.add('loading');
                submitBtn.disabled = true;
            }
        });
    }

    // Animate form fields on focus
    const formInputs = document.querySelectorAll('.form-control');
    formInputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('focused');
        });
        
        input.addEventListener('blur', function() {
            if (!this.value) {
                this.parentElement.classList.remove('focused');
            }
        });
        
        // Check if input has value on load (for browser autofill)
        if (input.value) {
            input.parentElement.classList.add('focused');
        }
    });

    // Company code formatting
    const companyCodeInput = document.querySelector('#company_code');
    if (companyCodeInput) {
        companyCodeInput.addEventListener('input', function(e) {
            // Convert to uppercase and remove non-alphanumeric characters
            let value = e.target.value.toUpperCase().replace(/[^A-Z0-9-]/g, '');
            
            // Add dashes every 4 characters
            if (value.length > 4 && !value.includes('-')) {
                value = value.match(/.{1,4}/g).join('-');
            }
            
            e.target.value = value;
        });
    }

    // Smooth scroll to alert messages
    const alerts = document.querySelectorAll('.alert');
    if (alerts.length > 0) {
        alerts[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // Add ripple effect to buttons
    const buttons = document.querySelectorAll('.btn-primary, .btn-outline-primary');
    buttons.forEach(button => {
        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;
            
            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');
            
            // Remove any existing ripples
            const existingRipple = this.querySelector('.ripple');
            if (existingRipple) {
                existingRipple.remove();
            }
            
            this.appendChild(ripple);
            
            setTimeout(() => ripple.remove(), 600);
        });
    });

    // Animate registration options
    const registrationOptions = document.querySelector('.registration-options');
    if (registrationOptions) {
        registrationOptions.style.opacity = '0';
        registrationOptions.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            registrationOptions.style.transition = 'all 0.6s ease';
            registrationOptions.style.opacity = '1';
            registrationOptions.style.transform = 'translateY(0)';
        }, 300);
    }

    // Password visibility toggle
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach(input => {
        const wrapper = input.parentElement;
        const toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.className = 'password-toggle';
        toggleBtn.innerHTML = '👁️';
        toggleBtn.style.cssText = `
            position: absolute;
            right: 1rem;
            top: 50%;
            transform: translateY(-50%);
            background: none;
            border: none;
            cursor: pointer;
            font-size: 1.2rem;
            opacity: 0.6;
            transition: opacity 0.3s ease;
        `;
        
        toggleBtn.addEventListener('click', function() {
            if (input.type === 'password') {
                input.type = 'text';
                this.innerHTML = '🙈';
            } else {
                input.type = 'password';
                this.innerHTML = '👁️';
            }
        });
        
        toggleBtn.addEventListener('mouseenter', function() {
            this.style.opacity = '1';
        });
        
        toggleBtn.addEventListener('mouseleave', function() {
            this.style.opacity = '0.6';
        });
        
        wrapper.style.position = 'relative';
        wrapper.appendChild(toggleBtn);
    });

    // Form validation feedback
    const requiredInputs = document.querySelectorAll('.form-control[required]');
    requiredInputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (this.value.trim() === '') {
                this.classList.add('invalid');
                this.classList.remove('valid');
            } else {
                this.classList.add('valid');
                this.classList.remove('invalid');
            }
        });
    });

    // Email validation
    const emailInput = document.querySelector('input[type="email"]');
    if (emailInput) {
        emailInput.addEventListener('blur', function() {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (this.value && !emailRegex.test(this.value)) {
                this.classList.add('invalid');
                this.classList.remove('valid');
                
                // Add error message if not exists
                if (!this.parentElement.querySelector('.error-message')) {
                    const errorMsg = document.createElement('small');
                    errorMsg.className = 'error-message';
                    errorMsg.style.color = '#dc3545';
                    errorMsg.textContent = 'Please enter a valid email address';
                    this.parentElement.appendChild(errorMsg);
                }
            } else if (this.value) {
                // Remove error message if exists
                const errorMsg = this.parentElement.querySelector('.error-message');
                if (errorMsg) {
                    errorMsg.remove();
                }
            }
        });
    }

    // Animate auth container on load
    const authContainer = document.querySelector('.auth-container');
    if (authContainer) {
        authContainer.style.opacity = '0';
        authContainer.style.transform = 'scale(0.95)';
        
        setTimeout(() => {
            authContainer.style.transition = 'all 0.5s ease';
            authContainer.style.opacity = '1';
            authContainer.style.transform = 'scale(1)';
        }, 100);
    }
});

// Add CSS for valid/invalid states
const style = document.createElement('style');
style.textContent = `
    .form-control.valid {
        border-color: #28a745 !important;
    }
    
    .form-control.invalid {
        border-color: #dc3545 !important;
    }
    
    .ripple {
        position: absolute;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.6);
        transform: scale(0);
        animation: ripple-animation 0.6s ease-out;
        pointer-events: none;
    }
    
    @keyframes ripple-animation {
        to {
            transform: scale(4);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);