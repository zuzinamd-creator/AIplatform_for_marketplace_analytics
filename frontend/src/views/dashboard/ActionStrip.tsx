import { Link } from "react-router-dom";

import { Card } from "../../ui/card";
import type { ActionCard } from "./action-strip";

export type ActionStripProps = {
  cards: ActionCard[];
  isLoading?: boolean;
};

export function ActionStrip({ cards, isLoading }: ActionStripProps) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3" data-testid="action-strip">
      {isLoading ? (
        <div className="text-sm text-ink-muted md:col-span-3" data-testid="action-strip-loading">
          Загрузка действий…
        </div>
      ) : (
        cards.map((card) => (
          <Card key={card.id} className="p-4" data-testid={`action-card-${card.id}`}>
            <div className="text-sm font-semibold text-ink">{card.title}</div>
            <div className="mt-2 text-sm leading-relaxed text-ink-secondary">{card.body}</div>
            <Link to={card.ctaHref} className="link-muted mt-3 inline-block text-xs font-medium">
              {card.ctaLabel}
            </Link>
          </Card>
        ))
      )}
    </div>
  );
}
