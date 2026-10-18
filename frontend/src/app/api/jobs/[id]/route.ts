import { API_URL } from "@/lib/api";

export const dynamic = "force-dynamic";

/** Job progress, polled by the progress page. */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  try {
    const res = await fetch(`${API_URL}/jobs/${encodeURIComponent(id)}`, { cache: "no-store" });
    return new Response(res.body, { status: res.status, headers: { "Content-Type": "application/json" } });
  } catch {
    return Response.json({ detail: `Can't reach the Hetu API at ${API_URL}.` }, { status: 502 });
  }
}
