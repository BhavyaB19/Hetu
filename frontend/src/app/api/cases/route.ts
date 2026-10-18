import { API_URL } from "@/lib/api";

/** Starts a case job. Proxies to the backend so the browser never needs the API's address. */
export async function POST(request: Request) {
  try {
    const res = await fetch(`${API_URL}/cases`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: await request.text(),
    });
    return new Response(res.body, { status: res.status, headers: { "Content-Type": "application/json" } });
  } catch {
    return Response.json({ detail: `Can't reach the Hetu API at ${API_URL}.` }, { status: 502 });
  }
}
