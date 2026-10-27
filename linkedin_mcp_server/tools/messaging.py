"""
LinkedIn messaging tools.

Provides inbox listing, conversation reading, and message search.

This fork is read-only for messaging: the send_message tool is removed.
"""

import logging
from typing import Annotated, Any

from fastmcp import Context, FastMCP
from pydantic import Field

from linkedin_mcp_server.config.schema import DEFAULT_TOOL_TIMEOUT_SECONDS
from linkedin_mcp_server.core.exceptions import (
    InvalidReferenceError,
)
from linkedin_mcp_server.dependencies import get_ready_extractor, tool_errors
from linkedin_mcp_server.linkedin.identifiers import (
    normalize_person_identifier,
    normalize_thread_id,
)

logger = logging.getLogger(__name__)


def register_messaging_tools(
    mcp: FastMCP, *, tool_timeout: float = DEFAULT_TOOL_TIMEOUT_SECONDS
) -> None:
    """Register all messaging-related tools with the MCP server."""

    @mcp.tool(
        timeout=tool_timeout,
        title="Get Inbox",
        annotations={"readOnlyHint": True, "openWorldHint": True},
        tags={"messaging"},
    )
    @tool_errors
    async def get_inbox(
        ctx: Context,
        limit: Annotated[int, Field(ge=1, le=50)] = 20,
    ) -> dict[str, Any]:
        """
        List recent conversations from the LinkedIn messaging inbox.

        The returned inbox text and result URL come from the ordinary messaging
        inbox. Click-derived conversation references are collected separately
        after requesting the compose page, which avoided inbox auto-opening on
        the measured variant. A row contributes a click-derived reference only
        after its click is followed by an observed different thread path. The
        scan stops at its first unverifiable click. section_errors.inbox
        reports that stop or unavailable scan rows; captured inbox text and
        independently extracted anchors retain their normal handling. A known
        thread_id can bypass row attribution when calling get_conversation.

        Args:
            ctx: FastMCP context for progress reporting
            limit: Maximum number of conversations to load (1-50, default 20)

        Returns:
            Dict with url, sections (inbox -> raw text), optional references, and
            optional section_errors (inbox -> why click-derived references are
            incomplete).
        """
        extractor = await get_ready_extractor(ctx, tool_name="get_inbox")
        logger.info("Fetching inbox (limit=%d)", limit)

        await ctx.report_progress(
            progress=0, total=100, message="Loading messaging inbox"
        )

        result = await extractor.get_inbox(limit=limit)

        await ctx.report_progress(progress=100, total=100, message="Complete")

        return result

    @mcp.tool(
        timeout=tool_timeout,
        title="Get Conversation",
        # Not read-only, though it reads: resolving a username enumerates the
        # inbox by click-visiting rows, and LinkedIn marks a visited row as read.
        # The docstring below has always said so. An unread message the user has
        # not seen is state, and losing it is not something a reader should do.
        annotations={"openWorldHint": True},
        tags={"messaging"},
    )
    @tool_errors
    async def get_conversation(
        ctx: Context,
        linkedin_username: str | None = None,
        thread_id: str | None = None,
        index: Annotated[int, Field(ge=0)] = 0,
    ) -> dict[str, Any]:
        """
        Read a specific messaging conversation.

        Provide either linkedin_username or thread_id to identify the conversation.

        When looked up by linkedin_username, resolution searches the messaging
        inbox for the participant's display name and click-visits every
        matching row to capture its thread ID — LinkedIn's sidebar has no
        anchor hrefs or thread-id attributes, so this is the only available
        path. Each visit selects the row in the LinkedIn UI and may mark it
        as read. Pass thread_id directly to skip this enumeration.

        Username resolution scans matching rows from a requested compose page
        first. Its indexable sequence ends before the first unresolved click,
        missing matching click target, or admitted row that fails the existing
        exact display-name check. An index outside that verified prefix is
        refused with its reason. Search is a fallback only when the inbox scan
        has no observed matching result and no such barrier; it never
        substitutes a result after a stopped or gapped inbox scan. Pass a known
        thread_id to bypass username/index resolution.

        Args:
            ctx: FastMCP context for progress reporting
            linkedin_username: LinkedIn username of the conversation participant; a full profile URL is accepted too
            thread_id: LinkedIn messaging thread ID
            index: 0-based selector for which thread to open when the
                participant has multiple threads (e.g. an organic 1-on-1 plus
                an InMail). Ignored when thread_id is provided. To enumerate
                thread IDs first, call search_conversations.

        Returns:
            Dict with url, sections (conversation -> raw text), and optional references.
        """
        if not linkedin_username and not thread_id:
            raise InvalidReferenceError(
                "Provide at least one of linkedin_username or thread_id"
            )
        if thread_id:
            thread_id = normalize_thread_id(thread_id)
        else:
            linkedin_username = normalize_person_identifier(linkedin_username or "")
        extractor = await get_ready_extractor(ctx, tool_name="get_conversation")
        logger.info(
            "Fetching conversation: username=%s, thread_id=%s, index=%d",
            linkedin_username,
            thread_id,
            index,
        )

        await ctx.report_progress(progress=0, total=100, message="Loading conversation")

        result = await extractor.get_conversation(
            linkedin_username=linkedin_username,
            thread_id=thread_id,
            index=index,
        )

        await ctx.report_progress(progress=100, total=100, message="Complete")

        return result

    @mcp.tool(
        timeout=tool_timeout,
        title="Search Conversations",
        # Same reason as `get_conversation`: enumerating result rows selects them
        # in LinkedIn's UI, which can mark them read. Its own `limit` argument is
        # documented in those terms.
        annotations={"openWorldHint": True},
        tags={"messaging", "search"},
    )
    @tool_errors
    async def search_conversations(
        keywords: str,
        ctx: Context,
        limit: Annotated[int, Field(ge=1, le=50)] = 20,
    ) -> dict[str, Any]:
        """
        Search messages by keyword.

        Click-derived references require an observed different thread path
        after each row click. The first unverifiable click stops further row
        clicks and is reported in section_errors.search_results. Already-read
        text and independently extracted anchors retain their normal handling.
        A result without that diagnostic does not guarantee that every
        conversation was enumerated.

        Args:
            keywords: Search keywords to filter conversations
            ctx: FastMCP context for progress reporting
            limit: Maximum number of search-result rows to enumerate as
                conversation references (1-50, default 20). Each enumeration
                selects the row in LinkedIn's UI and may mark it as read, so
                a low cap is preferable for noisy queries.

        Returns:
            Dict with url, sections (search_results -> raw text), optional
            references, and optional section_errors (search_results -> where
            click-derived references stopped).
        """
        extractor = await get_ready_extractor(ctx, tool_name="search_conversations")
        logger.info("Searching conversations: keywords='%s', limit=%d", keywords, limit)

        await ctx.report_progress(progress=0, total=100, message="Searching messages")

        result = await extractor.search_conversations(keywords, limit=limit)

        await ctx.report_progress(progress=100, total=100, message="Complete")

        return result
