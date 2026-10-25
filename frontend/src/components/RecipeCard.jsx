import { useId, useState } from "react";

const DIET_LABELS = { vegetarian: "Vegetarian", vegan: "Vegan", gluten_free: "Gluten-free", nut_free: "Nut-free" };
const BODY = "M10 18h44a4 4 0 0 1 4 4v54a6 6 0 0 1-6 6H12a6 6 0 0 1-6-6V22a4 4 0 0 1 4-4z";

// A jar that fills with the share of the recipe's ingredients you already
// have. Green = covered, pink = still missing.
function Gauge({ coverage, id }) {
  const pct = Math.round(coverage * 100);
  const inner = 60; // fill area height in SVG units
  return (
    <figure className="gauge" title={`${pct}% of this recipe's ingredients are covered`}>
      <svg viewBox="0 0 64 86" role="img" aria-label={`${pct}% of the ingredients covered`}>
        <defs>
          <clipPath id={`clip-${id}`}><path d={BODY} /></clipPath>
        </defs>
        <rect x="16" y="2" width="32" height="12" rx="3" fill="var(--saffron)" stroke="var(--ink)" strokeWidth="2.5" />
        <g clipPath={`url(#clip-${id})`}>
          <rect x="0" y="18" width="64" height="64" fill="var(--tomato-wash)" />
          <g className="gauge__liquid" style={{ transform: `translateY(${(1 - coverage) * inner}px)` }}>
            <rect x="0" y="22" width="64" height="64" fill="var(--basil)" />
            <rect x="0" y="22" width="64" height="3" fill="#fff" opacity="0.4" />
          </g>
        </g>
        <path d={BODY} fill="none" stroke="var(--ink)" strokeWidth="2.5" />
        <rect x="13" y="26" width="4" height="44" rx="2" fill="#fff" opacity="0.7" />
      </svg>
      <figcaption className="gauge__pct">{pct}%</figcaption>
      <span className="gauge__word">covered</span>
    </figure>
  );
}

function Swap({ item, options, onHave }) {
  const [first, ...rest] = options || [];
  return (
    <li className="gap">
      <div className="gap__top">
        <strong className="gap__name">{item}</strong>
        <button type="button" className="btn btn--ghost btn--small" onClick={() => onHave(item)}>
          I have {item}
        </button>
      </div>
      {first ? (
        <p className="gap__swap">
          Swap in <strong>{first.text}</strong>
          {first.have_all && <span className="owned">you have this</span>}
          <span className="gap__note"> - {first.note}</span>
          {rest.slice(0, 1).map((o) => (
            <span key={o.text} className="gap__alt">
              Or {o.text}{o.have_all && <span className="owned">you have this</span>} - {o.note}
            </span>
          ))}
        </p>
      ) : (
        <p className="gap__swap gap__swap--none">No substitute in our table. This one needs a trip to the shop.</p>
      )}
    </li>
  );
}

export default function RecipeCard({ recipe, rank, onHave }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const uid = useId().replace(/:/g, "");
  const r = recipe;

  async function copyList() {
    const text = `${r.title}\nStill needed:\n${r.missing.map((m) => `- ${m}`).join("\n")}`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard blocked: do nothing */
    }
  }

  return (
    <article className="card" style={{ "--delay": `${Math.min(rank, 8) * 45}ms` }}>
      <Gauge coverage={r.coverage} id={uid} />

      <div className="card__main">
        <header className="card__head">
          <h3 className="card__title">{r.title}</h3>
          <p className="card__meta">
            <span>score {r.score.toFixed(2)}</span>
            <span>{r.steps} steps</span>
            {r.diet_tags.filter((t) => DIET_LABELS[t]).slice(0, 2).map((t) => (
              <span key={t} className="tag">{DIET_LABELS[t]}</span>
            ))}
          </p>
        </header>

        <p className="card__why">{r.why}</p>

        <dl className="lists">
          <div className="lists__row">
            <dt>You have</dt>
            <dd>
              <ul className="chips">
                {r.have.map((i) => <li key={i} className="chip chip--have">{i}</li>)}
              </ul>
            </dd>
          </div>
          {r.assumed.length > 0 && (
            <div className="lists__row">
              <dt>Assumed</dt>
              <dd>
                <ul className="chips">
                  {r.assumed.map((i) => <li key={i} className="chip chip--assumed">{i}</li>)}
                </ul>
              </dd>
            </div>
          )}
        </dl>

        {r.missing.length === 0 ? (
          <p className="ready">Nothing missing. You can cook this now.</p>
        ) : (
          <div className="missing">
            <h4 className="missing__title">Still missing ({r.missing.length})</h4>
            <ul className="gaps">
              {r.missing.map((m) => (
                <Swap key={m} item={m} options={r.substitutions[m]} onHave={onHave} />
              ))}
            </ul>
          </div>
        )}

        <div className="card__actions">
          <button type="button" className="btn btn--ghost btn--small" aria-expanded={open} aria-controls={`recipe-${uid}`} onClick={() => setOpen(!open)}>
            {open ? "Hide the recipe" : "See the recipe"}
          </button>
          {r.missing.length > 0 && (
            <button type="button" className="btn btn--ghost btn--small" onClick={copyList}>
              {copied ? "Copied" : "Copy shopping list"}
            </button>
          )}
        </div>

        {open && (
          <div className="recipe" id={`recipe-${uid}`}>
            <h4 className="recipe__h">Ingredients</h4>
            <ul className="recipe__ings">
              {r.raw_ingredients.map((l, i) => <li key={i}>{l}</li>)}
            </ul>
            <h4 className="recipe__h">Directions</h4>
            <ol className="recipe__steps">
              {r.directions.map((s, i) => <li key={i}>{s}</li>)}
            </ol>
            <p className="recipe__src">Source: {r.source}</p>
          </div>
        )}
      </div>
    </article>
  );
}
