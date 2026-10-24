export function ReviewBanner({ count }: { count: number }) {
  return (
    <section className="review-banner" aria-label="Review queue">
      <span className="dot dot--amber" />
      <div>
        <h2 className="review-banner__title">
          {count} transaction{count === 1 ? '' : 's'} to review
        </h2>
        <p className="review-banner__sub">
          Predicted categories are waiting for your confirmation.
        </p>
      </div>
    </section>
  );
}
