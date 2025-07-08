// Password Strength Indicator
document.addEventListener('DOMContentLoaded', function() {
    // Password strength rules
    const passwordRules = {
        minLength: 8,
        requireUppercase: true,
        requireLowercase: true,
        requireNumbers: true,
        requireSpecialChars: true,
        specialChars: '!@#$%^&*()_+-=[]{}|;:,.<>?'
    };

    // Function to check password strength
    function checkPasswordStrength(password) {
        let strength = 0;
        const feedback = [];

        // Check minimum length
        if (password.length >= passwordRules.minLength) {
            strength += 20;
        } else {
            feedback.push(`At least ${passwordRules.minLength} characters`);
        }

        // Check for uppercase letters
        if (passwordRules.requireUppercase && /[A-Z]/.test(password)) {
            strength += 20;
        } else if (passwordRules.requireUppercase) {
            feedback.push('One uppercase letter');
        }

        // Check for lowercase letters
        if (passwordRules.requireLowercase && /[a-z]/.test(password)) {
            strength += 20;
        } else if (passwordRules.requireLowercase) {
            feedback.push('One lowercase letter');
        }

        // Check for numbers
        if (passwordRules.requireNumbers && /\d/.test(password)) {
            strength += 20;
        } else if (passwordRules.requireNumbers) {
            feedback.push('One number');
        }

        // Check for special characters
        const specialCharRegex = new RegExp(`[${passwordRules.specialChars.replace(/[\[\]\\]/g, '\\$&')}]`);
        if (passwordRules.requireSpecialChars && specialCharRegex.test(password)) {
            strength += 20;
        } else if (passwordRules.requireSpecialChars) {
            feedback.push('One special character');
        }

        // Bonus points for length
        if (password.length >= 12) {
            strength = Math.min(100, strength + 10);
        }
        if (password.length >= 16) {
            strength = Math.min(100, strength + 10);
        }

        return {
            score: strength,
            feedback: feedback,
            isValid: strength >= 100
        };
    }

    // Function to update the strength indicator UI
    function updateStrengthIndicator(input, result) {
        let container = input.parentElement.querySelector('.password-strength-container');
        
        // Create container if it doesn't exist
        if (!container) {
            container = document.createElement('div');
            container.className = 'password-strength-container';
            
            const indicator = document.createElement('div');
            indicator.className = 'password-strength-indicator';
            
            const bar = document.createElement('div');
            bar.className = 'password-strength-bar';
            
            const text = document.createElement('div');
            text.className = 'password-strength-text';
            
            const requirements = document.createElement('ul');
            requirements.className = 'password-requirements';
            
            indicator.appendChild(bar);
            container.appendChild(indicator);
            container.appendChild(text);
            container.appendChild(requirements);
            
            input.parentElement.appendChild(container);
        }

        const bar = container.querySelector('.password-strength-bar');
        const text = container.querySelector('.password-strength-text');
        const requirements = container.querySelector('.password-requirements');

        // Update bar width and color
        bar.style.width = result.score + '%';
        
        // Remove all strength classes
        bar.className = 'password-strength-bar';
        
        // Add appropriate class based on score
        if (result.score < 40) {
            bar.classList.add('strength-weak');
            text.textContent = 'Weak';
            text.className = 'password-strength-text text-weak';
        } else if (result.score < 70) {
            bar.classList.add('strength-fair');
            text.textContent = 'Fair';
            text.className = 'password-strength-text text-fair';
        } else if (result.score < 100) {
            bar.classList.add('strength-good');
            text.textContent = 'Good';
            text.className = 'password-strength-text text-good';
        } else {
            bar.classList.add('strength-strong');
            text.textContent = 'Strong';
            text.className = 'password-strength-text text-strong';
        }

        // Update requirements list
        requirements.innerHTML = '';
        if (result.feedback.length > 0) {
            requirements.innerHTML = '<li>' + result.feedback.join('</li><li>') + '</li>';
        }
    }

    // Function to check if passwords match
    function checkPasswordMatch(password, confirmPassword) {
        const confirmInput = document.querySelector(confirmPassword);
        if (!confirmInput) return;

        let matchIndicator = confirmInput.parentElement.querySelector('.password-match-indicator');
        
        if (!matchIndicator) {
            matchIndicator = document.createElement('div');
            matchIndicator.className = 'password-match-indicator';
            confirmInput.parentElement.appendChild(matchIndicator);
        }

        if (confirmInput.value === '') {
            matchIndicator.textContent = '';
            matchIndicator.className = 'password-match-indicator';
        } else if (password === confirmInput.value) {
            matchIndicator.innerHTML = '<i class="ti ti-check"></i> Passwords match';
            matchIndicator.className = 'password-match-indicator match';
        } else {
            matchIndicator.innerHTML = '<i class="ti ti-x"></i> Passwords do not match';
            matchIndicator.className = 'password-match-indicator no-match';
        }
    }

    // Attach to all password inputs
    const passwordInputs = document.querySelectorAll('input[type="password"][name="password"], input[type="password"][name="new_password"]');
    
    passwordInputs.forEach(input => {
        // Show initial requirements when focused
        input.addEventListener('focus', function() {
            if (this.value === '') {
                const result = checkPasswordStrength('');
                updateStrengthIndicator(this, result);
            }
        });

        // Check strength on input
        input.addEventListener('input', function() {
            const result = checkPasswordStrength(this.value);
            updateStrengthIndicator(this, result);

            // Check password match if there's a confirm field
            const formElement = this.closest('form');
            const confirmField = formElement.querySelector('input[name="confirm_password"], input[name="confirm_new_password"]');
            if (confirmField && confirmField.value) {
                checkPasswordMatch(this.value, '#' + confirmField.id);
            }
        });
    });

    // Attach to confirm password inputs
    const confirmInputs = document.querySelectorAll('input[name="confirm_password"], input[name="confirm_new_password"]');
    
    confirmInputs.forEach(input => {
        input.addEventListener('input', function() {
            const formElement = this.closest('form');
            const passwordField = formElement.querySelector('input[name="password"], input[name="new_password"]');
            if (passwordField) {
                checkPasswordMatch(passwordField.value, '#' + this.id);
            }
        });
    });

    // Prevent form submission if password is not strong enough
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const passwordField = this.querySelector('input[name="password"], input[name="new_password"]');
            if (passwordField && passwordField.value) {
                const result = checkPasswordStrength(passwordField.value);
                if (!result.isValid) {
                    e.preventDefault();
                    alert('Please ensure your password meets all the requirements.');
                    return false;
                }

                // Check password match
                const confirmField = this.querySelector('input[name="confirm_password"], input[name="confirm_new_password"]');
                if (confirmField && confirmField.value !== passwordField.value) {
                    e.preventDefault();
                    alert('Passwords do not match.');
                    return false;
                }
            }
        });
    });
});