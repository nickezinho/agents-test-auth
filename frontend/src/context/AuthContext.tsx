import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { api, setAccessToken, registerAuthCallbacks } from '../services/api';
import { AuthSuccessResponse, TokenRefreshResponse, UserResponse } from '../types/auth';

interface AuthContextType {
  user: UserResponse | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  secondsRemaining: number | null;
  login: (email: string, password: string) => Promise<void>;
  loginGoogle: (idToken: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => Promise<void>;
  forceRefresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [accessToken, setAccessTokenState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [secondsRemaining, setSecondsRemaining] = useState<number | null>(null);
  const timerRef = useRef<number | null>(null);

  // Inicia ou reinicia contagem regressiva para expiração do token
  const startExpiryCountdown = useCallback((expiresInSeconds: number) => {
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
    }
    setSecondsRemaining(expiresInSeconds);
    timerRef.current = window.setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev === null || prev <= 1) {
          if (timerRef.current) window.clearInterval(timerRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, []);

  // Atualização atômica do token
  const handleUpdateToken = useCallback((newToken: string) => {
    setAccessToken(newToken);
    setAccessTokenState(newToken);
    startExpiryCountdown(900); // 15 minutos padrão
  }, [startExpiryCountdown]);

  // Logout local e limpeza
  const handleLocalLogout = useCallback(() => {
    setAccessToken(null);
    setAccessTokenState(null);
    setUser(null);
    setSecondsRemaining(null);
    if (timerRef.current) {
      window.clearInterval(timerRef.current);
    }
  }, []);

  // Registra callbacks no Axios para quando o interceptor renovar ou falhar
  useEffect(() => {
    registerAuthCallbacks(handleUpdateToken, handleLocalLogout);
  }, [handleUpdateToken, handleLocalLogout]);

  // Carrega os dados do perfil atual a partir do Access Token
  const fetchUserProfile = useCallback(async () => {
    try {
      const res = await api.get<UserResponse>('/auth/me');
      setUser(res.data);
    } catch {
      handleLocalLogout();
    }
  }, [handleLocalLogout]);

  // Inicialização (Silent Refresh no F5 aproveitando cookie HttpOnly)
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const res = await api.post<TokenRefreshResponse>('/auth/refresh');
        const token = res.data.access_token;
        handleUpdateToken(token);
        // Após obter o token, busca os dados do usuário
        const userRes = await api.get<UserResponse>('/auth/me', {
          headers: { Authorization: `Bearer ${token}` }
        });
        setUser(userRes.data);
      } catch {
        // Usuário não autenticado no início
        handleLocalLogout();
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, [handleUpdateToken, handleLocalLogout]);

  // Login Local
  const login = async (email: string, password: string) => {
    const res = await api.post<AuthSuccessResponse>('/auth/login', { email, password });
    handleUpdateToken(res.data.access_token);
    setUser(res.data.user);
  };

  // Login Google
  const loginGoogle = async (idToken: string) => {
    const res = await api.post<AuthSuccessResponse>('/auth/google', { id_token: idToken });
    handleUpdateToken(res.data.access_token);
    setUser(res.data.user);
  };

  // Cadastro Local
  const register = async (email: string, password: string, fullName: string) => {
    await api.post<UserResponse>('/auth/register', {
      email,
      password,
      full_name: fullName,
    });
  };

  // Logout Seguro
  const logout = async () => {
    try {
      await api.post('/auth/logout');
    } finally {
      handleLocalLogout();
    }
  };

  // Forçar Refresh Manual (para testes no Dashboard do laboratório)
  const forceRefresh = async () => {
    const res = await api.post<TokenRefreshResponse>('/auth/refresh');
    handleUpdateToken(res.data.access_token);
    await fetchUserProfile();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        accessToken,
        isAuthenticated: !!accessToken && !!user,
        isLoading,
        secondsRemaining,
        login,
        loginGoogle,
        register,
        logout,
        forceRefresh,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth deve ser utilizado dentro de um AuthProvider.');
  }
  return context;
};
