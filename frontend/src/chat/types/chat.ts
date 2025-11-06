// Type definitions for chat functionality

export interface Attachment {
  url: string;
  name: string;
  type: string;
  content: string;
  contentType: string;
}

export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'user_image';
  createdAt?: Date;
  attachments?: Attachment[];
  experimental_attachments?: Attachment[];
  metadata?: {
    filename?: string;
    totalPages?: number;
    pageCount?: string;
    [key: string]: any;
  };
}

export interface CreateMessage {
  id?: string;
  content: string;
  role?: 'user' | 'assistant' | 'user_image';
  createdAt?: Date;
  attachments?: Attachment[];
  metadata?: {
    filename?: string;
    totalPages?: number;
    pageCount?: string;
    [key: string]: any;
  };
}

export interface ChatRequestOptions {
  headers?: Record<string, string>;
  body?: any;
  signal?: AbortSignal;
  experimental_attachments?: Attachment[];
}

export interface User {
  /**
   * Unique identifier for the user
   */
  id: string;

  /**
   * User's email address
   */
  email: string;

  /**
   * Optional display name for the user
   */
  name?: string;
}
