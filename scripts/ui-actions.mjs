import { chromium, expect } from "@playwright/test";
import fs from "node:fs";
const browser = await chromium.launch({
  channel: process.env.BROWSER_CHANNEL || "msedge",
  headless: true,
});
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  let documentLoads = 0;
  page.on("request", (r) => {
    if (r.isNavigationRequest()) documentLoads++;
  });
  await page.goto("http://localhost:3000");
  await page.locator("#username").fill("admin");
  await page.locator("#password").fill("admin123");
  await page.locator("#kc-login").click();
  await expect(
    page.getByRole("heading", { name: "Обзор сотрудничества" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Взаимодействия", exact: true }).click();
  await page.locator("tbody tr").first().click();
  await expect(
    page.getByRole("button", { name: "Изменить этап" }),
  ).toBeVisible();
  const baseline = documentLoads;
  const timings = {};
  await page
    .getByLabel("Комментарий к текущему этапу")
    .fill("Проверка интерфейса: комментарий");
  let start = performance.now();
  await page.getByRole("button", { name: "Отправить", exact: true }).click();
  await expect(
    page.getByText("Комментарий добавлен", { exact: true }),
  ).toBeVisible();
  timings.comment_ms = Math.round(performance.now() - start);
  await page.getByRole("button", { name: "Изменить этап" }).click();
  await page
    .getByRole("dialog")
    .getByLabel("Комментарий", { exact: true })
    .fill("Проверка интерфейса: переход");
  start = performance.now();
  await page.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(page.getByText("Этап изменён", { exact: true })).toBeVisible();
  timings.transition_ms = Math.round(performance.now() - start);
  await page
    .locator("input[type=file]")
    .first()
    .setInputFiles({
      name: "demo.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("%PDF-1.4\nDemo attachment\n%%EOF"),
    });
  await expect(page.getByText("Файл загружен", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Отчёты", exact: true }).click();
  start = performance.now();
  await page.getByRole("button", { name: "Предпросмотр" }).click();
  await expect(page.getByText(/Найдено записей:/)).toBeVisible();
  timings.report_preview_ms = Math.round(performance.now() - start);
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "XLSX", exact: true }).click();
  expect((await download).suggestedFilename()).toBe("report.xlsx");
  await page.getByRole("link", { name: "Импорт", exact: true }).click();
  const file = await page.request.get("http://localhost:8000/health");
  expect(file.ok()).toBeTruthy();
  // Download template through the authenticated browser, then upload that same XLSX for preview.
  const templateEvent = page.waitForEvent("download");
  await page.getByRole("button", { name: "Скачать шаблон" }).click();
  const template = await templateEvent;
  fs.mkdirSync("data/browser", { recursive: true });
  await template.saveAs("data/browser/template.xlsx");
  await page
    .locator("input[type=file]")
    .setInputFiles("data/browser/template.xlsx");
  await expect(
    page.getByText("Предпросмотр выбранного сопоставления"),
  ).toBeVisible();
  expect(documentLoads).toBe(baseline);
  const result = {
    ...timings,
    full_page_reloads_during_edits: documentLoads - baseline,
    upload: true,
    xlsx_download: true,
    excel_preview: true,
  };
  fs.writeFileSync("docs/ui-performance.json", JSON.stringify(result, null, 2));
  console.log(JSON.stringify(result));
} finally {
  await browser.close();
}
