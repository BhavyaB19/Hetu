import { NextRequest, NextResponse } from "next/server";
import { API_URL } from "@/lib/api";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const sort = request.nextUrl.searchParams.get("sort") || "top";

  const res = await fetch(`${API_URL}/polls/${encodeURIComponent(id)}/comments?sort=${encodeURIComponent(sort)}`, {
    cache: "no-store",
  });

  const data = await res.json().catch(() => ([]));
  return NextResponse.json(data, { status: res.status });
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const cookieHeader = request.headers.get("cookie") || "";
  const body = await request.json().catch(() => ({}));

  const res = await fetch(`${API_URL}/polls/${encodeURIComponent(id)}/comments`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Cookie: cookieHeader,
    },
    body: JSON.stringify(body),
  });

  const data = await res.json().catch(() => ({ detail: "Invalid server response" }));
  const response = NextResponse.json(data, { status: res.status });

  const setCookie = res.headers.get("set-cookie");
  if (setCookie) {
    response.headers.set("set-cookie", setCookie);
  }

  return response;
}
