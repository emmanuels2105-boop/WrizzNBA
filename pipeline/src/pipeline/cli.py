from pathlib import Path
from typing import List

import typer

from pipeline.backtest.walk_forward import run_backtest, run_backtest_minutes_based
from pipeline.client.wnba_client import WnbaClient
from pipeline.config import (
    DEFAULT_DB_PATH,
    DEFAULT_MINUTES_WINDOW,
    DEFAULT_ROLLING_WINDOW,
    DEFAULT_SEASONS,
)
from pipeline.db.connection import get_connection, init_db
from pipeline.ingest.sync import run_ingest
from pipeline.prediction.generate import generate_predictions
from pipeline.props import get_prop_type

app = typer.Typer(no_args_is_help=True)


@app.command("init-db")
def init_db_command(
    db_path: Path = typer.Option(DEFAULT_DB_PATH, "--db-path", help="Path to the SQLite database file"),
) -> None:
    """Create the SQLite schema (idempotent) and seed prop types."""
    conn = get_connection(db_path)
    try:
        init_db(conn)
    finally:
        conn.close()
    typer.echo(f"Initialized database at {db_path}")


@app.command("ingest")
def ingest_command(
    seasons: List[str] = typer.Option(DEFAULT_SEASONS, "--season", help="Season year to ingest, e.g. 2026"),
    db_path: Path = typer.Option(DEFAULT_DB_PATH, "--db-path", help="Path to the SQLite database file"),
) -> None:
    """Fetch and store historical game logs plus the current schedule."""
    conn = get_connection(db_path)
    try:
        init_db(conn)
        summary = run_ingest(conn, WnbaClient(), seasons)
    finally:
        conn.close()
    typer.echo(f"Ingest complete: {summary}")


@app.command("predict")
def predict_command(
    prop_type: str = typer.Option("POINTS", "--prop-type", help="Prop type to predict"),
    n: int = typer.Option(DEFAULT_ROLLING_WINDOW, "--n", help="Rolling window size (games)"),
    db_path: Path = typer.Option(DEFAULT_DB_PATH, "--db-path", help="Path to the SQLite database file"),
) -> None:
    """Generate predictions for each team's next scheduled game."""
    conn = get_connection(db_path)
    try:
        init_db(conn)  # idempotent -- applies any schema migrations (e.g. new columns)
        summary = generate_predictions(conn, get_prop_type(prop_type), n)
    finally:
        conn.close()
    typer.echo(f"Predict complete: {summary}")
    for player_id, full_name in summary.skipped_players:
        typer.echo(f"  skipped (no history): {full_name} ({player_id})")


@app.command("backtest")
def backtest_command(
    model: str = typer.Option(
        "rolling_average", "--model", help="Model to backtest: rolling_average or minutes_based"
    ),
    prop_type: str = typer.Option("POINTS", "--prop-type", help="Prop type to backtest"),
    seasons: List[str] = typer.Option(DEFAULT_SEASONS, "--season", help="Seasons to include, e.g. 2026"),
    n: int = typer.Option(DEFAULT_ROLLING_WINDOW, "--n", help="Rolling window size (games)"),
    minutes_n: int = typer.Option(
        DEFAULT_MINUTES_WINDOW, "--minutes-n", help="Minutes window size, minutes_based model only"
    ),
    db_path: Path = typer.Option(DEFAULT_DB_PATH, "--db-path", help="Path to the SQLite database file"),
) -> None:
    """Walk-forward backtest of a model against stored game logs."""
    conn = get_connection(db_path)
    try:
        if model == "rolling_average":
            report = run_backtest(conn, get_prop_type(prop_type), seasons, n)
        elif model == "minutes_based":
            report = run_backtest_minutes_based(conn, get_prop_type(prop_type), seasons, n, minutes_n)
        else:
            raise typer.BadParameter("model must be 'rolling_average' or 'minutes_based'")
    finally:
        conn.close()
    typer.echo(
        f"Backtest complete ({model}): n={n} evaluated={report.n_evaluated} skipped={report.n_skipped} "
        f"MAE={report.mae:.3f} MAPE={report.mape:.3%} "
        f"(excluded {report.mape_excluded_zero_actuals} zero-actual games from MAPE)"
    )


if __name__ == "__main__":
    app()
