"use client";
import { createContext, useContext, useState, useEffect, useCallback } from "react";

const AuthContext = createContext(null);

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("cinema_auth_token");
    }
    return null;
  });

  // Initialize auth state
  useEffect(() => {
    const initAuth = async () => {
      const storedToken = localStorage.getItem("cinema_auth_token");
      if (storedToken) {
        try {
          const res = await fetch(`${API_URL}/api/auth/me`, {
            headers: { Authorization: `Bearer ${storedToken}` }
          });
          if (res.ok) {
            const data = await res.json();
            setUser(data);
            setToken(storedToken);
          } else {
            localStorage.removeItem("cinema_auth_token");
          }
        } catch {
          localStorage.removeItem("cinema_auth_token");
        }
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Login failed");
    
    localStorage.setItem("cinema_auth_token", data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  }, []);

  const register = useCallback(async (email, password, name) => {
    const res = await fetch(`${API_URL}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, name })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Registration failed");
    
    localStorage.setItem("cinema_auth_token", data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("cinema_auth_token");
    setToken(null);
    setUser(null);
  }, []);

  const updatePreferences = useCallback(async (preferences) => {
    if (!token) return;
    const res = await fetch(`${API_URL}/api/auth/preferences`, {
      method: "PUT",
      headers: { 
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify(preferences)
    });
    const data = await res.json();
    if (res.ok) {
      setUser(prev => ({ ...prev, preferences: data.preferences }));
    }
    return data;
  }, [token]);

  const syncNow = useCallback(async () => {
    if (!token) return;
    const res = await fetch(`${API_URL}/api/auth/sync`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${token}` }
    });
    return res.json();
  }, [token]);

  const value = {
    user,
    token,
    loading,
    login,
    register,
    logout,
    updatePreferences,
    syncNow,
    isAuthenticated: !!user
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}