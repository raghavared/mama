"use client";

import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ContentJob } from "@/types";
import { statusColor, formatRelativeTime, pipelineLabel } from "@/lib/utils";
import { ArrowRight } from "lucide-react";

export function RecentJobs({ jobs }: { jobs: ContentJob[] }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-base">Recent Jobs</CardTitle>
        <Link
          href="/jobs"
          className="text-sm text-primary hover:underline flex items-center gap-1"
        >
          View all <ArrowRight className="h-3 w-3" />
        </Link>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {jobs.length === 0 && (
            <p className="text-sm text-muted-foreground py-4 text-center">
              No jobs yet. Trigger your first content job!
            </p>
          )}
          {jobs.map((job) => (
            <Link
              key={job.id}
              href={`/jobs/${job.id}`}
              className="flex items-center justify-between rounded-lg border p-3 hover:bg-accent/50 transition-colors"
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium truncate">{job.topic}</p>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-xs text-muted-foreground">
                    {pipelineLabel(job.pipeline_type)}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatRelativeTime(job.created_at)}
                  </span>
                </div>
              </div>
              <Badge
                className={statusColor(job.status)}
                variant="secondary"
              >
                {job.status.replace("_", " ")}
              </Badge>
            </Link>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
