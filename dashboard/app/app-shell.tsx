"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { AuthGuard } from "@/components/auth/auth-guard";
import { useAuth } from "@/lib/auth";
import { useWebSocket } from "@/lib/websocket";

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === "/login";
  const { token } = useAuth();
  const { connect, disconnect } = useWebSocket();

  useEffect(() => {
    if (token) {
      connect(token);
    } else {
      disconnect();
    }
    return () => disconnect();
  }, [token, connect, disconnect]);

  if (isLoginPage) {
    return <>{children}</>;
  }

  return (
    <AuthGuard>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </AuthGuard>
  );
}
