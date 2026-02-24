"use client";

import { create } from "zustand";

type WSStatus = "connecting" | "connected" | "disconnected";

interface WSMessage {
  type: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

interface WSStore {
  status: WSStatus;
  messages: WSMessage[];
  lastEvent: WSMessage | null;
  connect: (token: string) => void;
  disconnect: () => void;
  subscribe: (type: string, cb: (msg: WSMessage) => void) => () => void;
}

let ws: WebSocket | null = null;
const listeners = new Map<string, Set<(msg: WSMessage) => void>>();

const WS_BASE =
  process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/ws";

export const useWebSocket = create<WSStore>((set, get) => ({
  status: "disconnected",
  messages: [],
  lastEvent: null,

  connect: (token: string) => {
    if (ws && ws.readyState === WebSocket.OPEN) return;

    set({ status: "connecting" });
    ws = new WebSocket(`${WS_BASE}?token=${token}`);

    ws.onopen = () => set({ status: "connected" });

    ws.onmessage = (event) => {
      try {
        const msg: WSMessage = JSON.parse(event.data);
        set((state) => ({
          messages: [...state.messages.slice(-99), msg],
          lastEvent: msg,
        }));
        const cbs = listeners.get(msg.type);
        if (cbs) cbs.forEach((cb) => cb(msg));
        const allCbs = listeners.get("*");
        if (allCbs) allCbs.forEach((cb) => cb(msg));
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => {
      set({ status: "disconnected" });
      // Auto-reconnect after 3s
      setTimeout(() => {
        const { status } = get();
        if (status === "disconnected") {
          get().connect(token);
        }
      }, 3000);
    };

    ws.onerror = () => ws?.close();
  },

  disconnect: () => {
    ws?.close();
    ws = null;
    set({ status: "disconnected", messages: [] });
  },

  subscribe: (type: string, cb: (msg: WSMessage) => void) => {
    if (!listeners.has(type)) listeners.set(type, new Set());
    listeners.get(type)!.add(cb);
    return () => {
      listeners.get(type)?.delete(cb);
    };
  },
}));
