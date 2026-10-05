import React, { useEffect, useRef } from 'react';

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: unknown) => void;
          renderButton: (parent: HTMLElement, options: unknown) => void;
          prompt: () => void;
        };
      };
    };
  }
}

interface GoogleButtonProps {
  onSuccess: (credential: string) => void;
  onError?: (error: unknown) => void;
  isLoading?: boolean;
}

export const GoogleButton: React.FC<GoogleButtonProps> = ({ onSuccess, onError, isLoading }) => {
  const buttonDivRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Configura o GIS se estiver disponível no window
    if (window.google?.accounts?.id && buttonDivRef.current) {
      try {
        window.google.accounts.id.initialize({
          client_id: 'mock-google-client-id.apps.googleusercontent.com',
          callback: (response: { credential: string }) => {
            if (response.credential) {
              onSuccess(response.credential);
            }
          },
        });

        window.google.accounts.id.renderButton(buttonDivRef.current, {
          theme: 'filled_black',
          size: 'large',
          width: '100%',
          text: 'continue_with',
          shape: 'rectangular',
        });
      } catch (err) {
        if (onError) onError(err);
      }
    }
  }, [onSuccess, onError]);

  // Handler de simulação rápida para laboratório de testes
  const handleSimulateGoogleAuth = () => {
    // Token mock assinado aceito pelo backend para validação em ambiente de laboratório
    const mockToken = "mock_google_token_:dev.user@empresa.com:Dev User (Google):sub_google_882910";
    onSuccess(mockToken);
  };

  return (
    <div className="w-full flex flex-col gap-2">
      <div ref={buttonDivRef} className="w-full min-h-[40px] flex justify-center" />
      
      {/* Botão de conveniência para laboratório / dev offline */}
      <button
        type="button"
        onClick={handleSimulateGoogleAuth}
        disabled={isLoading}
        className="w-full py-2.5 px-4 rounded-xl border border-slate-700 bg-slate-900/80 hover:bg-slate-800 text-slate-200 text-sm font-semibold flex items-center justify-center gap-3 transition-all hover:border-slate-600 disabled:opacity-50 shadow-sm"
      >
        <svg className="w-4 h-4" viewBox="0 0 24 24">
          <path
            fill="#4285F4"
            d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"
          />
          <path
            fill="#34A853"
            d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.35 24 12 24z"
          />
          <path
            fill="#FBBC05"
            d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.99 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
          />
          <path
            fill="#EA4335"
            d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.35 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
          />
        </svg>
        Continuar com Google (OAuth Lab)
      </button>
    </div>
  );
};
