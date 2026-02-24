"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";

function LoadingSpinner() {
  return (
    <div className="flex h-screen items-center justify-center">
      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
    </div>
  );
}

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { token, loadUser, _hasHydrated } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  // Only call loadUser once hydration is confirmed and a token exists.
  // This refreshes the user profile from the backend without blocking the UI.
  useEffect(() => {
    if (_hasHydrated && token) {
      loadUser();
    }
  }, [_hasHydrated, token, loadUser]);

  // Only redirect after hydration is complete so we don't bounce to /login
  // during the brief moment before localStorage is read.
  useEffect(() => {
    if (_hasHydrated && !token && pathname !== "/login") {
      router.push("/login");
    }
  }, [_hasHydrated, token, pathname, router]);

  // Still rehydrating from localStorage — show spinner, never redirect yet.
  if (!_hasHydrated) {
    return <LoadingSpinner />;
  }

  // Hydration done but no token — spinner while the redirect is in flight.
  if (!token && pathname !== "/login") {
    return <LoadingSpinner />;
  }

  return <>{children}</>;
}
