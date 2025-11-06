import { apiClient, baseUrl } from './api-client';
import type { User } from '../types';

export async function checkAuthentication(): Promise<User | null> {
  try {
    const response = await apiClient.post('/auth/is-authenticated/', {});

    if (response.data.is_authenticated) {
      return {
        id: response.data.user_id,
        email: response.data.email
      };
    } else {
      window.alert('Login expired. Please log in again.');
      window.location.href = `${baseUrl}/auth/login`;
      return null;
    }
  } catch (error) {
    window.alert('Login required. Please log in again.');
    window.location.href = `${baseUrl}/auth/login`;
    return null;
  }
}
