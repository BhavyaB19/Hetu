import { notFound } from "next/navigation";

import { JobProgress } from "@/components/JobProgress";
import { API_URL, api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function JobPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const { data: job, response } = await api
    .GET("/jobs/{job_id}", { params: { path: { job_id: id } } })
    .catch(() => ({ data: undefined, response: undefined }));

  if (response?.status === 404) notFound();
  if (!job) {
    return <p className="card p-6 text-sm text-ivory-muted">Can&apos;t reach the Hetu API at {API_URL}.</p>;
  }
  return <JobProgress initial={job} />;
}
