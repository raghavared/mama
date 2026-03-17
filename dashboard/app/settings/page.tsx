"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { SystemConfig, Platform, OAuthConnection, OAuthPlatform } from "@/types";
import { toast } from "sonner";
import { Save, Key, Palette, Settings2, RefreshCw, Link2, Instagram, Linkedin, Facebook, Twitter, Youtube, Link as LinkIcon, Unlink } from "lucide-react";

const ALL_PLATFORMS: { id: Platform; label: string }[] = [
  { id: "instagram", label: "Instagram" },
  { id: "linkedin", label: "LinkedIn" },
  { id: "facebook", label: "Facebook" },
  { id: "x_twitter", label: "X / Twitter" },
  { id: "youtube", label: "YouTube" },
];

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

export default function SettingsPage() {
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [connections, setConnections] = useState<OAuthConnection[]>([]);
  const [connectingPlatform, setConnectingPlatform] = useState<OAuthPlatform | null>(null);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await api.getConfig();
      setConfig(data);
    } catch {
      // error
    } finally {
      setLoading(false);
    }
  };

  const loadConnections = async () => {
    try {
      const data = await api.getOAuthStatus();
      // Ensure data is an array
      if (Array.isArray(data)) {
        setConnections(data);
      } else {
        console.warn('OAuth status returned non-array:', data);
        setConnections([]);
      }
    } catch (err: any) {
      console.error('Failed to load OAuth connections:', err);
      setConnections([]); // CRITICAL: Set empty array on error
      // Don't show error to user - connections are optional
    }
  };

  useEffect(() => {
    loadConfig();
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

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    try {
      const updated = await api.updateConfig(config);
      setConfig(updated);
      toast.success("Settings saved");
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  };

  const updateField = (field: keyof SystemConfig, value: any) => {
    setConfig((prev) => (prev ? { ...prev, [field]: value } : null));
  };

  const togglePlatform = (platformId: Platform) => {
    if (!config) return;
    const current = config.active_platforms;
    const updated = current.includes(platformId)
      ? current.filter((p) => p !== platformId)
      : [...current, platformId];
    updateField("active_platforms", updated);
  };

  const handleConnect = async (platform: OAuthPlatform) => {
    setConnectingPlatform(platform);
    try {
      const response = await api.initiateOAuth(platform);

      // CRITICAL: Validate response before opening popup
      if (!response || !response.auth_url) {
        throw new Error(`No authorization URL returned for ${platform}. Please configure OAuth credentials in .env file.`);
      }

      const { auth_url } = response;

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
      console.error('OAuth initiation error:', err);
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
    // Safety check - ensure connections is an array
    if (!Array.isArray(connections)) {
      return { platform, status: "disconnected" };
    }
    return (
      connections.find((c) => c.platform === platform) || {
        platform,
        status: "disconnected",
      }
    );
  };

  if (!config && loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <Header
        title="Settings"
        description="System configuration"
        actions={
          <Button size="sm" onClick={handleSave} disabled={saving}>
            <Save className="h-4 w-4 mr-1" />
            {saving ? "Saving..." : "Save Changes"}
          </Button>
        }
      />

      <div className="p-6">
        <Tabs defaultValue="brand">
          <TabsList className="mb-4">
            <TabsTrigger value="brand">
              <Palette className="h-3 w-3 mr-1" /> Brand
            </TabsTrigger>
            <TabsTrigger value="pipeline">
              <Settings2 className="h-3 w-3 mr-1" /> Pipeline
            </TabsTrigger>
            <TabsTrigger value="apis">
              <Key className="h-3 w-3 mr-1" /> API Keys
            </TabsTrigger>
            <TabsTrigger value="social">
              <Link2 className="h-3 w-3 mr-1" /> Social Connections
            </TabsTrigger>
          </TabsList>

          <TabsContent value="brand">
            <div className="grid gap-4 max-w-2xl">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Brand Identity</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Brand Name</label>
                    <Input
                      value={config?.brand_name || ""}
                      onChange={(e) =>
                        updateField("brand_name", e.target.value)
                      }
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">
                      Brand Description
                    </label>
                    <Textarea
                      value={config?.brand_description || ""}
                      onChange={(e) =>
                        updateField("brand_description", e.target.value)
                      }
                      rows={3}
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Brand Voice</label>
                    <Input
                      value={config?.brand_voice || ""}
                      onChange={(e) =>
                        updateField("brand_voice", e.target.value)
                      }
                      placeholder="e.g. professional, friendly, innovative"
                    />
                  </div>
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Content Goals</label>
                    <Textarea
                      value={config?.content_goals || ""}
                      onChange={(e) =>
                        updateField("content_goals", e.target.value)
                      }
                      rows={2}
                    />
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="pipeline">
            <div className="grid gap-4 max-w-2xl">
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Pipeline Settings</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">
                      Max Improvement Cycles
                    </label>
                    <Input
                      type="number"
                      min={1}
                      max={10}
                      value={config?.max_improvement_cycles || 3}
                      onChange={(e) =>
                        updateField(
                          "max_improvement_cycles",
                          parseInt(e.target.value)
                        )
                      }
                    />
                    <p className="text-xs text-muted-foreground">
                      Maximum times content loops back for improvements after
                      rejection
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Image Generation</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Provider</label>
                    <p className="text-xs text-muted-foreground">
                      Choose which AI service generates images for content posts
                    </p>
                    <div className="space-y-2">
                      {[
                        { id: 'dalle', label: 'DALL-E 3 (OpenAI)', description: 'High quality image generation from OpenAI' },
                        { id: 'gemini', label: 'Imagen 3 (Google Gemini)', description: 'Fast, high-quality generation from Google' },
                      ].map((provider) => (
                        <div
                          key={provider.id}
                          className="flex items-center justify-between rounded-md border p-3 cursor-pointer"
                          onClick={() => updateField('image_generation_provider', provider.id)}
                        >
                          <div>
                            <span className="text-sm font-medium">{provider.label}</span>
                            <p className="text-xs text-muted-foreground">{provider.description}</p>
                          </div>
                          <div
                            className={cn(
                              'h-4 w-4 rounded-full border-2',
                              config?.image_generation_provider === provider.id
                                ? 'border-primary bg-primary'
                                : 'border-muted-foreground'
                            )}
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">Active Platforms</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <div className="space-y-2">
                      {ALL_PLATFORMS.map((p) => (
                        <div
                          key={p.id}
                          className="flex items-center justify-between rounded-md border p-3"
                        >
                          <span className="text-sm">{p.label}</span>
                          <Switch
                            checked={
                              config?.active_platforms.includes(p.id) || false
                            }
                            onCheckedChange={() => togglePlatform(p.id)}
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="apis">
            <Card className="max-w-2xl">
              <CardHeader className="pb-3">
                <CardTitle className="text-base">
                  API Key Status
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {config?.api_keys_configured &&
                    Object.entries(config.api_keys_configured).map(
                      ([key, configured]) => (
                        <div
                          key={key}
                          className="flex items-center justify-between rounded-md border p-3"
                        >
                          <div className="flex items-center gap-2">
                            <Key className="h-4 w-4 text-muted-foreground" />
                            <span className="text-sm font-medium">
                              {key
                                .replace(/_/g, " ")
                                .replace(/\b\w/g, (l) => l.toUpperCase())}
                            </span>
                          </div>
                          <Badge
                            variant={configured ? "success" : "destructive"}
                          >
                            {configured ? "Configured" : "Missing"}
                          </Badge>
                        </div>
                      )
                    )}
                </div>
                <p className="text-xs text-muted-foreground mt-4">
                  API keys are configured via environment variables on the
                  server. Update .env file and restart the API.
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="social">
            <div className="grid gap-4 max-w-3xl">
              {(Object.keys(PLATFORM_CONFIG) as OAuthPlatform[]).map((platform) => {
                const platformConfig = PLATFORM_CONFIG[platform];
                const connection = getConnectionForPlatform(platform);
                const Icon = platformConfig.icon;
                const isConnected = connection.status === "connected";
                const hasError = connection.status === "error";

                return (
                  <Card key={platform}>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Icon className={`h-6 w-6 ${platformConfig.color}`} />
                          <div>
                            <CardTitle className="text-base">{platformConfig.label}</CardTitle>
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
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
