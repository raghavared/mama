"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { ApprovalCard } from "@/components/approvals/approval-card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { ContentJob } from "@/types";
import { RefreshCw, CheckCircle2 } from "lucide-react";

export default function ApprovalsPage() {
  const [jobs, setJobs] = useState<ContentJob[]>([]);
  const [loading, setLoading] = useState(true);

  const loadPending = async () => {
    setLoading(true);
    try {
      const res = await api.listJobs({ status: "awaiting_approval", limit: 50 });
      setJobs(res.jobs || []);
    } catch {
      // error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPending();
  }, []);

  return (
    <div className="flex flex-col">
      <Header
        title="Approval Queue"
        description={`${jobs.length} items awaiting review`}
        actions={
          <Button variant="outline" size="sm" onClick={loadPending}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        }
      />

      <div className="p-6 space-y-4">
        {jobs.length === 0 && !loading && (
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <CheckCircle2 className="h-12 w-12 mb-4 text-green-300" />
            <p className="text-lg font-medium">All caught up!</p>
            <p className="text-sm">No content awaiting approval.</p>
          </div>
        )}
        <div className="grid gap-4 lg:grid-cols-2">
          {jobs.map((job) => (
            <ApprovalCard key={job.id} job={job} onAction={loadPending} />
          ))}
        </div>
      </div>
    </div>
  );
}
