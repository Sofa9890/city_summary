WARM_CLOTHES_THRESHOLD_C = 0
EXPENSIVE_RATE_THRESHOLD = 100


def needs_warm_clothes(temp_c: float) -> bool:
    return temp_c < WARM_CLOTHES_THRESHOLD_C


def is_expensive(rate_to_rub: float) -> bool:
    return rate_to_rub > EXPENSIVE_RATE_THRESHOLD
