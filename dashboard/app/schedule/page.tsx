"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import type { ScheduledJob } from "@/types";
import { toast } from "sonner";
import {
  Plus,
  Trash2,
  Calendar,
  Clock,
  RefreshCw,
} from "lucide-react";

const PLATFORMS = [
  { id: "instagram", label: "Instagram" },
  { id: "linkedin", label: "LinkedIn" },
  { id: "facebook", label: "Facebook" },
  { id: "x_twitter", label: "X" },
  { id: "youtube", label: "YouTube" },
];

export default function SchedulePage() {
  const [jobs, setJobs] = useState<ScheduledJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newTopic, setNewTopic] = useState("");
  const [newCron, setNewCron] = useState("0 9 * * 1-5");
  const [newPlatforms, setNewPlatforms] = useState<string[]>([
    "instagram",
    "linkedin",
  ]);

  const loadJobs = async () => {
    setLoading(true);
    try {
      const data = await api.listScheduledJobs();
      setJobs(data);
    } catch {
      // error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const handleCreate = async () => {
    if (!newTopic.trim()) return;
    try {
      await api.createScheduledJob({
        topic: newTopic,
        cron_expression: newCron,
        platforms: newPlatforms as any[],
        enabled: true,
      });
      toast.success("Scheduled job created");
      setShowCreate(false);
      setNewTopic("");
      loadJobs();
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this scheduled job?")) return;
    try {
      await api.deleteScheduledJob(id);
      toast.success("Deleted");
      loadJobs();
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const togglePlatform = (id: string) => {
    setNewPlatforms((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  return (
    <div className="flex flex-col">
      <Header
        title="Schedule"
        description="Automated content scheduling"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={loadJobs}>
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
            <Button size="sm" onClick={() => setShowCreate(true)}>
              <Plus className="h-4 w-4 mr-1" />
              Add Schedule
            </Button>
          </div>
        }
      />

      <div className="p-6 space-y-4">
        {jobs.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <Calendar className="h-12 w-12 mb-4 text-muted-foreground/30" />
            <p className="text-lg font-medium">No schedules yet</p>
            <p className="text-sm">Create automated content schedules</p>
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-2">
          {jobs.map((job) => (
            <Card key={job.id}>
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium">{job.topic}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <Clock className="h-3 w-3 text-muted-foreground" />
                      <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                        {job.cron_expression}
                      </code>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant={job.enabled ? "success" : "secondary"}>
                      {job.enabled ? "Active" : "Paused"}
                    </Badge>
                    <button
                      onClick={() => handleDelete(job.id)}
                      className="text-muted-foreground hover:text-destructive p-1"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1">
                  {job.platforms.map((p) => (
                    <Badge key={p} variant="outline" className="text-xs">
                      {p.replace("_", " ")}
                    </Badge>
                  ))}
                </div>
                <div className="text-xs text-muted-foreground">
                  Next run: {new Date(job.next_run).toLocaleString()}
                  {job.last_run && (
                    <> | Last: {new Date(job.last_run).toLocaleString()}</>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Create Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent onClose={() => setShowCreate(false)}>
          <DialogHeader>
            <DialogTitle>Create Scheduled Job</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 mt-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Topic</label>
              <Input
                value={newTopic}
                onChange={(e) => setNewTopic(e.target.value)}
                placeholder="Content topic..."
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Cron Expression</label>
              <Input
                value={newCron}
                onChange={(e) => setNewCron(e.target.value)}
                placeholder="0 9 * * 1-5"
              />
              <p className="text-xs text-muted-foreground">
                Default: 9 AM weekdays
              </p>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Platforms</label>
              <div className="flex flex-wrap gap-2">
                {PLATFORMS.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => togglePlatform(p.id)}
                    className="focus:outline-none"
                  >
                    <Badge
                      variant={
                        newPlatforms.includes(p.id) ? "default" : "outline"
                      }
                      className="cursor-pointer"
                    >
                      {p.label}
                    </Badge>
                  </button>
                ))}
              </div>
            </div>
            <Button onClick={handleCreate} className="w-full">
              Create Schedule
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
