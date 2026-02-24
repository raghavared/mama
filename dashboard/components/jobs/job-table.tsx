"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { ContentJob } from "@/types";
import { statusColor, formatRelativeTime, pipelineLabel } from "@/lib/utils";
import { ExternalLink, Trash2, RotateCcw } from "lucide-react";
import { api } from "@/lib/api";
import { toast } from "sonner";

// Statuses that make sense to reinitiate (not pending/in_progress/paused)
const REINITIATEABLE = new Set(["failed", "rejected", "published", "awaiting_approval"]);

interface JobTableProps {
  jobs: ContentJob[];
  onJobDeleted?: (jobId: string) => void;
  onJobReinitiated?: (jobId: string) => void;
}

export function JobTable({ jobs, onJobDeleted, onJobReinitiated }: JobTableProps) {
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [reinitiating, setReinitiating] = useState<string | null>(null);

  const handleDeleteClick = (jobId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setConfirmDeleteId(jobId);
  };

  const handleConfirmDelete = async () => {
    if (!confirmDeleteId) return;
    setDeleting(true);
    try {
      await api.deleteJob(confirmDeleteId);
      toast.success("Job deleted");
      onJobDeleted?.(confirmDeleteId);
    } catch (err: any) {
      toast.error(err.message || "Failed to delete job");
    } finally {
      setDeleting(false);
      setConfirmDeleteId(null);
    }
  };

  const handleReinitate = async (jobId: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setReinitiating(jobId);
    try {
      await api.reinitiateJob(jobId);
      toast.success("Job reinitiated — pipeline restarting");
      onJobReinitiated?.(jobId);
    } catch (err: any) {
      toast.error(err.message || "Failed to reinitiate job");
    } finally {
      setReinitiating(null);
    }
  };

  const confirmJob = jobs.find((j) => j.id === confirmDeleteId);

  return (
    <>
      {/* Confirmation dialog */}
      {confirmDeleteId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-background rounded-lg border shadow-lg p-6 w-full max-w-sm mx-4">
            <h3 className="font-semibold text-lg mb-2">Delete Job?</h3>
            <p className="text-sm text-muted-foreground mb-4">
              This will permanently delete{" "}
              <span className="font-medium text-foreground">
                &quot;{confirmJob?.name || confirmJob?.topic}&quot;
              </span>{" "}
              and cannot be undone.
            </p>
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setConfirmDeleteId(null)}
                disabled={deleting}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                size="sm"
                onClick={handleConfirmDelete}
                disabled={deleting}
              >
                {deleting ? (
                  <span className="flex items-center gap-2">
                    <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    Deleting…
                  </span>
                ) : (
                  "Delete"
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Topic</TableHead>
            <TableHead>Pipeline</TableHead>
            <TableHead>Source</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Improvements</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="w-24" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {jobs.length === 0 && (
            <TableRow>
              <TableCell
                colSpan={7}
                className="text-center text-muted-foreground py-8"
              >
                No jobs found
              </TableCell>
            </TableRow>
          )}
          {jobs.map((job) => (
            <TableRow key={job.id}>
              <TableCell className="max-w-[250px]">
                <Link
                  href={`/jobs/${job.id}`}
                  className="hover:underline block"
                >
                  {job.name ? (
                    <>
                      <span className="font-medium truncate block">{job.name}</span>
                      <span className="text-xs text-muted-foreground truncate block">{job.topic}</span>
                    </>
                  ) : (
                    <span className="font-medium truncate block">{job.topic}</span>
                  )}
                </Link>
              </TableCell>
              <TableCell>
                <Badge variant="outline">{pipelineLabel(job.pipeline_type)}</Badge>
              </TableCell>
              <TableCell className="text-muted-foreground text-xs capitalize">
                {job.topic_source}
              </TableCell>
              <TableCell>
                <Badge
                  className={statusColor(job.status)}
                  variant="secondary"
                >
                  {job.status.replace(/_/g, " ")}
                </Badge>
              </TableCell>
              <TableCell className="text-center">
                {job.improvement_count > 0 ? (
                  <Badge variant="warning">{job.improvement_count}x</Badge>
                ) : (
                  <span className="text-muted-foreground">-</span>
                )}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {formatRelativeTime(job.created_at)}
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-1">
                  <Link href={`/jobs/${job.id}`}>
                    <ExternalLink className="h-4 w-4 text-muted-foreground hover:text-foreground" />
                  </Link>
                  {REINITIATEABLE.has(job.status) && (
                    <button
                      onClick={(e) => handleReinitate(job.id, e)}
                      disabled={reinitiating === job.id}
                      className="p-1 rounded hover:bg-blue-50 text-muted-foreground hover:text-blue-600 transition-colors disabled:opacity-50"
                      title="Reinitiate job"
                    >
                      {reinitiating === job.id ? (
                        <span className="h-4 w-4 block animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
                      ) : (
                        <RotateCcw className="h-4 w-4" />
                      )}
                    </button>
                  )}
                  <button
                    onClick={(e) => handleDeleteClick(job.id, e)}
                    className="p-1 rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                    title="Delete job"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </>
  );
}
