"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import type { OAuthConnection, OAuthPlatform } from "@/types";
import { toast } from "sonner";
import {
  RefreshCw,
  Instagram,
  Linkedin,
  Facebook,
  Twitter,
  Youtube,
  Link as LinkIcon,
  Unlink,
} from "lucide-react";

const PLATFORM_CONFIG: Record<
  OAuthPlatform,
  { label: string; icon: any; color: string }
> = {
  instagram: {
    label: "Instagram",
    icon: Instagram,
    color: "text-pink-600",
  },
  facebook: {
    label: "Facebook",
    icon: Facebook,
    color: "text-blue-600",
  },
  linkedin: {
    label: "LinkedIn",
    icon: Linkedin,
    color: "text-blue-700",
  },
  twitter: {
    label: "X / Twitter",
    icon: Twitter,
    color: "text-black dark:text-white",
  },
  youtube: {
    label: "YouTube",
    icon: Youtube,
    color: "text-red-600",
  },
};

export default function SocialConnectionsPage() {
  const [connections, setConnections] = useState<OAuthConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const [connectingPlatform, setConnectingPlatform] = useState<OAuthPlatform | null>(null);

  const loadConnections = async () => {
    setLoading(true);
    try {
      const data = await api.getOAuthStatus();
      setConnections(data);
    } catch (err: any) {
      toast.error(err.message || "Failed to load connection status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadConnections();

    // Listen for OAuth callback messages from popup
    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;

      if (event.data.type === "oauth_success") {
        toast.success(`Successfully connected to ${event.data.platform}`);
        loadConnections();
      } else if (event.data.type === "oauth_error") {
        toast.error(event.data.error || "OAuth connection failed");
      }
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  const handleConnect = async (platform: OAuthPlatform) => {
    setConnectingPlatform(platform);
    try {
      const { auth_url } = await api.initiateOAuth(platform);

      // Open OAuth URL in popup window
      const width = 600;
      const height = 700;
      const left = window.screen.width / 2 - width / 2;
      const top = window.screen.height / 2 - height / 2;

      window.open(
        auth_url,
        "oauth_popup",
        `width=${width},height=${height},left=${left},top=${top},toolbar=no,location=no,status=no,menubar=no,scrollbars=yes,resizable=yes`
      );
    } catch (err: any) {
      toast.error(err.message || `Failed to initiate ${platform} OAuth`);
    } finally {
      setConnectingPlatform(null);
    }
  };

  const handleDisconnect = async (platform: OAuthPlatform) => {
    try {
      await api.disconnectOAuth(platform);
      toast.success(`Disconnected from ${PLATFORM_CONFIG[platform].label}`);
      loadConnections();
    } catch (err: any) {
      toast.error(err.message || `Failed to disconnect from ${platform}`);
    }
  };

  const getConnectionForPlatform = (platform: OAuthPlatform): OAuthConnection => {
    return (
      connections.find((c) => c.platform === platform) || {
        platform,
        status: "disconnected",
      }
    );
  };

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <Header
        title="Social Connections"
        description="Manage OAuth connections to social media platforms"
        actions={
          <Button size="sm" variant="outline" onClick={loadConnections}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Refresh
          </Button>
        }
      />

      <div className="p-6">
        <div className="grid gap-4 max-w-3xl">
          {(Object.keys(PLATFORM_CONFIG) as OAuthPlatform[]).map((platform) => {
            const config = PLATFORM_CONFIG[platform];
            const connection = getConnectionForPlatform(platform);
            const Icon = config.icon;
            const isConnected = connection.status === "connected";
            const hasError = connection.status === "error";

            return (
              <Card key={platform}>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Icon className={`h-6 w-6 ${config.color}`} />
                      <div>
                        <CardTitle className="text-base">{config.label}</CardTitle>
                        {isConnected && connection.username && (
                          <p className="text-xs text-muted-foreground mt-1">
                            Connected as: {connection.username}
                          </p>
                        )}
                      </div>
                    </div>
                    <Badge
                      variant={
                        isConnected ? "success" : hasError ? "destructive" : "secondary"
                      }
                    >
                      {isConnected
                        ? "Connected"
                        : hasError
                        ? "Error"
                        : "Not Connected"}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  {hasError && connection.error_message && (
                    <p className="text-xs text-destructive mb-3">
                      {connection.error_message}
                    </p>
                  )}
                  <div className="flex items-center gap-2">
                    {isConnected ? (
                      <>
                        {connection.connected_at && (
                          <p className="text-xs text-muted-foreground flex-1">
                            Connected on{" "}
                            {new Date(connection.connected_at).toLocaleDateString()}
                          </p>
                        )}
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleDisconnect(platform)}
                        >
                          <Unlink className="h-3 w-3 mr-1" />
                          Disconnect
                        </Button>
                      </>
                    ) : (
                      <Button
                        size="sm"
                        onClick={() => handleConnect(platform)}
                        disabled={connectingPlatform === platform}
                      >
                        <LinkIcon className="h-3 w-3 mr-1" />
                        {connectingPlatform === platform
                          ? "Opening..."
                          : "Connect"}
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
