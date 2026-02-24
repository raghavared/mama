"use client";

import { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { JobTable } from "@/components/jobs/job-table";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import type { ContentJob } from "@/types";
import { Plus, RefreshCw } from "lucide-react";
import Link from "next/link";

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "pending", label: "Pending" },
  { value: "in_progress", label: "In Progress" },
  { value: "awaiting_approval", label: "Awaiting Approval" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "improving", label: "Improving" },
  { value: "publishing", label: "Publishing" },
  { value: "published", label: "Published" },
  { value: "failed", label: "Failed" },
];

export default function JobsPage() {
  const [jobs, setJobs] = useState<ContentJob[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const limit = 20;

  const loadJobs = async () => {
    setLoading(true);
    try {
      const res = await api.listJobs({
        status: status || undefined,
        limit,
        offset: page * limit,
      });
      setJobs(res.jobs || []);
      setTotal(res.total || 0);
    } catch {
      // handle error
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, [status, page]);

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="flex flex-col">
      <Header
        title="Content Jobs"
        description={`${total} total jobs`}
        actions={
          <Link href="/jobs/new">
            <Button size="sm">
              <Plus className="h-4 w-4 mr-1" />
              New Job
            </Button>
          </Link>
        }
      />

      <div className="p-6 space-y-4">
        {/* Filters */}
        <div className="flex items-center gap-3">
          <div className="w-48">
            <Select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(0);
              }}
              options={STATUS_OPTIONS}
            />
          </div>
          <Button variant="outline" size="sm" onClick={loadJobs}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
        </div>

        {/* Table */}
        <div className="rounded-lg border bg-card">
          <JobTable
            jobs={jobs}
            onJobDeleted={(deletedId) =>
              setJobs((prev) => prev.filter((j) => j.id !== deletedId))
            }
            onJobReinitiated={() => loadJobs()}
          />
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Showing {page * limit + 1}-{Math.min((page + 1) * limit, total)}{" "}
              of {total}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= totalPages - 1}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
