import { chromium, expect } from "@playwright/test";
import fs from "node:fs";
fs.mkdirSync("docs/screenshots", { recursive: true });
const browser = await chromium.launch({
  channel: process.env.BROWSER_CHANNEL || "msedge",
  headless: true,
});
const results = [];
try {
  for (const role of ["admin", "manager", "user"]) {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 1000 },
    });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", (e) => {
      errors.push(e.message);
      console.error(e.message);
    });
    await page.goto("http://localhost:3000");
    await page.locator("#username").fill(role);
    await page.locator("#password").fill(role + "123");
    if (role === "admin")
      await page.screenshot({ path: "docs/screenshots/login.png" });
    await page.locator("#kc-login").click();
    await expect(
      page.getByRole("heading", { name: "Обзор сотрудничества" }),
    ).toBeVisible({ timeout: 45000 });
    await expect(
      page.getByRole("heading", { name: "Востребованность программ" }),
    ).toBeVisible({ timeout: 20000 });
    if (role === "admin") {
      await page.screenshot({
        path: "docs/screenshots/dashboard.png",
        fullPage: true,
      });
      for (const [path, heading, name] of [
        ["universities", "ВУЗы", "universities"],
        ["interactions/1", "Основы Python", "interaction"],
        ["workflows", "Workflow", "workflows"],
        ["reports", "Конструктор отчётов", "reports"],
        ["import", "Импорт Excel", "import"],
        ["users", "Пользователи", "users"],
        ["audit", "Журнал аудита", "audit"],
      ]) {
        await page.goto("http://localhost:3000/" + path);
        await expect(
          page.getByRole("heading", { name: heading, exact: true }),
        ).toBeVisible({ timeout: 20000 });
        if (path === "reports") {
          await page.getByRole("button", { name: "Предпросмотр" }).click();
          await expect(page.getByText(/Найдено записей:/)).toBeVisible();
        }
        await page.screenshot({
          path: `docs/screenshots/${name}.png`,
          fullPage: true,
        });
      }
    }
    if (role === "user") {
      await page.goto("http://localhost:3000/settings");
      await expect(
        page.getByText("403 · Недостаточно прав доступа"),
      ).toBeVisible();
      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto("http://localhost:3000/universities");
      await expect(
        page.getByRole("heading", { name: "ВУЗы", exact: true }),
      ).toBeVisible();
      await page.getByRole("button", { name: "Открыть меню" }).click();
      await expect(
        page.getByText("РТК", { exact: false }).last(),
      ).toBeVisible();
      await page.screenshot({ path: "docs/screenshots/mobile.png" });
    }
    expect(errors).toEqual([]);
    results.push({ role, login: true, errors });
    await context.close();
  }
  fs.writeFileSync(
    "docs/browser-results.json",
    JSON.stringify(results, null, 2),
  );
  console.log(JSON.stringify(results));
} finally {
  await browser.close();
}
