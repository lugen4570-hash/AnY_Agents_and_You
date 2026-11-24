/* Local E2E: real Edge Function, Python owner endpoints and SQL migration.
 * PGlite supplies Postgres and a local HTTP shim stands in for Supabase gateways.
 */
import { strict as assert } from 'node:assert';
import { spawn } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { mkdtemp, mkdir, readFile, rm } from 'node:fs/promises';
import { createServer } from 'node:http';
import { createServer as createTCPServer } from 'node:net';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';

const temporary = resolve('.test-tmp');
const modules = resolve(process.env.ANY_CLOUD_TEST_MODULES || '.test-tmp/cloud-tools/node_modules');
const { PGlite } = await import(pathToFileURL(resolve(modules, '@electric-sql/pglite/dist/index.js')).href);
const deno = process.env.ANY_CLOUD_TEST_DENO || 'deno';
const root = await mkdtemp(resolve(temporary, 'cloud-e2e-'));
const db = new PGlite();
const processes = [];
const testKey = randomUUID() + randomUUID();
const store = new Map();
const notifications = [];
let gateway;

async function availablePort() {
  const sock = createTCPServer().listen(0, '127.0.0.1');
  await new Promise(resolve => sock.once('listening', resolve));
  const port = sock.address().port;
  await new Promise(resolve => sock.close(resolve));
  return port;
}

function start(executable, args, env) {
  const proc = spawn(executable, args, { env: { ...process.env, ...env }, stdio: ['ignore', 'pipe', 'pipe'] });
  proc.stdout.on('data', bytes => process.stdout.write(bytes));
  proc.stderr.on('data', bytes => process.stderr.write(bytes));
  processes.push(proc);
  return proc;
}

async function waitFor(url) {
  for (let attempts = 0; attempts < 60; attempts++) {
    try { return await fetch(url); } catch (_) { await delay(250); }
  }
  throw Error('Service did not start: ' + url);
}

async function body(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(chunk);
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}
function reply(res, payload, code = 200) {
  res.writeHead(code, { 'Content-Type': 'application/json' }).end(JSON.stringify(payload));
}

const queries = {
  any_cloud_login: ['p_provider', 'p_subject', 'p_install', 'p_label'],
  any_cloud_device: ['p_action', 'p_token', 'p_data'],
  any_cloud_qr: ['p_action', 'p_data'],
  any_cloud_sms_reserve: ['p_phone'],
};
try {
  await db.exec('create role anon; create role authenticated; create role service_role;');
  await db.exec(await readFile('supabase/migrations/202611240001_any_cloud.sql', 'utf8'));
  assert.equal((await db.query("select has_function_privilege('anon', 'public.any_cloud_device(text,text,jsonb)', 'execute') as allowed")).rows[0].allowed, false);
  gateway = createServer(async (req, res) => {
    try {
      const data = await body(req);
      const name = req.url.split('/').at(-1);
      if (req.url.startsWith('/rest/v1/rpc/') && queries[name]) {
        if (req.headers.apikey !== 'local-service') return reply(res, {}, 403);
        const keys = queries[name];
        const args = keys.map(key => key === 'p_data' ? JSON.stringify(data[key]) : data[key]);
        const { rows } = await db.query('select public.' + name + '(' + keys.map((_, i) => '$' + (i + 1)).join(',') + ') as value', args);
        return reply(res, rows[0].value);
      }
      if (req.url === '/auth/v1/otp') {
        if (!store.has(data.phone)) store.set(data.phone, randomUUID());
        return reply(res, {});
      }
      if (req.url === '/auth/v1/verify') {
        if (data.token !== '123456' || !store.has(data.phone)) return reply(res, {}, 400);
        return reply(res, { user: { id: store.get(data.phone) } });
      }
      if (req.url === '/realtime/v1/api/broadcast') {
        notifications.push(...data.messages);
        return reply(res, {});
      }
      return reply(res, {}, 404);
    } catch (error) {
      console.error(error);
      reply(res, {}, 500);
    }
  }).listen(0, '127.0.0.1');
  await new Promise(resolve => gateway.once('listening', resolve));
  const edgePort = await availablePort();
  const edge = 'http://127.0.0.1:' + edgePort + '/any-cloud';
  start(deno, ['run', '--allow-net', '--allow-env', 'supabase/functions/any-cloud/index.ts'], {
    SUPABASE_URL: 'http://127.0.0.1:' + gateway.address().port,
    SUPABASE_SERVICE_ROLE_KEY: 'local-service', SUPABASE_ANON_KEY: 'local-anon',
    ANY_TEST_KEY: testKey, ANY_TEST_FIXTURES: '1', ANY_TEST_SMS_ENABLED: '1', ANY_TEST_PORT: String(edgePort),
  });
  await waitFor(edge);

  async function client(name) {
    const port = await availablePort();
    const dataDir = resolve(root, name);
    await mkdir(dataDir);
    start(process.env.ANY_CLOUD_TEST_PYTHON || 'python', ['roundtable.py'], {
      PYTHONUTF8: '1', ROUNDTABLE_PORT: String(port), ROUNDTABLE_LOG_DIR: dataDir,
      ROUNDTABLE_NO_BROWSER: '1', ANY_TEST_CLOUD_URL: edge, ANY_TEST_CLOUD_KEY: testKey,
    });
    const base = 'http://127.0.0.1:' + port;
    const html = await (await waitFor(base)).text();
    const token = html.match(/name="rt-token" content="([^"]+)"/)[1];
    return {
      base, dataDir,
      async call(action, data = {}) {
        return await (await fetch(base + '/api/cloud/account', {
          method: 'POST', headers: { 'Content-Type': 'application/json', 'X-RT-Token': token },
          body: JSON.stringify({ action, ...data }),
        })).json();
      },
    };
  }

  async function fixture(action, data) {
    return await (await fetch(edge, {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Any-Test-Key': testKey },
      body: JSON.stringify({ ...data, action }),
    })).json();
  }

  const [first, second, third] = await Promise.all([client('a'), client('b'), client('c')]);
  const consent = { consent: '2026-11-test' };
  assert.equal((await first.call('capabilities')).wechat, false);
  assert.equal((await first.call('session')).error, 'signed_out');
  assert.equal((await first.call('qr_create')).error, 'channel_unavailable');
  const expired = await first.call('qr_create', consent);
  await db.exec("update any_cloud.qr set expires_at = now() - interval '1 second'");
  assert.equal((await first.call('qr_poll', expired)).status, 'expired');

  async function login(client, subject) {
    const created = await client.call('qr_create', consent);
    assert.ok(created.attempt);
    assert.equal(created.key, undefined);
    assert.equal((await client.call('qr_poll', created)).status, 'pending');
    const persisted = JSON.parse(await readFile(resolve(client.dataDir, 'cloud-account.json')));
    const { rows } = await db.query('select id from any_cloud.qr where installation = $1 order by expires_at desc', [persisted.installation]);
    const id = rows[0].id;
    const { approval } = await fixture('test_scan', { id, subject });
    assert.ok(approval);
    assert.equal((await client.call('qr_poll', created)).status, 'scanned');
    assert.equal((await fixture('test_approve', { id, approval: 'invalid' })).error, 'invalid_request');
    assert.equal((await fixture('test_approve', { id, approval })).status, 'confirmed');
    const result = await client.call('qr_poll', created);
    assert.equal(result.token, undefined);
    return result;
  }

  const a = await login(first, 'account-a');
  assert.ok(a.signed_in);
  assert.ok((await first.call('rename', { name: '开发机' })).ok);
  const empty = await first.call('preferences');
  const initial = await first.call('sync', { version: empty.version, preferences: { theme: 'dark', language: 'zh-CN' } });
  assert.equal(initial.version, 1);
  const b = await login(second, 'account-a');
  assert.equal(b.account, a.account);
  assert.deepEqual(await second.call('preferences'), initial);
  const devices = await first.call('devices');
  assert.equal(devices.devices[0].name, '开发机');
  assert.equal(devices.devices.length, 2);

  await db.query('update any_cloud.accounts set device_limit = 2 where id = $1', [a.account]);
  assert.equal((await login(third, 'account-a')).error, 'device_limit');
  const c = await login(third, 'account-b');
  assert.ok(c.signed_in && c.account !== a.account);
  assert.deepEqual(await third.call('preferences'), { version: 0, preferences: {} });

  const next = await first.call('sync', { version: 1, preferences: { theme: 'light' } });
  assert.equal(next.version, 2);
  const conflict = await second.call('sync', { version: 1, preferences: { theme: 'system' } });
  assert.equal(conflict.error, 'conflict');
  assert.equal(conflict.preferences.theme, 'light');
  assert.equal((await second.call('sync', { version: 2, preferences: { language: 'en' } })).preferences.theme, 'light');
  assert.equal((await first.call('sync', { version: 3, preferences: { token: 'dummy' } })).error, 'invalid_request');

  const otherDevice = devices.devices.find(row => !row.current).id;
  const targetSession = await second.call('session');
  assert.ok((await third.call('revoke', { id: otherDevice })).ok);
  assert.equal((await second.call('session')).account, a.account);
  assert.ok((await first.call('revoke', { id: otherDevice })).ok);
  assert.equal(notifications.at(-1).topic, targetSession.topic);
  assert.equal((await second.call('session')).error, 'signed_out');
  assert.equal((await second.call('capabilities')).signed_in, false);
  assert.equal((await fetch(second.base + '/api/server/info')).status, 200);
  assert.equal((await second.call('preferences')).error, 'signed_out');

  const phone = '+15555550101';
  assert.ok((await first.call('sms_send', { ...consent, phone })).ok);
  assert.equal((await first.call('sms_send', { ...consent, phone })).error, 'sms_wait');
  assert.equal((await first.call('sms_bind', { ...consent, phone, code: '654321' })).error, 'invalid_code');
  assert.ok((await first.call('sms_bind', { ...consent, phone, code: '123456' })).ok);
  assert.equal((await first.call('session')).phone_bound, true);
  assert.equal((await second.call('sms_verify', { ...consent, phone, code: '123456' })).account, a.account);
  console.log('Cloud E2E passed: QR confirmation, two clients, preference conflict/recovery, cap, revocation, isolation and SMS binding');

  if (process.env.ANY_CLOUD_TEST_CHROME) {
    const { chromium } = await import(pathToFileURL(resolve(modules, 'playwright-core/index.mjs')).href);
    const browser = await chromium.launch({ executablePath: process.env.ANY_CLOUD_TEST_CHROME });
    try {
      const pages = await Promise.all([browser.newPage(), browser.newPage()]);
      const [pageA, pageB] = pages;
      const apiPath = '**/api/cloud/account';
      for (const [index, page] of pages.entries()) {
        await page.goto([first, second][index].base);
        await page.locator('#openSettingsBtn').click();
        await page.locator('[data-settings-tab="cloud"]').click();
        await page.locator('[data-enable-sync]').click();
        await page.getByText('已恢复云端偏好。').waitFor({ state: 'visible' });
        assert.equal(await page.locator('html').getAttribute('data-theme'), 'light');
      }
      await pageB.route(apiPath, route => route.abort());
      await pageB.locator('[data-settings-tab="general"]').click();
      await pageB.locator('[data-theme-choice="dark"]').click();
      await pageA.locator('[data-settings-tab="general"]').click();
      await pageA.locator('[data-theme-choice="system"]').click();
      for (let attempts = 0; attempts < 40; attempts++) {
        if ((await first.call('preferences')).preferences.theme === 'system') break;
        await delay(150);
      }
      assert.equal((await first.call('preferences')).preferences.theme, 'system');
      await pageB.unroute(apiPath);
      await pageB.locator('[data-settings-tab="cloud"]').click();
      await pageB.evaluate(() => window.dispatchEvent(new Event('online')));
      await pageB.locator('[data-keep]').click();
      await pageB.getByText('偏好已同步。').waitFor({ state: 'visible' });
      assert.equal((await first.call('preferences')).preferences.theme, 'dark');
      await pageA.locator('[data-settings-tab="cloud"]').click();
      await pageA.locator('[data-devices] button').click();
      await pageA.getByText('设备已下线。').waitFor({ state: 'visible' });
      await pageB.evaluate(() => window.dispatchEvent(new Event('online')));
      await pageB.getByText('此设备的云账号已退出，可以继续使用本地功能。').waitFor({ state: 'visible' });

      await pageB.locator('[data-channel="sms"]').click();
      await pageB.locator('[data-send-code]').click();
      await pageB.getByText('请先阅读并勾选用户协议和隐私政策，再继续登录。').waitFor({ state: 'visible' });
      await pageB.locator('[data-consent]').check();
      await pageB.locator('[name="phone"]').fill('+15555550102');
      await pageB.locator('[data-send-code]').click();
      await pageB.getByRole('button', { name: /秒后重发/ }).waitFor({ state: 'visible' });
      assert.ok(await pageB.locator('[data-send-code]').isDisabled());
      await pageB.locator('[name="code"]').fill('123456');
      await pageB.locator('[data-sms-form] [type="submit"]').click();
      await pageB.getByText('已登录 1 / 3 台设备').waitFor({ state: 'visible' });
      console.log('Browser E2E passed: opt-in, recovery, offline edit conflict and retry, remote sign-out, consent, SMS countdown');
    } finally {
      await browser.close();
    }
  }
} finally {
  for (const proc of processes) proc.kill();
  gateway?.closeAllConnections();
  gateway?.close();
  await db.close();
  await rm(root, { recursive: true, force: true, maxRetries: 3 }).catch(console.error);
}
