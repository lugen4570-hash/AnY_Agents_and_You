const env = (key: string) => Deno.env.get(key) || "";
const supabase = env("SUPABASE_URL");
const service = env("SUPABASE_SERVICE_ROLE_KEY");
const anon = env("SUPABASE_ANON_KEY");
const callback = env("ANY_WECHAT_TEST_CALLBACK_URL");
const testKey = env("ANY_TEST_KEY");
const wechatId = env("ANY_WECHAT_TEST_APP_ID");
const wechatSecret = env("ANY_WECHAT_TEST_APP_SECRET");
const wechatToken = env("ANY_WECHAT_TEST_CALLBACK_TOKEN");
const wechat = Boolean(callback && wechatId && wechatSecret && wechatToken);
const sms = env("ANY_TEST_SMS_ENABLED") === "1";
const testEnabled = testKey.length >= 32;
const uuid = /^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i;
const phonePattern = /^\+[1-9]\d{7,14}$/;
const consentVersion = "2026-11-test";
const encoder = new TextEncoder();
const secret = () => crypto.randomUUID() + crypto.randomUUID();
const json = (data: unknown, status = 200) => Response.json(data, {
  status, headers: { "cache-control": "no-store" },
});

type Obj = Record<string, unknown>;
const field = (data: Obj, key: string) => typeof data[key] === "string" ? data[key] : "";
const secureEqual = (a: string, b: string) => {
  const left = encoder.encode(a);
  const right = encoder.encode(b);
  let diff = left.length ^ right.length;
  for (let i = 0; i < right.length; i++) diff |= (left[i] || 0) ^ right[i];
  return diff === 0;
};

async function rpc(name: string, args: Obj) {
  const res = await fetch(supabase + "/rest/v1/rpc/" + name, {
    method: "POST", redirect: "error", signal: AbortSignal.timeout(6000),
    headers: { apikey: service, authorization: "Bearer " + service, "content-type": "application/json" },
    body: JSON.stringify(args),
  });
  if (!res.ok) throw new Error("Cloud database unavailable");
  return await res.json();
}
const qr = (p_action: string, p_data: Obj) => rpc("any_cloud_qr", { p_action, p_data });
const device = (p_action: string, p_token: string, p_data: Obj = {}) => rpc("any_cloud_device", {
  p_action, p_token, p_data,
});

async function auth(action: string, payload: Obj) {
  return await fetch(supabase + "/auth/v1/" + action, {
    method: "POST", redirect: "error", signal: AbortSignal.timeout(7000),
    headers: { apikey: anon, "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
}

let access: { token: string; expires: number } | undefined;
async function wechatQR(id: string) {
  if (!access || access.expires <= Date.now()) {
    const url = new URL("https://api.weixin.qq.com/cgi-bin/token");
    url.search = new URLSearchParams({
      grant_type: "client_credential", appid: wechatId, secret: wechatSecret,
    }).toString();
    const data = await (await fetch(url, { signal: AbortSignal.timeout(6000) })).json();
    if (!data.access_token) throw new Error("WeChat token unavailable");
    access = { token: data.access_token, expires: Date.now() + (Number(data.expires_in) - 120) * 1000 };
  }
  const url = new URL("https://api.weixin.qq.com/cgi-bin/qrcode/create");
  url.searchParams.set("access_token", access.token);
  const result = await (await fetch(url, {
    method: "POST", signal: AbortSignal.timeout(6000),
    body: JSON.stringify({ expire_seconds: 240, action_name: "QR_STR_SCENE", action_info: { scene: { scene_str: id } } }),
  })).json();
  if (!result.ticket) throw new Error("WeChat QR unavailable");
  return "https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket=" + encodeURIComponent(result.ticket);
}

async function acceptedCallback(url: URL) {
  const timestamp = url.searchParams.get("timestamp") || "";
  const nonce = url.searchParams.get("nonce") || "";
  if (!wechat || !/^\d{10}$/.test(timestamp) || !/^\w{1,64}$/.test(nonce) ||
      Math.abs(Date.now() / 1000 - Number(timestamp)) > 300) return false;
  const digest = await crypto.subtle.digest("SHA-1", encoder.encode([wechatToken, timestamp, nonce].sort().join("")));
  const hex = [...new Uint8Array(digest)].map((n) => n.toString(16).padStart(2, "0")).join("");
  return secureEqual(url.searchParams.get("signature") || "", hex);
}

function xmlField(xml: string, tag: string) {
  const match = xml.match(new RegExp("<" + tag + ">\\s*(?:<!\\[CDATA\\[([^<]*)\\]\\]>|([^<]*))\\s*</" + tag + ">"));
  return (match?.[1] ?? match?.[2] ?? "").trim();
}

async function wechatEvent(req: Request, url: URL) {
  if (!(await acceptedCallback(url))) return new Response("forbidden", { status: 403 });
  if (req.method === "GET") return new Response((url.searchParams.get("echostr") || "").slice(0, 128));
  if (req.method !== "POST") return new Response("method", { status: 405 });
  const xml = await req.text();
  if (xml.length > 8192 || xmlField(xml, "MsgType") !== "event") return new Response("success");
  const event = xmlField(xml, "Event").toLowerCase();
  const id = xmlField(xml, "EventKey").replace(/^qrscene_/, "");
  const from = xmlField(xml, "FromUserName");
  const to = xmlField(xml, "ToUserName");
  if (!["scan", "subscribe"].includes(event) || !uuid.test(id) ||
      !/^[\w-]{1,128}$/.test(from) || !/^[\w-]{1,128}$/.test(to)) return new Response("success");
  const approval = secret();
  const response = await qr("scan", { id, approval, subject: wechatId + ":" + from });
  if (response.status !== "scanned") return new Response("success");
  const link = new URL(callback);
  link.pathname = link.pathname.replace(/\/wechat\/?$/, "/approve");
  link.search = new URLSearchParams({ id, approval }).toString();
  return new Response(
    "<xml><ToUserName><![CDATA[" + from + "]]></ToUserName><FromUserName><![CDATA[" + to +
    "]]></FromUserName><CreateTime>" + Math.floor(Date.now() / 1000) +
    "</CreateTime><MsgType><![CDATA[text]]></MsgType><Content><![CDATA[确认登录 AnY 测试账号，请打开此链接：" +
    link.href + "]]></Content></xml>", { headers: { "content-type": "application/xml; charset=utf-8" } },
  );
}

function approvalPage(content: string) {
  return new Response('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>确认登录 AnY 测试账号</title><main><h1>确认登录 AnY 测试账号</h1>' + content + '</main>', {
    headers: {
      "content-type": "text/html; charset=utf-8", "cache-control": "no-store",
      "referrer-policy": "no-referrer", "content-security-policy": "default-src 'none'; form-action 'self'; frame-ancestors 'none'",
    },
  });
}

async function notify(topic: string) {
  try {
    const res = await fetch(supabase + "/realtime/v1/api/broadcast", {
      method: "POST", signal: AbortSignal.timeout(2000),
      headers: { apikey: service, "content-type": "application/json" },
      body: JSON.stringify({ messages: [{ topic, event: "session_changed", payload: {}, private: false }] }),
    });
    if (!res.ok) console.warn("Session notification unavailable");
  } catch {
    console.warn("Session notification unavailable");
  }
}

async function handle(req: Request) {
  const url = new URL(req.url);
  const route = url.pathname.split("/").at(-1);
  if (route === "wechat") return await wechatEvent(req, url);
  if (route === "approve" && wechat) {
    const id = url.searchParams.get("id") || "";
    const approval = url.searchParams.get("approval") || "";
    if (!uuid.test(id) || approval.length !== 72) return json({ error: "invalid_request" }, 400);
    if (req.method === "GET") return approvalPage('<form method="post"><button>确认登录</button></form>');
    if (req.method !== "POST") return json({ error: "invalid_request" }, 405);
    const result = await qr("approve", { id, approval });
    return approvalPage(result.status === "confirmed" ? "<p>已确认，可以返回 AnY。</p>" : "<p>确认链接已失效，请返回 AnY 刷新二维码。</p>");
  }
  if (req.method !== "POST") return json({ error: "invalid_request" }, 405);
  const text = await req.text();
  if (text.length > 4096) return json({ error: "invalid_request" }, 413);
  let data: Obj;
  try {
    data = JSON.parse(text);
    if (!data || typeof data !== "object" || Array.isArray(data)) throw Error();
  } catch { return json({ error: "invalid_request" }, 400); }

  const action = field(data, "action");
  const name = field(data, "name").trim();
  const installation = field(data, "installation");
  const token = req.headers.get("authorization")?.match(/^Bearer ([\da-f-]{64,72})$/i)?.[1] || "";
  const consent = data.consent === consentVersion;
  const enrollment = uuid.test(installation) && name.length > 0 && name.length <= 60 && consent;
  const allowed = testEnabled && secureEqual(req.headers.get("x-any-test-key") || "", testKey);
  const fixture = allowed && env("ANY_TEST_FIXTURES") === "1";
  if (action === "capabilities") {
    return json({ wechat: allowed && wechat, sms: allowed && sms, test: true, consent_version: consentVersion });
  }
  if (action === "qr_create" && (allowed && wechat || fixture) && enrollment) {
    const key = secret();
    const result = await qr("create", { key, installation, name });
    if (!result.id) return json(result, 400);
    return json({ ...result, key, image: wechat && !fixture ? await wechatQR(result.id) : null });
  }
  if (action === "qr_poll" && allowed && (wechat || fixture)) {
    return json(await qr("poll", { id: field(data, "id"), key: field(data, "key") }));
  }
  if (action === "test_scan" && fixture) {
    const approval = secret();
    const subject = field(data, "subject");
    if (!/^[\w-]{1,80}$/.test(subject)) return json({ error: "invalid_request" }, 400);
    const state = await qr("scan", { id: field(data, "id"), subject: "fixture:" + subject, approval });
    return json({ ...state, approval: state.status === "scanned" ? approval : undefined });
  }
  if (action === "test_approve" && fixture) {
    return json(await qr("approve", { id: field(data, "id"), approval: field(data, "approval") }));
  }
  if (action === "sms_send" && allowed && sms && consent) {
    const phone = field(data, "phone");
    if (!phonePattern.test(phone)) return json({ error: "invalid_request" }, 400);
    if (!(await rpc("any_cloud_sms_reserve", { p_phone: phone }))) return json({ error: "sms_wait" }, 429);
    const res = await auth("otp", { phone, create_user: true, channel: "sms" });
    return res.ok ? json({ ok: true, retry_after: 60 }) : json({ error: "sms_failed", retry_after: 60 }, 502);
  }
  if (["sms_verify", "sms_bind"].includes(action) && allowed && sms && enrollment) {
    const phone = field(data, "phone");
    const code = field(data, "code");
    if (!phonePattern.test(phone) || !/^\d{6}$/.test(code) || (action === "sms_bind" && !token)) {
      return json({ error: "invalid_request" }, 400);
    }
    const verified = await auth("verify", { type: "sms", phone, token: code });
    if (!verified.ok) return json({ error: "invalid_code" }, 400);
    const proof = await verified.json();
    // Use only the provider-verified identity. The client's Supabase JWT is never returned.
    if (!proof.user?.id) return json({ error: "invalid_code" }, 400);
    if (action === "sms_bind") return json(await device("bind_phone", token, { subject: proof.user.id }));
    return json(await rpc("any_cloud_login", {
      p_provider: "phone-test", p_subject: proof.user.id, p_install: installation, p_label: name,
    }));
  }
  if (!["session", "devices", "rename", "revoke", "logout", "preferences", "sync"].includes(action)) {
    return json({ error: "channel_unavailable" }, 400);
  }
  if (!token) return json({ error: "signed_out" }, 401);
  const result = await device(action, token, {
    name, id: field(data, "id"), version: data.version, preferences: data.preferences,
  });
  if (result.notify) {
    await notify(result.notify);
    delete result.notify;
  }
  if (action === "session" && result.topic && anon && supabase.startsWith("https://")) {
    result.realtime = supabase.replace(/^https:/, "wss:") + "/realtime/v1/websocket?" +
      new URLSearchParams({ apikey: anon, vsn: "1.0.0" });
  }
  return json(result, result.error === "signed_out" ? 401 : result.error === "conflict" ? 409 : 200);
}

Deno.serve({ port: Number(env("ANY_TEST_PORT") || 8000) }, async (req) => {
  try {
    return await handle(req);
  } catch {
    // Provider payloads, credentials and session tokens stay out of logs.
    return json({ error: "cloud_unavailable" }, 503);
  }
});
