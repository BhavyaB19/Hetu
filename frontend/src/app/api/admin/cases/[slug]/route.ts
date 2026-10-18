import { API_URL } from "@/lib/api";

export const dynamic = "force-dynamic";

const ADMIN_API_KEY = process.env.ADMIN_API_KEY ?? "hetu-dev-admin-key";

/** Patch case review_state, featured, or status. Admin only. */
export async function PATCH(request: Request, { params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  try {
    const body = await request.text();
    const res = await fetch(`${API_URL}/admin/cases/${encodeURIComponent(slug)}`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Key": ADMIN_API_KEY,
      },
      body,
    });
    return new Response(res.body, { status: res.status, headers: { "Content-Type": "application/json" } });
  } catch {
    return Response.json({ detail: `Can't reach the Hetu API at ${API_URL}.` }, { status: 502 });
  }
}
