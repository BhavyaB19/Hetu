import { NextRequest, NextResponse } from "next/server";
import { API_URL } from "@/lib/api";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const res = await fetch(`${API_URL}/polls/${encodeURIComponent(id)}/results`, {
    cache: "no-store",
  });

  const data = await res.json().catch(() => ({ detail: "Invalid response from backend" }));
  return NextResponse.json(data, { status: res.status });
}
