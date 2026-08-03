import axios, { AxiosError } from 'axios';

/**
 * Base de la API. Único sitio del frontend donde vive el host del servidor: el
 * resto del código construye rutas relativas y deja que este cliente las resuelva.
 * Sólo la hace falta explícita quien no pasa por axios — la redirección del SSO,
 * que es una navegación del navegador, no una petición.
 */
export const apiBaseUrl: string = import.meta.env.VITE_API_URL ?? '';

const axiosInstance = axios.create({ baseURL: apiBaseUrl });

axiosInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * FastAPI devuelve el motivo del fallo en `detail`. Axios, por su cuenta, deja un
 * `message` genérico del tipo «Request failed with status code 409», y las pantallas
 * pintan `err.message`. Sin esta traducción, migrar de fetch a Orval convertiría
 * «Ya existe un chatbot por defecto» en un número de estado.
 */
axiosInstance.interceptors.response.use(undefined, (error: AxiosError<{ detail?: unknown }>) => {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string' && detail) {
    error.message = detail;
  } else if (Array.isArray(detail)) {
    // Errores de validación de Pydantic: [{loc, msg, type}, …]
    const msgs = detail
      .map((d) => (d && typeof d === 'object' && 'msg' in d ? String((d as { msg: unknown }).msg) : ''))
      .filter(Boolean);
    if (msgs.length) error.message = msgs.join('; ');
  }
  return Promise.reject(error);
});

export const customInstance = <T>(url: string, options?: RequestInit): Promise<T> => {
  return axiosInstance({
    url,
    method: options?.method ?? 'GET',
    data: options?.body,
    headers: options?.headers as Record<string, string> | undefined,
  }).then((r) => r.data);
};
