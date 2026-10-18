import { redirect } from "next/navigation";

export default async function LegacyCaseRedirect({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  redirect(`/verdicts/${slug}`);
}
