import axios from 'axios';

export const customInstance = <T>(url: string, options?: RequestInit): Promise<T> => {
  const instance = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? '/api' });
  return instance({
    url,
    method: options?.method ?? 'GET',
    data: options?.body,
    headers: options?.headers as Record<string, string> | undefined,
  }).then((r) => r.data);
};
