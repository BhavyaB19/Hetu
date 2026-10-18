import { notFound } from "next/navigation";

import { JobProgress } from "@/components/JobProgress";
import { API_URL } from "@/lib/api";
import type { JobView } from "@/lib/api";

export const dynamic = "force-dynamic";

const ADMIN_API_KEY = process.env.ADMIN_API_KEY ?? "hetu-dev-admin-key";

export default async function AdminJobPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  let job: JobView | undefined;
  try {
    const res = await fetch(`${API_URL}/admin/jobs/${encodeURIComponent(id)}`, {
      headers: {
        "X-Admin-Key": ADMIN_API_KEY,
      },
      cache: "no-store",
    });
    if (res.status === 404) {
      notFound();
    }
    if (res.ok) {
      job = await res.json();
    }
  } catch {
    job = undefined;
  }

  if (!job) {
    return (
      <div className="py-8">
        <p className="card p-6 text-sm text-ivory-muted">Can&apos;t reach the Hetu API at {API_URL}.</p>
      </div>
    );
  }

  return (
    <div className="py-8">
      <JobProgress initial={job} />
    </div>
  );
}
