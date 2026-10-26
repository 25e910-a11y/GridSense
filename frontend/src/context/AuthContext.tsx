import { useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import { api, setOnUnauthorizedCallback } from '../services/api';
import type { AuthUser } from '../types/api';
import { AuthContext } from './auth-context-def';
import type { AuthContextType } from './auth-context-def';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const logout = useCallback(() => {
    api.logout();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const token = api.getToken();
    if (!token) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      const me = await api.getMe();
      if (me && me.authenticated) {
        setUser({
          username: me.username,
          role: me.role,
          assigned_block_id: me.assigned_block_id,
          assigned_floor_id: me.assigned_floor_id,
          permissions: me.permissions,
          authenticated: true,
        });
      } else {
        logout();
      }
    } catch {
      logout();
    } finally {
      setIsLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    setOnUnauthorizedCallback(() => {
      setUser(null);
    });

    let active = true;
    const initAuth = async () => {
      const token = api.getToken();
      if (!token) {
        if (active) setIsLoading(false);
        return;
      }
      try {
        const me = await api.getMe();
        if (active) {
          if (me && me.authenticated) {
            setUser({
              username: me.username,
              role: me.role,
              assigned_block_id: me.assigned_block_id,
              assigned_floor_id: me.assigned_floor_id,
              permissions: me.permissions,
              authenticated: true,
            });
          } else {
            api.logout();
            setUser(null);
          }
        }
      } catch {
        if (active) {
          api.logout();
          setUser(null);
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    };

    initAuth();
    return () => {
      active = false;
    };
  }, []);

  const login = async (username: string, password: string): Promise<AuthUser> => {
    const res = await api.login(username, password);
    const authUser: AuthUser = {
      username: res.username,
      role: res.role,
      assigned_block_id: res.assigned_block_id,
      assigned_floor_id: res.assigned_floor_id,
      permissions: res.permissions,
      authenticated: true,
    };
    setUser(authUser);
    return authUser;
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    role: user?.role || null,
    login,
    logout,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
