import { FeaturedCases } from "@/components/home/FeaturedCases";
import { MetricsCounters } from "@/components/home/MetricsCounters";
import { PollOfTheWeek } from "@/components/home/PollOfTheWeek";
import { ScalesHero } from "@/components/home/ScalesHero";
import { ThreeStorySection } from "@/components/home/ThreeStorySection";
import { api } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Home() {
  const { data: cases, error } = await api
    .GET("/cases")
    .catch(() => ({ data: undefined, error: true }));

  const featuredCase = cases && cases.length > 0 ? cases[0] : undefined;

  return (
    <div className="flex flex-col gap-14 pb-8">
      {/* 1. Hero with Anime.js v4 Scales of Justice */}
      <ScalesHero />

      {/* 2. Live Platform Metrics Counters with count-up */}
      <MetricsCounters />

      <hr className="gold-rule" />

      {/* 3. Three-Story Tripartite Section */}
      <ThreeStorySection />

      <hr className="gold-rule" />

      {/* 4. Featured Cases Section */}
      <FeaturedCases cases={cases} error={error} />

      {/* 5. Poll of the Week */}
      <PollOfTheWeek featuredCase={featuredCase} />
    </div>
  );
}
