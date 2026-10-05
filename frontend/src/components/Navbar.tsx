import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { ShieldCheck, LogOut, User as UserIcon, Activity } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 group-hover:scale-105 transition-transform">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-extrabold text-base tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
              AuthLab
            </span>
            <span className="ml-1.5 px-1.5 py-0.5 text-[10px] font-bold rounded uppercase tracking-wider bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              Multi-Agent
            </span>
          </div>
        </Link>

        <div className="flex items-center gap-4">
          {isAuthenticated && user ? (
            <div className="flex items-center gap-4">
              <div className="hidden sm:flex items-center gap-2.5 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs">
                {user.avatar_url ? (
                  <img src={user.avatar_url} alt={user.full_name} className="w-5 h-5 rounded-full" />
                ) : (
                  <UserIcon className="w-4 h-4 text-slate-400" />
                )}
                <span className="font-medium text-slate-300">{user.full_name}</span>
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              </div>

              <Link
                to="/dashboard"
                className="text-xs font-semibold px-3 py-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-900 transition-colors flex items-center gap-1.5"
              >
                <Activity className="w-3.5 h-3.5 text-indigo-400" />
                Dashboard
              </Link>

              <button
                onClick={handleLogout}
                className="text-xs font-semibold px-3 py-2 rounded-lg text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 border border-rose-500/20 transition-all flex items-center gap-1.5"
                title="Encerrar sessão"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Sair</span>
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <Link
                to="/login"
                className="text-xs font-semibold px-3.5 py-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-900 transition-colors"
              >
                Entrar
              </Link>
              <Link
                to="/register"
                className="text-xs font-semibold px-3.5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/25 transition-all"
              >
                Criar Conta
              </Link>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
