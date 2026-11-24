-- All client data access goes through the Edge Function and transaction-scoped RPCs.
create schema if not exists any_cloud;
revoke all on schema any_cloud from public, anon, authenticated;

create table any_cloud.accounts (
  id uuid primary key default gen_random_uuid(),
  device_limit integer not null default 3 check (device_limit between 1 and 10),
  policy_version text not null,
  consent_at timestamptz not null default now(),
  prefs jsonb not null default '{}',
  revision integer not null default 0
);
create table any_cloud.identities (
  provider text not null,
  subject text not null,
  account uuid not null references any_cloud.accounts(id) on delete cascade,
  primary key (provider, subject),
  unique (account, provider)
);
create table any_cloud.devices (
  account uuid not null references any_cloud.accounts(id) on delete cascade,
  installation uuid not null,
  label text not null check (length(trim(label)) between 1 and 60),
  token_hash text not null unique,
  notification_topic uuid not null default gen_random_uuid(),
  last_seen timestamptz not null default now(),
  expires_at timestamptz not null default now() + interval '30 days',
  revoked_at timestamptz,
  primary key (account, installation)
);
create table any_cloud.qr (
  id uuid primary key default gen_random_uuid(),
  claim_key text not null,
  installation uuid not null,
  label text not null,
  expires_at timestamptz not null default now() + interval '4 minutes',
  subject text,
  approval_key text,
  confirmed boolean not null default false,
  result jsonb
);
create table any_cloud.sms_rate (
  phone_hash text primary key,
  next_send timestamptz not null
);
alter table any_cloud.accounts enable row level security;
alter table any_cloud.identities enable row level security;
alter table any_cloud.devices enable row level security;
alter table any_cloud.qr enable row level security;
alter table any_cloud.sms_rate enable row level security;

create function any_cloud.digest(value text) returns text
language sql immutable strict set search_path = '' as $$
  select encode(sha256(convert_to(value, 'UTF8')), 'hex')
$$;

create function any_cloud.login(p_provider text, p_subject text, p_install uuid, p_label text, p_token text default null)
returns jsonb language plpgsql set search_path = '' as $$
declare
  account_id uuid;
  cap integer;
  token text := coalesce(p_token, gen_random_uuid()::text || gen_random_uuid()::text);
begin
  if p_provider not in ('wechat-test', 'phone', 'phone-test') or p_subject is null or
     p_install is null or coalesce(length(trim(p_label)), 0) not between 1 and 60 then
    return '{"error":"invalid_request"}';
  end if;
  perform pg_advisory_xact_lock(hashtextextended(p_provider || ':' || p_subject, 0));
  select account into account_id from any_cloud.identities where provider = p_provider and subject = p_subject;
  if not found then
    insert into any_cloud.accounts(policy_version) values ('2026-11-test') returning id into account_id;
    insert into any_cloud.identities values (p_provider, p_subject, account_id);
  end if;

  select device_limit into cap from any_cloud.accounts where id = account_id for update;
  if (select count(*) from any_cloud.devices
      where account = account_id and installation <> p_install
        and revoked_at is null and expires_at > now()) >= cap then
    return jsonb_build_object('error', 'device_limit', 'limit', cap);
  end if;

  insert into any_cloud.devices(account, installation, label, token_hash)
    values (account_id, p_install, trim(p_label), any_cloud.digest(token))
    on conflict (account, installation) do update
    set label = excluded.label, token_hash = excluded.token_hash, notification_topic = excluded.notification_topic,
        last_seen = now(), expires_at = excluded.expires_at, revoked_at = null;
  return jsonb_build_object('token', token, 'account', account_id);
end
$$;

create function public.any_cloud_login(p_provider text, p_subject text, p_install uuid, p_label text)
returns jsonb language sql security definer set search_path = '' as $$
  select any_cloud.login(p_provider, p_subject, p_install, p_label)
$$;

create function public.any_cloud_device(p_action text, p_token text, p_data jsonb)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  device any_cloud.devices;
  target any_cloud.devices;
  account_row any_cloud.accounts;
  patch jsonb;
  label_text text;
begin
  select * into device from any_cloud.devices where token_hash = any_cloud.digest(p_token);
  if not found then return '{"error":"signed_out"}'; end if;
  -- The account lock serializes enrollment, revocation and preference writes.
  select * into account_row from any_cloud.accounts where id = device.account for update;
  select * into device from any_cloud.devices
    where token_hash = any_cloud.digest(p_token) and revoked_at is null and expires_at > now();
  if not found then return '{"error":"signed_out"}'; end if;

  case p_action
  when 'session' then
    return jsonb_build_object('account', device.account, 'topic', device.notification_topic, 'phone_bound',
      exists(select from any_cloud.identities where account = device.account and provider = 'phone-test'));
  when 'bind_phone' then
    if not exists(select from any_cloud.identities where account = device.account and provider = 'wechat-test')
      or coalesce(length(p_data->>'subject'),0) = 0 then return '{"error":"invalid_request"}'; end if;
    insert into any_cloud.identities(provider, subject, account) values ('phone-test', p_data->>'subject', device.account)
      on conflict do nothing;
    if not exists(select from any_cloud.identities where account = device.account and provider = 'phone-test'
      and subject = p_data->>'subject') then return '{"error":"phone_taken"}'; end if;
    return '{"ok":true}';
  when 'devices' then
    update any_cloud.devices set last_seen = now() where account = device.account and installation = device.installation;
    return jsonb_build_object('limit', account_row.device_limit, 'devices', coalesce(
      (select jsonb_agg(jsonb_build_object(
        'id', installation, 'name', label, 'current', installation = device.installation, 'last_seen', last_seen
      ) order by installation <> device.installation, last_seen desc)
      from any_cloud.devices where account = device.account and revoked_at is null and expires_at > now()), '[]'));
  when 'rename' then
    label_text := trim(p_data->>'name');
    if coalesce(length(label_text), 0) not between 1 and 60 then return '{"error":"invalid_request"}'; end if;
    update any_cloud.devices set label = label_text where account = device.account and installation = device.installation;
    return '{"ok":true}';
  when 'revoke', 'logout' then
    update any_cloud.devices set revoked_at = now()
      where account = device.account and revoked_at is null and installation =
        case when p_action = 'logout' then device.installation else (p_data->>'id')::uuid end
      returning * into target;
    return jsonb_build_object('ok', true, 'notify', target.notification_topic);
  when 'preferences' then
    return jsonb_build_object('version', account_row.revision, 'preferences', account_row.prefs);
  when 'sync' then
    patch := p_data->'preferences';
    if jsonb_typeof(patch) is distinct from 'object' or jsonb_typeof(p_data->'version') is distinct from 'number' then
      return '{"error":"invalid_request"}';
    end if;
    if patch - array['theme', 'language'] <> '{}'::jsonb
      or (patch ? 'theme' and patch->'theme' not in ('"system"', '"light"', '"dark"'))
      or (patch ? 'language' and patch->'language' not in ('"auto"', '"zh-CN"', '"en"'))
      or patch = '{}'::jsonb then return '{"error":"invalid_request"}'; end if;
    if account_row.prefs @> patch then
      return jsonb_build_object('version', account_row.revision, 'preferences', account_row.prefs);
    end if;
    if to_jsonb(account_row.revision) <> p_data->'version' then
      return jsonb_build_object('error', 'conflict', 'version', account_row.revision, 'preferences', account_row.prefs);
    end if;
    update any_cloud.accounts set revision = revision + 1, prefs = prefs || patch
      where id = device.account returning * into account_row;
    return jsonb_build_object('version', account_row.revision, 'preferences', account_row.prefs);
  else return '{"error":"invalid_request"}';
  end case;
exception when invalid_text_representation then return '{"error":"invalid_request"}';
end
$$;

create function public.any_cloud_qr(p_action text, p_data jsonb)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  challenge any_cloud.qr;
  login_result jsonb;
  session_token text;
begin
  if p_action = 'create' then
    delete from any_cloud.qr where expires_at < now() - interval '5 minutes';
    insert into any_cloud.qr(claim_key, installation, label)
      values (any_cloud.digest(p_data->>'key'), (p_data->>'installation')::uuid, p_data->>'name')
      returning * into challenge;
    return jsonb_build_object('id', challenge.id, 'expires', challenge.expires_at);
  end if;

  select * into challenge from any_cloud.qr where id = (p_data->>'id')::uuid for update;
  if not found or challenge.expires_at <= now() then return '{"status":"expired"}'; end if;
  case p_action
  when 'scan' then
    if challenge.subject is not null or p_data->>'subject' is null or p_data->>'approval' is null then
      return '{"status":"ignored"}';
    end if;
    update any_cloud.qr set subject = p_data->>'subject', approval_key = any_cloud.digest(p_data->>'approval')
      where id = challenge.id;
    return '{"status":"scanned"}';
  when 'approve' then
    if challenge.approval_key is null or challenge.approval_key is distinct from any_cloud.digest(p_data->>'approval') then
      return '{"error":"invalid_request"}';
    end if;
    update any_cloud.qr set confirmed = true, approval_key = null where id = challenge.id;
    return '{"status":"confirmed"}';
  when 'poll' then
    if challenge.claim_key is distinct from any_cloud.digest(p_data->>'key') then return '{"error":"invalid_request"}'; end if;
    if challenge.subject is null then return '{"status":"pending"}'; end if;
    if not challenge.confirmed then return '{"status":"scanned"}'; end if;
    session_token := any_cloud.digest('session:' || (p_data->>'key'));
    if challenge.result is null then
      login_result := any_cloud.login('wechat-test', challenge.subject, challenge.installation, challenge.label, session_token);
      update any_cloud.qr set result = login_result - 'token' where id = challenge.id;
    else
      login_result := challenge.result;
    end if;
    if not (login_result ? 'error') then login_result := login_result || jsonb_build_object('token', session_token); end if;
    return login_result || '{"status":"confirmed"}';
  else return '{"error":"invalid_request"}';
  end case;
exception when invalid_text_representation or not_null_violation then return '{"error":"invalid_request"}';
end
$$;

create function public.any_cloud_sms_reserve(p_phone text)
returns boolean language plpgsql security definer set search_path = '' as $$
begin
  delete from any_cloud.sms_rate where next_send < now() - interval '1 hour';
  insert into any_cloud.sms_rate(phone_hash, next_send)
    values (any_cloud.digest(p_phone), now() + interval '60 seconds')
    on conflict (phone_hash) do update set next_send = excluded.next_send
    where any_cloud.sms_rate.next_send <= now();
  return found;
end
$$;

revoke execute on function public.any_cloud_login(text,text,uuid,text) from public, anon, authenticated;
revoke execute on function public.any_cloud_device(text,text,jsonb) from public, anon, authenticated;
revoke execute on function public.any_cloud_qr(text,jsonb) from public, anon, authenticated;
revoke execute on function public.any_cloud_sms_reserve(text) from public, anon, authenticated;
grant execute on function public.any_cloud_login(text,text,uuid,text) to service_role;
grant execute on function public.any_cloud_device(text,text,jsonb) to service_role;
grant execute on function public.any_cloud_qr(text,jsonb) to service_role;
grant execute on function public.any_cloud_sms_reserve(text) to service_role;
