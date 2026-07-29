# WNBA Points Prediction Pipeline (v1)

Standalone Python pipeline that fetches WNBA game data, stores it in a local
SQLite database, and predicts each team's next game's player points. Run
manually via CLI -- no scheduling/automation.

The Next.js app in the parent repo is not wired up to this yet; predictions
just sit in `data/wnba.db` for now.

## Setup

```
uv sync
```

## Commands

```
uv run pipeline init-db                      # create schema (idempotent)
uv run pipeline ingest [--season 2026 ...]   # fetch + store game logs and schedule
uv run pipeline predict [--prop-type POINTS] [--n 10]
uv run pipeline backtest [--model rolling_average|minutes_based] [--prop-type POINTS] [--n 10] [--minutes-n 5] [--season 2026 ...]
```

`ingest` calls `init-db` internally, so a fresh `data/wnba.db` can be built with
just `uv run pipeline ingest`. Default seasons and window sizes live in
`src/pipeline/config.py`.

## Models

- **`rolling_average`** (`prediction/baseline.py`) — the v1 floor: a player's
  last N games' average, season-reset with prior-season cold start. Still
  used as the comparison baseline for new models.
- **`minutes_based`** (`prediction/minutes_based.py`) — **the model `predict`
  actually uses.** Projects `predicted_minutes × points-per-minute rate`,
  using two *different-sized* windows: a longer, more stable window (`--n`,
  default 10) for the rate, and a shorter, more responsive window
  (`--minutes-n`, default 5) for minutes. This split matters: if both used the
  same window, `mean(minutes) × (sum(points)/sum(minutes))` algebraically
  collapses to exactly `mean(points)` (the sums of minutes cancel out) --
  i.e. it would be a no-op wrapper around `rolling_average`. The rate is a
  *pooled* rate (`sum(points)/sum(minutes)`, not a mean of each game's
  individual ratio) so a single low-minute garbage-time appearance (e.g. 1
  minute/4 points = a 4.0 points-per-minute ratio) can't skew it.

  Backtested on 2024-2026 data: `minutes_based` MAE 4.196 vs `rolling_average`
  MAE 4.221 (both `n=10`; `minutes_n=5`, chosen via a sweep from 3-10 that
  found 5-6 both near-optimal). Reproduce with:
  ```
  uv run pipeline backtest --model rolling_average
  uv run pipeline backtest --model minutes_based
  ```

## Known risks

- **Undocumented API.** `stats.wnba.com` and `cdn.wnba.com` are not public,
  documented APIs -- endpoints, params, or response shapes can change without
  notice. All request/response knowledge is isolated in
  `src/pipeline/client/wnba_client.py`, so a break should only require changes
  there.
- **Bot protection.** `stats.wnba.com`'s `/stats/*` endpoints silently drop
  connections from plain `requests`/`curl` (Akamai-style TLS fingerprinting).
  The client uses `curl_cffi` with `impersonate="chrome"` to work around this.
- **Exhibition data.** The league game log occasionally includes non-franchise
  "teams" (national-team exhibitions, All-Star draft squads) alongside the 15
  real WNBA franchises. `ingest/sync.py` filters these out by team_id range
  (`1611661xxx` = real franchise); if the league ever reassigns that id range
  this filter would need revisiting.

## Extending to a new prop type

1. Add a row to `SEED_PROP_TYPES` in `src/pipeline/db/schema.py`.
2. Register it in `PROP_TYPES` in `src/pipeline/props.py`, pointing
   `stat_column` at the existing `player_game_stats` column (rebounds, assists,
   etc. are already ingested).
3. Add the column name to `ALLOWED_STAT_COLUMNS` in `src/pipeline/db/repository.py`
   if it isn't already there.

No re-fetch or migration needed -- the box score data is already stored.
