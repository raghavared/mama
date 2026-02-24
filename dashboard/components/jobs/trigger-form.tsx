"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api } from "@/lib/api";
import { toast } from "sonner";
import { Rocket } from "lucide-react";

const PLATFORMS = [
  { id: "instagram", label: "Instagram" },
  { id: "linkedin", label: "LinkedIn" },
  { id: "facebook", label: "Facebook" },
  { id: "x_twitter", label: "X / Twitter" },
  { id: "youtube", label: "YouTube" },
];

export function TriggerForm() {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [topic, setTopic] = useState("");
  const [platforms, setPlatforms] = useState<string[]>([
    "instagram",
    "linkedin",
    "facebook",
  ]);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const togglePlatform = (id: string) => {
    setPlatforms((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    if (platforms.length === 0) {
      toast.error("Select at least one platform");
      return;
    }
    setLoading(true);
    try {
      const res = await api.triggerJob(topic, "manual", platforms, name.trim() || undefined, description.trim() || undefined);
      toast.success("Job triggered!");
      router.push(`/jobs/${res.job_id}`);
    } catch (err: any) {
      toast.error(err.message || "Failed to trigger job");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="max-w-2xl mx-auto">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Rocket className="h-5 w-5" />
          Trigger New Content Job
        </CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <label className="text-sm font-medium">Job Name <span className="text-muted-foreground font-normal">(optional)</span></label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Q1 AI Tools Campaign"
              maxLength={200}
            />
            <p className="text-xs text-muted-foreground">
              A short label to identify this job in the dashboard
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Description <span className="text-muted-foreground font-normal">(optional)</span></label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What is this job about? Any context, goals, or notes..."
              className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 resize-none"
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Topic</label>
            <Input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. AI productivity tools for small businesses"
              required
            />
            <p className="text-xs text-muted-foreground">
              MAMA will enrich this topic and create a content brief
            </p>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Target Platforms</label>
            <div className="flex flex-wrap gap-2">
              {PLATFORMS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => togglePlatform(p.id)}
                  className="focus:outline-none"
                >
                  <Badge
                    variant={
                      platforms.includes(p.id) ? "default" : "outline"
                    }
                    className="cursor-pointer"
                  >
                    {p.label}
                  </Badge>
                </button>
              ))}
            </div>
          </div>

          <Button type="submit" disabled={loading} className="w-full">
            {loading ? (
              <span className="flex items-center gap-2">
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                Triggering...
              </span>
            ) : (
              <>
                <Rocket className="h-4 w-4 mr-2" />
                Launch Content Pipeline
              </>
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
