import os
import socket
from unittest.mock import patch

import pytest

import sec_doc_tool.tagging.llm_tagger as llm_tagger
from sec_doc_tool import ChunkedDocument


@pytest.mark.parametrize(
    "model",
    [
        "vertex_ai/gemini-2.5-flash",
        "openai/gpt-4o-mini",
        # "hosted_vllm/microsoft/Phi-4-mini-instruct",
    ],
)
@pytest.mark.skipif(socket.gethostname() != "uno.local", reason="for local testing only")
def test_tag_with_api(model):
    os.environ["TAGGING_MODEL"] = model

    filing = ChunkedDocument.load("1002427", "0001133228-24-004879")
    assert filing

    tags, _, _ = llm_tagger.tag_with_api(filing.chunks[10].text)
    assert (
        tags
        and "Morgan Stanley" in tags["summary"]
        and "Insight Fund" in tags["tags"]["fund_names"]
    )


@pytest.mark.parametrize(
    "model",
    [
        "vertex_ai/gemini-2.5-flash",
        "openai/gpt-4o-mini",
        # "hosted_vllm/microsoft/Phi-4-mini-instruct",
    ],
)
@pytest.mark.skipif(socket.gethostname() != "uno.local", reason="for local testing only")
def test_batch_tag_with_api(model):
    os.environ["TAGGING_MODEL"] = model

    filing = ChunkedDocument.load("1002427", "0001133228-24-004879")
    assert filing

    # Patch batch_completion to monitor calls but allow real execution
    with patch.object(
        llm_tagger, "batch_completion", wraps=llm_tagger.batch_completion
    ) as mock_batch_completion:
        tags, _, _ = llm_tagger.batch_tag_with_api(
            [c.text for c in filing.chunks[10:15]], batch_size=3
        )
        assert tags and len(tags) == 5
        assert mock_batch_completion.call_count == 2
        assert (
            tags[0]
            and "Morgan Stanley" in tags[0]["summary"]
            and "Insight Fund" in tags[0]["tags"]["fund_names"]
        )
