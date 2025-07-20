import json
import re
from typing import Any, Dict, Optional


class TaggingResponseParser:
    """Parser for LLM response for tagging"""

    def __init__(self):
        pass

    def parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse response text from various LLM formats into structured data.

        Args:
            response_text: Raw response text from LLM

        Returns:
            Dictionary with 'summary' and 'tags' keys
        """
        # Try JSON parsing first
        json_result = self._try_parse_json(response_text)
        if json_result:
            return json_result

        # Try markdown/bullet format parsing
        return self._parse_markdown_format(response_text)

    def _try_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """Try to extract and parse JSON from the response."""
        # Look for JSON in markdown code blocks
        json_pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
        match = re.search(json_pattern, text, re.DOTALL)

        if match:
            json_str = match.group(1)
            # Extract text before JSON as summary
            text_before_json = text[: match.start()].strip()
        else:
            # Try to find JSON object directly
            json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
            match = re.search(json_pattern, text, re.DOTALL)
            if match:
                json_str = match.group(0)
                text_before_json = text[: match.start()].strip()
            else:
                return None

        try:
            data = json.loads(json_str)
            return self._normalize_json_data(data, text_before_json)
        except json.JSONDecodeError:
            return None

    def _normalize_json_data(
        self, data: Dict[str, Any], summary_text: str = ""
    ) -> Dict[str, Any]:
        """Normalize JSON data to our expected format."""
        result = {"summary": "", "tags": {}}

        # Extract summary from JSON or use provided summary text
        if "summary" in data:
            result["summary"] = str(data["summary"])
        elif summary_text:
            # Clean up the summary text
            summary = re.sub(r"\n+", " ", summary_text)
            summary = re.sub(r"\s+", " ", summary).strip()
            result["summary"] = summary

        # All other fields go to tags
        for key, value in data.items():
            if key != "summary":
                result["tags"][key] = str(value)

        return result

    def _parse_markdown_format(self, text: str) -> Dict[str, Any]:
        """Parse markdown/bullet format responses."""
        result = {"summary": "", "tags": {}}

        # Extract summary
        summary = self._extract_summary(text)
        if summary:
            result["summary"] = summary

        # Extract tags
        tags = self._extract_tags(text)
        result["tags"] = tags

        return result

    def _extract_summary(self, text: str) -> str:
        """Extract summary from various formats."""
        # Look for explicit summary section
        summary_patterns = [
            r"(?:Summary:|summary:)\s*\n?(.*?)(?:\n-|\nTags:|\n\*\*|$)",
            r"^(.*?)(?:\n-|\n\*\*|Tags:|```)",  # First paragraph before tags or code
            r"The snippet.*?(?=\n-|\n\*\*|Tags:|```|$)",  # Specific SEC snippet pattern
            r"^(.*?)(?=```json)",  # Text before JSON code block
        ]

        for pattern in summary_patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                summary = match.group(1).strip()
                # Clean up the summary
                summary = re.sub(r"\n+", " ", summary)
                summary = re.sub(r"\s+", " ", summary)
                if len(summary) > 50:  # Ensure it's substantial
                    return summary

        return ""

    def _extract_tags(self, text: str) -> Dict[str, str]:
        """Extract tags from markdown/bullet format."""
        tags = {}

        # Pattern for bullet points with various formats
        patterns = [
            r"-\s*\*\*(.*?)\*\*:\s*(.*?)(?=\n|$)",  # - **tag**: value
            r"-\s*(.*?):\s*(.*?)(?=\n|$)",  # - tag: value
            r"\*\s*(.*?):\s*(.*?)(?=\n|$)",  # * tag: value
            r"•\s*(.*?):\s*(.*?)(?=\n|$)",  # • tag: value
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for tag_name, tag_value in matches:
                # Clean up the tag name and value
                tag_name = tag_name.strip().lower().replace(" ", "_").replace("-", "_")
                tag_value = tag_value.strip()

                # Handle special cases
                if tag_value.lower() in ["", "not provided", "none", "n/a"]:
                    tag_value = ""

                tags[tag_name] = tag_value

        # remove quotes and extra spaces from keys and values
        tags = {k.strip(" \"'"): v.strip(" \"'") for k, v in tags.items()}

        return tags

    def parse_batch(self, responses: list) -> list:
        """Parse multiple responses."""
        return [self.parse_response(response) for response in responses]
