"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { ContentJob } from "@/types";
import { formatRelativeTime, pipelineLabel } from "@/lib/utils";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { toast } from "sonner";
import {
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  ExternalLink,
} from "lucide-react";

export function ApprovalCard({
  job,
  onAction,
}: {
  job: ContentJob;
  onAction: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [feedback, setFeedback] = useState("");
  const [loading, setLoading] = useState(false);
  const { user } = useAuth();

  const handleDecision = async (decision: "approved" | "rejected") => {
    if (!user) return;
    if (decision === "rejected" && !feedback.trim()) {
      toast.error("Please provide feedback for rejection");
      return;
    }
    setLoading(true);
    try {
      await api.approveJob(
        job.id,
        decision,
        user.id,
        feedback || undefined
      );
      toast.success(`Content ${decision}`);
      onAction();
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <CardContent className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <Link
              href={`/jobs/${job.id}`}
              className="font-medium hover:underline flex items-center gap-1"
            >
              {job.topic}
              <ExternalLink className="h-3 w-3" />
            </Link>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline">
                {pipelineLabel(job.pipeline_type)}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {formatRelativeTime(job.created_at)}
              </span>
              {job.improvement_count > 0 && (
                <Badge variant="warning">
                  Cycle {job.improvement_count}
                </Badge>
              )}
            </div>
          </div>
          <button
            onClick={() => setExpanded(!expanded)}
            className="text-muted-foreground hover:text-foreground p-1"
          >
            {expanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </button>
        </div>

        {/* Content Preview */}
        {expanded && (
          <div className="space-y-3 border-t pt-3">
            {job.script && (
              <div>
                <label className="text-xs font-medium text-muted-foreground">
                  Script Preview
                </label>
                <pre className="mt-1 text-sm bg-muted p-3 rounded-md max-h-[200px] overflow-y-auto whitespace-pre-wrap">
                  {job.script.content.slice(0, 500)}
                  {job.script.content.length > 500 ? "..." : ""}
                </pre>
              </div>
            )}
            {job.content_brief && (
              <div>
                <label className="text-xs font-medium text-muted-foreground">
                  Brief
                </label>
                <p className="text-sm mt-1">
                  {job.content_brief.marketing_angle}
                </p>
              </div>
            )}

            {/* Previous Feedback */}
            {job.approval_records.length > 0 && (
              <div>
                <label className="text-xs font-medium text-muted-foreground">
                  Previous Reviews
                </label>
                {job.approval_records.map((r) => (
                  <div
                    key={r.id}
                    className="mt-1 flex items-start gap-2 text-sm"
                  >
                    {r.decision === "approved" ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500 mt-0.5" />
                    )}
                    <div>
                      <span className="font-medium">{r.gate}</span>
                      {r.feedback && (
                        <p className="text-muted-foreground">{r.feedback}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="space-y-2">
          <Textarea
            placeholder="Feedback (required for rejection)..."
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            className="min-h-[60px]"
          />
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="success"
              disabled={loading}
              onClick={() => handleDecision("approved")}
              className="flex-1"
            >
              <CheckCircle2 className="h-4 w-4 mr-1" />
              Approve
            </Button>
            <Button
              size="sm"
              variant="destructive"
              disabled={loading}
              onClick={() => handleDecision("rejected")}
              className="flex-1"
            >
              <XCircle className="h-4 w-4 mr-1" />
              Reject
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
