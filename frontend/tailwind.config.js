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
          DEFAULT: colors.blue[500],
          600: colors.blue[600],
          700: colors.blue[700],
          800: colors.blue[800]
        },
        secondary: {
          100: colors.violet[100],
          200: colors.violet[200],
          DEFAULT: colors.violet[500],
          600: colors.violet[600],
          700: colors.violet[700],
          800: colors.violet[800],
          900: colors.violet[900],
        },
        tertiary: {
          DEFAULT: colors.fuchsia[500],
          600: colors.fuchsia[600],
        },
        accent: {
          DEFAULT: colors.purple[500],
          600: colors.purple[600],
        }
      }
    },
  },
  plugins: [
  ],
}