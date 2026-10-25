import { useState } from "react";

const DIETS = [
  { id: "vegetarian", label: "Vegetarian" },
  { id: "vegan", label: "Vegan" },
  { id: "gluten_free", label: "Gluten-free" },
  { id: "nut_free", label: "Nut-free" },
];

// One labelled slider with a live plain-language readout and named ends.
function Slider({ id, label, value, onChange, readout, left, right }) {
  return (
    <div className="slider">
      <div className="slider__head">
        <label htmlFor={id} className="slider__label">{label}</label>
        <output htmlFor={id} className="slider__readout">{readout}</output>
      </div>
      <input
        id={id}
        className="slider__input"
        type="range"
        min="0"
        max="1"
        step="0.05"
        value={value}
        style={{ "--pct": `${value * 100}%` }}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <div className="slider__ends" aria-hidden="true">
        <span>{left}</span>
        <span>{right}</span>
      </div>
    </div>
  );
}

export default function Controls({ settings, onChange, llmAvailable }) {
  const allowed = Math.round((1 - settings.strictness) * 5);
  const steps = Math.round(3 + settings.effort * 12);
  // On phones the panel starts collapsed so results are visible first.
  // On wide screens CSS keeps it open and the toggle does nothing.
  const [open, setOpen] = useState(() => window.matchMedia("(min-width: 901px)").matches);
  const summary = `${allowed === 0 ? "Nothing missing" : `up to ${allowed} missing`}, about ${steps} steps${
    settings.diets.length ? `, ${settings.diets.length} diet filter${settings.diets.length > 1 ? "s" : ""}` : ""}`;

  function toggleDiet(id) {
    const diets = settings.diets.includes(id)
      ? settings.diets.filter((d) => d !== id)
      : [...settings.diets, id];
    onChange({ diets });
  }

  return (
    <aside className="controls" aria-labelledby="controls-title">
      <h2 className="controls__title" id="controls-title">
        <button type="button" className="controls__toggle" aria-expanded={open} aria-controls="controls-body" onClick={() => setOpen(!open)}>
          <span>Steer the results</span>
          <span className="controls__summary">{summary}</span>
          <span className="controls__chev" aria-hidden="true">{open ? "−" : "+"}</span>
        </button>
      </h2>
      <div className="controls__body" id="controls-body" hidden={!open}>

      <Slider
        id="strictness"
        label="Strictness"
        value={settings.strictness}
        onChange={(strictness) => onChange({ strictness })}
        readout={allowed === 0 ? "Nothing missing" : `Up to ${allowed} missing`}
        left="Happy to shop a little"
        right="Only what I have"
      />

      <Slider
        id="effort"
        label="Effort"
        value={settings.effort}
        onChange={(effort) => onChange({ effort })}
        readout={`About ${steps} steps`}
        left="Few steps"
        right="More involved"
      />

      <fieldset className="diets">
        <legend className="diets__legend">Dietary needs</legend>
        <div className="diets__row">
          {DIETS.map((d) => (
            <button
              key={d.id}
              type="button"
              className="diet"
              aria-pressed={settings.diets.includes(d.id)}
              onClick={() => toggleDiet(d.id)}
            >
              {d.label}
            </button>
          ))}
        </div>
        <p className="diets__hint">Tags come from ingredient names and lean cautious. Always check labels if you have an allergy.</p>
      </fieldset>

      <label className="check">
        <input
          type="checkbox"
          checked={settings.assumeStaples}
          onChange={(e) => onChange({ assumeStaples: e.target.checked })}
        />
        <span>Assume I have salt, pepper, oil and water</span>
      </label>

      {llmAvailable && (
        <label className="check">
          <input type="checkbox" checked={settings.useLlm} onChange={(e) => onChange({ useLlm: e.target.checked })} />
          <span>Reword explanations with an LLM (ranking stays the same)</span>
        </label>
      )}
      </div>
    </aside>
  );
}
