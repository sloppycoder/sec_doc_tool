import logging
import os

from litellm import batch_completion, completion
from litellm.cost_calculator import completion_cost
from litellm.utils import token_counter

from sec_doc_tool.tagging.llm_tagger_prompt import prompt
from sec_doc_tool.tagging.parser import TaggingResponseParser

logger = logging.getLogger(__name__)


# upper limit for text send to LLM
# to prevent abnormally large text chunk (usually result from bugs)
# to exceed API token limit or local server capacity
MAX_TEXT_LENGTH = 4000

parser = TaggingResponseParser()


def tag_with_api(text: str) -> tuple[dict, int, float]:
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

        model = os.environ.get("TAGGING_MODEL", "")
        if not model:
            logger.error("TAGGING_MODEL environment variable is not set")
            return {}, 0, 0.0

        response = completion(
            model=model,
            messages=messages,
            temperature=0,
        )

        if model.startswith("hosted_vllm/"):
            cost = 0.0
            token_count = token_counter(model="gpt-4o-mini", messages=messages)
        else:
            cost = completion_cost(completion_response=response)
            token_count = token_counter(model=model, messages=messages)

        content = response.choices[0].message.content  # pyright: ignore
        result = parser.parse_response(content)  # pyright: ignore
        if result:
            return result, token_count, cost
        else:
            logger.warning(f"No JSON block found in LLM response: {content}")
    except Exception as e:
        logger.error(f"Error in tag_with_api: {e}")

    return {}, 00, 0.0


def batch_tag_with_api(
    text_chunks: list[str], batch_size: int = 24
) -> tuple[list[dict], int, float]:
    """
    Use LiteLLM to get tags for a batch of text chunks.

    Args:
        text_chunks: The list of text chunks to analyze and tag
        batch_size: The number of chunks to process in parallel

    Returns:
        tuple[list[dict], int, float]: A tuple containing (list of tags dictionaries, total token count, total cost in dollars)
    """
    model = os.environ.get("TAGGING_MODEL", "")
    if not model:
        logger.error("TAGGING_MODEL environment variable is not set")
        return [], 0, 0.0

    results = []
    token_count = 0
    total_cost = 0.0

    try:
        all_messages = []
        for text in text_chunks:
            formatted_prompt = prompt.replace("{TEXT_TO_TAG}", text)
            if len(formatted_prompt) > MAX_TEXT_LENGTH:
                logger.warning(
                    f"text chunk {len(formatted_prompt)} truncated. {formatted_prompt[:100]}"
                )
                formatted_prompt = formatted_prompt[:MAX_TEXT_LENGTH]
            all_messages.append([{"role": "user", "content": formatted_prompt}])

        for i in range(0, len(all_messages), batch_size):
            messages = all_messages[i : i + batch_size]
            responses = batch_completion(
                model=model,
                messages=messages,
                temperature=0,
            )

            if model.startswith("hosted_vllm/"):
                token_count += sum(
                    [
                        token_counter(model="gpt4o-mini", messages=messages)
                        for messages in messages
                    ]
                )
            else:
                total_cost += sum(
                    [
                        completion_cost(completion_response=response)
                        for response in responses
                    ]
                )
                token_count += sum(
                    [
                        token_counter(model=model, messages=messages)
                        for messages in messages
                    ]
                )

            for response in responses:
                content = response.choices[0].message.content  # pyright: ignore
                result = parser.parse_response(content)  # pyright: ignore
                results.append(result if result else {})

        return results, token_count, total_cost

    except Exception as e:
        logger.error(f"Error in batch_tag_with_api: {e}")

    return [], 0, 0.0
