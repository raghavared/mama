// ─── User & Auth ──────────────────────────────────────────────────────────────

export type UserRole = "admin" | "content_manager" | "reviewer";

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  avatar?: string;
  created_at: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
}

// ─── Content Job ──────────────────────────────────────────────────────────────

export type JobStatus =
  | "pending"
  | "in_progress"
  | "awaiting_approval"
  | "approved"
  | "rejected"
  | "improving"
  | "publishing"
  | "published"
  | "failed";

export type PipelineType = "image_post" | "video_post";
export type TopicSource = "manual" | "trending" | "scheduled";

export type Platform =
  | "instagram"
  | "linkedin"
  | "facebook"
  | "x_twitter"
  | "youtube";

export interface RunHistory {
  run_number: number;
  reinitiated_at: string;
  reinitiated_by: string;
  status_at_end: string;
  pipeline_type: string | null;
  pipeline_logs: { step: string; status: string; detail: string; timestamp: string; }[];
}

export interface ContentJob {
  id: string;
  name?: string | null;
  description?: string | null;
  topic: string;
  topic_source: TopicSource;
  pipeline_type: PipelineType | null;
  status: JobStatus;
  created_at: string;
  updated_at: string;
  improvement_count: number;
  reinitiation_count: number;
  run_history: RunHistory[];
  error_message: string | null;
  content_brief?: ContentBrief;
  script?: Script;
  media_assets: MediaAsset[];
  approval_records: ApprovalRecord[];
  published_posts: PublishedPost[];
  metadata: Record<string, any>;
}

export interface ContentBrief {
  job_id: string;
  topic: string;
  marketing_angle: string;
  target_audience: string;
  tone: string;
  key_messages: string[];
  platform_strategy: Record<string, string>;
  created_by: string;
}

export interface Script {
  job_id: string;
  type: "image_script" | "video_script";
  content: string;
  image_prompts?: string[];
  video_frames?: VideoFrame[];
  audio_narration?: string;
  created_by: string;
  version: number;
}

export interface VideoFrame {
  frame_number: number;
  scene_description: string;
  duration_seconds: number;
  transition_type?: string;
  audio_cue?: string;
}

export interface MediaAsset {
  id: string;
  job_id: string;
  type: "image" | "video_clip" | "audio" | "final_video";
  source: string;
  file_path: string;
  format: string;
  quality_score?: number;
  metadata: Record<string, any>;
  created_at: string;
}

export type ApprovalGate =
  | "script_csa"
  | "image_cmi_cst"
  | "audio"
  | "video_approver"
  | "vam"
  | "human";

export interface ApprovalRecord {
  id: string;
  job_id: string;
  gate: ApprovalGate;
  subject_type: string;
  decision: "approved" | "rejected";
  feedback?: string;
  reviewer: string;
  reviewed_at: string;
}

export interface PublishedPost {
  id: string;
  job_id: string;
  platform: Platform;
  platform_post_id: string;
  post_url: string;
  posted_at: string;
  analytics?: PostAnalytics;
}

export interface PostAnalytics {
  impressions: number;
  likes: number;
  shares: number;
  comments: number;
  clicks: number;
  reach: number;
}

// ─── Agent Activity ─────────────────────────────────────────────────────────

export interface AgentActivity {
  id: string;
  agent_id: string;
  agent_name: string;
  action: string;
  job_id: string;
  timestamp: string;
  details: Record<string, any>;
  status: "success" | "error" | "info";
}

// ─── Dashboard Stats ────────────────────────────────────────────────────────

export interface DashboardStats {
  total_jobs: number;
  active_jobs: number;
  published_today: number;
  approval_pending: number;
  total_impressions: number;
  total_engagement: number;
  cost_today: number;
  jobs_by_status: Record<JobStatus, number>;
  jobs_by_platform: Record<Platform, number>;
  recent_activity: AgentActivity[];
}

// ─── Scheduling ─────────────────────────────────────────────────────────────

export interface ScheduledJob {
  id: string;
  topic: string;
  cron_expression: string;
  platforms: Platform[];
  enabled: boolean;
  next_run: string;
  last_run?: string;
}

// ─── Configuration ──────────────────────────────────────────────────────────

export interface SystemConfig {
  brand_name: string;
  brand_description: string;
  brand_voice: string;
  content_goals: string;
  max_improvement_cycles: number;
  image_generation_provider: 'dalle' | 'gemini' | 'stable_diffusion';
  active_platforms: Platform[];
  api_keys_configured: Record<string, boolean>;
}
