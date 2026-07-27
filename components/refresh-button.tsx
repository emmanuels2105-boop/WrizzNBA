"use client";

import { useState, useTransition } from "react";
import { Loader2, RefreshCw } from "lucide-react";

import { refreshData, type RefreshResult } from "@/app/actions";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function RefreshButton() {
  const [isPending, startTransition] = useTransition();
  const [result, setResult] = useState<RefreshResult | null>(null);

  function handleClick() {
    setResult(null);
    startTransition(async () => {
      setResult(await refreshData());
    });
  }

  return (
    <div className="flex flex-col items-end gap-1.5">
      <Button onClick={handleClick} disabled={isPending} size="sm" variant="outline">
        {isPending ? <Loader2 className="animate-spin" /> : <RefreshCw />}
        {isPending ? "Refreshing…" : "Refresh Data"}
      </Button>
      {result && (
        <p
          className={cn(
            "max-w-xs whitespace-pre-line text-right text-xs",
            result.success ? "text-muted-foreground" : "text-destructive",
          )}
        >
          {result.message}
        </p>
      )}
    </div>
  );
}
