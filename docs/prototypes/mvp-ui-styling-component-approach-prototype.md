# Prototype: MVP UI Styling And Component Approach

Throwaway planning prototype for [Wayfinder Ticket: MVP UI Styling And Component Approach Prototype](https://github.com/chof747/print-job-manager/issues/34).

Question: which frontend styling and UI component approach should the MVP use after comparing concrete options in the context of the operations cockpit and guided import flow?

This is not an implementation spec. It is a comparison artifact for choosing the MVP UI implementation direction before the app shell exists.

## Accepted UI Context

- The MVP shell is an operations cockpit with scheduler explanation as a drill-in.
- The post-create UI should make scheduler authority clear: the queue is a projection, not the source of job selection.
- The import flow is a guided upload-to-create workflow: upload, metadata review, requirements, scheduling details, final create.
- The UI needs dense operational information without feeling like a generic admin dashboard.
- The codebase does not yet have a production frontend stack or established component system.

## Shared Sample Surfaces

Operations cockpit:

```text
Operations

Next scheduler decision
Voron 2.4 is idle. Selected job: Panel clips.
Why: eligible, due today, priority 20, loaded material match.

Printers
- Voron 2.4: idle, black PLA, 0.4 mm, enclosed
- Prusa MK4: printing Camera mount, 42m remaining
- Mini: paused, needs attention

Active queue projection
1. Panel clips: ready, selected for Voron 2.4
2. Gearbox cover: ready, waits for Mini attention
3. Enclosure hinge: ready, prefers Prusa MK4

Needs user action
- Failed bracket: failed during first layer
```

Guided import flow:

```text
Import G-code

1. Upload file
2. Review extracted metadata
3. Fill missing required values
4. Add printer requirements and scheduling details
5. Confirm and create job
```

## Variant A: Tailwind Plus Locally Owned Components

Shape: Tailwind CSS for layout and visual language, with a small set of locally owned headless/shadcn-style components copied into the app as needed.

Representative component code:

```tsx
function OperationsCockpit({ decision, printers, jobs, failures }: Props) {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <section className="mx-auto grid max-w-7xl gap-4 p-4 lg:grid-cols-[1.2fr_0.8fr]">
        <Card className="border-cyan-400/30 bg-cyan-950/30">
          <CardHeader eyebrow="Next scheduler decision" title={decision.printerName} />
          <p className="text-2xl font-semibold">{decision.selectedJobName}</p>
          <ReasonList reasons={decision.reasons} />
          <div className="mt-4 flex gap-2">
            <Button>Start assignment</Button>
            <Button variant="secondary">Explain ranking</Button>
          </div>
        </Card>

        <StatusRail printers={printers} />
        <QueueProjection jobs={jobs} />
        <ActionInbox failures={failures} />
      </section>
    </main>
  );
}
```

Operations cockpit feel:

```text
Dark operations console, compact cards, strong status color, dense tables where needed.
Primary design tokens live as Tailwind theme values and CSS variables.
Components are app-owned: Button, Card, Badge, Stepper, Table, Dialog, FormField.
```

Guided import feel:

```text
Left progress rail: Upload -> Metadata -> Requirements -> Scheduling -> Confirm
Main panel: focused form step with extracted metadata badges and provenance labels
Right rail: completeness checklist and detected file facts
```

What it supports well:

- Fast MVP delivery because layout, spacing, and responsive states are directly expressible in the component markup.
- Strong VS Code ergonomics: class completion, no context-switching into style files for most layout work, easy local diffs.
- A product-specific operations visual language without fighting a vendor theme.
- Gradual component ownership: start with a small local set and add primitives only when the UI actually needs them.
- Server-rendered or client-rendered React can both use the same styling approach.

Tradeoffs:

- Utility-heavy markup can become noisy if components are not extracted at real seams.
- Accessibility quality depends on using solid primitives for dialogs, menus, selects, and tabs rather than hand-rolling behavior.
- The team owns consistency; there is no vendor library enforcing it.

Best fit if:

- The MVP needs a distinct operational cockpit rather than a generic SaaS/admin look.
- The app starts small but needs room for dense domain-specific surfaces.
- The team values local ownership and low abstraction over a large prebuilt kit.

## Variant B: Heavy Component Library

Shape: adopt a full component library such as MUI, Ant Design, Mantine, or Chakra, using its layout, form, table, dialog, and theme systems from the start.

Representative component code:

```tsx
function OperationsCockpit({ decision, printers, jobs, failures }: Props) {
  return (
    <AppShell>
      <Grid>
        <Grid.Col span={8}>
          <Card withBorder>
            <Text size="xs">Next scheduler decision</Text>
            <Title order={2}>{decision.selectedJobName}</Title>
            <List>{decision.reasons.map((reason) => <List.Item>{reason}</List.Item>)}</List>
            <Group>
              <Button>Start assignment</Button>
              <Button variant="light">Explain ranking</Button>
            </Group>
          </Card>
        </Grid.Col>
        <Grid.Col span={4}><PrinterList printers={printers} /></Grid.Col>
        <Grid.Col span={8}><DataTable records={jobs} /></Grid.Col>
        <Grid.Col span={4}><ActionList failures={failures} /></Grid.Col>
      </Grid>
    </AppShell>
  );
}
```

Operations cockpit feel:

```text
Polished admin application, fast access to tables/forms/modals, familiar component density.
Visual language is mostly vendor-shaped unless the theme is heavily customized.
```

Guided import feel:

```text
Library Stepper, Upload, Form, Select, Table, Alert, Modal.
Validation and disabled states are mostly library conventions.
```

What it supports well:

- Fastest path to fully featured forms, tables, modals, date pickers, and accessibility defaults.
- Fewer early design-system decisions.
- Useful if MVP risk is mostly CRUD/forms rather than product-specific interaction shape.

Tradeoffs:

- The MVP may look and feel like the library before it feels like Print Job Manager.
- Custom dense operational cockpit layouts can fight the library's component assumptions.
- Bundle size and theming complexity arrive early.
- Vendor APIs become part of app code at many call sites, making future replacement expensive.
- VS Code ergonomics shift from local markup/CSS to remembering library prop systems.

Best fit if:

- The team wants conventional admin UI speed above product-specific visual identity.
- The import flow's forms and tables dominate over scheduler explanation and operational cockpit clarity.
- The chosen library's defaults are acceptable for the long term.

## Variant C: CSS Modules Plus Minimal Headless Components

Shape: component-local CSS modules for styling, with only headless accessibility primitives for behavior-heavy widgets.

Representative component code:

```tsx
import styles from "./OperationsCockpit.module.css";

function OperationsCockpit({ decision, printers, jobs, failures }: Props) {
  return (
    <main className={styles.shell}>
      <section className={styles.grid}>
        <article className={styles.schedulerDecision}>
          <p className={styles.eyebrow}>Next scheduler decision</p>
          <h2>{decision.selectedJobName}</h2>
          <ReasonList reasons={decision.reasons} />
          <div className={styles.actions}>
            <button className={styles.primaryButton}>Start assignment</button>
            <button className={styles.secondaryButton}>Explain ranking</button>
          </div>
        </article>

        <StatusRail printers={printers} />
        <QueueProjection jobs={jobs} />
        <ActionInbox failures={failures} />
      </section>
    </main>
  );
}
```

Operations cockpit feel:

```text
Hand-authored product UI, clear separation between structure and styling.
Styles can be named after domain layout concepts: shell, schedulerDecision, queueProjection, actionInbox.
```

Guided import feel:

```text
Custom stepper and panel layout, normal HTML forms, explicit CSS for review tables and completeness states.
```

What it supports well:

- Minimal dependency surface and low framework lock-in.
- Clear domain names in stylesheets can make complex layouts readable.
- No utility-class noise in JSX.
- Easy to create a distinctive visual language from scratch.

Tradeoffs:

- Slower iteration for responsive layout and state variants than Tailwind.
- More custom CSS decisions early: spacing scale, color tokens, focus states, variants, composition.
- Component variants can drift unless conventions are established immediately.
- Form and interaction primitives still need a separate accessibility strategy.

Best fit if:

- The team strongly prefers authored CSS and wants the lowest styling dependency footprint.
- UI iteration speed is less important than explicit stylesheet control.
- The MVP can tolerate hand-built component conventions from day one.

## Comparison Against MVP Drivers

| Driver | Tailwind + local components | Heavy component library | CSS modules + headless |
|---|---|---|---|
| Fast MVP delivery | Strong | Strong for standard forms; weaker for custom cockpit | Moderate |
| Maintainable UI code | Strong if components are extracted at domain seams | Moderate; vendor APIs spread widely | Strong if CSS conventions are disciplined |
| VS Code ergonomics | Strong with Tailwind tooling | Moderate; prop/API memory heavy | Strong for CSS readers, slower for iteration |
| Operations-focused visual language | Strong | Weak to moderate | Strong |
| Accessibility baseline | Moderate; use headless primitives | Strongest out of box | Moderate; use headless primitives |
| Bundle/control surface | Moderate and controllable | Heaviest | Lightest |
| Future replacement cost | Low to moderate | High | Low |
| Fit for guided import | Strong | Strongest for off-the-shelf form widgets | Moderate |
| Fit for operations cockpit | Strongest | Moderate | Strong |

## Recommended MVP Approach

Choose Variant A: Tailwind CSS plus locally owned shadcn/ui-style components, backed by accessible headless primitives for behavior-heavy widgets.

The MVP should not adopt a heavy component library as the primary UI substrate. It should also not start with unconstrained CSS modules as the default styling approach.

Initial component set:

- `Button`
- `Card`
- `Badge`
- `Stepper`
- `FormField`
- `Select` backed by an accessible primitive
- `Dialog` backed by an accessible primitive
- `Table` or `DataGrid` only as a thin local component, not a heavy grid dependency
- `StatusPill`
- `ReasonList`

Initial visual language:

- Dark operations shell by default, because the cockpit is closer to a shop-floor/status console than a back-office admin screen.
- High-contrast state colors for `idle`, `printing`, `paused`, `failed`, `blocked`, `ready`, and `archived`.
- Dense but legible cards and tables, with scheduler explanations visually promoted above queue rows.
- Import flow can use a lighter panel treatment inside the same token system so it feels guided rather than alarm-heavy.

Why this recommendation:

- It best matches the already-decided operations cockpit direction.
- It preserves local control over scheduler explanation, queue projection, and failure-action surfaces.
- It keeps MVP implementation fast without taking on a vendor design system as architecture.
- It supports VS Code-driven iteration: most layout changes stay near the component being shaped.
- It leaves room to add headless accessibility primitives exactly where needed instead of adopting an entire component suite.

## Decision Prompt

Pick one:

- A: Tailwind CSS plus locally owned shadcn/ui-style components.
- B: Heavy component library as the primary UI substrate.
- C: CSS modules plus minimal headless components.
- Hybrid: specify which approach owns layout/styling, which approach owns behavior-heavy primitives, and what must be excluded.

The decision should also name whether the MVP should use a dark operations shell by default.
