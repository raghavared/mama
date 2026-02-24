"use client";

import { Header } from "@/components/layout/header";
import { TriggerForm } from "@/components/jobs/trigger-form";

export default function NewJobPage() {
  return (
    <div className="flex flex-col">
      <Header title="New Content Job" description="Trigger a new content generation pipeline" />
      <div className="p-6">
        <TriggerForm />
      </div>
    </div>
  );
}
