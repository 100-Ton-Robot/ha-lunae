// Redraws the README images in ../../images from a running Home Assistant with two Lunae entries, named
// "Cairo Bus Stop" (map location) and "Geocentric" (centre of the Earth). Values are live, so each run differs.
//
//   HA_URL=https://ha.example.com HA_DASHBOARD=lunae-test HA_TOKEN_FILE=token npm run screenshots
//
// HA_DASHBOARD must be a storage-mode dashboard the script may write to: it adds (or replaces) the view in
// view.json and leaves the dashboard's other views alone. The token needs admin rights to save the dashboard.
const fs = require("node:fs");
const path = require("node:path");
const { test, expect } = require("@playwright/test");

const DASHBOARD = process.env.HA_DASHBOARD;
const IMAGES = process.env.IMAGES_DIR || path.join(__dirname, "..", "..", "images");
const VIEW = require("./view.json");
// One image per section of view.json, in order.
const SHOTS = ["cairo_position.png", "cairo_phase_size.png", "geocentric.png"];

function readToken() {
  if (!process.env.HA_TOKEN_FILE) throw new Error("Set HA_TOKEN_FILE to a file holding a long-lived access token");
  const token = fs.readFileSync(process.env.HA_TOKEN_FILE, "utf8").trim();
  if (!token) throw new Error(`${process.env.HA_TOKEN_FILE} is empty`);
  return token;
}

async function logIn(page) {
  await page.addInitScript(token => {
    if (localStorage.getItem("hassTokens")) return;
    localStorage.setItem("hassTokens", JSON.stringify({
      hassUrl: location.origin,
      clientId: `${location.origin}/`,
      access_token: token,
      token_type: "Bearer",
      refresh_token: "",
      expires_in: 31536000,
      expires: Date.now() + 31536000000,
    }));
  }, readToken());
}

async function waitForHass(page) {
  await page.waitForFunction(() => document.querySelector("home-assistant")?.hass?.connected, null, { timeout: 30_000 });
}

test.beforeAll(() => {
  if (!DASHBOARD) throw new Error("Set HA_DASHBOARD to the url_path of a storage-mode dashboard, e.g. lunae-test");
  if (VIEW.sections.length !== SHOTS.length) throw new Error("view.json and SHOTS disagree on the number of sections");
  fs.mkdirSync(IMAGES, { recursive: true });
});

test("screenshots: one per section", async ({ page }) => {
  await logIn(page);
  await page.goto("/");
  await waitForHass(page);

  // Every entity the view shows must exist and have a value, or the pictures would show errors.
  const missing = await page.evaluate(view => {
    const states = document.querySelector("home-assistant").hass.states;
    const ids = JSON.stringify(view).match(/(?:sensor|binary_sensor)\.lunae_[a-z0-9_]+/g);
    return [...new Set(ids)].filter(id => !states[id] || ["unknown", "unavailable"].includes(states[id].state));
  }, VIEW);
  expect(missing, "entities missing or without a value").toEqual([]);

  await page.evaluate(async ({ dashboard, view }) => {
    const hass = document.querySelector("home-assistant").hass;
    const config = await hass.callWS({ type: "lovelace/config", url_path: dashboard });
    config.views = (config.views || []).filter(v => v.path !== view.path).concat([view]);
    await hass.callWS({ type: "lovelace/config/save", url_path: dashboard, config });
  }, { dashboard: DASHBOARD, view: VIEW });

  await page.goto(`/${DASHBOARD}/${VIEW.path}`);
  await waitForHass(page);
  const sections = page.locator("hui-sections-view hui-section");
  await expect(sections).toHaveCount(SHOTS.length, { timeout: 30_000 });
  // History graphs draw last; give them time after the chart elements appear.
  await expect(page.locator("hui-history-graph-card ha-chart-base")).toHaveCount(2, { timeout: 30_000 });
  await page.waitForTimeout(3000);

  for (const [i, name] of SHOTS.entries()) {
    await sections.nth(i).screenshot({ path: path.join(IMAGES, name), animations: "disabled" });
  }
});
