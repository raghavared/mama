import type {
  ContentJob,
  DashboardStats,
  User,
  ScheduledJob,
  SystemConfig,
  AgentActivity,
  OAuthConnection,
  OAuthPlatform,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };
    if (this.token) {
      headers["Authorization"] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (response.status === 401) {
      this.token = null;
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("Unauthorized");
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API error: ${response.status}`);
    }

    // 204 No Content (e.g. DELETE) has no body — skip JSON parsing
    if (response.status === 204 || response.headers.get("content-length") === "0") {
      return undefined as T;
    }
    return response.json();
  }

  // ─── Auth ───────────────────────────────────────────────────────────

  async login(email: string, password: string) {
    return this.request<{ token: string; user: User }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  async register(name: string, email: string, password: string, role: string) {
    return this.request<{ token: string; user: User }>(
      "/api/v1/auth/register",
      { method: "POST", body: JSON.stringify({ name, email, password, role }) }
    );
  }

  async getMe() {
    return this.request<User>("/api/v1/auth/me");
  }

  // ─── Jobs ───────────────────────────────────────────────────────────

  async triggerJob(
    topic: string,
    topicSource: string = "manual",
    platforms: string[] = ["instagram", "linkedin", "facebook"],
    name?: string,
    description?: string
  ) {
    return this.request<{ job_id: string; status: string }>(
      "/api/v1/jobs/trigger",
      {
        method: "POST",
        body: JSON.stringify({
          topic,
          topic_source: topicSource,
          platforms,
          name: name || undefined,
          description: description || undefined,
        }),
      }
    );
  }

  async getJob(jobId: string) {
    return this.request<ContentJob>(`/api/v1/jobs/${jobId}`);
  }

  async listJobs(params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }) {
    const query = new URLSearchParams();
    if (params?.status) query.set("status", params.status);
    if (params?.limit) query.set("limit", String(params.limit));
    if (params?.offset) query.set("offset", String(params.offset));
    return this.request<{
      jobs: ContentJob[];
      total: number;
      offset: number;
      limit: number;
    }>(`/api/v1/jobs?${query}`);
  }

  async approveJob(
    jobId: string,
    decision: "approved" | "rejected",
    reviewerId: string,
    feedback?: string
  ) {
    return this.request<{ job_id: string; decision: string; status: string }>(
      `/api/v1/jobs/${jobId}/approve`,
      {
        method: "POST",
        body: JSON.stringify({
          decision,
          reviewer_id: reviewerId,
          feedback,
        }),
      }
    );
  }

  async pauseJob(jobId: string) {
    return this.request<{ job_id: string; status: string }>(
      `/api/v1/jobs/${jobId}/pause`,
      { method: "POST" }
    );
  }

  async resumeJob(jobId: string) {
    return this.request<{ job_id: string; status: string }>(
      `/api/v1/jobs/${jobId}/resume`,
      { method: "POST" }
    );
  }

  // ─── Dashboard ──────────────────────────────────────────────────────

  async getDashboardStats() {
    return this.request<DashboardStats>("/api/v1/dashboard/stats");
  }

  // ─── Agent Activity ─────────────────────────────────────────────────

  async getAgentActivity(limit: number = 50) {
    return this.request<AgentActivity[]>(
      `/api/v1/agents/activity?limit=${limit}`
    );
  }

  // ─── Scheduling ─────────────────────────────────────────────────────

  async listScheduledJobs() {
    return this.request<ScheduledJob[]>("/api/v1/schedule");
  }

  async createScheduledJob(job: Partial<ScheduledJob>) {
    return this.request<ScheduledJob>("/api/v1/schedule", {
      method: "POST",
      body: JSON.stringify(job),
    });
  }

  async deleteScheduledJob(jobId: string) {
    return this.request<void>(`/api/v1/schedule/${jobId}`, {
      method: "DELETE",
    });
  }

  // ─── Config ─────────────────────────────────────────────────────────

  async getConfig() {
    return this.request<SystemConfig>("/api/v1/config");
  }

  async updateConfig(config: Partial<SystemConfig>) {
    return this.request<SystemConfig>("/api/v1/config", {
      method: "PATCH",
      body: JSON.stringify(config),
    });
  }

  // ─── Users ──────────────────────────────────────────────────────────

  async listUsers() {
    return this.request<User[]>("/api/v1/users");
  }

  async updateUserRole(userId: string, role: string) {
    return this.request<User>(`/api/v1/users/${userId}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    });
  }

  async reinitiateJob(jobId: string) {
    return this.request<{ job_id: string; status: string }>(
      `/api/v1/jobs/${jobId}/reinitiate`,
      { method: "POST" }
    );
  }

  async deleteJob(jobId: string) {
    return this.request<void>(`/api/v1/jobs/${jobId}`, {
      method: "DELETE",
    });
  }

  // ─── OAuth & Social Connections ─────────────────────────────────────

  async getOAuthStatus() {
    return this.request<OAuthConnection[]>("/api/v1/oauth/status");
  }

  async initiateOAuth(platform: OAuthPlatform) {
    return this.request<{ auth_url: string }>(
      `/api/v1/oauth/${platform}/authorize`,
      { method: "POST" }
    );
  }

  async disconnectOAuth(platform: OAuthPlatform) {
    return this.request<void>(`/api/v1/oauth/${platform}/disconnect`, {
      method: "DELETE",
    });
  }
}

export const api = new ApiClient();
