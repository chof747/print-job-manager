import { useEffect, useRef, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";

import { useOperatorSetup } from "./use-operator-setup";
import { Button, Card, FormField } from "./ui";

type PrinterForm = { printerId: string; enclosure: boolean; hardenedNozzle: boolean; nozzleDiameter: string; buildVolume: { x: string; y: string; z: string } };
type MaterialForm = { materialType: string; color: string; amount: string };

const inputClass = "w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400";

export function SetupDialog({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const dialog = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  close.current = onClose;

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const element = dialog.current;
    element?.querySelector<HTMLElement>("input, button")?.focus();
    function handleKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        close.current();
      } else if (event.key === "Tab" && element) {
        const focusable = Array.from(element.querySelectorAll<HTMLElement>("button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled)"));
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
      }
    }
    document.addEventListener("keydown", handleKey);
    return () => { document.removeEventListener("keydown", handleKey); previous?.focus(); };
  }, []);

  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-4" onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <div ref={dialog} role="dialog" aria-modal="true" aria-label={title} className="max-h-full w-full max-w-lg overflow-y-auto rounded-2xl border border-slate-200 bg-white p-6 shadow-xl">
      <div className="mb-5 flex items-center justify-between gap-4">
        <h2 className="text-lg font-bold text-slate-900">{title}</h2>
        <Button type="button" variant="secondary" onClick={onClose}>Close</Button>
      </div>
      {children}
    </div>
  </div>;
}

export function OperatorSetup({ apiBaseUrl }: { apiBaseUrl: string }) {
  const [open, setOpen] = useState<"printer" | "material" | null>(null);
  const printerForm = useForm<PrinterForm>({ defaultValues: { printerId: "", enclosure: false, hardenedNozzle: false, nozzleDiameter: "", buildVolume: { x: "", y: "", z: "" } } });
  const materialForm = useForm<MaterialForm>({ defaultValues: { materialType: "", color: "", amount: "" } });
  const { printer, material } = useOperatorSetup(apiBaseUrl);
  const [printerStatus, setPrinterStatus] = useState("");
  const [materialStatus, setMaterialStatus] = useState("");

  async function handleSavePrinter() {
    const { printerId, enclosure, hardenedNozzle, nozzleDiameter, buildVolume } = printerForm.getValues();
    if (!printerId.trim()) return;
    const diameter = Number(nozzleDiameter);
    const volumeValues = [buildVolume.x, buildVolume.y, buildVolume.z];
    const hasVolume = volumeValues.some((value) => value.trim());
    if ((nozzleDiameter.trim() && (!Number.isFinite(diameter) || diameter <= 0)) ||
      (hasVolume && volumeValues.some((value) => !value.trim() || !Number.isFinite(Number(value)) || Number(value) <= 0))) {
      setPrinterStatus("Enter positive finite printer dimensions");
      return;
    }
    try {
      await printer.mutateAsync({ printerId: printerId.trim(), capabilities: {
        enclosure,
        ...(hardenedNozzle ? { hardenedNozzle: true } : {}),
        ...(nozzleDiameter.trim() ? { nozzleDiameter: diameter } : {}),
        ...(hasVolume ? { buildVolume: { x: Number(buildVolume.x), y: Number(buildVolume.y), z: Number(buildVolume.z) } } : {}),
      } });
      setPrinterStatus("Printer saved");
    } catch {
      setPrinterStatus("Unable to save printer");
    }
  }

  async function handleSaveMaterial() {
    const { materialType, color, amount } = materialForm.getValues();
    const quantity = Number(amount);
    if (!materialType.trim() || !color.trim() || !Number.isFinite(quantity) || quantity <= 0) return;
    try {
      await material.mutateAsync({ materialType: materialType.trim(), color: color.trim(), amountGrams: quantity });
      setMaterialStatus("Material saved");
    } catch {
      setMaterialStatus("Unable to save material");
    }
  }

  return <Card aria-label="Operator setup">
    <div className="flex flex-wrap gap-3">
      <Button type="button" onClick={(event) => { event.currentTarget.focus(); setOpen("printer"); }}>Set up printer</Button>
      <Button type="button" onClick={(event) => { event.currentTarget.focus(); setOpen("material"); }}>Add material</Button>
    </div>
    {open === "printer" && <SetupDialog title="Printer setup" onClose={() => setOpen(null)}><section aria-label="Printer setup" className="grid gap-4">
      <FormField label="Printer ID"><input className={inputClass} {...printerForm.register("printerId")} /></FormField>
      <div className="flex flex-wrap gap-4 text-sm font-bold text-slate-700">
        <label className="flex items-center gap-2"><input type="checkbox" className="h-4 w-4 accent-indigo-600" {...printerForm.register("enclosure")} /> Enclosure</label>
        <label className="flex items-center gap-2"><input type="checkbox" className="h-4 w-4 accent-indigo-600" {...printerForm.register("hardenedNozzle")} /> Hardened nozzle</label>
      </div>
      <FormField label="Nozzle diameter (mm)"><input className={inputClass} type="number" step="any" {...printerForm.register("nozzleDiameter")} /></FormField>
      <div className="grid gap-3 sm:grid-cols-3">{(["x", "y", "z"] as const).map((axis) => <FormField key={axis} label={`Build volume ${axis.toUpperCase()} (mm)`}>
        <input className={inputClass} type="number" step="any" {...printerForm.register(`buildVolume.${axis}`)} />
      </FormField>)}</div>
      <p className="text-sm text-slate-500">Saving replaces any existing capabilities for this printer.</p>
      <Button type="button" onClick={() => void handleSavePrinter()}>Save printer</Button>
      {printerStatus && <p role="status">{printerStatus}</p>}
    </section></SetupDialog>}
    {open === "material" && <SetupDialog title="Material setup" onClose={() => setOpen(null)}><section aria-label="Material setup" className="grid gap-4">
      <FormField label="Material type"><input className={inputClass} {...materialForm.register("materialType")} /></FormField>
      <FormField label="Color"><input className={inputClass} {...materialForm.register("color")} /></FormField>
      <FormField label="Amount (grams)"><input className={inputClass} type="number" step="any" {...materialForm.register("amount")} /></FormField>
      <Button type="button" onClick={() => void handleSaveMaterial()}>Save material</Button>
      {materialStatus && <p role="status">{materialStatus}</p>}
    </section></SetupDialog>}
  </Card>;
}
