"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ContentJob } from "@/types";
import { ArrowRight, CheckCircle2, XCircle, Loader2, Circle } from "lucide-react";

const IMAGE_STEPS = [
  { key: "topic_enrichment", label: "Topic" },
  { key: "content_brief", label: "Brief" },
  { key: "decision", label: "Decision" },
  { key: "image_script", label: "Script (CST)" },
  { key: "script_approval", label: "CSA Review" },
  { key: "image_generation", label: "Image Gen" },
  { key: "image_approval", label: "Approval" },
  { key: "publishing", label: "Publish" },
];

const VIDEO_STEPS = [
  { key: "topic_enrichment", label: "Topic" },
  { key: "content_brief", label: "Brief" },
  { key: "decision", label: "Decision" },
  { key: "video_script", label: "Script (VST)" },
  { key: "script_approval", label: "CSA Review" },
  { key: "script_separation", label: "Split" },
  { key: "video_generation", label: "Video Gen" },
  { key: "audio_generation", label: "Audio Gen" },
  { key: "av_merge", label: "AV Merge" },
  { key: "vam_approval", label: "VAM" },
  { key: "human_review", label: "Human" },
  { key: "publishing", label: "Publish" },
];

function getStepStatus(
  stepKey: string,
  job: ContentJob & { current_step?: string | null },
): "done" | "active" | "pending" | "error" {
  const statusOrder: Record<string, number> = {
    topic_enrichment: 0,
    content_brief: 1,
    decision: 2,
    image_script: 3,
    video_script: 3,
    script_approval: 4,
    script_separation: 5,
    image_generation: 5,
    video_generation: 6,
    audio_generation: 6,
    image_approval: 6,
    av_merge: 7,
    vam_approval: 8,
    human_review: 9,
    publishing: 10,
  };

  const BACKEND_STEP_LEVELS: Record<string, number> = {
    mama_enrichment: 0,
    cmi_brief: 1,
    decision_maker: 2,
    cst_script: 3,
    vst_script: 3,
    csa_approval: 4,
    image_generation: 5,
    video_generation: 6,
    audio_generation: 6,
  };

  const jobStatusMap: Record<string, number> = {
    pending: -1,
    in_progress: 2,
    awaiting_approval: 6,
    approved: 7,
    rejected: 4,
    improving: 3,
    publishing: 10,
    published: 11,
    failed: -2,
  };

  if (job.status === "failed") return "error";

  let currentLevel: number;
  // Use current_step for live progress when pipeline is running or paused
  if (
    (job.status === "in_progress") &&
    job.current_step &&
    BACKEND_STEP_LEVELS[job.current_step] !== undefined
  ) {
    currentLevel = BACKEND_STEP_LEVELS[job.current_step];
  } else {
    currentLevel = jobStatusMap[job.status] ?? 0;
  }

  const stepLevel = statusOrder[stepKey] ?? 0;
  if (stepLevel < currentLevel) return "done";
  if (stepLevel === currentLevel) return "active";
  return "pending";
}

function StepIcon({ status }: { status: "done" | "active" | "pending" | "error" }) {
  switch (status) {
    case "done":
      return <CheckCircle2 className="h-5 w-5 text-green-500" />;
    case "active":
      return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
    case "error":
      return <XCircle className="h-5 w-5 text-red-500" />;
    default:
      return <Circle className="h-5 w-5 text-muted-foreground/30" />;
  }
}

export function PipelineFlow({ job }: { job: ContentJob & { current_step?: string | null } }) {
  const steps =
    job.pipeline_type === "video_post" ? VIDEO_STEPS : IMAGE_STEPS;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Pipeline Progress</CardTitle>
          <Badge
            variant={
              job.pipeline_type === "video_post" ? "info" : "secondary"
            }
          >
            {job.pipeline_type === "video_post"
              ? "Video Pipeline"
              : "Image Pipeline"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-1 overflow-x-auto pb-2">
          {steps.map((step, i) => {
            const status = getStepStatus(step.key, job);
            return (
              <div key={step.key} className="flex items-center">
                <div className="flex flex-col items-center gap-1 min-w-[72px]">
                  <StepIcon status={status} />
                  <span className="text-[10px] text-muted-foreground text-center leading-tight">
                    {step.label}
                  </span>
                </div>
                {i < steps.length - 1 && (
                  <ArrowRight
                    className={`h-4 w-4 shrink-0 ${
                      status === "done"
                        ? "text-green-400"
                        : "text-muted-foreground/20"
                    }`}
                  />
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
