import { test, expect } from "@playwright/test";

const BASE = "http://localhost:3000";

test.describe("RatingGuard 全功能测试", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");
  });

  /* ───── 1. 页面加载 ───── */
  test("1-页面标题和头部导航", async ({ page }) => {
    await expect(page).toHaveTitle(/RatingGuard/);
    await expect(page.locator("h1")).toContainText("RatingGuard");
    await expect(page.locator("text=AI 差评挽回特工")).toBeVisible();
    await expect(page.locator("text=RG")).toBeVisible();
    await expect(page.locator("text=System Online")).toBeVisible();
  });

  /* ───── 2. 输入模式切换 ───── */
  test("2-输入模式切换: 抓取 ↔ 手动输入", async ({ page }) => {
    // 默认是抓取模式
    await expect(page.locator('input[placeholder*="商品 URL"]')).toBeVisible();
    await expect(page.locator("text=暂无差评数据")).toBeVisible();

    // 切换到手动输入
    await page.click("text=✏️ 手动输入");
    await expect(page.locator('textarea[placeholder*="差评"]')).toBeVisible();
    await expect(page.getByRole("button", { name: "开始分析" })).toBeVisible();

    // 切回抓取
    await page.click("text=🔗 抓取");
    await expect(page.locator('input[placeholder*="商品 URL"]')).toBeVisible();
  });

  /* ───── 3. 手动输入 → 流式分析 → 完整结果 ───── */
  test("3-手动输入差评并查看完整分析结果", async ({ page }) => {
    await page.click("text=✏️ 手动输入");

    await page.fill(
      'textarea[placeholder*="差评"]',
      "The product quality is terrible, arrived with scratches and took 3 weeks to deliver. Very disappointed."
    );
    await page.fill('input[placeholder="可选"]', "TestCustomer");
    await page.selectOption("select", "US");

    // 点击开始分析
    await page.click("text=开始分析");
    await expect(page.locator("text=分析中…")).toBeVisible({ timeout: 3000 });

    // 等待分析结果出现（最多 60s）
    await expect(page.locator("text=差评分析")).toBeVisible({ timeout: 60000 });
    await expect(page.locator("text=挽回邮件")).toBeVisible({ timeout: 5000 });

    // 验证分析卡片有实际内容
    await expect(page.locator("text=根因分类")).toBeVisible();
    await expect(page.locator("text=愤怒指数")).toBeVisible();
    await expect(page.locator("text=沟通风格")).toBeVisible();

    // 验证邮件不是原始 JSON（之前修过的 bug）
    const main = page.locator("main");
    await expect(main).not.toContainText('"reason_category"', { timeout: 5000 });

    // 验证操作按钮出现
    await expect(page.locator("text=Copy to Clipboard")).toBeVisible({ timeout: 5000 });
    await expect(page.locator("text=Send Email")).toBeVisible({ timeout: 5000 });
  });

  /* ───── 4. Copy 按钮 ───── */
  test("4-Copy to Clipboard 按钮", async ({ page }) => {
    await page.click("text=✏️ 手动输入");
    await page.fill(
      'textarea[placeholder*="差评"]',
      "Item arrived broken. Packaging was poor."
    );
    await page.click("text=开始分析");

    await expect(page.locator("text=Copy to Clipboard")).toBeVisible({ timeout: 60000 });
    await page.click("text=Copy to Clipboard");
    await expect(page.locator("text=Copied!")).toBeVisible({ timeout: 3000 });
  });

  /* ───── 5. Send 按钮 ───── */
  test("5-Send Email 按钮模拟发送", async ({ page }) => {
    await page.click("text=✏️ 手动输入");
    await page.fill(
      'textarea[placeholder*="差评"]',
      "Color is different from the photo. Not happy."
    );
    await page.click("text=开始分析");

    await expect(page.locator("text=Send Email")).toBeVisible({ timeout: 60000 });
    await page.click("text=Send Email");
    await expect(page.locator("text=Sent Successfully!")).toBeVisible({ timeout: 3000 });
  });

  /* ───── 6. 桌面双栏布局 1280px ───── */
  test("6-桌面双栏布局", async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 800 });
    const aside = page.locator("aside");
    const main = page.locator("main");
    await expect(aside).toBeVisible();
    await expect(main).toBeVisible();

    const asideBox = await aside.boundingBox();
    const mainBox = await main.boundingBox();
    expect(asideBox).not.toBeNull();
    expect(mainBox).not.toBeNull();
    expect(asideBox!.x).toBeLessThan(mainBox!.x);
  });

  /* ───── 7. 空状态 ───── */
  test("7-抓取模式空状态", async ({ page }) => {
    await expect(page.locator("text=暂无差评数据")).toBeVisible();
  });

  /* ───── 8. 评分星星交互 ───── */
  test("8-评分星星点击", async ({ page }) => {
    await page.click("text=✏️ 手动输入");
    const stars = page.locator("button:has-text('★')");
    expect(await stars.count()).toBe(5);
    await stars.nth(2).click(); // 选 3 星
    const activeStars = page.locator("button.text-amber-400");
    expect(await activeStars.count()).toBe(3);
  });

  /* ───── 9. 国家下拉框 — 11 种语言 ───── */
  test("9-国家下拉框包含至少 11 种语言", async ({ page }) => {
    await page.click("text=✏️ 手动输入");
    const select = page.locator("select");
    const options = await select.locator("option").allTextContents();
    expect(options.length).toBeGreaterThanOrEqual(11);
    expect(options.some((o) => o.includes("美国"))).toBeTruthy();
    expect(options.some((o) => o.includes("日本"))).toBeTruthy();
    expect(options.some((o) => o.includes("德国"))).toBeTruthy();
  });
});
