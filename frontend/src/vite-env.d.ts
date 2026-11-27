/// <reference types="vite/client" />

interface Window {
  google?: { accounts: { id: {
    initialize: (options: { client_id: string; callback: (response: { credential: string }) => void }) => void;
    renderButton: (parent: HTMLElement, options: Record<string, string | number | boolean>) => void;
    prompt: () => void;
  } } };
}

interface ImportMetaEnv {
  readonly VITE_GOOGLE_CLIENT_ID?: string;
  readonly VITE_API_URL?: string;
  readonly VITE_CSRF_COOKIE_NAME?: string;
}
