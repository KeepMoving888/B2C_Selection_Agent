import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const analysisApi = {
  create: (data: { keyword: string; market: string; budget: string }) =>
    apiClient.post('/analysis', data),
  get: (id: string) => apiClient.get(`/analysis/${id}`),
  history: () => apiClient.get('/analysis/history/list'),
};

export const profitApi = {
  calculate: (data: {
    selling_price: number;
    unit_cost: number;
    category: string;
    market: string;
  }) => apiClient.post('/profit/calculate', data),
};

export const authApi = {
  login: (username: string, password: string) =>
    apiClient.post(
      '/auth/login',
      new URLSearchParams({ username, password }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    ),
  me: () => apiClient.get('/auth/me'),
};
