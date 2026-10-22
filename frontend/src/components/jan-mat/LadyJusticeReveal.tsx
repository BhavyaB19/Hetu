import { ScrollSequence } from "@/components/motion/ScrollSequence";
import { hasMedia, readSequence } from "@/lib/media";

const BLINK = { mp4: "/media/lady/blink.mp4", webm: "/media/lady/blink.webm" };

/**
 * Jan Mat opening: Lady Justice blinks behind her blindfold; scrolling turns her, moves in
 * to her face and the blindfold falls away. Scrolling back plays it in reverse. Renders
 * nothing until the frames are added, so the page simply starts at the ballots.
 */
export function LadyJusticeReveal() {
  const manifest = readSequence("lady/reveal");
  if (!manifest) return null;

  return (
    <ScrollSequence
      manifest={manifest}
      label="Lady Justice turns, and her blindfold falls away"
      runwayVh={300}
      idleVideo={hasMedia(BLINK.mp4) ? { mp4: BLINK.mp4, webm: hasMedia(BLINK.webm) ? BLINK.webm : undefined } : undefined}
      steps={[{ at: 0.92, text: "Justice is blind. The public is not." }]}
    >
      <a
        href="#ballots"
        className="rounded-md border border-gold-line bg-ink/70 px-4 py-2 text-sm text-gold hover:border-gold hover:text-ivory focus-visible:outline-2 focus-visible:outline-gold"
      >
        Skip to the ballots ↓
      </a>
    </ScrollSequence>
  );
}
