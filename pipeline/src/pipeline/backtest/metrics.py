from statistics import mean


def mae(actual_predicted_pairs: list[tuple[float, float]]) -> float:
    return mean(abs(actual - predicted) for actual, predicted in actual_predicted_pairs)


def mape(actual_predicted_pairs: list[tuple[float, float]]) -> tuple[float, int]:
    """Returns (mape, n_excluded_zero_actuals). A 0-point game makes percentage
    error undefined, so those rows are excluded rather than silently blown up."""
    valid = [(actual, predicted) for actual, predicted in actual_predicted_pairs if actual != 0]
    excluded = len(actual_predicted_pairs) - len(valid)
    if not valid:
        return float("nan"), excluded
    value = mean(abs(actual - predicted) / actual for actual, predicted in valid)
    return value, excluded
