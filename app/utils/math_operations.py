def percentage_change(current, previous):
    return (
        round(100 * (current - previous) / abs(previous), 2) if previous != 0 else 0.00
    )
