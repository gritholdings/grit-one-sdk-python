import axios from 'axios';

// Use window.location.origin to get the base URL dynamically (works in Vite)
const baseUrl: string = window.location.origin;

// Get CSRF token from cookie
const getCookie = (name: string): string | undefined => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift();
};

// Create axios instance with default configs
const apiClient = axios.create({
  baseURL: baseUrl,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  }
});

// Add request interceptor to include CSRF token
apiClient.interceptors.request.use((config) => {
  const token = getCookie('csrftoken');
  if (token) {
    config.headers['X-CSRFToken'] = token;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export {
  apiClient,
  baseUrl,
  getCookie
};
