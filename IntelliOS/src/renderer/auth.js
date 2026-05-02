// DOM Elements
const loginForm = document.getElementById('login-form');
const signupForm = document.getElementById('signup-form');
const showSignupLink = document.getElementById('showSignup');
const showLoginLink = document.getElementById('showLogin');
const loginFormDiv = document.getElementById('loginForm');
const signupFormDiv = document.getElementById('signupForm');

// Event Listeners
loginForm.addEventListener('submit', handleLogin);
signupForm.addEventListener('submit', handleSignup);
showSignupLink.addEventListener('click', toggleForms);
showLoginLink.addEventListener('click', toggleForms);

// Form Toggle
function toggleForms(e) {
    e.preventDefault();
    loginFormDiv.classList.toggle('hidden');
    signupFormDiv.classList.toggle('hidden');
}

// Login Handler
async function handleLogin(e) {
    e.preventDefault();
    
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    
    try {
        const result = await window.api.login({ username, password });
        console.log(result);
        
        if (result.message === 'Successful') {
            // Store user data and workspaces
            await window.api.setUserData({
                username,
                workspaces: result.workspaces
            });
            
            // Redirect to main page
            window.location.href = 'index.html';
        } else {
            showError(loginForm, result.message);
        }
    } catch (error) {
        showError(loginForm, 'Login failed. Please try again.');
    }
}

// Signup Handler
async function handleSignup(e) {
    e.preventDefault();
    
    const signupData = {
        username: document.getElementById('signup-username').value,
        password: document.getElementById('signup-password').value,
        name: document.getElementById('signup-name').value,
        email: document.getElementById('signup-email').value
    };
    
    try {
        const result = await window.api.signup(signupData);
        showSuccess(signupForm, 'Account created successfully! Please log in.');
        setTimeout(() => {
            toggleForms({ preventDefault: () => {} });
        }, 2000);
    } catch (error) {
        showError(signupForm, 'Signup failed. Please try again.');
    }
}

// Helper Functions
function showError(form, message) {
    const errorDiv = form.querySelector('.error-message') || document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    if (!form.querySelector('.error-message')) {
        form.appendChild(errorDiv);
    }
}

function showSuccess(form, message) {
    const successDiv = form.querySelector('.success-message') || document.createElement('div');
    successDiv.className = 'success-message';
    successDiv.textContent = message;
    if (!form.querySelector('.success-message')) {
        form.appendChild(successDiv);
    }
}