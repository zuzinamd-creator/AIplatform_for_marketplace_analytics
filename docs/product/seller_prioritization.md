# Seller prioritization

Priority tiers:

- **Сделать сегодня** (`today`)
- **На этой неделе** (`this_week`)
- **Информация** (`informational`)

Inputs (deterministic):

- revenue/impact opportunity score
- urgency score
- confidence score
- deterioration / trust signals (stale data, missing costs, payout mismatch)
- inventory workflow boost

Implementation: `app/ai/product/prioritization.py`

