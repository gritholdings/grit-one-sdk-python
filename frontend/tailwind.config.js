const colors = require('tailwindcss/colors')

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "../home/**/*.{html,js}",
  ],
  theme: {
    extend: {
      colors: {
        // The numbers 400-50 indicate increasing lightness levels.
        // The numbers 600-950 indicate increasing darkness levels.
        primary: {
          50: colors.blue[50],
          100: colors.blue[100],
          200: colors.blue[200],
          300: colors.blue[300],
          400: colors.blue[400],
          DEFAULT: colors.blue[500],
          600: colors.blue[600],
          700: colors.blue[700],
          800: colors.blue[800],
          900: colors.blue[900],
          950: colors.blue[950],
        },
        secondary: {
          50: colors.violet[50],
          100: colors.violet[100],
          200: colors.violet[200],
          300: colors.violet[300],
          400: colors.violet[400],
          DEFAULT: colors.violet[500],
          600: colors.violet[600],
          700: colors.violet[700],
          800: colors.violet[800],
          900: colors.violet[900],
          950: colors.violet[950],
        },
        tertiary: {
          50: colors.fuchsia[50],
          100: colors.fuchsia[100],
          200: colors.fuchsia[200],
          300: colors.fuchsia[300],
          400: colors.fuchsia[400],
          DEFAULT: colors.fuchsia[500],
          600: colors.fuchsia[600],
          700: colors.fuchsia[700],
          800: colors.fuchsia[800],
          900: colors.fuchsia[900],
          950: colors.fuchsia[950],
        },
        accent: {
          50: colors.purple[50],
          100: colors.purple[100],
          200: colors.purple[200],
          300: colors.purple[300],
          400: colors.purple[400],
          DEFAULT: colors.purple[500],
          600: colors.purple[600],
          700: colors.purple[700],
          800: colors.purple[800],
          900: colors.purple[900],
          950: colors.purple[950],
        }
      }
    },
  },
  plugins: [
  ],
}