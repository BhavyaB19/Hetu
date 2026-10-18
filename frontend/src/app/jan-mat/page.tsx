import type { Metadata } from "next";

import { PollList } from "@/components/jan-mat/PollList";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { api, type PollView } from "@/lib/api";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Jan Mat (जन मत) — Public Opinion on Decided Verdicts | Hetu",
  description:
    "Participate in democratic deliberation on published Indian criminal judgments. Structured ballots, reason tallies, and community commentary on decided cases.",
};

export default async function JanMatPage() {
  const { data: polls, error } = await api
    .GET("/polls")
    .catch(() => ({ data: undefined, error: true }));

  return (
    <div className="flex flex-col gap-10 py-6">
      {/* Page Header */}
      <header className="flex flex-col gap-3 border-b border-gold-line pb-6">
        <p className="eyebrow">Democratic Deliberation</p>
        <h1 className="font-serif text-3xl sm:text-5xl text-ivory">Jan Mat (जन मत)</h1>
        <p className="text-base text-ivory-muted leading-relaxed max-w-2xl">
          Public polling and discourse on signed, published judicial verdicts.
          Voice your perspective on judicial reasoning, proportionality, and evidence without personal abuse.
        </p>
      </header>

      {/* 3. Disclaimers & Ethics */}
      <section className="card p-5 sm:p-6 bg-gold-soft/10 border-gold-line flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex flex-col gap-1 text-xs text-ivory-muted leading-relaxed max-w-xl">
          <p>
            <strong className="text-gold">Non-Representative Sample:</strong> Jan Mat polls reflect digital participation, not a scientific cross-section of India.
          </p>
          <p>
            <strong className="text-gold">Pending Trials Policy:</strong> We do not open polls or discussion on pending trials.
          </p>
        </div>
        <div className="shrink-0 text-xs font-semibold text-gold">
          Decided Cases Only
        </div>
      </section>

      {/* 4. Poll Index with Sort Tabs */}
      {error || !polls ? (
        <ErrorState
          eyebrow="Ballots Offline"
          title="Unable to load public ballots"
          message="Could not connect to the Hetu poll service. Ensure the backend is running and refresh."
        />
      ) : polls.length === 0 ? (
        <EmptyState
          eyebrow="Ballot Queue Empty"
          title="No active ballots at this moment"
          description="Polls open automatically upon publication of reviewed criminal judgments. Check back shortly as new verdicts are published."
          actionHref="/verdicts"
          actionLabel="Browse Decided Cases"
        />
      ) : (
        <PollList polls={polls as PollView[]} />
      )}
    </div>
  );
}
