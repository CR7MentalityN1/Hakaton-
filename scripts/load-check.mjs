import { chromium } from "@playwright/test";
import fs from "node:fs";
const browser = await chromium.launch({
  channel: process.env.BROWSER_CHANNEL || "msedge",
  headless: true,
});
try {
  const page = await browser.newPage();
  let authorization;
  page.on("request", (r) => {
    if (r.url().includes("/api/v1/auth/me"))
      authorization = r.headers().authorization;
  });
  await page.goto("http://localhost:3000");
  await page.locator("#username").fill("admin");
  await page.locator("#password").fill("admin123");
  await page.locator("#kc-login").click();
  await page.getByRole("heading", { name: "Обзор сотрудничества" }).waitFor();
  if (!authorization) throw Error("No Keycloak session");
  const request = async (path, body) => {
    const start = performance.now();
    const r = await fetch("http://127.0.0.1:8000/api/v1" + path, {
      method: body ? "POST" : "GET",
      headers: { authorization, "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    await r.arrayBuffer();
    if (!r.ok) throw Error(`${path}: ${r.status}`);
    return performance.now() - start;
  };
  await request("/dashboard");
  const concurrent = await Promise.all(
    Array.from({ length: 50 }, (_, i) =>
      request(["/universities", "/interactions", "/dashboard"][i % 3]),
    ),
  );
  const reports = await Promise.all(
    Array.from({ length: 10 }, (_, i) =>
      request("/reports/export", {
        format: ["pdf", "xls", "xlsx", "json"][i % 4],
        columns:
          i % 2
            ? ["university", "program", "product", "stage"]
            : [
                "university",
                "direction",
                "program",
                "product",
                "stage",
                "responsible",
                "contract_number",
                "license_end_date",
              ],
      }),
    ),
  );
  const stats = (values) => {
    const sorted = [...values].sort((a, b) => a - b);
    return {
      requests: values.length,
      p50_ms: Math.round(sorted[Math.floor(sorted.length * 0.5)]),
      p95_ms: Math.round(
        sorted[Math.min(sorted.length - 1, Math.floor(sorted.length * 0.95))],
      ),
      max_ms: Math.round(sorted.at(-1)),
      errors: 0,
    };
  };
  const result = {
    environment:
      "Windows native PostgreSQL 17, Keycloak 26.2.5, Redis unavailable; loopback, demo dataset",
    timestamp: new Date().toISOString(),
    concurrent_50: stats(concurrent),
    reports_10: stats(reports),
  };
  fs.writeFileSync("docs/load-results.json", JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
} finally {
  await browser.close();
}
