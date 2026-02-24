"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { AgentActivity } from "@/types";
import { formatRelativeTime } from "@/lib/utils";
import { Bot, CheckCircle2, AlertCircle, Info } from "lucide-react";

const statusIcons = {
  success: <CheckCircle2 className="h-4 w-4 text-green-500" />,
  error: <AlertCircle className="h-4 w-4 text-red-500" />,
  info: <Info className="h-4 w-4 text-blue-500" />,
};

export function ActivityFeed({ activities }: { activities: AgentActivity[] }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Agent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3 max-h-[400px] overflow-y-auto">
          {activities.length === 0 && (
            <p className="text-sm text-muted-foreground py-4 text-center">
              No agent activity yet.
            </p>
          )}
          {activities.map((activity) => (
            <div
              key={activity.id}
              className="flex items-start gap-3 text-sm"
            >
              <div className="mt-0.5">
                {statusIcons[activity.status]}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium flex items-center gap-1">
                    <Bot className="h-3 w-3" />
                    {activity.agent_name}
                  </span>
                  <span className="text-muted-foreground text-xs">
                    {formatRelativeTime(activity.timestamp)}
                  </span>
                </div>
                <p className="text-muted-foreground truncate">
                  {activity.action}
                </p>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
