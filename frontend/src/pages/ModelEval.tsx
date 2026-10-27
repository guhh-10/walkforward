import { ApiError } from '../api/client';
import type { Evaluation } from '../api/types';
import { Async } from '../components/Async';
import { ConfusionMatrix } from '../components/ConfusionMatrix';
import { Icon } from '../components/Icon';
import { PerClassTable } from '../components/PerClassTable';
import { useEvaluation } from '../hooks/useEvaluation';
import { formatDateTime, formatPercent } from '../lib/format';

const TRAIN_COMMAND = 'python -m app.scripts.train_classifier';

const ALGORITHM_NAMES: Record<string, string> = {
  logreg_tfidf: 'Logistic regression + TF-IDF',
  complement_nb: 'Complement Naive Bayes + TF-IDF',
};

function Score({ label, value, hint }: { label: string; value: number; hint: string }) {
  return (
    <div className="card score">
      <span className="metric__label">{label}</span>
      <span className="score__value">{formatPercent(value * 100)}</span>
      <span className="card__sub">{hint}</span>
    </div>
  );
}

function EvaluationView({ evaluation }: { evaluation: Evaluation }) {
  const { metrics } = evaluation;
  return (
    <>
      <section className="card model-summary">
        <div>
          <span className="pill pill--positive">Active</span>
          <h2 className="card__title">
            {evaluation.version_tag} ·{' '}
            {ALGORITHM_NAMES[evaluation.algorithm] ?? evaluation.algorithm}
          </h2>
          <p className="card__sub">Trained {formatDateTime(evaluation.trained_at)}</p>
        </div>
        <dl className="facts">
          <div>
            <dt>Labelled transactions</dt>
            <dd>{evaluation.dataset_size}</dd>
          </div>
          <div>
            <dt>Training / test</dt>
            <dd>
              {metrics.n_train} / {metrics.n_test}
            </dd>
          </div>
          <div>
            <dt>Random seed</dt>
            <dd>{metrics.seed}</dd>
          </div>
        </dl>
      </section>

      <section className="score-grid" aria-label="Headline metrics">
        <Score
          label="Macro F1 (headline)"
          value={metrics.macro_f1}
          hint="Average over categories, so small ones count as much as big ones"
        />
        <Score label="Accuracy" value={metrics.accuracy} hint="Share of test transactions right" />
        <Score
          label="Weighted F1"
          value={metrics.weighted_f1}
          hint="Like macro F1, but weighted by category size"
        />
      </section>

      {metrics.warnings.length > 0 && (
        <section className="review-banner review-banner--stack" aria-label="Warnings">
          <Icon name="warning" size={20} className="tone-warning" />
          <ul className="warnings">
            {metrics.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </section>
      )}

      <PerClassTable classes={metrics.per_class} />
      <ConfusionMatrix data={metrics.confusion_matrix} />
    </>
  );
}

function NoModel() {
  return (
    <section className="card empty-model">
      <Icon name="model_training" size={32} className="tone-muted" />
      <h2 className="card__title">No classifier trained yet</h2>
      <p>
        The app works without one. To train the first classifier, confirm or categorise some
        transactions, then run this in the <code>backend</code> folder:
      </p>
      <code className="command">{TRAIN_COMMAND}</code>
    </section>
  );
}

export default function ModelEval() {
  const query = useEvaluation();
  const noModel = query.error instanceof ApiError && query.error.code === 'NO_ACTIVE_MODEL';

  return (
    <div className="dashboard">
      <section className="dashboard__intro">
        <h1>Model evaluation</h1>
        <p>How well the category classifier does on transactions it was not trained on.</p>
      </section>
      {noModel ? (
        <NoModel />
      ) : (
        <Async query={query} minHeight={320}>
          {(evaluation) => <EvaluationView evaluation={evaluation} />}
        </Async>
      )}
    </div>
  );
}
