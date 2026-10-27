# Hardened fork notes

This fork differs from upstream (stickerdaniel/linkedin-mcp-server) in one code
change: the `send_message` MCP tool is removed. The browser-side sender in
`linkedin/message_sender.py` is left in place but is unreachable from any
registered tool. `connect_with_person` is still present and is a write action.

Forked at upstream commit a943666 (v4.28.0). Do not update from upstream or
use `uvx ...@latest`; review diffs first.

## Run it low-risk

- Use a secondary LinkedIn account. LinkedIn's User Agreement prohibits
  automated access, and any account can be restricted or banned.
- Log in once by hand, with browser cookie auto-import off:

      ./scripts/run-hardened.sh --login

- Then run the server on loopback only:

      ./scripts/run-hardened.sh

- Keep per-call approval on in your MCP client for `connect_with_person`.
  Never auto-approve it. Page content (profiles, posts, messages) is untrusted
  and can carry prompt injection.
- Session cookies live in `~/.linkedin-mcp/profile/`. Treat it like a password.

## What the script pins

- `--no-auto-import`: never reads cookies from your local Chrome profile.
- `LINKEDIN_MCP_CHECK_FOR_UPDATES=off`: no PyPI version check.
- HTTP transport, if you pass it, binds `127.0.0.1` (the upstream default).

The only other outbound call is a GitHub issue search sent on error, with a
fixed query string and no personal data.
