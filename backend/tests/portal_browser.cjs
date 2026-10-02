'use strict';

const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const { chromium } = require('playwright');

const baseURL = process.env.PORTAL_BASE_URL;
const key = process.env.BACKEND_API_KEY;
const fixture = process.env.PORTAL_FIXTURE ? JSON.parse(process.env.PORTAL_FIXTURE) : null;
const screenshotDir = process.env.PORTAL_SCREENSHOT_DIR;

async function run() {
  const browser = await chromium.launch({ headless: true, ...(process.env.PLAYWRIGHT_CHANNEL ? { channel: process.env.PLAYWRIGHT_CHANNEL } : {}) });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, timezoneId: 'Asia/Ho_Chi_Minh' });
  const page = await context.newPage();
  page.setDefaultTimeout(20000);
  const uncaught = [];
  const requests = [];
  page.on('pageerror', error => uncaught.push(error.message));
  page.on('request', request => { if (request.url().includes('/api/v1/')) requests.push({ method: request.method(), url: request.url() }); });
  const editor = page.locator('#editor-dialog');
  const field = name => editor.locator(`[name="${name}"]`);
  const save = () => page.locator('#save-button').click();
  const waitLoaded = async () => {
    await page.waitForFunction(() => !App.loading && !App.opening);
    assert.equal(await page.locator('#page-error').isVisible(), false, 'Unexpected page error');
  };
  const nav = async view => { await page.locator(`[data-view="${view}"]`).click(); await waitLoaded(); };
  const row = id => page.locator(`tr[data-record-id="${id}"]`);
  const closeEditor = () => editor.locator('[data-close]').first().click();
  const responseAfter = async (method, endpoint, action, expected) => {
    const waiting = page.waitForResponse(response => response.request().method() === method && new URL(response.url()).pathname === `/api/v1${endpoint}`);
    await action();
    const response = await waiting;
    assert.equal(response.status(), expected, `Unexpected HTTP status: ${method} ${endpoint}`);
    await page.waitForFunction(() => !App.pending);
    return response.status() === 204 ? null : (await response.json()).data;
  };
  const create = async () => {
    await page.locator('#create-button').click();
    await editor.waitFor({ state: 'visible' });
  };
  const confirm = async (action, id, expected, method = 'DELETE', endpoint) => {
    await row(id).locator(`[data-action="${action}"]`).click();
    await page.locator('#confirm-dialog').waitFor({ state: 'visible' });
    return responseAfter(method, endpoint, () => page.locator('#confirm-button').click(), expected);
  };
  const snapshot = async name => {
    if (!screenshotDir) return;
    fs.mkdirSync(screenshotDir, { recursive: true });
    await page.screenshot({ path: path.join(screenshotDir, `${name}.png`), fullPage: true });
  };
  const checkWidth = async () => {
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), true, 'Page overflows horizontally');
  };

  try {
    await page.goto(`${baseURL}portal/`, { waitUntil: 'networkidle' });
    assert.equal(await page.locator('h1').textContent(), 'Người dùng');
    assert.equal(await page.locator('#create-button').isDisabled(), true);
    await page.locator('#connect-button').click();
    await page.locator('#api-key').fill('invalid_key_'.repeat(4));
    await responseAfter('GET', '/health', () => page.locator('#connection-form button[type="submit"]').click(), 401);
    assert.equal(await page.locator('#connection-error').isVisible(), true);
    assert.equal(await page.locator('#create-button').isDisabled(), true);
    await page.locator('#api-key').fill(key);
    await responseAfter('GET', '/health', () => page.locator('#connection-form button[type="submit"]').click(), 200);
    await waitLoaded();
    assert.equal(await page.locator('#connection-status').textContent(), 'Đã kết nối');
    assert.equal(await page.locator('#api-key').inputValue(), '');
    assert.equal(await page.evaluate(secret => Object.values(localStorage).concat(Object.values(sessionStorage), [document.cookie]).some(value => String(value).includes(secret)), key), false);
    assert.equal(requests.some(request => request.url.includes('key=')), false);

    if (!fixture) {
      await page.locator('#search').fill('unfindable_readonly_portal_2e5b3a7f');
      assert.match(await page.locator('#table-body').textContent(), /Không có bản ghi/);
      await page.locator('#search').fill('');
      await create();
      await field('user_code').fill('readonly_validation');
      await field('full_name').fill('   ');
      const before = requests.filter(request => request.method === 'POST').length;
      await save();
      assert.equal(await field('full_name').evaluate(input => input.validity.valueMissing), true);
      assert.equal(requests.filter(request => request.method === 'POST').length, before);
      await field('full_name').fill('Validation only');
      await field('email').fill('person@local');
      await responseAfter('POST', '/users', save, 400);
      assert.equal(await field('email').getAttribute('aria-invalid'), 'true');
      assert.equal(await field('full_name').inputValue(), 'Validation only');
      await closeEditor();
      for (const view of ['devices', 'sessions', 'logs', 'users']) await nav(view);
      await checkWidth();
      await snapshot('portal-desktop');
      await context.setOffline(true);
      await page.locator('#refresh-button').click();
      await page.waitForFunction(() => !App.loading);
      assert.equal(await page.locator('#page-error').isVisible(), true);
      assert.equal(await page.locator('tr[data-record-id]').count(), 0);
      await context.setOffline(false);
      await page.locator('#refresh-button').click();
      await waitLoaded();
    } else {
      const user = fixture.user;
      const second = fixture.second_user;
      await page.locator('#search').fill(second.user_code);
      await confirm('delete', second.id, 204, 'DELETE', `/users/${second.id}`);
      await waitLoaded();
      await page.locator('#search').fill('');
      await create();
      await field('user_code').fill(user.user_code);
      await field('full_name').fill('Portal duplicate');
      await responseAfter('POST', '/users', save, 409);
      assert.match(await page.locator('#editor-error').textContent(), /đã tồn tại/);
      assert.equal(await field('user_code').inputValue(), user.user_code);
      const hostileName = 'Portal <img src=x onerror="window.__xss=1">';
      await field('user_code').fill(second.user_code);
      await field('full_name').fill(hostileName);
      await field('department').fill(fixture.department);
      const before = requests.filter(request => request.method === 'POST' && request.url.endsWith('/users')).length;
      const created = await responseAfter('POST', '/users', () => page.locator('#save-button').evaluate(button => { button.click(); button.click(); }), 201);
      await waitLoaded();
      assert.equal(requests.filter(request => request.method === 'POST' && request.url.endsWith('/users')).length, before + 1);
      assert.match(await row(created.id).textContent(), /Portal <img/);
      assert.equal(await row(created.id).locator('img').count(), 0);
      assert.equal(await page.evaluate(() => window.__xss), undefined);
      await row(created.id).locator('[data-action="edit"]').click();
      await editor.waitFor({ state: 'visible' });
      await field('full_name').fill('Portal User Updated');
      await field('phone').fill('0900000000');
      const updated = await responseAfter('PATCH', `/users/${created.id}`, save, 200);
      assert.equal(updated.phone, '0900000000');
      await waitLoaded();

      await nav('devices');
      await page.locator('[name="device_code"]').fill(fixture.device.device_code);
      await page.locator('#apply-filters').click();
      await waitLoaded();
      await confirm('delete', fixture.device.id, 204, 'DELETE', `/devices/${fixture.device.id}`);
      await waitLoaded();
      await create();
      await field('device_code').fill(fixture.device.device_code);
      await field('name').fill('Portal Device');
      const device = await responseAfter('POST', '/devices', save, 201);
      await page.locator('#detail-dialog').waitFor({ state: 'visible' });
      assert.equal((await page.locator('.secret-token').textContent()).length, 64);
      assert.equal(await page.locator('#copy-token').isVisible(), true);
      assert.equal(await page.locator('#detail-content').textContent().then(text => text.includes('api_key_hash')), false);
      await page.locator('#detail-dialog [data-close]').first().click();
      assert.equal(await page.locator('.secret-token').count(), 0);
      await waitLoaded();
      await row(device.id).locator('[data-action="edit"]').click();
      await editor.waitFor({ state: 'visible' });
      const patchesBefore = requests.filter(request => request.method === 'PATCH').length;
      await save();
      assert.equal(requests.filter(request => request.method === 'PATCH').length, patchesBefore);
      assert.match(await page.locator('#toast').textContent(), /Không có thay đổi/);
      await field('settings.threshold').fill('81');
      await field('settings.doorDuration').fill('4');
      await field('settings.liveness').uncheck();
      await field('status').selectOption('online');
      const changedDevice = await responseAfter('PATCH', `/devices/${device.id}`, save, 200);
      assert.deepEqual(changedDevice.settings, { threshold: 81, doorDuration: 4, liveness: false });
      await waitLoaded();

      await nav('sessions');
      await create();
      await field('user_id').selectOption(user.id);
      await field('device_id').selectOption(device.id);
      const session = await responseAfter('POST', '/registration-sessions', save, 201);
      await waitLoaded();
      await confirm('completed', session.id, 409, 'PATCH', `/registration-sessions/${session.id}`);
      assert.match(await page.locator('#confirm-error').textContent(), /vector/);
      await page.locator('#confirm-dialog [data-close]').first().click();
      await row(session.id).locator('[data-action="embedding"]').click();
      await editor.waitFor({ state: 'visible' });
      await field('model_name').fill('portal-integration');
      await field('model_version').fill('1');
      await field('dimension').fill('3');
      await field('embedding_data').fill('[0.1, 0.2]');
      const putsBefore = requests.filter(request => request.method === 'PUT').length;
      await save();
      assert.match(await page.locator('#editor-error').textContent(), /Số chiều/);
      assert.equal(requests.filter(request => request.method === 'PUT').length, putsBefore);
      await field('embedding_data').fill('[0.1, 0.2, 0.3]');
      await responseAfter('PUT', `/users/${user.id}/face-embedding`, save, 200);
      await waitLoaded();
      await confirm('completed', session.id, 200, 'PATCH', `/registration-sessions/${session.id}`);
      await waitLoaded();
      assert.match(await row(session.id).textContent(), /Hoàn tất/);

      await nav('logs');
      await create();
      await field('id').fill(fixture.log_id);
      await field('device_id').selectOption(device.id);
      await field('user_id').selectOption(user.id);
      await field('result').selectOption('granted');
      await field('confidence').fill('99.5');
      const log = await responseAfter('POST', '/access-logs', save, 201);
      await waitLoaded();
      assert.equal(await row(log.id).locator('[data-action="delete"]').count(), 0);
      await create();
      await field('id').fill(log.id);
      await field('device_id').selectOption(device.id);
      await field('user_id').selectOption(user.id);
      await field('result').selectOption('granted');
      await field('confidence').fill('99.5');
      await field('access_time').fill(await page.evaluate(value => localDateInput(value), log.access_time));
      await responseAfter('POST', '/access-logs', save, 200);
      assert.match(await page.locator('#toast').textContent(), /không tạo bản ghi trùng/);
      await waitLoaded();
      await nav('users');
      await confirm('delete', user.id, 409, 'DELETE', `/users/${user.id}`);
      assert.equal(await page.locator('#confirm-error').isVisible(), true);
      await page.locator('#confirm-dialog [data-close]').first().click();
      assert.equal(await row(user.id).count(), 1);
      await snapshot('portal-write-desktop');
    }

    await page.setViewportSize({ width: 390, height: 844 });
    await nav('users');
    await checkWidth();
    const headingOverlap = await page.evaluate(() => {
      const title = document.querySelector('h1').getBoundingClientRect();
      const buttons = document.querySelector('.page-actions').getBoundingClientRect();
      return title.right > buttons.left && title.bottom > buttons.top && buttons.bottom > title.top;
    });
    assert.equal(headingOverlap, false);
    await snapshot(fixture ? 'portal-write-mobile' : 'portal-mobile');
    await create();
    const dialogFits = await editor.evaluate(dialog => {
      const rect = dialog.getBoundingClientRect();
      return rect.left >= 0 && rect.right <= innerWidth && rect.top >= 0 && rect.bottom <= innerHeight;
    });
    assert.equal(dialogFits, true);
    await snapshot(fixture ? 'portal-write-mobile-form' : 'portal-mobile-form');
    await closeEditor();
    await page.locator('#disconnect-button').click();
    assert.equal(await page.locator('tr[data-record-id]').count(), 0);
    assert.equal(await page.locator('#create-button').isDisabled(), true);
    assert.equal(await page.evaluate(() => Api.key), '');
    assert.deepEqual(uncaught, []);
    console.log(fixture ? 'Real portal write workflows passed.' : 'Real portal readonly, validation, auth, offline and responsive checks passed.');
  } finally {
    await context.setOffline(false);
    await browser.close();
  }
}
run().catch(error => {
  const message = String(error.stack || error).split(key || '__unused_secret__').join('[redacted]');
  console.error(message);
  process.exitCode = 1;
});
