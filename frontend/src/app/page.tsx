import { CauseList } from "@/components/home/CauseList";
import { GapMeasure } from "@/components/home/GapMeasure";
import { HomeHero } from "@/components/home/HomeHero";
import { JanMatPanel } from "@/components/home/JanMatPanel";
import { ThreeOpenings } from "@/components/home/ThreeOpenings";
import { ErrorState } from "@/components/ui/ErrorState";
import { api } from "@/lib/api";
import { hasMedia, readSequence } from "@/lib/media";

export const dynamic = "force-dynamic";

const BLINK = { mp4: "/media/lady/blink.mp4", webm: "/media/lady/blink.webm" };

export default async function Home() {
  const [{ data: cases }, { data: home }] = await Promise.all([
    api.GET("/cases").catch(() => ({ data: undefined })),
    api.GET("/home").catch(() => ({ data: undefined })),
  ]);

  const featured = home?.featured_cases[0] ?? cases?.[0];
  const { data: view } = featured
    ? await api.GET("/cases/{slug}", { params: { path: { slug: featured.slug } } }).catch(() => ({ data: undefined }))
    : { data: undefined };

  const poll = home?.poll_of_the_week ?? undefined;
  const pollHref = poll ? `/jan-mat/${poll.id}` : "/jan-mat";
  const blink = hasMedia(BLINK.mp4) ? { mp4: BLINK.mp4, webm: hasMedia(BLINK.webm) ? BLINK.webm : undefined } : undefined;

  return (
    <div className="bleed -my-8">
      <HomeHero manifest={readSequence("lady/reveal")} blink={blink} counters={home?.counters} pollHref={pollHref} />

      {view && featured ? (
        <>
          <ThreeOpenings view={view} pollHref={pollHref} />
          <GapMeasure cases={cases ?? [featured]} featured={featured} gap={view.gap} />
        </>
      ) : (
        <div className="mx-auto max-w-3xl px-4 py-20">
          <ErrorState
            eyebrow="The record"
            title="Published cases could not be loaded"
            message="The Hetu service did not answer. Refresh in a moment; the cases appear here once it is back."
          />
        </div>
      )}

      {cases && cases.length > 0 && <CauseList cases={cases} />}
      <JanMatPanel poll={poll} />
    </div>
  );
}
