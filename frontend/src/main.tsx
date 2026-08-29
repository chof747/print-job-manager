import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import "./app.css";
import { App } from "./app";
import { RuntimeConfigGate } from "./runtime-config-gate";


const container = document.getElementById("root");

if (container) {
  createRoot(container).render(
    <StrictMode>
      <RuntimeConfigGate>
        <App />
      </RuntimeConfigGate>
    </StrictMode>,
  );
}
