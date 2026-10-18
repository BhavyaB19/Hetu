import { API_URL } from "@/lib/api";

export const dynamic = "force-dynamic";

const ADMIN_API_KEY = process.env.ADMIN_API_KEY ?? "hetu-dev-admin-key";

/** List all cases for admin view (including draft and unvetted cases). */
export async function GET() {
  try {
    const res = await fetch(`${API_URL}/admin/cases`, {
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

/** Ingest a new case in the background. Admin only. */
export async function POST(request: Request) {
  try {
    const body = await request.text();
    const res = await fetch(`${API_URL}/admin/cases`, {
      method: "POST",
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
