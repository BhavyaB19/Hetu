import { API_URL } from "@/lib/api";

export const dynamic = "force-dynamic";

const ADMIN_API_KEY = process.env.ADMIN_API_KEY ?? "hetu-dev-admin-key";

/** Job progress, polled by the admin job viewer. */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const res = await fetch(`${API_URL}/admin/jobs/${encodeURIComponent(id)}`, {
      headers: {
        "X-Admin-Key": ADMIN_API_KEY,
      },
      cache: "no-store",
    });
    return new Response(res.body, { status: res.status, headers: { "Content-Type": "application/json" } });
  } catch {
    return Response.json({ detail: `Can't reach the Hetu API at ${API_URL}.` }, { status: 502 });
  }
}
