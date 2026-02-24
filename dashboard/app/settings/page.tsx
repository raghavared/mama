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
import type { SystemConfig, Platform } from "@/types";
import { toast } from "sonner";
import { Save, Key, Palette, Settings2, RefreshCw } from "lucide-react";

const ALL_PLATFORMS: { id: Platform; label: string }[] = [
  { id: "instagram", label: "Instagram" },
  { id: "linkedin", label: "LinkedIn" },
  { id: "facebook", label: "Facebook" },
  { id: "x_twitter", label: "X / Twitter" },
  { id: "youtube", label: "YouTube" },
];

export default function SettingsPage() {
  const [config, setConfig] = useState<SystemConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

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

  useEffect(() => {
    loadConfig();
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
        </Tabs>
      </div>
    </div>
  );
}
