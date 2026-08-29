import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

type RuntimeConfig = {
  apiBaseUrl?: string;
};

const currentDirectory = dirname(fileURLToPath(import.meta.url));

function loadApiBaseUrl() {
  const runtimeConfigPath = resolve(currentDirectory, "public/runtime-config.json");
  const runtimeConfig = JSON.parse(readFileSync(runtimeConfigPath, "utf8")) as RuntimeConfig;

  return runtimeConfig.apiBaseUrl?.startsWith("/") ? runtimeConfig.apiBaseUrl : undefined;
}

const apiBaseUrl = loadApiBaseUrl();

export default defineConfig({
  plugins: [tailwindcss()],
  server: apiBaseUrl
    ? {
        proxy: {
          [apiBaseUrl]: {
            target: "http://127.0.0.1:8000",
            changeOrigin: true,
          },
        },
      }
    : undefined,
});
