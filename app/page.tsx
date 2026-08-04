import { PredictionsTable } from "@/components/predictions-table";
import { RefreshButton } from "@/components/refresh-button";
import { Card, CardAction, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getLastRefreshedAt, getUpcomingPredictions } from "@/lib/db";

export const dynamic = "force-dynamic";
export const maxDuration = 120;

function formatLastRefreshed(iso: string | null): string {
  if (!iso) return "Never";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

export default function Home() {
  const predictions = getUpcomingPredictions();
  const lastRefreshedAt = getLastRefreshedAt();

  return (
    <div className="flex flex-1 justify-center bg-background px-6 py-16">
      <div className="flex w-full max-w-4xl flex-col gap-6">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            WNBA Points Predictions
          </h1>
          <p className="text-sm text-muted-foreground">
            Projected minutes &times; points-per-minute rate, for the top 10 projected scorers in each of tomorrow&apos;s games.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Next Game Projections</CardTitle>
            <CardAction className="flex flex-col items-end gap-1.5">
              <RefreshButton />
              <span className="text-xs text-muted-foreground">
                Last refreshed: {formatLastRefreshed(lastRefreshedAt)}
              </span>
            </CardAction>
          </CardHeader>
          <CardContent>
            {/* Remounts (resetting the game filter to "All Games") whenever a
                refresh produces new data -- a stale filter could otherwise point
                at a game that's no longer in the new dataset. */}
            <PredictionsTable predictions={predictions} key={lastRefreshedAt ?? "never"} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
