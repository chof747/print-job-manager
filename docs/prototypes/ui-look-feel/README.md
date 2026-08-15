# UI Look And Feel Prototype

This directory preserves the accepted MVP UI direction from [Wayfinder Ticket: MVP UI Styling And Component Approach Prototype](https://github.com/chof747/print-job-manager/issues/34).

The prototype is a visual reference, not production code. It captures the chosen structured operations shell:

- burger-menu navigation for major screens
- printer-specific subtabs at the top of the operations cockpit
- next print job first, with richer detail
- next scheduled jobs for the selected printer below the primary job
- multi-printer eligibility marked in each eligible queue
- most important actions shown as an icon panel
- supporting printer state, queue summary, and material stock below the primary decision area

Run it with:

```sh
npm run prototype:ui-look-feel
```

Then open:

```text
http://localhost:4173
```
