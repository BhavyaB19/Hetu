import { Skeleton } from "@/components/ui/Skeleton";

export default function Loading() {
  return (
    <div className="flex flex-col gap-12 max-w-6xl mx-auto py-6">
      <div className="flex flex-col gap-4">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-4 w-48" />
        <Skeleton className="h-10 w-3/4" />
        <Skeleton className="h-5 w-2/3" />
        <div className="flex gap-4 border-b border-gold-line pb-3 pt-2">
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-20" />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="card p-6 flex flex-col gap-4">
          <Skeleton className="h-6 w-36" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-4 w-full" />
        </div>
        <div className="card p-6 flex flex-col gap-4">
          <Skeleton className="h-6 w-36" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-4 w-full" />
        </div>
      </div>
    </div>
  );
}
