"use client";

import { createContext, useContext, useEffect, useState } from "react";

interface User {
  sub: string;
  email: string;
  name: string;
  picture?: string;
}

interface UserContextType {
  user: User | null;
  isLoading: boolean;
  login: () => void;
  logout: () => void;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(false); // Start as false to avoid blocking render

  useEffect(() => {
    // Check if user is logged in by checking for session cookie
    const checkAuth = async () => {
      setIsLoading(true);
      try {
        const response = await fetch("/api/auth/me");
        if (response.ok) {
          const userData = await response.json();
          setUser(userData);
        } else {
          // 401 is expected when not logged in, don't log as error
          setUser(null);
        }
      } catch (error) {
        // Network error or other issue
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = () => {
    window.location.href = "/api/auth/login";
  };

  const logout = () => {
    window.location.href = "/api/auth/logout";
  };

  return (
    <UserContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </UserContext.Provider>
  );
}

export function useUser() {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error("useUser must be used within a UserProvider");
  }
  return context;
}
