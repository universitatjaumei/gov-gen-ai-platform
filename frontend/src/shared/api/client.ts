import axios from 'axios';

export const customInstance = <T>(config: Parameters<typeof axios>[0]): Promise<T> => {
  const instance = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? '/api' });
  return instance(config!).then((r) => r.data);
};
