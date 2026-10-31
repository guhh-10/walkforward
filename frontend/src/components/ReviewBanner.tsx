import { Icon } from './Icon';

export function ReviewBanner({ count }: { count: number }) {
  return (
    <a className="review-banner review-banner--link" href="#review" aria-label="Open review queue">
      <span className="dot dot--amber" />
      <div>
        <h2 className="review-banner__title">
          {count} transaction{count === 1 ? '' : 's'} to review
        </h2>
        <p className="review-banner__sub">
          Predicted categories are waiting for your confirmation.
        </p>
      </div>
      <Icon name="chevron_right" size={20} className="review-banner__go" />
    </a>
  );
}
