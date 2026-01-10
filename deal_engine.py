def score_deal(old_price, new_price):
    if old_price <= 0:
        return 0

    drop = old_price - new_price
    discount_pct = (drop / old_price) * 100

    score = 0
    if drop >= 300:
        score += 1
    if discount_pct >= 25:
        score += 2
    if discount_pct >= 40:
        score += 2

    return score
