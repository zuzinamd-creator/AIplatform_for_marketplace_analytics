# Period analytics UX (seller dashboard)

This UX layer makes analytics **period-aware**, comparison-ready, and transparent.

## Requirements

- single period selection (custom range + presets)
- comparison mode (previous period or custom period B)
- show deltas and % change when comparison enabled
- surface integrity warnings and completeness / freshness metadata

## Components

- `frontend/src/ui/period-selector.tsx`: preset + custom range selector with optional comparison
- `frontend/src/state/period.ts`: stored period selection (localStorage)

