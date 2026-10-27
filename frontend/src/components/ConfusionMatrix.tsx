import type { ConfusionMatrix as ConfusionMatrixData } from '../api/types';

export function ConfusionMatrix({ data }: { data: ConfusionMatrixData }) {
  return (
    <div className="card">
      <div className="card__head">
        <div>
          <h2 className="card__title">Confusion matrix</h2>
          <p className="card__sub">
            Rows are the true category, columns what the model predicted. A strong diagonal means
            few mistakes.
          </p>
        </div>
      </div>
      <div className="table-scroll">
        <table className="matrix">
          <caption className="sr-only">Confusion matrix of true versus predicted category</caption>
          <thead>
            <tr>
              <th scope="col" className="matrix__corner">
                True \ Predicted
              </th>
              {data.labels.map((label) => (
                <th key={label} scope="col" className="matrix__col" title={label}>
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.matrix.map((row, i) => {
              const rowMax = Math.max(...row, 1);
              return (
                <tr key={data.labels[i]}>
                  <th scope="row" className="matrix__row" title={data.labels[i]}>
                    {data.labels[i]}
                  </th>
                  {row.map((count, j) => (
                    <td
                      key={data.labels[j]}
                      className={`matrix__cell${i === j ? ' matrix__cell--diag' : ''}`}
                      style={
                        count > 0
                          ? { background: `rgba(0, 81, 213, ${0.1 + (0.6 * count) / rowMax})` }
                          : undefined
                      }
                    >
                      {count === 0 ? '' : count}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
