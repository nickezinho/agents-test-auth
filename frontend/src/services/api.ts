import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { TokenRefreshResponse } from '../types/auth';

// Cria instância configurada do Axios
export const api = axios.create({
  baseURL: '/api/v1',
  withCredentials: true, // Essencial para envio e recebimento de cookies HttpOnly
  headers: {
    'Content-Type': 'application/json',
  },
});

// Estado interno para token em memória
let inMemoryAccessToken: string | null = null;
let logoutCallback: (() => void) | null = null;
let updateTokenCallback: ((token: string) => void) | null = null;

export const setAccessToken = (token: string | null) => {
  inMemoryAccessToken = token;
};

export const getAccessToken = () => inMemoryAccessToken;

export const registerAuthCallbacks = (
  onUpdateToken: (token: string) => void,
  onLogout: () => void
) => {
  updateTokenCallback = onUpdateToken;
  logoutCallback = onLogout;
};

// Interceptor de Requisição: Injeta o Bearer Token do Access Token em memória
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (inMemoryAccessToken && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${inMemoryAccessToken}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Controle de concorrência para Silent Refresh (ADR-005)
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((promise) => {
    if (error) {
      promise.reject(error);
    } else {
      promise.resolve(token);
    }
  });
  failedQueue = [];
};

// Interceptor de Resposta: Trata 401, enfileira chamadas simultâneas e executa Silent Refresh
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    // Se o erro não for 401 ou a requisição já tiver sido retentada, rejeita
    if (!error.response || error.response.status !== 401 || !originalRequest) {
      return Promise.reject(error);
    }

    // Não tenta refresh para rotas públicas ou se a própria chamada de refresh falhou
    const url = originalRequest.url || '';
    if (url.includes('/auth/login') || url.includes('/auth/refresh') || url.includes('/auth/register')) {
      return Promise.reject(error);
    }

    if (originalRequest._retry) {
      return Promise.reject(error);
    }

    // Se um refresh já estiver em andamento, enfileira a requisição concorrente
    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      })
        .then((token) => {
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        })
        .catch((err) => Promise.reject(err));
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      // Dispara o refresh silencioso consumindo o cookie HttpOnly
      const refreshResponse = await api.post<TokenRefreshResponse>('/auth/refresh');
      const newAccessToken = refreshResponse.data.access_token;

      // Atualiza token em memória e no contexto
      setAccessToken(newAccessToken);
      if (updateTokenCallback) {
        updateTokenCallback(newAccessToken);
      }

      // Libera todas as requisições enfileiradas com o novo token
      processQueue(null, newAccessToken);

      // Repete a requisição original que havia falhado
      originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
      return api(originalRequest);
    } catch (refreshError) {
      // Se o refresh falhar (expirado, revogado ou ataque de reuso), rejeita a fila e desloga
      processQueue(refreshError as Error, null);
      setAccessToken(null);
      if (logoutCallback) {
        logoutCallback();
      }
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);
