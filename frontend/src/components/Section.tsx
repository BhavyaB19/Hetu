export function Section({
  id,
  eyebrow,
  title,
  children,
}: {
  id?: string;
  eyebrow: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="flex scroll-mt-6 flex-col gap-5">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h2 className="mt-1 font-serif text-2xl text-ivory sm:text-3xl">{title}</h2>
      </div>
      {children}
    </section>
  );
}
