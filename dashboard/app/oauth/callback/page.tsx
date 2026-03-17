"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { RefreshCw, CheckCircle2, XCircle } from "lucide-react";

export default function OAuthCallbackPage() {
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("Processing OAuth callback...");

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const error = searchParams.get("error");
    const errorDescription = searchParams.get("error_description");

    if (error) {
      setStatus("error");
      setMessage(errorDescription || error || "OAuth authorization failed");
      // Notify parent window of failure
      if (window.opener) {
        window.opener.postMessage(
          { type: "oauth_error", error: errorDescription || error },
          window.location.origin
        );
      }
      // Close after 3 seconds
      setTimeout(() => window.close(), 3000);
      return;
    }

    if (!code || !state) {
      setStatus("error");
      setMessage("Missing authorization code or state parameter");
      if (window.opener) {
        window.opener.postMessage(
          { type: "oauth_error", error: "Missing parameters" },
          window.location.origin
        );
      }
      setTimeout(() => window.close(), 3000);
      return;
    }

    // Extract platform from state parameter
    const platform = state.split(":")[0];

    // Call backend callback endpoint
    fetch(
      `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/oauth/${platform}/callback?code=${code}&state=${state}`,
      {
        method: "GET",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      }
    )
      .then(async (response) => {
        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          throw new Error(error.detail || "Failed to complete OAuth");
        }
        return response.json();
      })
      .then(() => {
        setStatus("success");
        setMessage("Successfully connected! Closing window...");
        // Notify parent window of success
        if (window.opener) {
          window.opener.postMessage(
            { type: "oauth_success", platform },
            window.location.origin
          );
        }
        // Close window after 1 second
        setTimeout(() => window.close(), 1000);
      })
      .catch((err) => {
        setStatus("error");
        setMessage(err.message || "Failed to complete OAuth");
        if (window.opener) {
          window.opener.postMessage(
            { type: "oauth_error", error: err.message },
            window.location.origin
          );
        }
        setTimeout(() => window.close(), 3000);
      });
  }, [searchParams]);

  return (
    <div className="flex h-screen items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4 text-center">
        {status === "loading" && (
          <>
            <RefreshCw className="h-12 w-12 animate-spin text-primary" />
            <p className="text-lg font-medium">{message}</p>
          </>
        )}
        {status === "success" && (
          <>
            <CheckCircle2 className="h-12 w-12 text-green-600" />
            <p className="text-lg font-medium text-green-600">{message}</p>
          </>
        )}
        {status === "error" && (
          <>
            <XCircle className="h-12 w-12 text-destructive" />
            <p className="text-lg font-medium text-destructive">{message}</p>
            <p className="text-sm text-muted-foreground">
              This window will close automatically
            </p>
          </>
        )}
      </div>
    </div>
  );
}
