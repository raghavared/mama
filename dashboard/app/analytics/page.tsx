"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import {
  StatusChart,
  PlatformChart,
  EngagementChart,
} from "@/components/analytics/charts";
import { StatsCards } from "@/components/dashboard/stats-cards";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { DashboardStats } from "@/types";
import { RefreshCw } from "lucide-react";

// Mock engagement trend data for demo
const mockEngagementTrend = Array.from({ length: 14 }, (_, i) => {
  const d = new Date();
  d.setDate(d.getDate() - (13 - i));
  return {
    date: d.toLocaleDateString("en-US", { month: "short", day: "numeric" }),
    impressions: Math.floor(Math.random() * 5000) + 1000,
    engagement: Math.floor(Math.random() * 500) + 100,
  };
});

export default function AnalyticsPage() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  const loadStats = async () => {
    setLoading(true);
    try {
      const data = await api.getDashboardStats();
      setStats(data);
    } catch {
      // error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadStats();
  }, []);

  return (
    <div className="flex flex-col">
      <Header
        title="Analytics"
        description="Performance metrics and insights"
        actions={
          <Button variant="outline" size="sm" onClick={loadStats}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        }
      />

      <div className="p-6 space-y-6">
        <StatsCards stats={stats} />

        <div className="grid gap-6 lg:grid-cols-2">
          <StatusChart data={stats?.jobs_by_status} />
          <PlatformChart data={stats?.jobs_by_platform} />
          <EngagementChart data={mockEngagementTrend} />
        </div>
      </div>
    </div>
  );
}
