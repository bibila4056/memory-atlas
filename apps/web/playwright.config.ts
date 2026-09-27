import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  use: { baseURL: "http://127.0.0.1:3000", headless: true },
  webServer: [
    { command: "../../.venv/bin/python -m uvicorn app.main:app --app-dir ../api --port 8000", url: "http://127.0.0.1:8000/api/health", reuseExistingServer: !process.env.CI },
    { command: "npm run dev -- --hostname 127.0.0.1", url: "http://127.0.0.1:3000/memories/demo", reuseExistingServer: !process.env.CI, timeout: 120000 },
  ],
});
