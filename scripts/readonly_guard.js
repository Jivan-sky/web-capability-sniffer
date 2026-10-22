'use strict';

/**
 * Fail-closed browser guard for read-only exploration.
 *
 * This module is dependency-free. It accepts a Playwright-like page/context so
 * it can be unit-tested without launching a browser.
 */

const READ_ONLY_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);
const ACTION_PARAM_NAMES = new Set([
  'action',
  'op',
  'operation',
  'method',
  'cmd',
  'command',
  'mode',
  'do',
  'act',
  'type',
  'verb',
  'intent',
  'mutation',
]);
const METHOD_OVERRIDE_HEADERS = ['x-http-method-override', 'x-method-override'];

// Path matching is segment-based, not substring-based: `dropdown` is not
// treated as `drop`, while camelCase forms such as `deleteAll` are caught.
// A hit is blocked even for GET because some systems mutate state via GET.
const DANGEROUS_PATH_SEGMENTS = new Set([
  'drop',
  'truncate',
  'delete',
  'remove',
  'destroy',
  'purge',
  'clear',
  'reset',
  'init',
  'initialize',
  'restore',
  'rollback',
  'overwrite',
  'batch',
  'bulk',
  'import',
  'upload',
  'save',
  'create',
  'update',
  'edit',
  'add',
  'write',
  'submit',
  'execute',
  'exec',
  'run',
  'trigger',
  'sync',
  'migrate',
  'generate',
  'export',
  'download',
  'saveas',
  'print',
  'enable',
  'disable',
  'logout',
  'signout',
  'grant',
  'revoke',
  'assign',
  'transfer',
  'role',
  'permission',
  'approve',
  'reject',
  'pay',
  'refund',
  'send',
  'notify',
  'publish',
  'deploy',
  'rebuild',
  'refresh',
  'analyze',
  'scan',
  'probe',
  'enumerate',
  'brute',
  'inject',
  'idor',
]);

const DANGEROUS_ACTION_VALUE = new RegExp(
  `(?:^|[^a-z])(?:${[...DANGEROUS_PATH_SEGMENTS]
    .map((token) => token.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('|')})(?:$|[^a-z])`,
  'i'
);

function decodePathname(pathname) {
  try {
    return decodeURIComponent(pathname);
  } catch {
    return null;
  }
}

function pathSegments(pathname) {
  const decoded = decodePathname(pathname);
  if (decoded === null) return null;
  return decoded
    .replace(/([a-z0-9])([A-Z])/g, '$1/$2')
    .split(/[^A-Za-z0-9]+/)
    .filter(Boolean)
    .map((segment) => segment.toLowerCase());
}

function hasDangerousPathSegment(pathname) {
  const segments = pathSegments(pathname);
  if (segments === null) return true;
  return segments.some((segment) => DANGEROUS_PATH_SEGMENTS.has(segment));
}

function parseUrl(rawUrl) {
  try {
    return new URL(rawUrl);
  } catch {
    return null;
  }
}

function matchesPath(pathname, rule) {
  // POST allowlists are exact paths. Wildcards and prefix matching would let a
  // read endpoint become a write endpoint through one extra path segment.
  if (typeof rule !== 'string' || rule.length === 0 || rule.includes('*')) return false;
  return pathname === rule;
}

function hasDangerousActionParameter(searchParams) {
  for (const [key, value] of searchParams) {
    const segments = pathSegments(`/${value}`);
    if (
      ACTION_PARAM_NAMES.has(key.toLowerCase()) &&
      (DANGEROUS_ACTION_VALUE.test(value) || (segments && segments.some((segment) => DANGEROUS_PATH_SEGMENTS.has(segment))))
    ) {
      return true;
    }
  }
  return false;
}

function hasGraphQLWrite(body) {
  // A GraphQL POST endpoint can carry both queries and mutations. Do not let a
  // path-level allowlist turn into a mutation allowlist.
  return typeof body === 'string' && /(^|[^a-z])(mutation|subscription)([^a-z]|$)/i.test(body);
}

function classifyRequest({
  url,
  method = 'GET',
  allowReadPostPaths = [],
  allowSessionPostPaths = [],
  dangerousPath = null,
  headers = {},
  body = undefined,
} = {}) {
  const parsed = parseUrl(url);
  if (!parsed) {
    return { allow: false, reason: 'invalid-url', level: 'C' };
  }

  const normalizedMethod = String(method).trim().toUpperCase();
  const pathname = parsed.pathname;
  const readRules = Array.isArray(allowReadPostPaths) ? allowReadPostPaths : [];
  const sessionRules = Array.isArray(allowSessionPostPaths) ? allowSessionPostPaths : [];

  if (decodePathname(pathname) === null) {
    return { allow: false, reason: 'invalid-path-encoding', level: 'C', method: normalizedMethod, path: pathname };
  }

  if (hasDangerousPathSegment(pathname)) {
    return { allow: false, reason: 'dangerous-path', level: 'C', method: normalizedMethod, path: pathname };
  }

  if (dangerousPath) dangerousPath.lastIndex = 0;
  if (dangerousPath && dangerousPath.test(decodePathname(pathname))) {
    return { allow: false, reason: 'dangerous-path', level: 'C', method: normalizedMethod, path: pathname };
  }

  if (hasDangerousActionParameter(parsed.searchParams)) {
    return { allow: false, reason: 'dangerous-action-parameter', level: 'C', method: normalizedMethod, path: pathname };
  }

  const normalizedHeaders = Object.fromEntries(
    Object.entries(headers || {}).map(([key, value]) => [key.toLowerCase(), String(value)])
  );
  for (const header of METHOD_OVERRIDE_HEADERS) {
    const override = normalizedHeaders[header];
    if (override && !READ_ONLY_METHODS.has(override.trim().toUpperCase())) {
      return { allow: false, reason: 'method-override', level: 'C', method: normalizedMethod, path: pathname };
    }
  }

  if (READ_ONLY_METHODS.has(normalizedMethod)) {
    return { allow: true, reason: 'read-only-method', level: 'A', method: normalizedMethod, path: pathname };
  }

  if (normalizedMethod === 'POST') {
    const readAllowed = readRules.some((rule) => matchesPath(pathname, rule));
    const sessionAllowed = sessionRules.some((rule) => matchesPath(pathname, rule));
    if (!readAllowed && !sessionAllowed) {
      return { allow: false, reason: 'post-not-allowlisted', level: 'C', method: normalizedMethod, path: pathname };
    }
    if (readAllowed && hasGraphQLWrite(body)) {
      return { allow: false, reason: 'graphql-write', level: 'C', method: normalizedMethod, path: pathname };
    }
    return {
      allow: true,
      reason: readAllowed ? 'allowlisted-read-post' : 'allowlisted-session-post',
      level: 'A',
      method: normalizedMethod,
      path: pathname,
    };
  }

  return { allow: false, reason: 'method-not-read-only', level: 'C', method: normalizedMethod, path: pathname };
}

function sanitizeText(value) {
  return String(value ?? '')
    .slice(0, 240)
    .replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, '[email]')
    .replace(/\b(token|access_token|session|secret|password|passwd|pwd|key)=[^&\s]+/gi, '$1=[redacted]')
    .replace(/\b[0-9a-f]{8}-[0-9a-f-]{27,}\b/gi, '[uuid]')
    .replace(/\b[0-9a-f]{24,}\b/gi, '[hash]')
    .replace(/\b\d{6,}\b/g, '[id]');
}

function safePath(pathname) {
  const decoded = decodePathname(pathname);
  return sanitizeText(decoded === null ? pathname : decoded);
}

function safeTarget(url) {
  const parsed = parseUrl(url);
  if (!parsed) return { origin: '', path: '' };
  return { origin: parsed.origin, path: safePath(parsed.pathname) };
}

/**
 * Install a fail-closed request guard and dialog dismisser.
 *
 * @param {object} target Playwright Page or BrowserContext (must expose route/unroute/on)
 * @param {object} options
 * @param {string[]} options.allowReadPostPaths Exact pathnames
 *        that are documented read-only POST endpoints. Empty by default.
 * @param {string[]} options.allowSessionPostPaths Exact pathnames for a
 *        dedicated login/session-creation endpoint. Not a read allowlist.
 * @param {RegExp} options.dangerousPath Path pattern to block even for GET.
 * @param {(event: object) => void} options.onBlocked Called once per blocked request/dialog.
 */
function reportEvent(sink, onBlocked, event) {
  sink.push(event);
  try {
    onBlocked(event);
  } catch (error) {
    sink.push({
      type: 'callback-error',
      at: new Date().toISOString(),
      reason: String(error).slice(0, 240),
    });
  }
}

function installDialogGuard(target, options = {}) {
  if (!target || typeof target.on !== 'function') {
    throw new TypeError('installDialogGuard requires a Playwright-like page');
  }

  const onBlocked = typeof options.onBlocked === 'function' ? options.onBlocked : () => {};
  const dialogs = [];

  const dialogHandler = async (dialog) => {
    let event;
    try {
      event = {
        type: 'dialog',
        at: new Date().toISOString(),
        dialogType: dialog.type ? dialog.type() : 'unknown',
        message: sanitizeText(dialog.message ? dialog.message() : ''),
        level: 'C',
        execution: '阻断',
        reason: 'dialog-dismissed',
      };
    } catch (error) {
      event = {
        type: 'dialog-error',
        at: new Date().toISOString(),
        reason: String(error).slice(0, 240),
        level: 'C',
        execution: '阻断',
      };
    }
    reportEvent(dialogs, onBlocked, event);
    try {
      await dialog.dismiss();
    } catch (error) {
      dialogs.push({
        type: 'dialog-dismiss-error',
        at: new Date().toISOString(),
        reason: String(error).slice(0, 240),
      });
    }
  };

  target.on('dialog', dialogHandler);

  return {
    dialogs,
    uninstall: () => {
      if (typeof target.off === 'function') target.off('dialog', dialogHandler);
    },
  };
}

function normalizeAllowlist(value, name) {
  if (!Array.isArray(value)) return [];
  for (const rule of value) {
    if (typeof rule !== 'string' || !rule.startsWith('/') || rule.includes('*') || rule.includes('?') || rule.includes('#')) {
      throw new TypeError(`${name} must contain exact pathnames beginning with '/'`);
    }
  }
  return value.slice();
}

async function installReadOnlyGuard(target, options = {}) {
  if (!target || typeof target.route !== 'function') {
    throw new TypeError('installReadOnlyGuard requires a Playwright-like page or context');
  }

  const allowReadPostPaths = normalizeAllowlist(options.allowReadPostPaths, 'allowReadPostPaths');
  const allowSessionPostPaths = normalizeAllowlist(options.allowSessionPostPaths, 'allowSessionPostPaths');
  const dangerousPath = options.dangerousPath || null;
  const onBlocked = typeof options.onBlocked === 'function' ? options.onBlocked : () => {};
  const blocked = [];

  const handler = async (route) => {
    try {
      const request = route.request();
      const decision = classifyRequest({
        url: request.url(),
        method: request.method(),
        allowReadPostPaths,
        allowSessionPostPaths,
        dangerousPath,
        headers: typeof request.headers === 'function' ? request.headers() : {},
        body: typeof request.postData === 'function' ? request.postData() : undefined,
      });

      if (decision.allow) {
        await route.continue();
        return;
      }

      const event = {
        type: 'request',
        at: new Date().toISOString(),
        ...safeTarget(request.url()),
        method: decision.method,
        level: decision.level,
        reason: decision.reason,
        execution: '阻断',
      };
      reportEvent(blocked, onBlocked, event);
      await route.abort('blockedbyclient');
    } catch (error) {
      // Fail closed: an unexpected guard error must not let the request through.
      const event = { type: 'guard-error', at: new Date().toISOString(), reason: String(error) };
      reportEvent(blocked, onBlocked, event);
      try {
        await route.abort('blockedbyclient');
      } catch {
        // If abort itself fails, there is nothing safe left to do; the caller must stop.
      }
    }
  };

  await target.route('**/*', handler);

  // BrowserContext does not emit page dialogs. Attach per page when using a context.
  const isContext =
    typeof target.newPage === 'function' || typeof target.pages === 'function';
  let dialogGuard = null;
  if (!isContext) {
    try {
      dialogGuard = installDialogGuard(target, { onBlocked });
    } catch {
      dialogGuard = null;
    }
  }

  return {
    blocked,
    dialogs: dialogGuard ? dialogGuard.dialogs : [],
    get events() {
      return [...blocked, ...(dialogGuard ? dialogGuard.dialogs : [])];
    },
    uninstall: async () => {
      if (typeof target.unroute === 'function') await target.unroute('**/*', handler);
      if (dialogGuard) dialogGuard.uninstall();
    },
  };
}

module.exports = {
  DANGEROUS_PATH_SEGMENTS,
  READ_ONLY_METHODS,
  classifyRequest,
  installDialogGuard,
  installReadOnlyGuard,
};
