import { expect, test } from "@playwright/test";

test("chat shell shows sidebar, composer and word-for-me button", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "+ Nova conversa" })).toBeVisible();
  await expect(page.getByRole("link", { name: "🧠 Memória" })).toBeVisible();
  await expect(page.getByPlaceholder("Escreva o que está no seu coração...")).toBeVisible();
  await expect(page.getByRole("button", { name: "✨ Uma palavra pra mim" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sobre o que você quer conversar hoje?" })).toBeVisible();
});

test("memory page shows list or empty state", async ({ page }) => {
  await page.goto("/memoria");
  await expect(page.getByRole("heading", { name: "Memória" })).toBeVisible();
  await expect(
    page.getByText("Ainda não guardei nada sobre você.", { exact: false }).or(page.getByRole("button", { name: "Apagar" }).first()),
  ).toBeVisible();
});

test("about page demo card opens popup with translations, greek and cross references", async ({ page }) => {
  await page.goto("/sobre");
  await page.locator("figcaption button").first().click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("tab", { name: "ACF" })).toBeVisible();
  await expect(dialog.getByText(/^G\d{4}/).first()).toBeVisible();
  await expect(dialog.getByRole("heading", { name: "Passagens ligadas" })).toBeVisible();
  await expect(dialog.locator("section").last().getByRole("button").first()).toBeVisible();
});
