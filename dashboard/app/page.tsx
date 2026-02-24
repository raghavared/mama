"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { RecentJobs } from "@/components/dashboard/recent-jobs";
import { ActivityFeed } from "@/components/dashboard/activity-feed";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useWebSocket } from "@/lib/websocket";
import type { DashboardStats, ContentJob, AgentActivity } from "@/types";
import { Plus, RefreshCw } from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [jobs, setJobs] = useState<ContentJob[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsRes, jobsRes] = await Promise.all([
        api.getDashboardStats().catch(() => null),
        api.listJobs({ limit: 8 }).catch(() => ({ jobs: [] })),
      ]);
      if (statsRes) setStats(statsRes);
      setJobs(jobsRes.jobs || []);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  // Real-time updates
  useWebSocket((s) => {
    if (s.lastEvent?.type === "job_update") {
      loadData();
    }
  });

  return (
    <div className="flex flex-col">
      <Header
        title="Dashboard"
        description="Marketing Agent System Overview"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={loadData}>
              <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Link href="/jobs/new">
              <Button size="sm">
                <Plus className="h-4 w-4 mr-1" />
                New Job
              </Button>
            </Link>
          </div>
        }
      />

      <div className="p-6 space-y-6">
        <StatsCards stats={stats} />

        <div className="grid gap-6 lg:grid-cols-2">
          <RecentJobs jobs={jobs} />
          <ActivityFeed activities={stats?.recent_activity || []} />
        </div>
      </div>
    </div>
  );
}
