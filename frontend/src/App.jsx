import { useEffect, useMemo, useState } from "react";
import { getHealth, getRecommendations, getStarters } from "./api.js";
import { useDebounced, useStoredState } from "./hooks.js";
import Controls from "./components/Controls.jsx";
import RecipeCard from "./components/RecipeCard.jsx";
import Shelf from "./components/Shelf.jsx";
import { EmptyState, ErrorState, NoResults, Skeleton } from "./components/States.jsx";

const DEFAULT_SETTINGS = { strictness: 0.3, effort: 0.5, diets: [], assumeStaples: true, useLlm: false };

export default function App() {
  const [items, setItems] = useStoredState("pm.items", []);
  const [settings, setSettings] = useStoredState("pm.settings", DEFAULT_SETTINGS);
  const [starters, setStarters] = useState([]);
  const [health, setHealth] = useState(null);
  const [data, setData] = useState(null);
  const [status, setStatus] = useState("idle"); // idle | loading | ready | error
  const [retry, setRetry] = useState(0);

  // One-time info: recipe count + quick-add ingredients.
  useEffect(() => {
    const controller = new AbortController();
    getHealth(controller.signal).then(setHealth).catch(() => {});
    getStarters(controller.signal).then(setStarters).catch(() => {});
    return () => controller.abort();
  }, [retry]);

  // Wait until the user stops typing / dragging before asking the server.
  const payload = useMemo(
    () => JSON.stringify({
      items,
      strictness: settings.strictness,
      effort: settings.effort,
      diets: settings.diets,
      assume_staples: settings.assumeStaples,
      use_llm: settings.useLlm,
    }),
    [items, settings],
  );
  const debouncedPayload = useDebounced(payload, 250);

  useEffect(() => {
    const body = JSON.parse(debouncedPayload);
    if (body.items.length === 0) {
      setData(null);
      setStatus("idle");
      return undefined;
    }
    const controller = new AbortController();
    setStatus("loading");
    getRecommendations(body, controller.signal)
      .then((res) => { setData(res); setStatus("ready"); })
      .catch((err) => { if (err.name !== "AbortError") setStatus("error"); });
    return () => controller.abort();
  }, [debouncedPayload, retry]);

  const addItem = (raw) =>
    setItems((prev) => (prev.some((p) => p.toLowerCase() === raw.toLowerCase()) ? prev : [...prev, raw]));
  const removeItem = (index) => setItems((prev) => prev.filter((_, i) => i !== index));
  const change = (patch) => setSettings((prev) => ({ ...prev, ...patch }));

  const results = data?.results ?? [];
  const showEmpty = items.length === 0;

  return (
    <>
      <header className="top">
        <div className="top__inner">
          <a className="brand" href="/">
            <img src="/jar.svg" alt="" width="28" height="28" />
            Pantry Matcher
          </a>
          {health && <p className="top__stat"><span>{health.recipes.toLocaleString()}</span> real recipes, none invented</p>}
        </div>
      </header>

      <main className="page">
        <section className="hero">
          <h1 className="hero__title">What’s on your <mark className="hero__mark">shelf</mark>?</h1>
          <p className="hero__lead">
            Add what you have. We’ll rank real recipes by how well they fit, show what’s missing,
            and suggest what could stand in.
          </p>
        </section>

        <Shelf
          items={items}
          resolved={data?.resolved ?? []}
          onAdd={addItem}
          onRemove={removeItem}
          onClear={() => setItems([])}
        />

        <div className="layout">
          <Controls settings={settings} onChange={change} llmAvailable={Boolean(health?.llm)} />

          <section className="results" aria-labelledby="results-title">
            {showEmpty ? (
              <EmptyState
                starters={starters}
                onPick={addItem}
                onSample={(list) => setItems(list)}
              />
            ) : status === "error" ? (
              <ErrorState onRetry={() => setRetry((n) => n + 1)} />
            ) : !data ? (
              <Skeleton />
            ) : results.length === 0 ? (
              <NoResults
                strictness={settings.strictness}
                hasDiets={settings.diets.length > 0}
                onLoosen={() => change({ strictness: 0 })}
                onClearDiets={() => change({ diets: [] })}
              />
            ) : (
              <>
                <div className="results__head">
                  <h2 className="results__title" id="results-title">Best matches</h2>
                  <p className="results__count" aria-live="polite">
                    Top {results.length} of {data.total_recipes.toLocaleString()} recipes
                  </p>
                </div>
                <ol className="cards" aria-busy={status === "loading"}>
                  {results.map((r, i) => (
                    <li key={r.id}>
                      <RecipeCard recipe={r} rank={i} onHave={addItem} />
                    </li>
                  ))}
                </ol>
              </>
            )}
          </section>
        </div>
      </main>

      <footer className="foot">
        Recipes come from a public dataset, and we never invent dishes. Dietary tags are derived from
        ingredient names, so check labels if you have an allergy.
      </footer>
    </>
  );
}
