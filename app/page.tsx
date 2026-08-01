import { Info } from "lucide-react";

import { LineChecker } from "@/components/line-checker";
import { RefreshButton } from "@/components/refresh-button";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { getLastRefreshedAt, getUpcomingPredictions, type ConfidenceLevel } from "@/lib/db";

const CONFIDENCE_LABEL: Record<ConfidenceLevel, string> = {
  very_high: "Very High",
  high: "High",
  medium: "Medium",
  low: "Low",
  lock: "It's a Lock",
};

// Red -> orange-yellow -> green -> bright green: a status-style read (bad to
// good), each step's text color picked from its own WCAG contrast against
// white/near-black (e.g. warning #fab219 only clears 1.8:1 with white text but
// 10.7:1 with dark text). "lock" is a separate, rare tier layered on top of
// this scale (see lib/db.ts) -- its shimmering purple/bright-green styling
// lives in app/globals.css as `.confidence-lock` since it needs a CSS animation
// gradient (background-position keyframes), not just a static Tailwind class.
const CONFIDENCE_STYLE: Record<ConfidenceLevel, string> = {
  low: "border-transparent bg-[#d03b3b] text-white",
  medium: "border-transparent bg-[#fab219] text-[#0b0b0b]",
  high: "border-transparent bg-[#0ca30c] text-[#0b0b0b]",
  very_high: "border-transparent bg-[#22c55e] text-[#0b0b0b]",
  lock: "confidence-lock border-transparent font-bold",
};

export const dynamic = "force-dynamic";
export const maxDuration = 120;

function formatGameDate(dateStr: string): string {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${dateStr}T00:00:00Z`));
}

function formatLastRefreshed(iso: string | null): string {
  if (!iso) return "Never";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(iso));
}

function HeaderTip({ label, tip }: { label: string; tip: string }) {
  return (
    <span className="inline-flex items-center justify-end gap-1">
      {label}
      <Tooltip>
        <TooltipTrigger aria-label={`What is "${label}"?`}>
          <Info className="size-3.5 text-muted-foreground" />
        </TooltipTrigger>
        <TooltipContent>{tip}</TooltipContent>
      </Tooltip>
    </span>
  );
}

function TeamBadge({ abbreviation, fullName }: { abbreviation: string; fullName: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge variant="outline">{abbreviation}</Badge>
      </TooltipTrigger>
      <TooltipContent>{fullName}</TooltipContent>
    </Tooltip>
  );
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
            <CardDescription>
              {predictions.length > 0
                ? `${predictions.length} players`
                : "No predictions available"}
            </CardDescription>
            <CardAction className="flex flex-col items-end gap-1.5">
              <RefreshButton />
              <span className="text-xs text-muted-foreground">
                Last refreshed: {formatLastRefreshed(lastRefreshedAt)}
              </span>
            </CardAction>
          </CardHeader>
          <CardContent>
            {predictions.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No predictions yet. Run{" "}
                <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                  uv run pipeline ingest
                </code>{" "}
                then{" "}
                <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                  uv run pipeline predict
                </code>{" "}
                from <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">/pipeline</code> to generate some.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Player</TableHead>
                    <TableHead>Matchup</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead className="text-right">
                      <HeaderTip
                        label="Predicted"
                        tip="Projected minutes (last 5 games) multiplied by a points-per-minute rate (last 10 games). Falls back to last season's numbers early in the season."
                      />
                    </TableHead>
                    <TableHead className="text-right">
                      <HeaderTip
                        label="Range"
                        tip="Expected range around the prediction, based on typical historical error for predictions of this size (from a backtest across past seasons)."
                      />
                    </TableHead>
                    <TableHead className="text-right">
                      <HeaderTip
                        label="Confidence"
                        tip="Based on how consistent this player's own recent scoring has been, compared to today's other predictions (Low = least consistent quarter, Very High = most consistent quarter). It's a Lock is a stricter cutoff on the same signal -- a real but modest edge, not a guarantee."
                      />
                    </TableHead>
                    <TableHead className="text-right">
                      <HeaderTip
                        label="Line"
                        tip="Type in a book's line and odds to see this prediction's edge and a suggested half-Kelly stake for both sides."
                      />
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {predictions.map((prediction) => (
                    <TableRow
                      key={`${prediction.playerName}-${prediction.gameDate}-${prediction.opponent}`}
                    >
                      <TableCell className="font-medium text-foreground">
                        {prediction.playerName}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        <TeamBadge abbreviation={prediction.team} fullName={prediction.teamFullName} />
                        <span className="mx-1.5">vs</span>
                        <TeamBadge
                          abbreviation={prediction.opponent}
                          fullName={prediction.opponentFullName}
                        />
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatGameDate(prediction.gameDate)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Badge>{prediction.predictedValue.toFixed(1)} pts</Badge>
                      </TableCell>
                      <TableCell className="text-right text-muted-foreground tabular-nums">
                        {prediction.predictedLow !== null && prediction.predictedHigh !== null
                          ? `${prediction.predictedLow.toFixed(1)} – ${prediction.predictedHigh.toFixed(1)}`
                          : "—"}
                      </TableCell>
                      <TableCell className="text-right">
                        <Badge className={CONFIDENCE_STYLE[prediction.confidence]}>
                          {CONFIDENCE_LABEL[prediction.confidence]}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {prediction.predictedLow !== null && prediction.predictedHigh !== null ? (
                          <LineChecker
                            mean={prediction.predictedValue}
                            stdev={(prediction.predictedHigh - prediction.predictedLow) / 2}
                          />
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
