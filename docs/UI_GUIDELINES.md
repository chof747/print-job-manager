# UI guidelines

This is the living baseline for the application's interface. Extend it as new
patterns are agreed, and use it when implementing or reviewing UI changes.
Existing screens may not yet follow every rule; they are not the standard merely
because they already exist.

The decision to maintain a consistent UI standard is recorded in
[ADR-0017](adr/0017-maintain-consistent-ui-guidelines.md).

## Multi-row interactions

When a user interaction needs more than one row of input widgets, present it in
an overlay dialog rather than an in-page panel. This includes setup and editing
flows, such as job or printer setup. Ensure the dialog remains usable at narrow
viewport sizes and can be dismissed without saving.

**Exception:** A multi-row filter rail may remain in-page when the user can
collapse it completely, leaving the filtered content accessible. This exception
is for filtering controls; a collapsible panel is not a substitute for an overlay
dialog in multi-row setup or editing flows.

## Saving in panels and dialogs

- Close or hide an editing panel or dialog after its save or update succeeds.
  Wait for the operation to succeed before closing it; starting a request is not
  success. The updated information should be visible in the surrounding view.
- If validation or saving fails, keep the panel or dialog open, preserve the
  user's entries, and show an actionable error. Do not report success or discard
  the input.
- Test both successful and unsuccessful saves, including asynchronous failures.

## Transient messages

Present transient feedback and operation results in a dismissible message overlay,
not as a new message embedded below the triggering control. Use green styling for
successful outcomes and red for failures or blocked outcomes, with text that
communicates the outcome without relying on color alone. Keep overlays accessible
by keyboard, restore focus on dismissal, and retain the user's input. Errors or
blocked outcomes that prevent a flow from continuing must use an overlay.
Existing screens should be brought into line as they are updated.

Field validation after a save or submission attempt is an exception: display an
actionable message directly beneath each affected input, keeping the panel or
dialog open and preserving the user's entries. Format the message with red text,
a light red background, and a rounded red border, as in the eligibility check
(`rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-800`).
Associate the message with its input and mark the input invalid for assistive
technology; communicate the error in text rather than relying on color alone.

## Input widgets

All input widgets must follow a consistent visual style. The baseline for text,
number and date inputs, textareas, and selects is the styling used by the
priority/scheduling editor in `frontend/src/app.tsx`, also used by the queue
filters in `frontend/src/queue-filters.tsx`:

```text
rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400
```

This provides rounded corners, a visible slate border, white background, padded
dark text, a subtle shadow, and a cyan keyboard-focus ring. Add `w-full` where a
control should fill its container, as in the filters. Use the same baseline for
selects and textareas; choose appropriate native control types and input-specific
attributes rather than changing their meaning to match the appearance.

Use `FormField` from `frontend/src/ui.tsx` for labelled fields. It wraps the
control in a label styled with `grid gap-2 text-sm font-bold text-slate-700`,
providing consistent label typography and spacing. Include units in the label
when a value has a unit, such as `Nozzle diameter (mm)`.

Checkboxes and other controls that cannot use the text-input box styling should
still fit the same visual language, have a visible keyboard focus indication,
and have an associated label. Reuse existing shared components or styles where
available instead of introducing unrelated variants.

The priority editor is the source of the baseline classes, not a claim that all
of its current fields comply: its assignment-mode select and conditional printer
ID input currently lack those classes. Likewise, existing save flows may still
need to be updated to follow the closing rule above.
