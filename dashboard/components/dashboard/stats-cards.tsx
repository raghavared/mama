"use client";

import { Card, CardContent } from "@/components/ui/card";
import type { DashboardStats } from "@/types";
import {
  Briefcase,
  PlayCircle,
  CheckCircle2,
  Clock,
  Eye,
  Heart,
  DollarSign,
  TrendingUp,
} from "lucide-react";

const statCards = [
  {
    key: "total_jobs" as const,
    label: "Total Jobs",
    icon: Briefcase,
    color: "text-blue-600",
    bg: "bg-blue-50",
  },
  {
    key: "active_jobs" as const,
    label: "Active",
    icon: PlayCircle,
    color: "text-green-600",
    bg: "bg-green-50",
  },
  {
    key: "published_today" as const,
    label: "Published Today",
    icon: CheckCircle2,
    color: "text-emerald-600",
    bg: "bg-emerald-50",
  },
  {
    key: "approval_pending" as const,
    label: "Pending Approval",
    icon: Clock,
    color: "text-yellow-600",
    bg: "bg-yellow-50",
  },
  {
    key: "total_impressions" as const,
    label: "Impressions",
    icon: Eye,
    color: "text-purple-600",
    bg: "bg-purple-50",
    format: true,
  },
  {
    key: "total_engagement" as const,
    label: "Engagement",
    icon: Heart,
    color: "text-pink-600",
    bg: "bg-pink-50",
    format: true,
  },
  {
    key: "cost_today" as const,
    label: "Cost Today",
    icon: DollarSign,
    color: "text-orange-600",
    bg: "bg-orange-50",
    isCurrency: true,
  },
];

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

export function StatsCards({ stats }: { stats: DashboardStats | null }) {
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 xl:grid-cols-7">
      {statCards.map((card) => {
        const value = stats ? stats[card.key] : 0;
        const display = card.isCurrency
          ? `$${(value as number).toFixed(2)}`
          : card.format
          ? formatNumber(value as number)
          : value;

        return (
          <Card key={card.key}>
            <CardContent className="flex items-center gap-3 p-4">
              <div className={`rounded-lg p-2 ${card.bg}`}>
                <card.icon className={`h-5 w-5 ${card.color}`} />
              </div>
              <div>
                <p className="text-2xl font-bold">{display}</p>
                <p className="text-xs text-muted-foreground">{card.label}</p>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
