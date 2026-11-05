import { useState } from "react";

import { Button, FormField } from "./ui";

const groups = {
  "Job details": [
    { key: "material", label: "Filter by material" },
    { key: "minDurationSeconds", label: "Minimum duration (seconds)", type: "number" },
    { key: "minPriority", label: "Minimum priority", type: "number" },
    { key: "dueBefore", label: "Due before", type: "date" },
    { key: "tag", label: "Filter by tag" },
    { key: "assignmentMode", label: "Filter by printer assignment", type: "select" },
  ],
  "Print requirements": [
    { key: "maxFilamentWeightGrams", label: "Maximum filament weight (grams)", type: "number" },
    { key: "nozzleDiameter", label: "Nozzle diameter (mm)", type: "number", step: "any" },
    { key: "maxDimensionX", label: "Maximum X dimension (mm)", type: "number", step: "any" },
    { key: "maxDimensionY", label: "Maximum Y dimension (mm)", type: "number", step: "any" },
    { key: "maxDimensionZ", label: "Maximum Z dimension (mm)", type: "number", step: "any" },
  ],
  "Source & diagnostics": [
    { key: "slicer", label: "Slicer" },
    { key: "diagnosticCode", label: "Diagnostic code" },
    { key: "provenanceParser", label: "Provenance parser" },
  ],
} satisfies Record<string, Array<{ key: string; label: string; type?: string; step?: string }>>;

type Group = keyof typeof groups;
type Field = { key: string; label: string; type?: string; step?: string };
const inputClass = "w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400";

export function QueueFilters({ applied, onApply }: { applied: string; onApply: (filters: string) => void }) {
  const [open, setOpen] = useState(false);
  const [group, setGroup] = useState<Group>("Job details");
  const [values, setValues] = useState<Record<string, string>>({});
  const appliedEntries = Array.from(new URLSearchParams(applied).entries());
  const labels = Object.fromEntries((Object.values(groups).flat() as Field[]).map(({ key, label }) => [key, label]));

  function apply() {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(values)) {
      if (value.trim()) params.set(key, value.trim());
    }
    onApply(params.toString());
    setOpen(false);
  }

  return (
    <div className="my-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2 text-sm text-slate-600" aria-live="polite">
          <span>{appliedEntries.length ? `${appliedEntries.length} active ${appliedEntries.length === 1 ? "filter" : "filters"}` : "No filters applied"}</span>
          {appliedEntries.map(([key, value]) => <span key={key} className="rounded-full bg-indigo-50 px-2 py-1 text-xs text-indigo-800">{labels[key] ?? key}: {value}</span>)}
        </div>
        <Button type="button" variant="secondary" aria-expanded={open} aria-controls="queue-filter-panel" onClick={() => setOpen(!open)}>{open ? "Close filter rail" : "Open filter rail"}</Button>
      </div>
      {open && <div id="queue-filter-panel" className="mt-4 flex flex-col gap-4 border-t border-slate-200 pt-4 md:flex-row">
        <nav aria-label="Filter categories" className="flex flex-wrap gap-2 md:w-48 md:shrink-0 md:flex-col">
          {(Object.keys(groups) as Group[]).map((item) => <button type="button" key={item} aria-current={group === item ? "true" : undefined} onClick={() => setGroup(item)} className={`rounded-lg px-3 py-2 text-left text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 ${group === item ? "bg-indigo-100 font-bold text-indigo-800" : "text-slate-600 hover:bg-slate-100"}`}>{item}</button>)}
        </nav>
        <div className="min-w-0 flex-1">
          <h3 className="mb-3 font-bold">{group}</h3>
          <div className="grid gap-3 sm:grid-cols-2">
            {(groups[group] as Field[]).map(({ key, label, type, step }) => <FormField key={key} label={label}>
              {type === "select" ? <select className={inputClass} value={values[key] ?? ""} onChange={(event) => setValues({ ...values, [key]: event.target.value })}><option value="">Any</option><option value="unassigned">Unassigned</option><option value="preferred">Preferred</option><option value="required">Required</option></select> : <input className={inputClass} type={type ?? "text"} step={step} value={values[key] ?? ""} onChange={(event) => setValues({ ...values, [key]: event.target.value })} />}
            </FormField>)}
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Button type="button" onClick={apply}>Apply filters</Button>
            <Button type="button" variant="secondary" onClick={() => { setValues({}); onApply(""); }}>Clear all</Button>
          </div>
        </div>
      </div>}
    </div>
  );
}
