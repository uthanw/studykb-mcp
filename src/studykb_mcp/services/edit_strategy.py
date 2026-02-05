"""Edit strategy - Three-tier matching algorithm (Kilocode-style).

This module implements the core editing logic with three-tier fallback:
1. Exact match
2. Whitespace-flexible match
3. Token-based match
"""

import re
from dataclasses import dataclass


@dataclass
class ReplaceResult:
    """Result of a replacement operation."""

    success: bool
    content: str | None = None
    match_type: str | None = None  # "exact" | "whitespace_flexible" | "token"
    error: str | None = None


class EditStrategy:
    """Three-tier matching strategy - Kilocode style.

    Attempts replacement in order:
    1. Exact string match
    2. Whitespace-flexible match (normalizes whitespace)
    3. Token-based match (ignores all whitespace between tokens)
    """

    def perform_replacement(
        self,
        content: str,
        old_str: str,
        new_str: str,
        expected_count: int = 1,
    ) -> ReplaceResult:
        """Perform replacement using three-tier matching strategy.

        Args:
            content: Original file content
            old_str: String to search for
            new_str: Replacement string
            expected_count: Expected number of matches (default 1)

        Returns:
            ReplaceResult with success status and updated content or error
        """
        # Normalize line endings
        original_eol = self._detect_line_ending(content)
        normalized_content = content.replace("\r\n", "\n")
        normalized_old = old_str.replace("\r\n", "\n")
        normalized_new = new_str.replace("\r\n", "\n")

        # Tier 1: Exact match
        exact_count = normalized_content.count(normalized_old)
        if exact_count == expected_count:
            result = normalized_content.replace(normalized_old, normalized_new)
            return ReplaceResult(
                success=True,
                content=self._restore_line_ending(result, original_eol),
                match_type="exact",
            )

        # Tier 2: Whitespace-flexible match
        ws_regex = self._create_whitespace_flexible_regex(normalized_old)
        try:
            ws_matches = list(re.finditer(ws_regex, normalized_content, re.MULTILINE))
            ws_count = len(ws_matches)
            if ws_count == expected_count:
                result = self._replace_matches(
                    normalized_content, ws_matches, normalized_new
                )
                return ReplaceResult(
                    success=True,
                    content=self._restore_line_ending(result, original_eol),
                    match_type="whitespace_flexible",
                )
        except re.error:
            ws_count = 0

        # Tier 3: Token-based match
        token_regex = self._create_token_regex(normalized_old)
        try:
            token_matches = list(
                re.finditer(token_regex, normalized_content, re.MULTILINE)
            )
            token_count = len(token_matches)
            if token_count == expected_count:
                result = self._replace_matches(
                    normalized_content, token_matches, normalized_new
                )
                return ReplaceResult(
                    success=True,
                    content=self._restore_line_ending(result, original_eol),
                    match_type="token",
                )
        except re.error:
            token_count = 0

        # All tiers failed
        return ReplaceResult(
            success=False,
            error=self._format_match_error(
                normalized_old,
                {"exact": exact_count, "whitespace": ws_count, "token": token_count},
                expected_count,
            ),
        )

    def _detect_line_ending(self, content: str) -> str:
        """Detect original line ending style.

        Args:
            content: File content

        Returns:
            "\\r\\n" for Windows, "\\n" for Unix
        """
        if "\r\n" in content:
            return "\r\n"
        return "\n"

    def _restore_line_ending(self, content: str, eol: str) -> str:
        """Restore original line ending style.

        Args:
            content: Content with normalized line endings
            eol: Original line ending style

        Returns:
            Content with restored line endings
        """
        if eol == "\r\n":
            return content.replace("\n", "\r\n")
        return content

    def _create_whitespace_flexible_regex(self, text: str) -> str:
        """Create whitespace-flexible regex pattern.

        Converts consecutive whitespace to \\s+ pattern.

        Args:
            text: Original search text

        Returns:
            Regex pattern string
        """
        # Escape special characters
        escaped = re.escape(text)
        # Replace escaped whitespace sequences with \\s+
        pattern = re.sub(r"(\\ )+", r"\\s+", escaped)
        pattern = re.sub(r"(\\t)+", r"\\s+", pattern)
        pattern = re.sub(r"(\\n)+", r"\\s+", pattern)
        return pattern

    def _create_token_regex(self, text: str) -> str:
        """Create token-based regex pattern.

        Ignores all whitespace differences, only matches token sequence.

        Args:
            text: Original search text

        Returns:
            Regex pattern string
        """
        # Tokenize: extract code tokens (identifiers, numbers, operators)
        tokens = re.findall(r"[\w\d]+|[^\w\d\s]", text)
        if not tokens:
            return re.escape(text)

        # Build token sequence pattern (allow any whitespace between tokens)
        pattern = r"\s*".join(re.escape(token) for token in tokens)
        return pattern

    def _replace_matches(
        self, content: str, matches: list[re.Match], replacement: str
    ) -> str:
        """Replace all matches from back to front to avoid position shift.

        Args:
            content: Original content
            matches: List of regex matches
            replacement: Replacement string

        Returns:
            Content with replacements applied
        """
        result = content
        for match in reversed(matches):
            result = result[: match.start()] + replacement + result[match.end() :]
        return result

    def _format_match_error(
        self, old_str: str, counts: dict[str, int], expected: int
    ) -> str:
        """Format detailed match error message.

        Args:
            old_str: The search string that failed
            counts: Match counts for each tier
            expected: Expected match count

        Returns:
            Formatted error message with recovery suggestions
        """
        preview = old_str[:200] + ("..." if len(old_str) > 200 else "")
        return f"""在文件中找不到匹配内容

<error_details>
搜索内容:
{preview}

匹配结果:
- 精确匹配: {counts['exact']} 处
- 空白符容错匹配: {counts['whitespace']} 处
- Token 匹配: {counts['token']} 处
- 期望匹配: {expected} 处

恢复建议:
1. 使用 read_workspace_file 确认文件的当前内容
2. 确保 old_string 与文件内容精确匹配（包括空白符和缩进）
3. 添加更多上下文以确保唯一匹配
4. 检查文件是否已被其他操作修改
</error_details>"""
