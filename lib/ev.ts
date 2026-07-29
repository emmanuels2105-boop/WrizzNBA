export type SideResult = {
  probability: number;
  ev: number;
  halfKellyPct: number;
};

export type LineEvaluation = {
  over: SideResult;
  under: SideResult;
};

// Abramowitz-Stegun 7.1.26 approximation of erf -- accurate to ~1.5e-7,
// plenty for a betting-edge estimate built on a normal-approximated range.
function erf(x: number): number {
  const sign = x < 0 ? -1 : 1;
  const absX = Math.abs(x);

  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const p = 0.3275911;

  const t = 1 / (1 + p * absX);
  const y = 1 - ((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t * Math.exp(-absX * absX);
  return sign * y;
}

export function standardNormalCdf(z: number): number {
  return 0.5 * (1 + erf(z / Math.SQRT2));
}

// Net profit per $1 staked ("b" in Kelly terms).
export function americanOddsToPayoutMultiplier(odds: number): number {
  return odds < 0 ? 100 / -odds : odds / 100;
}

export function americanOddsToImpliedProbability(odds: number): number {
  return odds < 0 ? -odds / (-odds + 100) : 100 / (odds + 100);
}

// EV per $1 staked.
export function expectedValue(probability: number, odds: number): number {
  const payout = americanOddsToPayoutMultiplier(odds);
  return probability * payout - (1 - probability);
}

// Full Kelly f* = (p*b - q) / b, halved for variance reduction, clamped to 0
// (no bet) rather than a negative stake when the edge is negative.
export function halfKellyFraction(probability: number, odds: number): number {
  const b = americanOddsToPayoutMultiplier(odds);
  const q = 1 - probability;
  const fullKelly = (probability * b - q) / b;
  return Math.max(0, fullKelly / 2);
}

function evaluateSide(probability: number, odds: number): SideResult {
  return {
    probability,
    ev: expectedValue(probability, odds),
    halfKellyPct: halfKellyFraction(probability, odds) * 100,
  };
}

export function evaluateLine(input: {
  mean: number;
  stdev: number;
  line: number;
  overOdds: number;
  underOdds: number;
}): LineEvaluation {
  const { mean, stdev, line, overOdds, underOdds } = input;

  // Degenerate/delta distribution -- no spread to integrate over, so the
  // outcome relative to the line is certain rather than a division by zero.
  const probOver = stdev <= 0 ? (mean > line ? 1 : 0) : 1 - standardNormalCdf((line - mean) / stdev);
  const probUnder = 1 - probOver;

  return {
    over: evaluateSide(probOver, overOdds),
    under: evaluateSide(probUnder, underOdds),
  };
}
