/* ===========================================================================
 * SNAPSHOT — copied from catalog-platform/sites/heygabi-home/public/assets/
 * on 2026-08-26. Black Bloc's site is entirely DISCONNECTED from heygabi
 * (owner decision 2026-08-26, docs/info/phase8-design.md): it shares a domain
 * and nothing else. There is no sync script, no shared deploy, no runtime
 * dependency in either direction. A sixth estate theme reaches this site only
 * if somebody copies this file in again.
 *
 * ⚠️ The BODY below is the estate file verbatim EXCEPT for one hunk marked
 * "BLACK BLOC EDIT" (a non-string `detail` is not a sentence). Keep that
 * marker so a future re-copy is a three-line reapply rather than a diff
 * nobody can read. Its comments still describe the estate's own pages and repos;
 * none of that applies here. What matters is behaviour, and none of these
 * files opens a socket: they read localStorage and stamp attributes. This
 * page talks to its own origin and to the API origin, and to nothing else.
 * ===========================================================================
 */
/**
 * permission-ux.js — turn a failed fetch response into a human sentence.
 * ES module, browser-native, no build step.
 *
 * Owner requirement 2026-08-16: "make sure if any one gets permission blocked
 * they get a warning message and not a https only error. make it a good ux."
 * Nobody sees a bare HTTP status, a raw JSON error body, or a silent dead
 * control. A refusal says three things: what happened, what it needs, and how
 * to get it. A network/server failure is NOT a permission failure —
 * mislabelling an outage sends people to ask for access they already have, so
 * the two are told apart here in one place instead of in every fetch call.
 *
 * This is presentation only. It does not decide who can do what — the gate is
 * black_bloc/api/auth.py. This module only decides the sentence shown when a
 * gate that was already going to refuse, refuses.
 */

/** True for the two status codes that mean "a permission gate refused this", as opposed to a broken request or a dead server. */
export function isPermissionStatus(status) {
  return status === 401 || status === 403;
}

/**
 * Build the sentence for a non-ok fetch Response, given its (already
 * consumed) status and parsed body.
 *
 * @param {number} status        res.status
 * @param {{detail?: string, error?: string}|null} body  parsed JSON body, or null if unreadable/absent
 * @param {{ unauthenticated?: string, need?: string, forbidden?: string, fallback?: string }} [opts]
 *   unauthenticated: message for 401 (default: a lapsed-session prompt)
 *   need: named in the 403 sentence — e.g. "the contributor role". Omit when
 *     the exact role isn't known here; the generic "ask an admin" still
 *     satisfies the standard.
 *   forbidden: full override for the 403 sentence (skips `need` composition)
 *   fallback: message for any other non-ok status, when the body gave no
 *     detail/error of its own. Defaults to a generic retry sentence — never
 *     the raw status code.
 * @returns {string}
 */
export function describeHttpFailure(status, body, opts) {
  const o = opts || {};
  if (status === 401) {
    return o.unauthenticated || 'Your sign-in has lapsed — sign in again.';
  }
  if (status === 403) {
    if (o.forbidden) return o.forbidden;
    const need = o.need ? ` That needs ${o.need}.` : '';
    return `You don't have permission to do that.${need} Ask an admin.`;
  }
  // BLACK BLOC EDIT: only a STRING is a sentence. FastAPI's validation errors
  // put a list of objects in `detail`, and String()-ing that shows a person
  // "[object Object]" — which is a bare status wearing a hat.
  const said = body && (body.detail ?? body.error);
  const serverSaid = typeof said === 'string' && said.trim() ? said : null;
  if (serverSaid) return o.fallback ? `${o.fallback} (${serverSaid})` : serverSaid;
  return o.fallback || 'Something went wrong on the server. Try again shortly.';
}
