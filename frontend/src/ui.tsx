import type { ComponentProps, ReactNode } from "react";


function joinClasses(...classes: Array<string | undefined>) {
  return classes.filter(Boolean).join(" ");
}


export function Card({ as: Component = "section", className, ...props }: ComponentProps<"section"> & { as?: "aside" | "section" }) {
  return (
    <Component
      className={joinClasses("rounded-2xl border border-slate-200 bg-white p-5 shadow-sm", className)}
      {...props}
    />
  );
}


export function Button({ className, variant = "primary", ...props }: ComponentProps<"button"> & { variant?: "primary" | "secondary" }) {
  const variants = {
    primary: "border-indigo-600 bg-indigo-600 text-white hover:bg-indigo-700",
    secondary: "border-slate-200 bg-white text-slate-700 hover:bg-slate-50",
  };

  return (
    <button
      className={joinClasses(
        "rounded-xl border px-4 py-2 text-sm font-bold shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}


export function Badge({ className, ...props }: ComponentProps<"span">) {
  return <span className={joinClasses("inline-flex rounded-full px-2.5 py-1 text-xs font-extrabold", className)} {...props} />;
}


export function StatusPill({ children, tone = "neutral" }: { children: ReactNode; tone?: "neutral" | "ready" | "attention" }) {
  const tones = {
    neutral: "bg-slate-100 text-slate-600",
    ready: "bg-emerald-100 text-emerald-800",
    attention: "bg-amber-100 text-amber-800",
  };

  return <Badge className={tones[tone]}>{children}</Badge>;
}


export function FormField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="grid gap-2 text-sm font-bold text-slate-700">
      {label}
      {children}
    </label>
  );
}


export function Stepper({ activeStep }: { activeStep: number }) {
  const steps = ["Upload", "Metadata", "Requirements", "Scheduling", "Confirm"];

  return (
    <ol aria-label="Import progress" className="grid gap-2 sm:grid-cols-5">
      {steps.map((step, index) => (
        <li
          key={step}
          className={joinClasses(
            "rounded-xl border px-3 py-2 text-xs font-bold",
            index <= activeStep ? "border-indigo-200 bg-indigo-50 text-indigo-800" : "border-slate-200 text-slate-500",
          )}
        >
          {index + 1}. {step}
        </li>
      ))}
    </ol>
  );
}


export function ReasonList({ reasons }: { reasons: string[] }) {
  return (
    <ul className="grid gap-2 text-sm text-slate-600">
      {reasons.map((reason) => <li key={reason}>{reason}</li>)}
    </ul>
  );
}
