import { AdminDashboard } from "./AdminDashboard";
import { API_URL } from "@/lib/api";
import type { CaseSummary } from "@/lib/api";

export const dynamic = "force-dynamic";

const ADMIN_API_KEY = process.env.ADMIN_API_KEY ?? "hetu-dev-admin-key";

export default async function AdminPage() {
  let cases: CaseSummary[] = [];
  let error: string | null = null;

  try {
    const res = await fetch(`${API_URL}/admin/cases`, {
      headers: {
        "X-Admin-Key": ADMIN_API_KEY,
      },
      cache: "no-store",
    });
    if (!res.ok) {
      error = `API returned status ${res.status}`;
    } else {
      cases = await res.json();
    }
  } catch (err) {
    error = err instanceof Error ? err.message : "Failed to reach backend API";
  }

  return (
    <div className="py-8">
      {error && (
        <div role="alert" className="card border-danger p-4 mb-6 text-sm text-danger">
          Could not load admin cases: {error}. Verify that the backend is running.
        </div>
      )}
      <AdminDashboard initialCases={cases} />
    </div>
  );
}
