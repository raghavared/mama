import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatRelativeTime(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export function statusColor(status: string): string {
  const map: Record<string, string> = {
    pending: "bg-gray-100 text-gray-700",
    in_progress: "bg-blue-100 text-blue-700",
    awaiting_approval: "bg-yellow-100 text-yellow-700",
    approved: "bg-green-100 text-green-700",
    rejected: "bg-red-100 text-red-700",
    improving: "bg-orange-100 text-orange-700",
    publishing: "bg-purple-100 text-purple-700",
    published: "bg-emerald-100 text-emerald-700",
    failed: "bg-red-100 text-red-800",
  };
  return map[status] || "bg-gray-100 text-gray-700";
}

export function platformIcon(platform: string): string {
  const map: Record<string, string> = {
    instagram: "Instagram",
    linkedin: "LinkedIn",
    facebook: "Facebook",
    x_twitter: "X",
    youtube: "YouTube",
  };
  return map[platform] || platform;
}

export function pipelineLabel(type: string | null): string {
  if (type === "image_post") return "Image Post";
  if (type === "video_post") return "Video Post";
  return "Undecided";
}
