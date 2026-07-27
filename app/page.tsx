import { Info } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
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
import { getUpcomingPredictions } from "@/lib/db";

export const dynamic = "force-dynamic";

function formatGameDate(dateStr: string): string {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${dateStr}T00:00:00Z`));
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

  return (
    <div className="flex flex-1 justify-center bg-background px-6 py-16">
      <div className="flex w-full max-w-4xl flex-col gap-6">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            WNBA Points Predictions
          </h1>
          <p className="text-sm text-muted-foreground">
            Rolling 10-game average, projected for each team&apos;s next scheduled game.
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
                        tip="Projected points from a rolling average of the player's last 10 games this season (falls back to last season's average early in the season)."
                      />
                    </TableHead>
                    <TableHead className="text-right">
                      <HeaderTip
                        label="Range"
                        tip="Expected range around the prediction (±1 standard deviation), based on how much the player's scoring varied over those games."
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
