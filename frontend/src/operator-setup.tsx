import { useState } from "react";
import { useForm } from "react-hook-form";

import { useOperatorSetup } from "./use-operator-setup";
import { Button, Card, FormField } from "./ui";

type PrinterForm = { printerId: string; enclosure: boolean; hardenedNozzle: boolean; nozzleDiameter: string; buildVolume: { x: string; y: string; z: string } };
type MaterialForm = { materialType: string; color: string; amount: string };

export function OperatorSetup({ apiBaseUrl }: { apiBaseUrl: string }) {
  const [showPrinter, setShowPrinter] = useState(false);
  const [showMaterial, setShowMaterial] = useState(false);
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
    <Button type="button" onClick={() => setShowPrinter(!showPrinter)}>Set up printer</Button>
    <Button type="button" onClick={() => setShowMaterial(!showMaterial)}>Add material</Button>
    {showPrinter && <section aria-label="Printer setup">
      <FormField label="Printer ID"><input {...printerForm.register("printerId")} /></FormField>
      <label><input type="checkbox" {...printerForm.register("enclosure")} /> Enclosure</label>
      <label><input type="checkbox" {...printerForm.register("hardenedNozzle")} /> Hardened nozzle</label>
      <FormField label="Nozzle diameter"><input type="number" step="any" {...printerForm.register("nozzleDiameter")} /></FormField>
      {(["x", "y", "z"] as const).map((axis) => <FormField key={axis} label={`Build volume ${axis.toUpperCase()}`}>
        <input type="number" step="any" {...printerForm.register(`buildVolume.${axis}`)} />
      </FormField>)}
      <p>Saving replaces any existing capabilities for this printer.</p>
      <Button type="button" onClick={() => void handleSavePrinter()}>Save printer</Button>
      {printerStatus && <p role="status">{printerStatus}</p>}
    </section>}
    {showMaterial && <section aria-label="Material setup">
      <FormField label="Material type"><input {...materialForm.register("materialType")} /></FormField>
      <FormField label="Color"><input {...materialForm.register("color")} /></FormField>
      <FormField label="Amount (grams)"><input type="number" {...materialForm.register("amount")} /></FormField>
      <Button type="button" onClick={() => void handleSaveMaterial()}>Save material</Button>
      {materialStatus && <p role="status">{materialStatus}</p>}
    </section>}
  </Card>;
}
