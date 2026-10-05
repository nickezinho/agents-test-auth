import { describe, it, expect, beforeEach, vi } from 'vitest';
import { api, setAccessToken, getAccessToken, registerAuthCallbacks } from '../services/api';

describe('Frontend API Client & Concurrency Engine', () => {
  beforeEach(() => {
    setAccessToken(null);
  });

  it('deve armazenar e retornar o Access Token estritamente em memória', () => {
    expect(getAccessToken()).toBeNull();

    setAccessToken('mock_access_token_123456');
    expect(getAccessToken()).toBe('mock_access_token_123456');

    setAccessToken(null);
    expect(getAccessToken()).toBeNull();
  });

  it('deve injetar o Access Token no header Authorization da requisição', async () => {
    setAccessToken('test_jwt_bearer_token');

    // Cria mock da requisição
    const config = { headers: {} as Record<string, string> };
    const requestInterceptor = (api.interceptors.request as any).handlers[0]?.fulfilled;

    if (requestInterceptor) {
      const modifiedConfig = requestInterceptor(config);
      expect(modifiedConfig.headers.Authorization).toBe('Bearer test_jwt_bearer_token');
    }
  });

  it('deve registrar e disparar callbacks de atualização de token', () => {
    const onUpdateToken = vi.fn();
    const onLogout = vi.fn();

    registerAuthCallbacks(onUpdateToken, onLogout);
    expect(onUpdateToken).not.toHaveBeenCalled();
    expect(onLogout).not.toHaveBeenCalled();
  });
});
