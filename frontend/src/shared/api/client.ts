import axios from 'axios';

const axiosInstance = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? '' });

axiosInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const customInstance = <T>(url: string, options?: RequestInit): Promise<T> => {
  return axiosInstance({
    url,
    method: options?.method ?? 'GET',
    data: options?.body,
    headers: options?.headers as Record<string, string> | undefined,
  }).then((r) => r.data);
};
