"use client";

import { useState } from "react";
import { Calculator } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { evaluateLine, type SideResult } from "@/lib/ev";
import { cn } from "@/lib/utils";

function parseInput(value: string): number | null {
  if (value.trim() === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function SideRow({ label, result }: { label: string; result: SideResult }) {
  const isPositiveEv = result.ev > 0;
  return (
    <div className="grid grid-cols-4 items-center gap-2 text-xs">
      <span className="font-medium text-foreground">{label}</span>
      <span className="text-right text-muted-foreground tabular-nums">
        {(result.probability * 100).toFixed(1)}%
      </span>
      <span
        className={cn(
          "text-right font-medium tabular-nums",
          isPositiveEv ? "text-[#0ca30c]" : "text-[#d03b3b]",
        )}
      >
        {result.ev >= 0 ? "+" : ""}
        {(result.ev * 100).toFixed(1)}%
      </span>
      <span className="text-right tabular-nums text-muted-foreground">
        {isPositiveEv ? `${result.halfKellyPct.toFixed(1)}%` : "—"}
      </span>
    </div>
  );
}

export function LineChecker({ mean, stdev }: { mean: number; stdev: number }) {
  const [line, setLine] = useState("");
  const [overOdds, setOverOdds] = useState("");
  const [underOdds, setUnderOdds] = useState("");

  const parsedLine = parseInput(line);
  const parsedOverOdds = parseInput(overOdds);
  const parsedUnderOdds = parseInput(underOdds);

  const result =
    parsedLine !== null && parsedOverOdds !== null && parsedUnderOdds !== null
      ? evaluateLine({
          mean,
          stdev,
          line: parsedLine,
          overOdds: parsedOverOdds,
          underOdds: parsedUnderOdds,
        })
      : null;

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="icon-sm" aria-label="Check line">
          <Calculator />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80">
        <div className="flex flex-col gap-3">
          <p className="text-sm font-medium text-foreground">Check a book&apos;s line</p>
          <div className="grid grid-cols-3 gap-2">
            <label className="flex flex-col gap-1 text-xs text-muted-foreground">
              Line
              <Input
                inputMode="decimal"
                placeholder="15.5"
                value={line}
                onChange={(e) => setLine(e.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-muted-foreground">
              Over odds
              <Input
                inputMode="numeric"
                placeholder="-110"
                value={overOdds}
                onChange={(e) => setOverOdds(e.target.value)}
              />
            </label>
            <label className="flex flex-col gap-1 text-xs text-muted-foreground">
              Under odds
              <Input
                inputMode="numeric"
                placeholder="-110"
                value={underOdds}
                onChange={(e) => setUnderOdds(e.target.value)}
              />
            </label>
          </div>

          {result ? (
            <div className="flex flex-col gap-1.5 border-t border-border pt-3">
              <div className="grid grid-cols-4 gap-2 text-xs text-muted-foreground">
                <span />
                <span className="text-right">Prob</span>
                <span className="text-right">EV</span>
                <span className="text-right">½-Kelly</span>
              </div>
              <SideRow label="Over" result={result.over} />
              <SideRow label="Under" result={result.under} />
            </div>
          ) : (
            <p className="border-t border-border pt-3 text-xs text-muted-foreground">
              Enter the line and both odds to see edge and suggested stake.
            </p>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
