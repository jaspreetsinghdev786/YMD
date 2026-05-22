/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./templates/**/*.html",
  ],
  theme: {
    extend: {
      colors: {
        "primary": "#ff0000",
        "background-light": "#f8f5f5",
        "background-dark": "#1a1a1a",
        "surface-light": "#ffffff",
        "surface-dark": "#262626",
        "neutral-dark": "#000000",
        "neutral-light": "#f5f5f5",
      },
      fontFamily: {
        "display": ["Space Grotesk", "sans-serif"],
        "body": ["Space Grotesk", "sans-serif"],
      },
      borderRadius: {
        "DEFAULT": "0.125rem",
        "sm": "2px",
        "md": "4px",
        "lg": "0.25rem",
        "xl": "0.5rem",
        "full": "0.75rem",
      },
      boxShadow: {
        'brutal': '4px 4px 0px 0px rgba(0,0,0,1)',
        'brutal-sm': '2px 2px 0px 0px rgba(0,0,0,1)',
        'brutal-dark': '4px 4px 0px 0px rgba(255,255,255,1)',
        'brutal-hover': '2px 2px 0px 0px rgba(0,0,0,1)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/container-queries'),
  ],
}
