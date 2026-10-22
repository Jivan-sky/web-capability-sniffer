'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');

const { classifyRequest, installReadOnlyGuard } = require('../scripts/readonly_guard');

function createFakeTarget() {
  const routes = new Map();
  const listeners = new Map();
  return {
    route: async (pattern, handler) => { routes.set(pattern, handler); },
    unroute: async (pattern, handler) => {
      if (routes.get(pattern) === handler) routes.delete(pattern);
    },
    on: (event, handler) => { listeners.set(event, handler); },
    off: (event, handler) => {
      if (listeners.get(event) === handler) listeners.delete(event);
    },
    _route: (pattern) => routes.get(pattern),
    _emit: (event, arg) => listeners.get(event)(arg),
    _hasRoute: (pattern) => routes.has(pattern),
    _hasListener: (event) => listeners.has(event),
  };
}

function createRoute({ url, method, throwOnRequest = false, headers = {}, body = undefined }) {
  const calls = [];
  return {
    request: () => {
      if (throwOnRequest) throw new Error('boom');
      return {
        url: () => url,
        method: () => method,
        headers: () => headers,
        postData: () => body,
      };
    },
    continue: async () => { calls.push(['continue']); },
    abort: async (code) => { calls.push(['abort', code]); },
    calls,
  };
}

function createDialog({ type = 'confirm', message = 'Delete?' } = {}) {
  const calls = [];
  return {
    type: () => type,
    message: () => message,
    dismiss: async () => { calls.push(['dismiss']); },
    calls,
  };
}

test('GET, HEAD and OPTIONS are read-only methods', () => {
  for (const method of ['GET', 'HEAD', 'OPTIONS', 'get']) {
    const decision = classifyRequest({ url: 'https://app.example.com/api/orders', method });
    assert.equal(decision.allow, true, `${method} should be allowed`);
    assert.equal(decision.level, 'A');
  }
});

test('POST is denied unless the pathname is explicitly allowlisted', () => {
  const denied = classifyRequest({ url: 'https://app.example.com/api/query', method: 'POST' });
  assert.equal(denied.allow, false);
  assert.equal(denied.reason, 'post-not-allowlisted');

  const allowed = classifyRequest({
    url: 'https://app.example.com/api/query',
    method: 'POST',
    allowReadPostPaths: ['/api/query'],
  });
  assert.equal(allowed.allow, true);
  assert.equal(allowed.reason, 'allowlisted-read-post');
});

test('POST allowlists are exact and wildcard patterns fail closed', () => {
  const exact = classifyRequest({
    url: 'https://app.example.com/graphql/v1?op=orders',
    method: 'POST',
    allowReadPostPaths: ['/graphql/v1'],
  });
  assert.equal(exact.allow, true);

  const wildcard = classifyRequest({
    url: 'https://app.example.com/graphql/v1?op=orders',
    method: 'POST',
    allowReadPostPaths: ['/graphql/*'],
  });
  assert.equal(wildcard.allow, false);
  assert.equal(wildcard.reason, 'post-not-allowlisted');
});

test('PUT, PATCH and DELETE are always denied', () => {
  for (const method of ['PUT', 'PATCH', 'DELETE']) {
    const decision = classifyRequest({ url: 'https://app.example.com/api/orders/1', method });
    assert.equal(decision.allow, false);
    assert.equal(decision.reason, 'method-not-read-only');
    assert.equal(decision.level, 'C');
  }
});

test('dangerous path segments are denied even for GET', () => {
  for (const path of [
    '/api/table/drop',
    '/api/orders/delete',
    '/api/admin/reset',
    '/api/users/grant',
    '/api/orders/save',
    '/api/orders/create',
    '/api/orders/update',
    '/api/orders/submit',
    '/api/orders/execute',
    '/api/orders/deleteAll',
    '/api/orders/%64elete',
  ]) {
    const decision = classifyRequest({ url: `https://app.example.com${path}`, method: 'GET' });
    assert.equal(decision.allow, false, `${path} should be blocked`);
    assert.equal(decision.reason, 'dangerous-path');
  }
});

test('invalid percent-encoded paths fail closed', () => {
  const decision = classifyRequest({ url: 'https://app.example.com/api/%E0%A4%A', method: 'GET' });
  assert.equal(decision.allow, false);
  assert.equal(decision.reason, 'invalid-path-encoding');
});

test('query values do not trigger dangerous-path matching', () => {
  const decision = classifyRequest({
    url: 'https://app.example.com/api/orders?keyword=delete',
    method: 'GET',
  });
  assert.equal(decision.allow, true);
});

test('dangerous action parameters are blocked even for GET', () => {
  for (const url of [
    'https://app.example.com/api/records?action=delete',
    'https://app.example.com/api/records?op=bulk_delete',
    'https://app.example.com/api/table?operation=DROP',
    'https://app.example.com/api/records?do=save',
    'https://app.example.com/api/records?type=update',
    'https://app.example.com/api/records?action=removeAll',
  ]) {
    const decision = classifyRequest({ url, method: 'GET' });
    assert.equal(decision.allow, false, `${url} should be blocked`);
    assert.equal(decision.reason, 'dangerous-action-parameter');
  }

  const benign = classifyRequest({
    url: 'https://app.example.com/api/records?action=list&mode=read',
    method: 'GET',
  });
  assert.equal(benign.allow, true);
});

test('dedicated session POST paths are separate from read POST paths', () => {
  const session = classifyRequest({
    url: 'https://app.example.com/api/auth/login',
    method: 'POST',
    allowSessionPostPaths: ['/api/auth/login'],
  });
  assert.equal(session.allow, true);
  assert.equal(session.reason, 'allowlisted-session-post');

  const missing = classifyRequest({
    url: 'https://app.example.com/api/auth/login',
    method: 'POST',
  });
  assert.equal(missing.allow, false);
});

test('allowlisted GraphQL POST cannot carry a mutation', () => {
  const decision = classifyRequest({
    url: 'https://app.example.com/graphql',
    method: 'POST',
    allowReadPostPaths: ['/graphql'],
    body: JSON.stringify({ query: 'mutation { deleteOrder(id: 1) { id } }' }),
  });
  assert.equal(decision.allow, false);
  assert.equal(decision.reason, 'graphql-write');
});

test('method override headers cannot turn a GET into a write', () => {
  const blocked = classifyRequest({
    url: 'https://app.example.com/api/records/1',
    method: 'GET',
    headers: { 'X-HTTP-Method-Override': 'DELETE' },
  });
  assert.equal(blocked.allow, false);
  assert.equal(blocked.reason, 'method-override');

  const allowed = classifyRequest({
    url: 'https://app.example.com/api/records/1',
    method: 'GET',
    headers: { 'X-HTTP-Method-Override': 'GET' },
  });
  assert.equal(allowed.allow, true);
});

test('ordinary words containing a dangerous token are not blocked', () => {
  const decision = classifyRequest({ url: 'https://app.example.com/api/dropdown', method: 'GET' });
  assert.equal(decision.allow, true);
});

test('invalid URLs fail closed', () => {
  const decision = classifyRequest({ url: 'not a url', method: 'GET' });
  assert.equal(decision.allow, false);
  assert.equal(decision.reason, 'invalid-url');
});

test('installReadOnlyGuard aborts a non-read-only request and records a safe event', async () => {
  const target = createFakeTarget();
  const events = [];
  const guard = await installReadOnlyGuard(target, { onBlocked: (event) => events.push(event) });
  const handler = target._route('**/*');
  const route = createRoute({
    url: 'https://app.example.com/api/orders?token=SECRET',
    method: 'POST',
  });

  await handler(route);

  assert.deepEqual(route.calls, [['abort', 'blockedbyclient']]);
  assert.equal(events.length, 1);
  assert.equal(events[0].method, 'POST');
  assert.equal(events[0].origin, 'https://app.example.com');
  assert.equal(events[0].path, '/api/orders');
  assert.equal(JSON.stringify(events[0]).includes('SECRET'), false);
  assert.equal(events[0].execution, '阻断');
  assert.equal(guard.blocked.length, 1);
});

test('blocked events redact IDs, emails and long numeric segments in the path', async () => {
  const target = createFakeTarget();
  const events = [];
  const guard = await installReadOnlyGuard(target, { onBlocked: (event) => events.push(event) });
  const handler = target._route('**/*');
  const route = createRoute({
    url: 'https://app.example.com/api/users/123456789/email/alice%40example.com/save',
    method: 'GET',
  });

  await handler(route);

  assert.equal(route.calls[0][0], 'abort');
  assert.equal(JSON.stringify(events).includes('123456789'), false);
  assert.equal(JSON.stringify(events).includes('alice@example.com'), false);
  assert.equal(JSON.stringify(events).includes('123456789'), false);
  assert.equal(guard.blocked.length, 1);
});

test('installReadOnlyGuard continues a GET request', async () => {
  const target = createFakeTarget();
  const guard = await installReadOnlyGuard(target);
  const handler = target._route('**/*');
  const route = createRoute({ url: 'https://app.example.com/api/orders', method: 'GET' });

  await handler(route);

  assert.deepEqual(route.calls, [['continue']]);
  assert.equal(guard.blocked.length, 0);
});

test('installReadOnlyGuard fails closed when the request object throws', async () => {
  const target = createFakeTarget();
  const events = [];
  const guard = await installReadOnlyGuard(target, { onBlocked: (event) => events.push(event) });
  const handler = target._route('**/*');
  const route = createRoute({ url: 'https://app.example.com/api/orders', method: 'GET', throwOnRequest: true });

  await handler(route);

  assert.deepEqual(route.calls, [['abort', 'blockedbyclient']]);
  assert.equal(guard.blocked[0].type, 'guard-error');
});

test('a throwing onBlocked callback still aborts the request', async () => {
  const target = createFakeTarget();
  const guard = await installReadOnlyGuard(target, {
    onBlocked: () => {
      throw new Error('callback failed');
    },
  });
  const handler = target._route('**/*');
  const route = createRoute({ url: 'https://app.example.com/api/orders', method: 'POST' });

  await handler(route);

  assert.deepEqual(route.calls, [['abort', 'blockedbyclient']]);
  assert.equal(guard.blocked.some((event) => event.type === 'callback-error'), true);
});

test('installReadOnlyGuard dismisses dialogs and never accepts them', async () => {
  const target = createFakeTarget();
  const events = [];
  const guard = await installReadOnlyGuard(target, { onBlocked: (event) => events.push(event) });
  const dialog = createDialog({ type: 'confirm', message: 'Delete this table?' });

  await target._emit('dialog', dialog);

  assert.deepEqual(dialog.calls, [['dismiss']]);
  assert.equal(events[0].type, 'dialog');
  assert.equal(events[0].execution, '阻断');
  assert.equal(guard.dialogs.length, 1);
});

test('dialog messages are redacted before they enter the audit event', async () => {
  const target = createFakeTarget();
  const events = [];
  await installReadOnlyGuard(target, { onBlocked: (event) => events.push(event) });
  const dialog = createDialog({
    message: 'Delete customer 123456789 / alice@example.com token=SECRET123?',
  });

  await target._emit('dialog', dialog);

  assert.equal(JSON.stringify(events).includes('123456789'), false);
  assert.equal(JSON.stringify(events).includes('alice@example.com'), false);
  assert.equal(JSON.stringify(events).includes('SECRET123'), false);
});

test('dialog guard still dismisses when reading dialog metadata throws', async () => {
  const target = createFakeTarget();
  await installReadOnlyGuard(target);
  const calls = [];
  const dialog = {
    type: () => {
      throw new Error('type failed');
    },
    message: () => 'Delete?',
    dismiss: async () => { calls.push(['dismiss']); },
  };

  await target._emit('dialog', dialog);

  assert.deepEqual(calls, [['dismiss']]);
});

test('installReadOnlyGuard rejects wildcard allowlists before routing', async () => {
  const target = createFakeTarget();
  await assert.rejects(
    () => installReadOnlyGuard(target, { allowReadPostPaths: ['/api/*'] }),
    /exact pathnames/
  );
  assert.equal(target._hasRoute('**/*'), false);
});

test('uninstall removes the route and dialog listener', async () => {
  const target = createFakeTarget();
  const guard = await installReadOnlyGuard(target);

  await guard.uninstall();

  assert.equal(target._hasRoute('**/*'), false);
  assert.equal(target._hasListener('dialog'), false);
});
