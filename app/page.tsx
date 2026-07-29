import { Info } from "lucide-react";

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
};

// Single-hue sequential ramp (blue, light->dark = low->high confidence), an
// ordinal use validated with dataviz's validate_palette.js --ordinal in both
// light and dark mode (lightness monotone, adjacent step gaps >= 0.06 OKLCH L,
// single hue, light-end contrast clears its surface in both modes). Text color
// per step is picked from its own WCAG contrast against white/near-black --
// the two lighter steps read better with dark text, the two darker with white.
const CONFIDENCE_STYLE: Record<ConfidenceLevel, string> = {
  low: "border-transparent bg-[#6da7ec] text-[#0b0b0b]",
  medium: "border-transparent bg-[#3987e5] text-[#0b0b0b]",
  high: "border-transparent bg-[#256abf] text-white",
  very_high: "border-transparent bg-[#184f95] text-white",
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
            Projected minutes &times; points-per-minute rate, for each team&apos;s next scheduled game.
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
                        tip="Expected range around the prediction (±1 standard deviation in projected minutes, scaled by the points-per-minute rate)."
                      />
                    </TableHead>
                    <TableHead className="text-right">
                      <HeaderTip
                        label="Confidence"
                        tip="How tight this prediction's range is relative to its value, compared to today's other predictions. Very High = tightest quarter of ranges; Low = widest quarter."
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
                        <Badge variant="outline">{prediction.team}</Badge>
                        <span className="mx-1.5">vs</span>
                        <Badge variant="outline">{prediction.opponent}</Badge>
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
