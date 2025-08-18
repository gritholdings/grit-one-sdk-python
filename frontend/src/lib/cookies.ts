  export const getCsrfToken = () => {
    // First try to get from DOM (for Django-rendered pages)
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement;
    if (csrfToken?.value) {
      return csrfToken.value;
    }
    
    // Fallback to cookie-based CSRF token
    const cookieValue = document.cookie
      .split('; ')
      .find(row => row.startsWith('csrftoken='))
      ?.split('=')[1];
    
    return cookieValue || '';
  };