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
  await expect(dialog.getByRole("button", { name: /^Ouvir / })).toBeVisible();
  await expect(dialog.locator("section").last().getByRole("button").first()).toBeVisible();
});

test("answer survives reload and reattaches (live, E2E_LIVE=1)", async ({ page, request }) => {
  test.skip(!process.env.E2E_LIVE, "usa o agente real");
  test.setTimeout(240_000);
  await page.goto("/");
  await page.getByPlaceholder("Escreva o que está no seu coração...").fill("Teste E2E: um versículo curto sobre esperança.");
  await page.getByPlaceholder("Escreva o que está no seu coração...").press("Enter");
  await expect(page.getByText("Teste E2E: um versículo curto sobre esperança.")).toBeVisible();
  await page.waitForTimeout(3000);
  await page.reload();
  await page.getByRole("button", { name: "Teste E2E: um versículo curto sobre esperança." }).click();
  await expect(page.locator("article.resposta figure, article.resposta blockquote").first()).toBeVisible({ timeout: 200_000 });
  const conversations = (await (await request.get("http://127.0.0.1:8000/api/v1/conversations")).json()).items as { id: string; title: string }[];
  for (const c of conversations.filter((c) => c.title.startsWith("Teste E2E:"))) {
    await request.delete(`http://127.0.0.1:8000/api/v1/conversations/${c.id}`);
  }
});

test("diary: create a prayer, mark it answered, then delete it", async ({ page }) => {
  const title = `Teste E2E oração ${Date.now()}`;
  await page.goto("/diario");
  await expect(page.getByRole("heading", { name: "Diário espiritual" })).toBeVisible();
  await page.getByRole("tab", { name: "Orações" }).click();
  await page.getByLabel("Novo pedido de oração").fill(title);
  await page.getByRole("button", { name: "Guardar pedido" }).click();
  const card = page.getByRole("listitem").filter({ hasText: title });
  await card.getByRole("button", { name: "Marcar como respondida" }).click();
  await card.getByLabel("Como Deus respondeu? (opcional)").fill("Resposta de teste");
  await card.getByRole("button", { name: "Glória a Deus, guardar" }).click();
  await expect(page.getByRole("heading", { name: "Respondidas" })).toBeVisible();
  await expect(card.getByText(/respondida em/)).toBeVisible();
  await card.getByRole("button", { name: "Apagar" }).click();
  await card.getByRole("button", { name: "Sim, apagar" }).click();
  await expect(page.getByText(title)).toHaveCount(0);
});

test("verse drawer saves and removes a personal note", async ({ page }) => {
  await page.goto("/sobre");
  await page.locator("figcaption button").first().click();
  const dialog = page.getByRole("dialog");
  const note = dialog.getByLabel(/Minha anotação sobre/);
  await expect(note).toBeVisible();
  const before = await note.inputValue();
  test.skip(before !== "", "já existe anotação real neste versículo; não mexer");
  await note.fill("Anotação de teste E2E");
  await dialog.getByRole("button", { name: "Salvar anotação" }).click();
  await expect(dialog.getByText("Guardada no Diário.")).toBeVisible();
  await dialog.getByRole("button", { name: "Apagar" }).click();
  await expect(note).toHaveValue("");
});

test("plans: start a theme plan, mark today as read, then end it", async ({ page, request }) => {
  const active = (await (await request.get("http://127.0.0.1:8000/api/v1/plans")).json()).items as { code: string }[];
  test.skip(active.some((p) => p.code === "familia"), "plano Família real em andamento; não mexer");
  await page.goto("/planos");
  const card = page.getByRole("listitem").filter({ has: page.getByRole("heading", { name: "Família" }) }).last();
  await card.getByRole("button", { name: "Começar hoje" }).click();
  const plan = page.getByRole("listitem").filter({ has: page.getByRole("heading", { name: "Família", level: 2 }) });
  await expect(plan.getByText("Leitura de hoje · dia 1")).toBeVisible();
  await expect(plan.getByText("Gn 2:18-25").first()).toBeVisible();
  await plan.getByRole("button", { name: "Marcar como lida" }).click();
  await expect(plan.getByText("1 de 7 dias lidos (14%)")).toBeVisible();
  await plan.getByRole("button", { name: "Encerrar plano" }).click();
  await plan.getByRole("button", { name: "Sim" }).click();
  await expect(page.getByRole("heading", { name: "Família", level: 2 })).toHaveCount(0);
});

test("print page of a conversation without cards renders cover and sources only", async ({ page, request }) => {
  const { id } = await (await request.post("http://127.0.0.1:8000/api/v1/conversations")).json();
  try {
    await page.goto(`/imprimir/conversa/${id}`);
    await expect(page.locator(".capa-titulo")).toHaveText("Nova conversa");
    await expect(page.getByRole("heading", { name: "Fontes e licenças" })).toBeVisible();
    await expect(page.locator("#aprofundamento")).toHaveCount(0);
    await expect(page.locator("#pessoas-lugares")).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Baixar PDF" })).toBeVisible();
  } finally {
    await request.delete(`http://127.0.0.1:8000/api/v1/conversations/${id}`);
  }
});

test("shortcuts: Ctrl+J finds a verse, Alt+F toggles focus mode", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Modo foco" })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await page.keyboard.press("Control+j");
  await expect(page.getByLabel("Ir para versículo")).toBeFocused();
  await page.keyboard.type("João 3:16");
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog").getByRole("heading", { name: "Jo 3:16" })).toBeVisible();
  await page.keyboard.press("Escape");
  await page.getByLabel("Ir para versículo").fill("Jo 3:99");
  await page.getByLabel("Ir para versículo").press("Enter");
  await expect(page.getByText("Não encontrei essa referência.")).toBeVisible();
  await page.keyboard.press("Alt+f");
  await expect(page.getByRole("navigation", { name: "Conversas" })).toBeHidden();
  await page.keyboard.press("Alt+f");
  await expect(page.getByRole("navigation", { name: "Conversas" })).toBeVisible();
});
