/* Test-only dependencies; the shipped site contains no JavaScript. */
const assert = require('node:assert/strict');
const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');
const axe = require('axe-core');

const base = new URL(process.env.SITE_URL || 'http://127.0.0.1:8000/');
const output = '/tmp/goswapps-web-validation/screenshots';
const widths = [320, 375, 390, 768, 1024, 1440];
const routes = ['', 'privacy.html', '404.html'];

async function assertLayout(page, label) {
  const overflow = await page.evaluate(() => {
    const viewport = document.documentElement.clientWidth;
    return [...document.querySelectorAll('body *')].filter(el => {
      if (el.closest('svg') || el.classList.contains('skip-link')) return false;
      const box = el.getBoundingClientRect();
      return box.width && (box.right > viewport + 1 || box.left < -1);
    }).map(el => `${el.tagName}.${el.className}`);
  });
  assert.deepEqual(overflow, [], `${label}: elements must fit the viewport`);
  assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `${label}: horizontal scroll`);
}

(async () => {
  await fs.mkdir(output, { recursive: true });
  const browser = await chromium.launch({
    ...(process.env.CHROMIUM_PATH ? { executablePath: process.env.CHROMIUM_PATH } : {}),
    headless: true,
  });
  let layouts = 0;
  let audits = 0;
  try {
    const context = await browser.newContext();
    const external = [];
    const failures = [];
    await context.route('**/*', route => {
      if (new URL(route.request().url()).origin !== base.origin) {
        external.push(route.request().url());
        return route.abort();
      }
      return route.continue();
    });
    const page = await context.newPage();
    page.on('pageerror', error => failures.push(error.message));
    page.on('requestfailed', request => failures.push(request.url()));
    page.on('response', response => { if (response.status() >= 400) failures.push(`${response.status()} ${response.url()}`); });

    for (const width of widths) {
      await page.setViewportSize({ width, height: 900 });
      for (const route of routes) {
        const label = `${route || 'home'} at ${width}px`;
        const response = await page.goto(new URL(route, base).href);
        assert.equal(response.status(), 200, label);
        assert.equal(await page.locator('h1').count(), 1);
        await assertLayout(page, label);
        layouts++;
        assert.equal(await page.locator('script').count(), 0, 'No site JavaScript');
        assert.equal(await page.evaluate(() => localStorage.length + sessionStorage.length), 0, 'No browser storage');
        assert.equal(await page.evaluate(() => document.cookie), '', 'No document cookies');

        if (width === 375 || width === 1440) {
          await page.screenshot({ path: path.join(output, `${route.replace('.html', '') || 'home'}-${width}.png`), fullPage: true });
          await page.addScriptTag({ content: axe.source });
          const results = await page.evaluate(async () => axe.run(document, {
            runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa', 'best-practice'] },
          }));
          assert.deepEqual(results.violations.map(v => ({ id: v.id, impact: v.impact, nodes: v.nodes.map(n => n.target) })), [], `${label}: accessibility violations`);
          audits++;
        }
      }
    }

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(base.href);
    await page.keyboard.press('Tab');
    assert.equal(await page.locator(':focus').textContent(), 'Skip to content');
    const focusStyle = await page.locator(':focus').evaluate(el => getComputedStyle(el).outlineStyle);
    assert.notEqual(focusStyle, 'none', 'Visible keyboard focus');
    await page.keyboard.press('Enter');
    assert.equal(new URL(page.url()).hash, '#main');
    await page.keyboard.press('Tab');
    assert.match(await page.locator(':focus').getAttribute('href'), /#apps$/);
    await page.keyboard.press('Enter');
    assert.equal(new URL(page.url()).hash, '#apps');
    await page.getByRole('link', { name: 'Get in touch' }).click();
    assert.equal(new URL(page.url()).hash, '#contact');
    assert((await page.locator('#contact').boundingBox()).y >= 0);
    assert.equal(await page.getByRole('link', { name: 'hello@goswapps.com' }).getAttribute('href'), 'mailto:hello@goswapps.com');
    assert.equal(await page.getByRole('link', { name: 'support@goswapps.com' }).getAttribute('href'), 'mailto:support@goswapps.com');

    // Follow every local page, asset, and fragment link without invoking email clients.
    for (const route of routes) {
      await page.goto(new URL(route, base).href);
      const links = await page.locator('a').evaluateAll(nodes => nodes.map(node => node.href));
      for (const href of new Set(links)) {
        const target = new URL(href);
        if (target.origin !== base.origin) continue;
        const response = await page.request.get(href);
        assert.equal(response.status(), 200, href);
        if (target.hash) {
          await page.goto(href);
          assert.equal(await page.locator(`[id="${target.hash.slice(1)}"]`).count(), 1, href);
        }
      }
    }

    // Increase text size independently of the viewport, preserving readable content.
    for (const route of routes) {
      await page.goto(new URL(route, base).href);
      await page.evaluate(() => {
        const elements = [...document.querySelectorAll('body *')].filter(el => !el.closest('svg'));
        const sizes = elements.map(el => parseFloat(getComputedStyle(el).fontSize));
        elements.forEach((el, i) => { el.style.fontSize = `${sizes[i] * 2}px`; });
      });
      await assertLayout(page, `${route || 'home'} at 200% text size`);
    }

    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto(base.href);
    assert.equal(await page.locator('.button').first().evaluate(el => getComputedStyle(el).transitionDuration), '0s');
    await page.emulateMedia({ media: 'print' });
    assert.equal(await page.locator('.hero-art').evaluate(el => getComputedStyle(el).display), 'none');
    assert.deepEqual(external, [], 'No external network requests');
    assert.deepEqual(failures, [], 'No failed resources or browser errors');
    assert.deepEqual(await context.cookies(), [], 'No cookies');

    const noJS = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 375, height: 812 } });
    const staticPage = await noJS.newPage();
    await staticPage.goto(base.href);
    await staticPage.getByRole('link', { name: 'Explore our apps' }).click();
    assert.equal(new URL(staticPage.url()).hash, '#apps');
    assert.equal(await staticPage.locator('.app-card').count(), 3);
    await staticPage.getByRole('link', { name: 'Website privacy' }).click();
    assert.equal(await staticPage.title(), 'Website privacy — GoSWAPPS Studios');
    await noJS.close();
    await context.close();
    console.log(`PASS: ${layouts} layouts, ${audits} axe accessibility audits, links, keyboard navigation, 200% text size, reduced motion, print styles, no-JavaScript navigation, no third-party requests, no cookies/storage, no browser errors.`);
    console.log(`Screenshots: ${output}`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
