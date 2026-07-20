import { Link, useLocation, useNavigate } from "react-router-dom";
import type { MouseEvent } from "react";

import { Card } from "../../ui/card";
import type { ActionCard } from "./action-strip";
import { scrollToHashTarget, splitPathAndHash } from "./hash-scroll";

export type ActionStripProps = {
  cards: ActionCard[];
  isLoading?: boolean;
};

function ActionCardCta({ href, label }: { href: string; label: string }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { pathname, hash } = splitPathAndHash(href);

  const onClick = (event: MouseEvent<HTMLAnchorElement>) => {
    if (!hash) return;

    const targetPath = pathname || location.pathname;
    const sameRoute = targetPath === location.pathname;

    if (!sameRoute) {
      // Cross-route: let React Router navigate; DashboardPage hash effect scrolls on mount.
      return;
    }

    // Same route: RR often skips scroll for hash-only updates — force scroll.
    event.preventDefault();
    if (location.hash !== hash) {
      navigate(`${location.pathname}${location.search}${hash}`);
    }
    // rAF: wait for hash/DOM paint (lazy cost panel wrapper already has the id).
    requestAnimationFrame(() => {
      scrollToHashTarget(hash);
    });
  };

  return (
    <Link
      to={href}
      onClick={onClick}
      className="mt-3 inline-block text-sm font-semibold text-brand hover:text-brand-hover hover:underline"
      data-testid="action-card-cta"
    >
      {label}
    </Link>
  );
}

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
            <ActionCardCta href={card.ctaHref} label={card.ctaLabel} />
          </Card>
        ))
      )}
    </div>
  );
}
