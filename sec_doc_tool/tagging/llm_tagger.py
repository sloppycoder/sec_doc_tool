import json
import logging
import os

from litellm import completion
from litellm.cost_calculator import completion_cost
from litellm.utils import token_counter

from sec_doc_tool.tagging.llm_tagger_prompt import prompt

logger = logging.getLogger(__name__)

model = os.environ.get("MODEL", "gemini-2.5-flash")

# upper limit for text send to LLM
# to prevent abnormally large text chunk (usually result from bugs)
# to exceed API token limit or local server capacity
MAX_TEXT_LENGTH = 4000


def tag_with_llm(text: str) -> tuple[dict, int, float]:
    """
    Use LiteLLM to get tags for a block of text.

    Args:
        text: The text to analyze and tag

    Returns:
        tuple[dict, float]: A tuple containing (tags dictionary, token count, cost in dollars)
    """
    try:
        formatted_prompt = prompt.replace("{TEXT_TO_TAG}", text)
        if len(formatted_prompt) > MAX_TEXT_LENGTH:
            logger.warning(
                f"text chunk {len(formatted_prompt)} truncated. {formatted_prompt[:100]}"
            )
            formatted_prompt = formatted_prompt[:MAX_TEXT_LENGTH]

        messages = [{"role": "user", "content": formatted_prompt}]
        token_count = token_counter(model=model, messages=messages)

        response = completion(
            model=model,
            messages=messages,
            temperature=0,
        )

        cost = completion_cost(completion_response=response)

        content = response.choices[0].message.content  # pyright: ignore
        result = _parse_md_json(content)  # pyright: ignore
        if result:
            return result, token_count, cost
        else:
            logger.warning(f"No JSON block found in LLM response: {content}")
    except Exception as e:
        logger.error(f"Error in tag_with_llm: {e}")

    return {}, 00, 0.0


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
