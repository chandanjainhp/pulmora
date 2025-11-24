// Modern Interactive Features for Lung Cancer Prediction App

// Smooth scroll to top function
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// Add scroll to top button
document.addEventListener('DOMContentLoaded', function() {
    // Create scroll to top button
    const scrollBtn = document.createElement('button');
    scrollBtn.innerHTML = '↑';
    scrollBtn.className = 'scroll-to-top';
    scrollBtn.style.cssText = `
        position: fixed;
        bottom: 30px;
        right: 30px;
        width: 50px;
        height: 50px;
        border-radius: 50%;
        background-color: #2874A6;
        color: white;
        border: none;
        font-size: 24px;
        cursor: pointer;
        display: none;
        z-index: 1000;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        transition: all 0.3s ease;
    `;
    
    document.body.appendChild(scrollBtn);
    
    // Show/hide scroll button based on scroll position
    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            scrollBtn.style.display = 'block';
        } else {
            scrollBtn.style.display = 'none';
        }
    });
    
    scrollBtn.addEventListener('click', scrollToTop);
    
    scrollBtn.addEventListener('mouseenter', function() {
        this.style.backgroundColor = '#1A5276';
        this.style.transform = 'scale(1.1)';
    });
    
    scrollBtn.addEventListener('mouseleave', function() {
        this.style.backgroundColor = '#2874A6';
        this.style.transform = 'scale(1)';
    });
});

// Form validation enhancement
function enhanceFormValidation(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    const inputs = form.querySelectorAll('input[required]');
    
    inputs.forEach(input => {
        input.addEventListener('blur', function() {
            if (!this.validity.valid) {
                this.style.borderColor = '#E74C3C';
                showError(this, 'This field is required');
            } else {
                this.style.borderColor = '#27AE60';
                removeError(this);
            }
        });
        
        input.addEventListener('input', function() {
            if (this.validity.valid) {
                this.style.borderColor = '#27AE60';
                removeError(this);
            }
        });
    });
}

function showError(input, message) {
    removeError(input);
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    input.parentNode.appendChild(errorDiv);
}

function removeError(input) {
    const errorDiv = input.parentNode.querySelector('.error-message');
    if (errorDiv) {
        errorDiv.remove();
    }
}

// Toast notification system
function showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    
    const colors = {
        success: '#27AE60',
        error: '#E74C3C',
        warning: '#F39C12',
        info: '#2874A6'
    };
    
    toast.style.backgroundColor = colors[type] || colors.info;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease-in-out';
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, duration);
}

// Add slide out animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// Loading overlay
function showLoading() {
    const overlay = document.createElement('div');
    overlay.className = 'loading-overlay';
    overlay.id = 'loadingOverlay';
    overlay.innerHTML = '<div class="loading-spinner"></div>';
    document.body.appendChild(overlay);
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.remove();
    }
}

// Password strength indicator
function checkPasswordStrength(password) {
    let strength = 0;
    if (password.length >= 8) strength++;
    if (password.match(/[a-z]+/)) strength++;
    if (password.match(/[A-Z]+/)) strength++;
    if (password.match(/[0-9]+/)) strength++;
    if (password.match(/[$@#&!]+/)) strength++;
    
    const strengthLevels = ['Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
    const colors = ['#E74C3C', '#F39C12', '#F1C40F', '#27AE60', '#27AE60'];
    
    return {
        score: strength,
        text: strengthLevels[strength - 1] || 'Too Short',
        color: colors[strength - 1] || '#E74C3C'
    };
}

function addPasswordStrengthIndicator(passwordInputId) {
    const passwordInput = document.getElementById(passwordInputId);
    if (!passwordInput) return;
    
    const indicator = document.createElement('div');
    indicator.id = 'passwordStrength';
    indicator.style.cssText = `
        margin-top: 5px;
        font-size: 14px;
        font-weight: bold;
    `;
    passwordInput.parentNode.appendChild(indicator);
    
    passwordInput.addEventListener('input', function() {
        const strength = checkPasswordStrength(this.value);
        indicator.textContent = 'Password Strength: ' + strength.text;
        indicator.style.color = strength.color;
    });
}

// Auto-save form data to localStorage (optional)
function enableAutoSave(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    const formKey = 'form_' + formId;
    
    // Load saved data
    const savedData = localStorage.getItem(formKey);
    if (savedData) {
        try {
            const data = JSON.parse(savedData);
            Object.keys(data).forEach(key => {
                const input = form.querySelector(`[name="${key}"]`);
                if (input && input.type !== 'password') {
                    input.value = data[key];
                }
            });
        } catch (e) {
            console.error('Error loading saved form data:', e);
        }
    }
    
    // Save data on input
    form.addEventListener('input', function() {
        const formData = new FormData(form);
        const data = {};
        for (let [key, value] of formData.entries()) {
            if (!key.includes('password')) {
                data[key] = value;
            }
        }
        localStorage.setItem(formKey, JSON.stringify(data));
    });
    
    // Clear saved data on successful submit
    form.addEventListener('submit', function() {
        setTimeout(() => {
            localStorage.removeItem(formKey);
        }, 1000);
    });
}

// Animate elements on scroll
function animateOnScroll() {
    const elements = document.querySelectorAll('.card, .results-card');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('fade-in');
            }
        });
    }, {
        threshold: 0.1
    });
    
    elements.forEach(element => {
        observer.observe(element);
    });
}

// Initialize features on page load
document.addEventListener('DOMContentLoaded', function() {
    // Add fade-in animation to cards
    animateOnScroll();
    
    // Enhance prediction form if it exists
    if (document.getElementById('predictionForm')) {
        enhanceFormValidation('predictionForm');
    }
    
    // Add password strength indicator to signup form
    if (document.getElementById('password1')) {
        addPasswordStrengthIndicator('password1');
    }
    
    // Show loading on form submit
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Only show loading if not generating PDF
            if (!this.querySelector('input[name="generate_pdf"]')) {
                showLoading();
            }
        });
    });
});

// Confirm password match validation
function setupPasswordConfirmation() {
    const password1 = document.getElementById('password1');
    const password2 = document.getElementById('password2');
    
    if (!password1 || !password2) return;
    
    password2.addEventListener('input', function() {
        if (this.value !== password1.value) {
            this.setCustomValidity('Passwords do not match');
            this.style.borderColor = '#E74C3C';
            showError(this, 'Passwords do not match');
        } else {
            this.setCustomValidity('');
            this.style.borderColor = '#27AE60';
            removeError(this);
        }
    });
}

document.addEventListener('DOMContentLoaded', setupPasswordConfirmation);

// Mobile menu toggle (if needed)
function toggleMobileMenu() {
    const nav = document.querySelector('ul');
    if (nav) {
        nav.classList.toggle('mobile-menu-active');
    }
}

// Prevent form resubmission on refresh
if (window.history.replaceState) {
    window.history.replaceState(null, null, window.location.href);
}

console.log('🎉 Modern features loaded successfully!');
