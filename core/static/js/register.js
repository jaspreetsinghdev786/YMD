document.addEventListener("DOMContentLoaded", async () => {
    // ============================================
    // GET CSRF TOKEN ON PAGE LOAD
    // ============================================
    try {
        await fetch("/api/accounts/csrf/", {
            credentials: "include"
        });
    } catch (err) {
        console.error("Failed to get CSRF token:", err);
    }

    // ============================================
    // DOM ELEMENTS
    // ============================================
    const form = document.querySelector("form");
    const emailInput = document.getElementById("email");
    const passwordInput = document.getElementById("password");
    const confirmPasswordInput = document.getElementById("confirm-password");
    const togglePasswordBtn = document.getElementById("togglePassword");

    // Password strength bar elements
    const strengthBar1 = document.getElementById("strength-1");
    const strengthBar2 = document.getElementById("strength-2");
    const strengthBar3 = document.getElementById("strength-3");
    const strengthMsg = document.getElementById("password-strength-msg");

    // Password match error message
    const passwordMatchError = document.getElementById("password-match-error");

    // ============================================
    // PASSWORD VISIBILITY TOGGLE
    // ============================================
    togglePasswordBtn.addEventListener("click", () => {
        const isPassword = passwordInput.type === "password";
        passwordInput.type = isPassword ? "text" : "password";
        togglePasswordBtn.innerHTML = isPassword
            ? `<span class="material-symbols-outlined text-xl">visibility</span>`
            : `<span class="material-symbols-outlined text-xl">visibility_off</span>`;
    });

    // ============================================
    // PASSWORD STRENGTH CHECKER
    // ============================================
    function calculatePasswordStrength(password) {
        let score = 0;

        if (!password || password.length === 0) {
            return 0;
        }

        // Scoring criteria
        if (password.length >= 8) score += 1;
        if (password.length >= 12) score += 1;
        if (/[a-z]/.test(password)) score += 1;
        if (/[A-Z]/.test(password)) score += 1;
        if (/\d/.test(password)) score += 1;
        if (/[^A-Za-z0-9]/.test(password)) score += 1;

        // Map score to strength level (1-3)
        if (score <= 2) return 1; // Weak
        if (score <= 4) return 2; // Fair
        return 3; // Strong
    }

    function updatePasswordStrength() {
        const password = passwordInput.value;
        const strength = calculatePasswordStrength(password);

        // Reset all bars to low opacity
        strengthBar1.style.opacity = "0.2";
        strengthBar2.style.opacity = "0.2";
        strengthBar3.style.opacity = "0.2";

        // If password is empty, hide message
        if (password.length === 0) {
            if (strengthMsg) strengthMsg.classList.add("hidden");
            return;
        }

        // Update bars and message based on strength
        if (strength >= 1) {
            strengthBar1.style.opacity = "1";
            if (strengthMsg) {
                strengthMsg.classList.remove("hidden");
                strengthMsg.textContent = "WEAK PASSWORD";
                strengthMsg.className = "text-primary text-[10px] font-bold mt-1 uppercase";
            }
        }

        if (strength >= 2) {
            strengthBar2.style.opacity = "1";
            if (strengthMsg) {
                strengthMsg.textContent = "FAIR PASSWORD";
                strengthMsg.className = "text-orange-500 text-[10px] font-bold mt-1 uppercase";
            }
        }

        if (strength >= 3) {
            strengthBar3.style.opacity = "1";
            if (strengthMsg) {
                strengthMsg.textContent = "STRONG PASSWORD";
                strengthMsg.className = "text-green-600 text-[10px] font-bold mt-1 uppercase";
            }
        }
    }

    // ============================================
    // PASSWORD MATCH VALIDATION
    // ============================================
    function checkPasswordsMatch() {
        const password = passwordInput.value;
        const confirm = confirmPasswordInput.value;

        if (confirm.length > 0 && password !== confirm) {
            passwordMatchError.classList.remove("hidden");
            confirmPasswordInput.classList.add("border-red-500");
            confirmPasswordInput.classList.remove("border-black");
        } else {
            passwordMatchError.classList.add("hidden");
            confirmPasswordInput.classList.remove("border-red-500");
            confirmPasswordInput.classList.add("border-black");
        }
    }

    // ============================================
    // EVENT LISTENERS FOR REAL-TIME VALIDATION
    // ============================================
    passwordInput.addEventListener("input", () => {
        updatePasswordStrength();
        checkPasswordsMatch();
    });

    confirmPasswordInput.addEventListener("input", checkPasswordsMatch);

    // ============================================
    // FORM SUBMISSION
    // ============================================
    form.addEventListener("submit", async (e) => {
        e.preventDefault();

        const email = emailInput.value.trim();
        const password = passwordInput.value.trim();
        const confirmPassword = confirmPasswordInput.value.trim();

        // Frontend validation
        if (!email || !password) {
            alert("Email and password are required");
            return;
        }

        if (password.length < 8) {
            alert("Password must be at least 8 characters");
            return;
        }

        if (password !== confirmPassword) {
            alert("Passwords do not match");
            return;
        }

        // Check password strength and warn if weak
        const strength = calculatePasswordStrength(password);
        if (strength < 2) {
            const proceed = confirm("Your password is weak. Do you want to continue anyway?");
            if (!proceed) return;
        }

        const payload = {
            email: email,
            password: password
        };

        try {
            const response = await fetch("/api/accounts/register/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCSRFToken()
                },
                credentials: "include",
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (!response.ok) {
                alert(data.error || data.errors || "Registration failed");
                return;
            }

            alert("Account created successfully! Please check your email to verify.");
            window.location.href = "/login/";
        } catch (error) {
            console.error("Registration error:", error);
            alert("Network error. Please try again.");
        }
    });

    // ============================================
    // HELPER FUNCTIONS
    // ============================================
    function getCSRFToken() {
        return document.cookie
            .split("; ")
            .find(row => row.startsWith("csrftoken="))
            ?.split("=")[1];
    }
});
