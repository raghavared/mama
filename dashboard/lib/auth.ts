"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User, AuthState } from "@/types";
import { api } from "./api";

interface AuthStore extends AuthState {
  _hasHydrated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (
    name: string,
    email: string,
    password: string,
    role: string
  ) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
}

export const useAuth = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      _hasHydrated: false,

      login: async (email: string, password: string) => {
        const res = await api.login(email, password);
        api.setToken(res.token);
        set({ user: res.user, token: res.token, isAuthenticated: true });
      },

      register: async (
        name: string,
        email: string,
        password: string,
        role: string
      ) => {
        const res = await api.register(name, email, password, role);
        api.setToken(res.token);
        set({ user: res.user, token: res.token, isAuthenticated: true });
      },

      logout: () => {
        api.setToken(null);
        set({ user: null, token: null, isAuthenticated: false });
      },

      loadUser: async () => {
        const { token } = get();
        if (!token) return;
        api.setToken(token);
        try {
          const user = await api.getMe();
          set({ user, isAuthenticated: true });
        } catch (err: any) {
          // Only clear auth on an explicit 401 — a network error (backend
          // temporarily down) should NOT log the user out.
          if (err.message === "Unauthorized") {
            set({ user: null, token: null, isAuthenticated: false });
          }
        }
      },
    }),
    {
      name: "mama-auth",
      // Persist token + isAuthenticated so the guard can make the right
      // decision synchronously on the first render after hydration.
      partialize: (state) => ({
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          // Restore the API client's in-memory token from localStorage.
          if (state.token) {
            api.setToken(state.token);
            state.isAuthenticated = true;
          }
          // Signal that rehydration is complete — AuthGuard waits for this
          // before making any redirect decisions.
          state._hasHydrated = true;
        }
      },
    }
  )
);
