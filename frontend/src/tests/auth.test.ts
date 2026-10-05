import { describe, it, expect } from 'vitest';
import { UserResponse, AuthSuccessResponse, DashboardDataResponse } from '../types/auth';

describe('Frontend Contract Type Assertions', () => {
  it('deve validar estrutura de UserResponse compatível com a API', () => {
    const mockUser: UserResponse = {
      id: '3fa85f64-5717-4562-b3fc-2c963f66afa6',
      email: 'user@exemplo.com',
      full_name: 'João da Silva',
      avatar_url: null,
      is_active: true,
      is_oauth_only: false,
    };

    expect(mockUser.email).toBe('user@exemplo.com');
    expect(mockUser.is_active).toBe(true);
  });

  it('deve validar estrutura de AuthSuccessResponse', () => {
    const mockAuth: AuthSuccessResponse = {
      access_token: 'jwt.token.here',
      token_type: 'Bearer',
      expires_in: 900,
      user: {
        id: '123',
        email: 'test@test.com',
        full_name: 'Test',
        avatar_url: null,
        is_active: true,
      },
    };

    expect(mockAuth.token_type).toBe('Bearer');
    expect(mockAuth.expires_in).toBe(900);
  });

  it('deve validar contrato de DashboardDataResponse', () => {
    const mockDash: DashboardDataResponse = {
      status: 'success',
      message: 'Acesso concedido',
      session_info: {
        user_id: '123',
        email: 'test@test.com',
        token_issued_at: '2026-10-05T12:00:00Z',
        token_expires_at: '2026-10-05T12:15:00Z',
        seconds_until_expiry: 900,
      },
      metrics: {
        total_logins: 5,
        last_login_ip: '127.0.0.1',
        active_sessions_count: 1,
      },
    };

    expect(mockDash.status).toBe('success');
    expect(mockDash.metrics.active_sessions_count).toBe(1);
  });
});
