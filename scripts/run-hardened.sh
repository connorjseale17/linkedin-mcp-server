#!/usr/bin/env bash
# Run the LinkedIn MCP server from this checkout with the risky defaults off.
set -euo pipefail
cd "$(dirname "$0")/.."
export LINKEDIN_MCP_CHECK_FOR_UPDATES=off
exec uv run --frozen python -m linkedin_mcp_server --no-auto-import "$@"
