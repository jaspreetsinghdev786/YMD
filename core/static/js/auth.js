// ===============================
// AUTH.JS – HttpOnly Cookie Based Authentication
// ===============================

const API_BASE_URL = "";

// ---------- COOKIE HELPERS ----------
function getCookie(name) {
    return document.cookie
        .split("; ")
        .find(row => row.startsWith(name + "="))
        ?.split("=")[1];
}

// ---------- SAFE JSON PARSE ----------
async function parseResponse(response) {
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
        try {
            return await response.json();
        } catch (err) {
            console.error("Failed to parse JSON:", err);
            return { error: "Invalid JSON response" };
        }
    }
    const text = await response.text();
    console.error("Non-JSON response:", text);
    return { error: text || "Invalid response format" };
}

// ---------- CSRF TOKEN HELPER ----------
function getCsrfToken() {
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    if (input) return input.value;
    return getCookie('csrftoken');
}

// ---------- GET CSRF TOKEN ON PAGE LOAD ----------
async function initCSRF() {
    try {
        await fetch(`${API_BASE_URL}/api/accounts/csrf-token/`, {
            credentials: 'include'  // Important for cookies
        });
    } catch (err) {
        console.error("Failed to get CSRF token:", err);
    }
}

// ---------- LOGIN ----------
async function login(email, password) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/accounts/login/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken()
            },
            credentials: 'include',  // Send and receive cookies
            body: JSON.stringify({ email, password })
        });

        const data = await parseResponse(response);
        if (!response.ok) throw new Error(data.error || "Login failed");

        // No need to store tokens - they're in HttpOnly cookies now!

        if (typeof toast !== 'undefined') {
            toast.success('Login successful!');
        }

        window.location.href = "/downloads/";
    } catch (err) {
        console.error("Login error:", err);
        if (typeof toast !== 'undefined') {
            toast.error(err.message || 'Login failed');
        }
        throw err;
    }
}

// ---------- REFRESH ACCESS TOKEN ----------
async function refreshAccessToken() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/accounts/refresh/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken()
            },
            credentials: 'include'  // Sends refresh_token cookie automatically
        });

        if (!response.ok) return false;

        const data = await parseResponse(response);
        return data.message === "Token refreshed";
    } catch (err) {
        console.error("Refresh token failed:", err);
        return false;
    }
}

// ---------- AUTH FETCH (AUTO REFRESH) ----------
async function authFetch(url, options = {}) {
    const fullUrl = url.startsWith("http") ? url : `${API_BASE_URL}${url}`;

    // Setup default options
    options.credentials = 'include';  // Send cookies automatically
    options.headers = {
        ...options.headers,
        "Content-Type": "application/json",
        "X-CSRFToken": getCsrfToken()  // Add CSRF token
    };

    let response = await fetch(fullUrl, options);

    // If unauthorized, try to refresh
    if (response.status === 401) {
        const refreshed = await refreshAccessToken();
        if (!refreshed) {
            logout();
            return;
        }
        // Retry the original request
        response = await fetch(fullUrl, options);
    }

    return response;
}

// ---------- LOGOUT ----------
async function logout() {
    try {
        await fetch(`${API_BASE_URL}/api/accounts/logout/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken()
            },
            credentials: 'include'  // Send cookies for logout
        });
    } catch (err) {
        console.error("Logout failed:", err);
    }

    // Cookies are deleted by backend, just redirect
    window.location.href = "/";
}

// ---------- CHECK AUTH STATUS ----------
async function checkAuthStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/accounts/auth/status/`, {
            credentials: 'include'
        });

        if (response.ok) {
            const data = await response.json();
            return data.authenticated;
        }
        return false;
    } catch (err) {
        console.error("Auth check failed:", err);
        return false;
    }
}

// ---------- UI INTERACTION ----------
document.addEventListener("DOMContentLoaded", async () => {
    // Initialize CSRF token
    await initCSRF();

    // 1. Login Form Submission
    const form = document.querySelector("form");
    if (form) {
        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const email = document.querySelector('input[name="email"]').value;
            const password = document.querySelector('input[name="password"]').value;
            await login(email, password);
        });
    }

    // 2. Google Login Button
    const googleBtn = document.querySelector(".btn-google-tech");
    if (googleBtn) {
        googleBtn.addEventListener("click", (e) => {
            e.preventDefault();
            handleGoogleLogin();
        });
    }

    // 3. Password Visibility Toggle
    const eyeBtn = document.querySelector(".eye-btn");
    const passwordInput = document.querySelector('input[name="password"]');
    if (eyeBtn && passwordInput) {
        eyeBtn.addEventListener("click", () => {
            const type = passwordInput.getAttribute("type") === "password" ? "text" : "password";
            passwordInput.setAttribute("type", type);
            eyeBtn.style.color = type === "text" ? "var(--text-primary)" : "var(--text-tertiary)";
        });
    }
});

// ---------- GOOGLE OAUTH LOGIN ----------
const handleGoogleLogin = () => {
    window.location.href = `${API_BASE_URL}/api/accounts/google/login/`;
};
