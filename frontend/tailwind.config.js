/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        blue: {
          DEFAULT: '#378ADD',
          light: '#E6F1FB',
        },
        indigo: {
          DEFAULT: '#534AB7',
          light: '#EEEDFE',
          dark: '#3C3489',
        },
        teal: {
          DEFAULT: '#1D9E75',
          light: '#E1F5EE',
        },
        coral: {
          DEFAULT: '#D85A30',
          light: '#FAECE7',
        },
        amber: {
          DEFAULT: '#BA7517',
          light: '#FAEEDA',
        },
      },
    },
  },
  plugins: [],
}
