# Marketplace cost model (WB)

Costs are represented as:

- Marketplace fees/charges: ledger operations (commission, logistics, storage, ads, penalties, acquiring, deductions)
- Product COGS: `cost_history` effective on the sale date

## Cost coverage semantics

- If cost history is missing, profit/margin can be **incomplete**.
- Coverage API and integrity warnings must surface missing-cost limitations to sellers.

