export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  avatar_url: string | null;
  is_active: boolean;
  is_oauth_only?: boolean;
  created_at?: string;
}

export interface AuthSuccessResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserResponse;
}

export interface TokenRefreshResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface ApiErrorResponse {
  code: string;
  detail: string;
  errors?: Array<{ field: string; message: string }>;
  timestamp: string;
  path?: string;
}

export interface DashboardDataResponse {
  status: string;
  message: string;
  session_info: {
    user_id: string;
    email: string;
    token_issued_at: string;
    token_expires_at: string;
    seconds_until_expiry: number;
  };
  metrics: {
    total_logins: number;
    last_login_ip: string;
    active_sessions_count: number;
  };
}
