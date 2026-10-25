// Sample shelves for the empty state. Every name exists in the recipe vocabulary.
export const SAMPLES = [
  { name: "Weeknight dinner", items: ["chicken", "rice", "onion", "garlic", "carrot"] },
  { name: "Baking afternoon", items: ["flour", "butter", "sugar", "egg", "milk", "vanilla"] },
  { name: "Soup from scraps", items: ["potato", "onion", "celery", "carrot", "chicken broth"] },
];

export function EmptyState({ starters, onPick, onSample }) {
  return (
    <section className="empty" aria-labelledby="empty-title">
      <h2 className="empty__title" id="empty-title">Stock the shelf to see what you can cook</h2>
      <p className="empty__lead">Type above, tap what’s in your kitchen, or start from a sample.</p>

      <div className="empty__group">
        <h3 className="empty__h">Try a sample shelf</h3>
        <div className="empty__samples">
          {SAMPLES.map((s) => (
            <button key={s.name} type="button" className="sample" onClick={() => onSample(s.items)}>
              <span className="sample__name">{s.name}</span>
              <span className="sample__items">{s.items.join(", ")}</span>
            </button>
          ))}
        </div>
      </div>

      {starters.length > 0 && (
        <div className="empty__group">
          <h3 className="empty__h">Or tap what you have</h3>
          <ul className="starters">
            {starters.map((s) => (
              <li key={s.name}>
                <button type="button" className="starter" onClick={() => onPick(s.name)}>
                  <span aria-hidden="true">+</span> {s.name}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export function NoResults({ strictness, hasDiets, onLoosen, onClearDiets }) {
  return (
    <section className="notice" role="status">
      <h2 className="notice__title">Nothing fits these settings</h2>
      <p>
        Try a looser Strictness, add more ingredients to your shelf
        {hasDiets ? ", or remove a dietary filter" : ""}.
      </p>
      <div className="notice__actions">
        {strictness > 0 && <button type="button" className="btn btn--small" onClick={onLoosen}>Allow more missing items</button>}
        {hasDiets && <button type="button" className="btn btn--ghost btn--small" onClick={onClearDiets}>Clear dietary filters</button>}
      </div>
    </section>
  );
}

export function ErrorState({ onRetry }) {
  return (
    <section className="notice notice--error" role="alert">
      <h2 className="notice__title">Can’t reach the recipe server</h2>
      <p>
        Start it from the project folder with <code>python -m uvicorn src.api:app --port 8000</code>,
        then try again.
      </p>
      <div className="notice__actions">
        <button type="button" className="btn btn--small" onClick={onRetry}>Try again</button>
      </div>
    </section>
  );
}

export function Skeleton() {
  return (
    <div className="cards" aria-hidden="true">
      {[0, 1, 2].map((n) => (
        <div key={n} className="card card--skeleton">
          <div className="skeleton skeleton--jar" />
          <div>
            <div className="skeleton skeleton--line skeleton--w60" />
            <div className="skeleton skeleton--line" />
            <div className="skeleton skeleton--line skeleton--w80" />
          </div>
        </div>
      ))}
    </div>
  );
}
