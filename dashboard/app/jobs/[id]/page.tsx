"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { Header } from "@/components/layout/header";
import { PipelineFlow } from "@/components/dashboard/pipeline-flow";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useWebSocket } from "@/lib/websocket";
import type { ContentJob } from "@/types";
import { statusColor, formatDate, pipelineLabel } from "@/lib/utils";
import {
  RefreshCw,
  CheckCircle2,
  XCircle,
  FileText,
  Image as ImageIcon,
  Film,
  Volume2,
  Globe,
  Pause,
  Play,
  Loader2,
  Clock,
  AlertCircle,
  RotateCcw,
  ChevronDown,
  ChevronRight,
  History,
  Maximize2,
} from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "sonner";

// Extended job type with pipeline_logs and current_step
interface JobWithLogs extends ContentJob {
  current_step: string | null;
  pipeline_logs: {
    step: string;
    status: string;
    detail: string;
    timestamp: string;
  }[];
  reinitiation_count: number;
  run_history: {
    run_number: number;
    reinitiated_at: string;
    reinitiated_by: string;
    status_at_end: string;
    pipeline_type: string | null;
    pipeline_logs: { step: string; status: string; detail: string; timestamp: string; }[];
  }[];
}

const STEP_LABELS: Record<string, string> = {
  mama_enrichment: "MAMA - Topic Enrichment",
  cmi_brief: "CMI - Content Brief",
  decision_maker: "Decision Maker",
  cst_script: "CST - Image Script",
  vst_script: "VST - Video Script",
  csa_approval: "CSA - Script Approval",
  human_review: "Human Review",
  image_generation: "Image Generation",
  video_generation: "Video Generation",
};

function StepStatusIcon({ status }: { status: string }) {
  switch (status) {
    case "running":
      return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
    case "done":
      return <CheckCircle2 className="h-4 w-4 text-green-500" />;
    case "failed":
      return <XCircle className="h-4 w-4 text-red-500" />;
    case "paused":
      return <Pause className="h-4 w-4 text-yellow-500" />;
    default:
      return <Clock className="h-4 w-4 text-muted-foreground" />;
  }
}

export default function JobDetailPage() {
  const params = useParams();
  const jobId = params.id as string;
  const [job, setJob] = useState<JobWithLogs | null>(null);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();
  const subscribe = useWebSocket((s) => s.subscribe);

  const loadJob = useCallback(async () => {
    try {
      const data = await api.getJob(jobId);
      setJob(data as unknown as JobWithLogs);
    } catch {
      // silently fail on polling
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    loadJob();
    // Poll every 3s while in_progress, otherwise 10s
    const interval = setInterval(() => {
      loadJob();
    }, job?.status === "in_progress" ? 3000 : 10000);
    return () => clearInterval(interval);
  }, [jobId, job?.status, loadJob]);

  // Listen for real-time WebSocket events for this job
  useEffect(() => {
    const unsub = subscribe("*", (msg) => {
      const payload = msg.payload as Record<string, unknown>;
      if (payload?.job_id === jobId) {
        // Refresh on any event for this job
        loadJob();
      }
    });
    return unsub;
  }, [jobId, subscribe, loadJob]);

  const handlePause = async () => {
    try {
      await api.pauseJob(jobId);
      toast.success("Job paused");
      loadJob();
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleResume = async () => {
    try {
      await api.resumeJob(jobId);
      toast.success("Job resumed");
      loadJob();
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const handleApproval = async (decision: "approved" | "rejected") => {
    if (!user) return;
    const feedback =
      decision === "rejected"
        ? prompt("Provide feedback for rejection:")
        : undefined;
    if (decision === "rejected" && !feedback) return;

    try {
      await api.approveJob(jobId, decision, user.id, feedback || undefined);
      toast.success(`Job ${decision}`);
      loadJob();
    } catch (err: any) {
      toast.error(err.message);
    }
  };

  const REINITIATEABLE = new Set(["failed", "rejected", "published", "awaiting_approval"]);
  const isProcessing = job?.status === "in_progress";
  const isPaused = job?.status === "paused";
  const canReinitiate = job ? REINITIATEABLE.has(job.status) : false;
  const [reinitiating, setReinitiating] = useState(false);
  const [expandedStep, setExpandedStep] = useState<string | null>(null);
  const [expandedRun, setExpandedRun] = useState<number | null>(null);
  const [previewAsset, setPreviewAsset] = useState<JobWithLogs['media_assets'][0] | null>(null);

  const handleReinitiate = async () => {
    if (!job) return;
    setReinitiating(true);
    try {
      await api.reinitiateJob(job.id);
      toast.success("Job reinitiated — pipeline restarting");
      loadJob();
    } catch (err: any) {
      toast.error(err.message || "Failed to reinitiate");
    } finally {
      setReinitiating(false);
    }
  };

  if (!job) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex flex-col">
      <Header
        title={job.name || job.topic}
        description={`${job.name ? job.topic + " | " : ""}Job ${job.id?.slice(0, 8) || ""}... | ${pipelineLabel(job.pipeline_type)}`}
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={loadJob}>
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>

            {/* Reinitiate */}
            {canReinitiate && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleReinitiate}
                disabled={reinitiating}
              >
                {reinitiating ? (
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                ) : (
                  <RotateCcw className="h-4 w-4 mr-1" />
                )}
                Reinitiate
              </Button>
            )}

            {/* Pause / Resume */}
            {isProcessing && (
              <Button size="sm" variant="outline" onClick={handlePause}>
                <Pause className="h-4 w-4 mr-1" />
                Pause
              </Button>
            )}
            {isPaused && (
              <Button size="sm" variant="default" onClick={handleResume}>
                <Play className="h-4 w-4 mr-1" />
                Resume
              </Button>
            )}

            {/* Approve / Reject */}
            {job.status === "awaiting_approval" && job.media_assets.length === 0 && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Loader2 className="h-3 w-3 animate-spin" />
                Media still generating…
              </span>
            )}
            {job.status === "awaiting_approval" && job.media_assets.length > 0 && (
              <>
                <Button
                  size="sm"
                  variant="success"
                  onClick={() => handleApproval("approved")}
                >
                  <CheckCircle2 className="h-4 w-4 mr-1" />
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => handleApproval("rejected")}
                >
                  <XCircle className="h-4 w-4 mr-1" />
                  Reject
                </Button>
              </>
            )}
          </div>
        }
      />

      <div className="p-6 space-y-6">
        {/* ── Live Processing Banner ──────────────────────────────────── */}
        {isProcessing && (
          <Card className="border-blue-200 bg-blue-50/50 dark:border-blue-900 dark:bg-blue-950/30">
            <CardContent className="flex items-center gap-4 p-4">
              <div className="relative">
                <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />
                <div className="absolute inset-0 h-8 w-8 rounded-full bg-blue-500/20 animate-ping" />
              </div>
              <div className="flex-1">
                <p className="font-medium text-blue-700 dark:text-blue-300">
                  Pipeline is processing...
                </p>
                <p className="text-sm text-blue-600/80 dark:text-blue-400/80">
                  {job.current_step
                    ? `Current step: ${STEP_LABELS[job.current_step] || job.current_step}`
                    : "Starting pipeline..."}
                </p>
              </div>
              <Badge className="bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900 dark:text-blue-300">
                LIVE
              </Badge>
            </CardContent>
          </Card>
        )}

        {isPaused && (
          <Card className="border-yellow-200 bg-yellow-50/50 dark:border-yellow-900 dark:bg-yellow-950/30">
            <CardContent className="flex items-center gap-4 p-4">
              <Pause className="h-8 w-8 text-yellow-500" />
              <div className="flex-1">
                <p className="font-medium text-yellow-700 dark:text-yellow-300">
                  Pipeline is paused
                </p>
                <p className="text-sm text-yellow-600/80 dark:text-yellow-400/80">
                  Click Resume to continue processing
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* ── Status Bar ─────────────────────────────────────────────── */}
        <div className="flex items-center gap-4 flex-wrap">
          <Badge className={statusColor(job.status)} variant="secondary">
            {job.status.replace(/_/g, " ")}
          </Badge>
          <span className="text-sm text-muted-foreground">
            Created {formatDate(job.created_at)}
          </span>
          <span className="text-sm text-muted-foreground">
            Updated {formatDate(job.updated_at)}
          </span>
          {job.improvement_count > 0 && (
            <Badge variant="warning">
              {job.improvement_count} improvement cycle(s)
            </Badge>
          )}
          {job.reinitiation_count > 0 && (
            <Badge variant="outline">
              {job.reinitiation_count} reinitiation{job.reinitiation_count > 1 ? 's' : ''}
            </Badge>
          )}
          {job.error_message && (
            <div className="flex items-center gap-1 text-red-600 text-sm">
              <AlertCircle className="h-4 w-4" />
              {job.error_message}
            </div>
          )}
        </div>

        {/* ── Job Description ─────────────────────────────────────────── */}
        {job.description && (
          <p className="text-sm text-muted-foreground border-l-2 border-muted pl-3">
            {job.description}
          </p>
        )}

        {/* ── Pipeline Visualization ─────────────────────────────────── */}
        <PipelineFlow job={job} />

        {/* ── Pipeline Logs (live step tracker) ──────────────────────── */}
        {job.pipeline_logs && job.pipeline_logs.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                Pipeline Execution Log
                {isProcessing && (
                  <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-1">
                {(() => {
                  // Group logs by step, preserving order of first appearance
                  const stepMap = new Map<string, typeof job.pipeline_logs>();
                  for (const log of job.pipeline_logs) {
                    if (!stepMap.has(log.step)) stepMap.set(log.step, []);
                    stepMap.get(log.step)!.push(log);
                  }

                  return Array.from(stepMap.entries()).map(([step, entries]) => {
                    const latest = entries[entries.length - 1];
                    const isExpanded = expandedStep === step;
                    const borderColor =
                      latest.status === "running"
                        ? "#3b82f6"
                        : latest.status === "done"
                        ? "#22c55e"
                        : latest.status === "failed"
                        ? "#ef4444"
                        : "#d1d5db";

                    // Parse pipeline decision from decision_maker detail text
                    let decisionPipeline: string | null = null;
                    if (step === "decision_maker") {
                      for (const e of entries) {
                        const m = e.detail?.match(/Pipeline:\s*(\w+)/);
                        if (m) { decisionPipeline = m[1]; break; }
                      }
                    }

                    return (
                      <div key={step}>
                        {/* Clickable step row */}
                        <div
                          className="flex items-center gap-3 text-sm border-l-2 pl-3 py-1.5 cursor-pointer hover:bg-muted/50 rounded-r-sm select-none"
                          style={{ borderColor }}
                          onClick={() => setExpandedStep(isExpanded ? null : step)}
                        >
                          <StepStatusIcon status={latest.status} />
                          <div className="flex-1 min-w-0">
                            <span className="font-medium">
                              {STEP_LABELS[step] || step}
                            </span>
                            {latest.detail && (
                              <p className="text-muted-foreground text-xs mt-0.5 truncate">
                                {latest.detail}
                              </p>
                            )}
                          </div>
                          <span className="text-xs text-muted-foreground whitespace-nowrap">
                            {new Date(latest.timestamp).toLocaleTimeString()}
                          </span>
                          {isExpanded ? (
                            <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          ) : (
                            <ChevronRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          )}
                        </div>

                        {/* Expanded content */}
                        {isExpanded && (
                          <div className="ml-8 mt-1 mb-3 space-y-1">
                            {/* Special decision_maker card */}
                            {step === "decision_maker" && decisionPipeline && (
                              <div className="rounded-lg border p-4 bg-muted/30 mb-3">
                                <div className="flex items-center gap-3">
                                  {decisionPipeline === "image_post" ? (
                                    <ImageIcon className="h-8 w-8 text-blue-500 flex-shrink-0" />
                                  ) : (
                                    <Film className="h-8 w-8 text-purple-500 flex-shrink-0" />
                                  )}
                                  <div className="flex-1 min-w-0">
                                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                                      Pipeline Decision
                                    </p>
                                    <p className="text-xl font-bold">
                                      {decisionPipeline === "image_post" ? "Image Post" : "Video Post"}
                                    </p>
                                  </div>
                                  <Badge
                                    className={
                                      decisionPipeline === "image_post"
                                        ? "bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900 dark:text-blue-300"
                                        : "bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-900 dark:text-purple-300"
                                    }
                                  >
                                    {decisionPipeline}
                                  </Badge>
                                </div>
                                {entries.find((e) => e.detail)?.detail && (
                                  <p className="mt-2 text-sm text-muted-foreground">
                                    {entries.find((e) => e.detail)?.detail}
                                  </p>
                                )}
                              </div>
                            )}

                            {/* Raw log entries for this step */}
                            {entries.map((entry, i) => (
                              <div key={i} className="flex items-start gap-2 text-xs py-0.5">
                                <StepStatusIcon status={entry.status} />
                                <span className="text-muted-foreground whitespace-nowrap">
                                  {new Date(entry.timestamp).toLocaleTimeString()}
                                </span>
                                <span
                                  className={
                                    entry.status === "running"
                                      ? "text-blue-600 font-medium"
                                      : entry.status === "failed"
                                      ? "text-red-600 font-medium"
                                      : "text-foreground font-medium"
                                  }
                                >
                                  {entry.status}
                                </span>
                                {entry.detail && (
                                  <span className="text-muted-foreground flex-1">
                                    — {entry.detail}
                                  </span>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    );
                  });
                })()}
              </div>
            </CardContent>
          </Card>
        )}

        {/* ── Run History ─────────────────────────────────────────────── */}
        {job.run_history && job.run_history.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center gap-2">
                <History className="h-4 w-4" />
                Run History
                <Badge variant="secondary">{job.run_history.length} previous run{job.run_history.length > 1 ? 's' : ''}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {[...job.run_history].reverse().map((run) => (
                  <div key={run.run_number} className="border rounded-md overflow-hidden">
                    <div
                      className="flex items-center gap-3 p-3 cursor-pointer hover:bg-muted/50 select-none"
                      onClick={() => setExpandedRun(expandedRun === run.run_number ? null : run.run_number)}
                    >
                      <RotateCcw className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <span className="text-sm font-medium">Run #{run.run_number}</span>
                        <p className="text-xs text-muted-foreground">
                          Ended: {run.status_at_end.replace(/_/g, ' ')} • {run.pipeline_type || 'unknown'} • {run.pipeline_logs?.length || 0} steps
                        </p>
                      </div>
                      <span className="text-xs text-muted-foreground whitespace-nowrap">{formatDate(run.reinitiated_at)}</span>
                      {expandedRun === run.run_number ? <ChevronDown className="h-4 w-4 text-muted-foreground" /> : <ChevronRight className="h-4 w-4 text-muted-foreground" />}
                    </div>
                    {expandedRun === run.run_number && run.pipeline_logs && (
                      <div className="border-t px-3 py-2 bg-muted/30 space-y-1">
                        <p className="text-xs text-muted-foreground mb-2">Reinitiated by {run.reinitiated_by}</p>
                        {run.pipeline_logs.map((log, i) => (
                          <div key={i} className="flex items-start gap-2 text-xs py-0.5">
                            <StepStatusIcon status={log.status} />
                            <span className="text-muted-foreground whitespace-nowrap">{new Date(log.timestamp).toLocaleTimeString()}</span>
                            <span className="font-medium">{STEP_LABELS[log.step] || log.step}</span>
                            {log.detail && <span className="text-muted-foreground">— {log.detail}</span>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* ── Tabbed Content ─────────────────────────────────────────── */}
        <Tabs defaultValue="brief">
          <TabsList>
            <TabsTrigger value="brief">
              <FileText className="h-3 w-3 mr-1" /> Brief
            </TabsTrigger>
            <TabsTrigger value="script">
              <FileText className="h-3 w-3 mr-1" /> Script
            </TabsTrigger>
            <TabsTrigger value="media">
              <ImageIcon className="h-3 w-3 mr-1" /> Media
            </TabsTrigger>
            <TabsTrigger value="approvals">
              <CheckCircle2 className="h-3 w-3 mr-1" /> Approvals
            </TabsTrigger>
            <TabsTrigger value="published">
              <Globe className="h-3 w-3 mr-1" /> Published
            </TabsTrigger>
          </TabsList>

          <TabsContent value="brief">
            {job.content_brief ? (
              <Card>
                <CardContent className="p-4 space-y-3">
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Marketing Angle</label>
                    <p className="text-sm">{job.content_brief.marketing_angle}</p>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Target Audience</label>
                    <p className="text-sm">{job.content_brief.target_audience}</p>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Tone</label>
                    <p className="text-sm">{job.content_brief.tone}</p>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Key Messages</label>
                    <ul className="list-disc list-inside text-sm">
                      {job.content_brief.key_messages.map((msg, i) => (
                        <li key={i}>{msg}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground">Platform Strategy</label>
                    <div className="grid grid-cols-2 gap-2 mt-1">
                      {Object.entries(job.content_brief.platform_strategy).map(([platform, strategy]) => (
                        <div key={platform} className="rounded border p-2 text-xs">
                          <span className="font-medium capitalize">{platform}</span>: {strategy}
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                {isProcessing && <Loader2 className="h-4 w-4 animate-spin" />}
                {isProcessing ? "Generating content brief..." : "Content brief not yet generated."}
              </div>
            )}
          </TabsContent>

          <TabsContent value="script">
            {job.script ? (
              <Card>
                <CardContent className="p-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{job.script.type}</Badge>
                    <Badge variant="secondary">v{job.script.version}</Badge>
                    <span className="text-xs text-muted-foreground">by {job.script.created_by}</span>
                  </div>
                  <pre className="whitespace-pre-wrap text-sm bg-muted p-4 rounded-md max-h-[400px] overflow-y-auto">
                    {job.script.content}
                  </pre>
                  {job.script.image_prompts && job.script.image_prompts.length > 0 && (
                    <div>
                      <label className="text-xs font-medium text-muted-foreground">Image Prompts</label>
                      {job.script.image_prompts.map((p, i) => (
                        <p key={i} className="text-sm bg-muted p-2 rounded mt-1">{p}</p>
                      ))}
                    </div>
                  )}
                  {job.script.video_frames && job.script.video_frames.length > 0 && (
                    <div>
                      <label className="text-xs font-medium text-muted-foreground">Video Frames</label>
                      <div className="space-y-2 mt-1">
                        {job.script.video_frames.map((f) => (
                          <div key={f.frame_number} className="bg-muted p-2 rounded text-sm">
                            <div className="flex items-center gap-2">
                              <Film className="h-3 w-3" />
                              <span className="font-medium">Frame {f.frame_number}</span>
                              <span className="text-xs text-muted-foreground">{f.duration_seconds}s</span>
                            </div>
                            <p className="mt-1">{f.scene_description}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ) : (
              <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                {isProcessing && <Loader2 className="h-4 w-4 animate-spin" />}
                {isProcessing ? "Generating script..." : "Script not yet generated."}
              </div>
            )}
          </TabsContent>

          <TabsContent value="media">
            <div className="grid gap-4 sm:grid-cols-2">
              {job.media_assets.length === 0 && (
                <div className="col-span-2 flex flex-col items-center justify-center py-8 gap-2 text-muted-foreground">
                  {isProcessing ? (
                    <>
                      <Loader2 className="h-8 w-8 animate-spin" />
                      <p className="text-sm">Generating media assets…</p>
                    </>
                  ) : (
                    <>
                      <ImageIcon className="h-8 w-8 opacity-30" />
                      <p className="text-sm">No media assets yet.</p>
                    </>
                  )}
                </div>
              )}
              {job.media_assets.map((asset) => {
                const hasUrl =
                  asset.url && asset.url.trim() !== "" && !asset.url.startsWith("stub");
                const isImage = asset.type === "image";
                const isVideo =
                  asset.type === "video_clip" || asset.type === "final_video";
                const TypeIcon =
                  asset.type === "image"
                    ? ImageIcon
                    : asset.type === "audio"
                    ? Volume2
                    : Film;
                return (
                  <Card key={asset.id}>
                    <CardContent className="p-4">
                      {/* Header row */}
                      <div className="flex items-center gap-2 mb-2">
                        <TypeIcon
                          className={`h-4 w-4 ${asset.type === "final_video" ? "text-green-500" : ""}`}
                        />
                        <span className="text-sm font-medium capitalize">
                          {asset.type.replace(/_/g, " ")}
                        </span>
                        <Badge variant="outline" className="text-xs ml-auto">
                          {asset.source}
                        </Badge>
                        {isImage && (
                          <Maximize2 className="h-3.5 w-3.5 text-muted-foreground cursor-pointer hover:text-foreground" onClick={() => setPreviewAsset(asset)} />
                        )}
                      </div>

                      {/* Media preview */}
                      {hasUrl && isImage && (
                        <div className="cursor-pointer" onClick={() => setPreviewAsset(asset)}>
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={asset.url}
                            alt={asset.type}
                            className="w-full object-cover max-h-64 rounded-md mb-2"
                          />
                        </div>
                      )}
                      {hasUrl && isVideo && (
                        <video
                          src={asset.url}
                          controls
                          className="w-full max-h-64 rounded-md mb-2"
                        />
                      )}
                      {!hasUrl && (
                        <div
                          className="flex items-center justify-center w-full h-24 rounded-md border-2 border-dashed border-muted mb-2 cursor-pointer hover:bg-muted/30"
                          onClick={() => setPreviewAsset(asset)}
                        >
                          <TypeIcon className="h-8 w-8 text-muted-foreground opacity-40" />
                        </div>
                      )}

                      {/* File path */}
                      <p
                        className="text-xs text-muted-foreground truncate"
                        title={asset.file_path}
                      >
                        {asset.file_path || "—"}
                      </p>

                      {/* Quality score bar */}
                      {asset.quality_score !== undefined && (
                        <div className="mt-2 flex items-center gap-2">
                          <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                            <div
                              className="h-full bg-green-500 rounded-full"
                              style={{
                                width: `${(asset.quality_score / 10) * 100}%`,
                              }}
                            />
                          </div>
                          <span className="text-xs font-medium">
                            {asset.quality_score}/10
                          </span>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </TabsContent>

          <TabsContent value="approvals">
            <div className="space-y-3">
              {job.approval_records.length === 0 && (
                <p className="text-sm text-muted-foreground py-4">No approval records yet.</p>
              )}
              {job.approval_records.map((record) => (
                <Card key={record.id}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline">{record.gate}</Badge>
                        <span className="text-sm text-muted-foreground">{record.subject_type}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {record.decision === "approved" ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500" />
                        )}
                        <span className="text-sm font-medium capitalize">{record.decision}</span>
                      </div>
                    </div>
                    {record.feedback && (
                      <p className="mt-2 text-sm bg-muted p-2 rounded">{record.feedback}</p>
                    )}
                    <p className="mt-2 text-xs text-muted-foreground">
                      Reviewed by {record.reviewer} at {formatDate(record.reviewed_at)}
                    </p>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="published">
            <div className="space-y-3">
              {job.published_posts.length === 0 && (
                <p className="text-sm text-muted-foreground py-4">Not published yet.</p>
              )}
              {job.published_posts.map((post) => (
                <Card key={post.id}>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Globe className="h-4 w-4" />
                        <span className="font-medium capitalize">{post.platform.replace("_", " ")}</span>
                      </div>
                      <a href={post.post_url} target="_blank" rel="noopener noreferrer" className="text-sm text-primary hover:underline">
                        View Post
                      </a>
                    </div>
                    {post.analytics && (
                      <div className="grid grid-cols-3 gap-2 mt-3">
                        {Object.entries(post.analytics).map(([key, val]) => (
                          <div key={key} className="text-center">
                            <p className="text-lg font-bold">{val}</p>
                            <p className="text-xs text-muted-foreground capitalize">{key}</p>
                          </div>
                        ))}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>

      {/* ── Image Lightbox Dialog ───────────────────────────────────── */}
      <Dialog open={!!previewAsset} onOpenChange={(open) => !open && setPreviewAsset(null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <ImageIcon className="h-4 w-4" />
              {previewAsset?.type?.replace(/_/g, ' ')} — {previewAsset?.source}
            </DialogTitle>
          </DialogHeader>
          <div className="flex flex-col items-center gap-4">
            {previewAsset && (() => {
              const hasRealUrl = previewAsset.url && !previewAsset.url.startsWith('stub');
              return hasRealUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={previewAsset.url} alt="preview" className="max-w-full max-h-[70vh] object-contain rounded-md" />
              ) : (
                <div className="flex flex-col items-center justify-center w-full h-64 bg-muted rounded-md gap-3">
                  <ImageIcon className="h-12 w-12 text-muted-foreground opacity-40" />
                  <p className="text-sm text-muted-foreground text-center">Development stub image<br/>No real image available in development mode</p>
                  <p className="text-xs text-muted-foreground font-mono">{previewAsset.file_path}</p>
                </div>
              );
            })()}
            {previewAsset?.metadata && Object.keys(previewAsset.metadata).length > 0 && (
              <div className="w-full text-xs text-muted-foreground border rounded-md p-3 space-y-1">
                {Object.entries(previewAsset.metadata).map(([k, v]) => (
                  <div key={k} className="flex gap-2">
                    <span className="font-medium capitalize">{k}:</span>
                    <span className="flex-1 break-all">{String(v)}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
