"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useWebSocket } from "@/lib/websocket";
import type { AgentActivity } from "@/types";
import { formatRelativeTime } from "@/lib/utils";
import {
  Bot,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Info,
  Zap,
  Brain,
  FileText,
  Image as ImageIcon,
  Film,
  Shield,
} from "lucide-react";

const AGENTS = [
  {
    id: "agent:mama",
    name: "MAMA",
    desc: "Marketing Agent - Topic enrichment & orchestration",
    icon: Zap,
    color: "text-blue-600",
  },
  {
    id: "agent:cmi",
    name: "CMI",
    desc: "Content Marketing Ideator - Brief generation",
    icon: Brain,
    color: "text-purple-600",
  },
  {
    id: "agent:decision_maker",
    name: "Decision Maker",
    desc: "Routes to image or video pipeline",
    icon: Brain,
    color: "text-indigo-600",
  },
  {
    id: "agent:cst",
    name: "CST",
    desc: "Content Script Team - Image scripts",
    icon: FileText,
    color: "text-green-600",
  },
  {
    id: "agent:vst",
    name: "VST",
    desc: "Video Script Team - Video scripts & frames",
    icon: Film,
    color: "text-orange-600",
  },
  {
    id: "agent:csa",
    name: "CSA",
    desc: "Content Script Approver - Quality gate",
    icon: Shield,
    color: "text-red-600",
  },
];

export default function AgentsPage() {
  const [activities, setActivities] = useState<AgentActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const wsStatus = useWebSocket((s) => s.status);

  const loadActivities = async () => {
    setLoading(true);
    try {
      const data = await api.getAgentActivity(100);
      setActivities(data);
    } catch {
      // error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadActivities();
  }, []);

  const getAgentActivities = (agentId: string) =>
    activities.filter((a) => a.agent_id === agentId);

  return (
    <div className="flex flex-col">
      <Header
        title="Agents"
        description="AI agent monitoring & activity"
        actions={
          <Button variant="outline" size="sm" onClick={loadActivities}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        }
      />

      <div className="p-6 space-y-6">
        {/* Agent Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {AGENTS.map((agent) => {
            const agentActivities = getAgentActivities(agent.id);
            const lastActivity = agentActivities[0];
            const successCount = agentActivities.filter(
              (a) => a.status === "success"
            ).length;
            const errorCount = agentActivities.filter(
              (a) => a.status === "error"
            ).length;

            return (
              <Card key={agent.id}>
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className={`mt-0.5 ${agent.color}`}>
                      <agent.icon className="h-5 w-5" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <h3 className="font-medium">{agent.name}</h3>
                        <Badge
                          variant={
                            wsStatus === "connected" ? "success" : "secondary"
                          }
                          className="text-[10px]"
                        >
                          {wsStatus === "connected" ? "Online" : "Offline"}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {agent.desc}
                      </p>
                      <div className="flex items-center gap-3 mt-3 text-xs">
                        <span className="flex items-center gap-1 text-green-600">
                          <CheckCircle2 className="h-3 w-3" />
                          {successCount}
                        </span>
                        <span className="flex items-center gap-1 text-red-600">
                          <AlertCircle className="h-3 w-3" />
                          {errorCount}
                        </span>
                        {lastActivity && (
                          <span className="text-muted-foreground">
                            Last: {formatRelativeTime(lastActivity.timestamp)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {/* Activity Log */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Activity Log</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {activities.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No agent activity recorded yet.
                </p>
              )}
              {activities.map((activity) => (
                <div
                  key={activity.id}
                  className="flex items-start gap-3 rounded-md border p-3 text-sm"
                >
                  <div className="mt-0.5">
                    {activity.status === "success" ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                    ) : activity.status === "error" ? (
                      <AlertCircle className="h-4 w-4 text-red-500" />
                    ) : (
                      <Info className="h-4 w-4 text-blue-500" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        {activity.agent_name}
                      </Badge>
                      <span className="text-muted-foreground text-xs">
                        {formatRelativeTime(activity.timestamp)}
                      </span>
                    </div>
                    <p className="mt-0.5">{activity.action}</p>
                    {activity.job_id && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        Job: {activity.job_id.slice(0, 8)}...
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
