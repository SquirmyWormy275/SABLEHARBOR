# Private-runtime browser sessions

The local service names its session cookie `sh_audit_session_<namespace>`, where the namespace is the first 32 hexadecimal characters of SHA256 over the canonical private audit-store root. The path itself is not sent to the browser. The name is stable across restarts and ports for the same runtime, and different private runtime roots receive different names.

This prevents separate localhost workrooms from overwriting each other's cookies: browser cookies are scoped by host/path, not by port. Login, authenticated cookie reads and logout all use the same derived name. Logout expires only that runtime's cookie. The namespace is an identifier, not a secret or an authorization decision; token validation, bearer authentication, CSRF and origin checks remain in place. Login cookie HttpOnly, SameSite, Secure configuration, lifetime and path are unchanged.

There is no fallback to the previous fixed `sh_audit_session` name. After an older service is restarted with this change, sign in again. No running service is automatically restarted, and existing audit state or principal credentials are not migrated by this change. Moving a private runtime to a different canonical path also changes its cookie namespace.

The HTTP endpoint and response contracts are unchanged. Tests use two actual applications sharing a single cookie jar on the same host and different ports, verifying concurrent sessions, logout isolation, same-root restart stability, rejected foreign/legacy cookies, unchanged CSRF/origin checks and bearer authentication, and the explicit insecure-cookie setting used by a local HTTP service.
