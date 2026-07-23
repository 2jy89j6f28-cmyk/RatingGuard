import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 90000,
  expect: { timeout: 60000 },
  retries: 0,
  use: {
    baseURL: "http://localhost:3000",
    headless: true,
    screenshot: "on",
    video: "off",
    viewport: { width: 1440, height: 900 },
  },
  projects: [
    {
      name: "chromium",
      use: { browserName: "chromium" },
    },
  ],
});
