import { useEffect, useId, useRef, useState } from "react";
import { getSuggestions } from "../api.js";
import { useDebounced } from "../hooks.js";

const LID_TONES = ["cobalt", "saffron", "teal", "ink"];

// Same ingredient name -> same jar colour every time.
function toneFor(name) {
  let sum = 0;
  for (const ch of name) sum += ch.charCodeAt(0);
  return LID_TONES[sum % LID_TONES.length];
}

function Jar({ label, unknown, hint, onRemove }) {
  return (
    <li className={`jar jar--${unknown ? "unknown" : toneFor(label)}`} title={hint}>
      <span className="jar__lid" aria-hidden="true" />
      <span className="jar__body">
        <span className="jar__label">{unknown ? `${label}?` : label}</span>
      </span>
      <button type="button" className="jar__remove" onClick={onRemove} aria-label={`Remove ${label} from your shelf`}>
        <span aria-hidden="true">×</span>
      </button>
    </li>
  );
}

// `items`: what the user typed. `resolved`: server's reading of each item
// (canonical name, or null when we do not know the ingredient).
export default function Shelf({ items, resolved, onAdd, onRemove, onClear }) {
  const [text, setText] = useState("");
  const [options, setOptions] = useState([]);
  const [active, setActive] = useState(-1);
  const [open, setOpen] = useState(false);
  const listId = useId();
  const inputRef = useRef(null);
  const query = useDebounced(text.trim(), 120);

  // Fetch autocomplete options for the last piece being typed.
  useEffect(() => {
    const piece = query.split(",").pop().trim();
    if (!piece) {
      setOptions([]);
      return undefined;
    }
    const controller = new AbortController();
    getSuggestions(piece, controller.signal)
      .then((list) => {
        setOptions(list.filter((o) => !items.includes(o.name)));
        setActive(-1);
      })
      .catch(() => {});
    return () => controller.abort();
  }, [query, items]);

  function commit(raw) {
    const pieces = raw.split(/[,;\n]/).map((p) => p.trim()).filter(Boolean);
    pieces.forEach(onAdd);
    setText("");
    setOptions([]);
    setOpen(false);
  }

  function onKeyDown(e) {
    if (e.key === "ArrowDown" && options.length) {
      e.preventDefault();
      setOpen(true);
      setActive((a) => (a + 1) % options.length);
    } else if (e.key === "ArrowUp" && options.length) {
      e.preventDefault();
      setActive((a) => (a <= 0 ? options.length - 1 : a - 1));
    } else if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      if (open && active >= 0) commit(options[active].name);
      else if (text.trim()) commit(text);
    } else if (e.key === "Escape") {
      setOpen(false);
    } else if (e.key === "Backspace" && !text && items.length) {
      onRemove(items.length - 1);
    }
  }

  function onPaste(e) {
    const pasted = e.clipboardData.getData("text");
    if (/[,;\n]/.test(pasted)) {
      e.preventDefault();
      commit(pasted);
    }
  }

  // Look up what the server made of each typed item (by its raw text).
  const byRaw = new Map(resolved.map((r) => [r.raw, r]));
  const seen = new Set();
  const jars = items.map((raw, index) => {
    const r = byRaw.get(raw);
    const canonical = r ? r.canonical : raw;
    const unknown = r ? r.canonical === null : false;
    const dup = !unknown && seen.has(canonical);
    seen.add(canonical);
    return { raw, index, label: canonical || raw, unknown, dup, fixed: r && r.how === "fuzzy" };
  });
  const shown = jars.filter((j) => !j.dup);
  const fixes = shown.filter((j) => j.fixed);
  const unknowns = shown.filter((j) => j.unknown);

  return (
    <section className="shelf" aria-labelledby="shelf-title">
      <div className="shelf__head">
        <h2 className="shelf__title" id="shelf-title">Your shelf</h2>
        {items.length > 0 && (
          <button type="button" className="shelf__clear" onClick={onClear}>Empty the shelf</button>
        )}
      </div>

      <div className="shelf__field">
        <label htmlFor="pantry-input" className="sr-only">Add an ingredient</label>
        <input
          id="pantry-input"
          ref={inputRef}
          className="shelf__input"
          type="text"
          value={text}
          autoComplete="off"
          placeholder="Add an ingredient: chicken, rice, tomatos…"
          role="combobox"
          aria-expanded={open && options.length > 0}
          aria-controls={listId}
          aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
          aria-autocomplete="list"
          onChange={(e) => { setText(e.target.value); setOpen(true); }}
          onKeyDown={onKeyDown}
          onPaste={onPaste}
          onBlur={() => setOpen(false)}
          onFocus={() => setOpen(true)}
        />
        <button type="button" className="btn shelf__add" onClick={() => text.trim() && commit(text)} disabled={!text.trim()}>
          Add to shelf
        </button>
        {open && options.length > 0 && (
          <ul className="suggest" id={listId} role="listbox" aria-label="Ingredient suggestions">
            {options.map((o, i) => (
              <li
                key={o.name}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === active}
                className={`suggest__item${i === active ? " is-active" : ""}`}
                onMouseDown={(e) => { e.preventDefault(); commit(o.name); inputRef.current?.focus(); }}
                onMouseEnter={() => setActive(i)}
              >
                {o.name}
              </li>
            ))}
          </ul>
        )}
      </div>

      <p className="shelf__notes" aria-live="polite">
        {fixes.map((j) => (
          <span key={j.raw} className="note note--fixed">Fixed the spelling: “{j.raw}” → {j.label}</span>
        ))}
        {unknowns.map((j) => (
          <span key={j.raw} className="note note--unknown">“{j.raw}” isn’t in our recipes, so it’s ignored</span>
        ))}
      </p>

      <ul className="shelf__jars" aria-label={`Ingredients on your shelf: ${shown.length}`}>
        {shown.length === 0 &&
          [0, 1, 2].map((n) => <li key={n} className="jar jar--ghost" aria-hidden="true"><span className="jar__lid" /><span className="jar__body" /></li>)}
        {shown.map((j) => (
          <Jar
            key={j.raw}
            label={j.label}
            unknown={j.unknown}
            hint={j.fixed ? `You typed “${j.raw}”` : undefined}
            onRemove={() => onRemove(j.index)}
          />
        ))}
      </ul>
    </section>
  );
}
