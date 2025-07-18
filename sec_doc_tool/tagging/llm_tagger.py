import json
import logging
import os
from typing import cast

from litellm import completion
from litellm.cost_calculator import completion_cost

from sec_doc_tool.tagging.llm_tagger_prompt import prompt

logger = logging.getLogger(__name__)

model = os.environ.get("MODEL", "gemini-2.5-flash")


def tag_with_llm(text: str) -> tuple[dict, float]:
    """
    Use LiteLLM to get tags for a block of text.

    Args:
        text: The text to analyze and tag

    Returns:
        tuple[dict, float]: A tuple containing (tags dictionary, cost in dollars)
    """
    try:
        formatted_prompt = prompt.replace("{TEXT_TO_TAG}", text)

        response = completion(
            model=model,
            messages=[{"role": "user", "content": formatted_prompt}],
            temperature=0,
        )

        cost = completion_cost(completion_response=response)
        content = cast(str, response.choices[0].message.content)  # type: ignore
        result = _parse_md_json(content)
        if result:
            return result, cost
        else:
            logger.warning(f"No JSON block found in LLM response: {content}")
            return {}, 0.0

    except Exception as e:
        logger.error(f"Error in tag_with_llm: {e}")
        return {}, 0.0


def _parse_md_json(md: str) -> dict | None:
    """Parse a markdown string that contains a JSON block."""
    start = md.find("```json")
    if start == -1:
        return None

    start += len("```json")
    end = md.find("```", start)
    if end == -1:
        return None

    json_str = md[start:end].strip()
    return json.loads(json_str)
