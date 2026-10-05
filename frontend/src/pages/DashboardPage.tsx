import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { DashboardDataResponse } from '../types/auth';
import { 
  ShieldCheck, 
  Clock, 
  KeyRound, 
  RotateCw, 
  Send, 
  Zap, 
  CheckCircle2, 
  XCircle, 
  Terminal, 
  User as UserIcon,
  LogOut
} from 'lucide-react';

interface LogEntry {
  id: string;
  time: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  payload?: unknown;
}

export const DashboardPage: React.FC = () => {
  const { user, accessToken, secondsRemaining, forceRefresh, logout } = useAuth();

  const [dashboardData, setDashboardData] = useState<DashboardDataResponse | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isCallingProtected, setIsCallingProtected] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isTestingConcurrency, setIsTestingConcurrency] = useState(false);

  const addLog = (type: LogEntry['type'], title: string, payload?: unknown) => {
    const newEntry: LogEntry = {
      id: Math.random().toString(36).substring(7),
      time: new Date().toLocaleTimeString(),
      type,
      title,
      payload,
    };
    setLogs((prev) => [newEntry, ...prev.slice(0, 19)]);
  };

  // 1. Testa rota protegida padrão
  const handleTestProtectedRoute = async () => {
    setIsCallingProtected(true);
    addLog('info', 'GET /api/v1/protected/dashboard disparado');
    try {
      const res = await api.get<DashboardDataResponse>('/protected/dashboard');
      setDashboardData(res.data);
      addLog('success', 'Acesso concedido à rota protegida (200 OK)', res.data);
    } catch (err: unknown) {
      addLog('error', 'Falha ao acessar rota protegida (401/403)', err);
    } finally {
      setIsCallingProtected(false);
    }
  };

  // 2. Força renovação manual do token
  const handleManualRefresh = async () => {
    setIsRefreshing(true);
    addLog('info', 'POST /api/v1/auth/refresh manual disparado');
    try {
      await forceRefresh();
      addLog('success', 'Token renovado com sucesso! Novo par gerado.');
    } catch (err: unknown) {
      addLog('error', 'Falha na renovação manual de token', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  // 3. Simula teste de concorrência com 5 requisições paralelas
  const handleTestConcurrency = async () => {
    setIsTestingConcurrency(true);
    addLog('warning', 'Disparando 5 requisições paralelas concorrentes...');

    const requests = [1, 2, 3, 4, 5].map((idx) =>
      api
        .get<DashboardDataResponse>('/protected/dashboard')
        .then((res) => {
          addLog('success', `Requisição #${idx} atendida com sucesso! (Status ${res.status})`);
          return res.data;
        })
        .catch((err) => {
          addLog('error', `Requisição #${idx} falhou`, err);
          throw err;
        })
    );

    try {
      await Promise.all(requests);
      addLog('success', 'Todas as 5 requisições simultâneas foram atendidas sem concorrência.');
    } catch {
      addLog('error', 'Erro durante teste de concorrência.');
    } finally {
      setIsTestingConcurrency(false);
    }
  };

  // Decodifica JWT para inspeção no laboratório
  const parseJwt = (token: string | null) => {
    if (!token) return null;
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload);
    } catch {
      return null;
    }
  };

  const decodedClaims = parseJwt(accessToken);
  const minutes = secondsRemaining !== null ? Math.floor(secondsRemaining / 60) : 0;
  const seconds = secondsRemaining !== null ? secondsRemaining % 60 : 0;
  const formattedCountdown = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  const expiryPercent = secondsRemaining !== null ? Math.min(100, Math.max(0, (secondsRemaining / 900) * 100)) : 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header do Dashboard */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-xl backdrop-blur-md">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt={user.full_name} className="w-full h-full rounded-2xl object-cover" />
            ) : (
              <UserIcon className="w-7 h-7" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white">{user?.full_name}</h1>
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Sessão Ativa
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-0.5">{user?.email}</p>
            <div className="flex items-center gap-2 mt-1 text-xs text-slate-500">
              <span>Método: {user?.is_oauth_only ? 'Google OIDC' : 'Senha Local'}</span>
              <span>•</span>
              <span>ID: {user?.id}</span>
            </div>
          </div>
        </div>

        {/* Card do Countdown Timer */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-center gap-4 min-w-[240px]">
          <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
            <Clock className="w-5 h-5 animate-pulse" />
          </div>
          <div className="flex-1">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-slate-400 font-medium">Vida do Token</span>
              <span className="font-mono font-bold text-amber-400">{formattedCountdown}</span>
            </div>
            <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-amber-500 to-indigo-500 transition-all duration-1000"
                style={{ width: `${expiryPercent}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Grid de Seções do Laboratório */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Painel 1: Ações de Teste de Autenticação */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-lg space-y-4">
          <div className="flex items-center gap-2.5">
            <ShieldCheck className="w-5 h-5 text-indigo-400" />
            <h2 className="font-bold text-base text-white">Testes de Segurança & Rotas</h2>
          </div>
          <p className="text-xs text-slate-400">
            Dispare chamadas para endpoints protegidos e simule rotação de token e concorrência no cliente.
          </p>

          <div className="space-y-3 pt-2">
            <button
              onClick={handleTestProtectedRoute}
              disabled={isCallingProtected}
              className="w-full py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700/80 active:scale-[0.99] border border-slate-700 text-slate-100 font-semibold text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5 text-indigo-400" />
              <span>Testar Rota Protegida (GET /dashboard)</span>
            </button>

            <button
              onClick={handleManualRefresh}
              disabled={isRefreshing}
              className="w-full py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700/80 active:scale-[0.99] border border-slate-700 text-slate-100 font-semibold text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              <RotateCw className={`w-3.5 h-3.5 text-emerald-400 ${isRefreshing ? 'animate-spin' : ''}`} />
              <span>Forçar Refresh Token Rotation</span>
            </button>

            <button
              onClick={handleTestConcurrency}
              disabled={isTestingConcurrency}
              className="w-full py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700/80 active:scale-[0.99] border border-slate-700 text-slate-100 font-semibold text-xs flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            >
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              <span>Simular Concorrência (5 Requisições)</span>
            </button>

            <button
              onClick={logout}
              className="w-full py-2.5 px-4 rounded-xl bg-rose-500/10 hover:bg-rose-500/20 active:scale-[0.99] border border-rose-500/20 text-rose-300 font-semibold text-xs flex items-center justify-center gap-2 transition-all"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Encerrar Sessão (Logout Ativo)</span>
            </button>
          </div>

          {/* Dados retornados da rota protegida */}
          {dashboardData && (
            <div className="mt-4 p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-2">
              <span className="font-semibold text-indigo-400 block">Resposta da Rota Protegida:</span>
              <div className="space-y-1 text-slate-300">
                <p>Status: <span className="text-emerald-400 font-medium">{dashboardData.status}</span></p>
                <p>Total de Logins: <span className="font-mono text-white">{dashboardData.metrics.total_logins}</span></p>
                <p>Sessões Ativas: <span className="font-mono text-white">{dashboardData.metrics.active_sessions_count}</span></p>
                <p>Último IP: <span className="font-mono text-slate-400">{dashboardData.metrics.last_login_ip}</span></p>
              </div>
            </div>
          )}
        </div>

        {/* Painel 2: Inspetor de Claims do JWT */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-lg space-y-4">
          <div className="flex items-center gap-2.5">
            <KeyRound className="w-5 h-5 text-amber-400" />
            <h2 className="font-bold text-base text-white">Claims do Access Token (JWT)</h2>
          </div>
          <p className="text-xs text-slate-400">
            Payload decodificado em memória (mantido estritamente no React state para evitar XSS persistente).
          </p>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs overflow-x-auto max-h-[320px]">
            <pre className="text-emerald-400">{JSON.stringify(decodedClaims, null, 2)}</pre>
          </div>

          <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-[11px] text-indigo-300 flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 flex-shrink-0 mt-0.5 text-indigo-400" />
            <span>
              O <strong>Refresh Token</strong> não é acessível por JavaScript. Ele trafega exclusivamente no cookie <code>HttpOnly</code>.
            </span>
          </div>
        </div>

        {/* Painel 3: Console / Logs de Execução ao Vivo */}
        <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 shadow-lg space-y-4 flex flex-col">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <Terminal className="w-5 h-5 text-indigo-400" />
              <h2 className="font-bold text-base text-white">Log de Tráfego de API</h2>
            </div>
            <button
              onClick={() => setLogs([])}
              className="text-[11px] text-slate-500 hover:text-slate-300 underline"
            >
              Limpar
            </button>
          </div>

          <div className="flex-1 min-h-[280px] p-3 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs overflow-y-auto space-y-2">
            {logs.length === 0 ? (
              <p className="text-slate-600 text-center py-8">Nenhum evento registrado ainda.</p>
            ) : (
              logs.map((log) => (
                <div
                  key={log.id}
                  className="p-2 rounded-lg bg-slate-900/60 border border-slate-800/80 text-[11px] space-y-1"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 font-semibold">
                      {log.type === 'success' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                      {log.type === 'error' && <XCircle className="w-3.5 h-3.5 text-rose-400" />}
                      {log.type === 'warning' && <Zap className="w-3.5 h-3.5 text-amber-400" />}
                      {log.type === 'info' && <Send className="w-3.5 h-3.5 text-indigo-400" />}
                      <span
                        className={
                          log.type === 'success'
                            ? 'text-emerald-300'
                            : log.type === 'error'
                            ? 'text-rose-300'
                            : log.type === 'warning'
                            ? 'text-amber-300'
                            : 'text-indigo-300'
                        }
                      >
                        {log.title}
                      </span>
                    </div>
                    <span className="text-slate-500 text-[10px]">{log.time}</span>
                  </div>
                  {log.payload && (
                    <pre className="text-slate-400 text-[10px] bg-slate-950/80 p-1.5 rounded overflow-x-auto">
                      {JSON.stringify(log.payload, null, 2)}
                    </pre>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
