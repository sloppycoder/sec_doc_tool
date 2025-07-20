import json
import os
import socket
import time
from datetime import datetime
from pathlib import Path

import pytest

import sec_doc_tool.tagging.llm_tagger as llm_tagger
from sec_doc_tool import ChunkedDocument

sample_filings = {
    # Morgan Stanley Insight Fund
    ("1002427", "0001133228-24-004879"): [
        7,  # prospectus
        39,  # fund management persons
        165,  # start of SAI
        166,  # SAI table of contents
        258,  # independent trustee ownership range
        259,  # independent trustee ownership range
        287,  # portfolio manager ownership range
    ],
    # LEUTHOLD FUNDS, INC.
    ("1000351", "0001387131-19-000505"): [
        44,  # portfolio manager bio, contains "Statement of Additional Information"
        45,  # portfolio manager bio
        78,  # tickers, "Statement of Additional Information" section start
        128,  # interested person ownership range
        139,  # portfolio manager ownership range
    ],
}


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

    tag_result, _, _ = llm_tagger.tag_with_api(filing.chunks[7].text)
    assert (
        tag_result
        and tag_result["summary"]
        and "Insight Fund" in tag_result["tags"]["fund_names"]
        and tag_result["tags"]["has_portfolio_manager_ownership"] == "no"
    )


# @pytest.mark.skip(reason="for local testing only")
def test_batch_tag_with_api():
    for model in [
        "vertex_ai/gemini-2.5-flash",
        "openai/gpt-4o-mini",
        "hosted_vllm/microsoft/Phi-4-mini-instruct",
    ]:
        os.environ["TAGGING_MODEL"] = model

        for (cik, accessio_number), chunk_nums in sample_filings.items():
            filing = ChunkedDocument.load(cik, accessio_number)
            assert filing

            text_chunks = [filing.chunks[i].text for i in chunk_nums]
            text_size = sum(len(c) for c in text_chunks)
            start_t = time.time()
            tag_results, token_count, cost = llm_tagger.batch_tag_with_api(text_chunks)
            elasped_t = time.time() - start_t
            key = f"{cik}/{accessio_number}"
            meta = {
                "text_size": text_size,
                "token_count": token_count,
                "cost": cost,
                "elapsed_time": elasped_t,
                "timestsamp": datetime.now().isoformat(),
            }

            _append_test_result(
                model=model.split("/")[-1],
                filing_key=key,
                tag_results=tag_results,
                meta=meta,
            )


def _append_test_result(
    model,
    filing_key,
    tag_results,
    meta,
    filename=Path(__file__).parent.parent / "tmp/test_llm_tagger_results.json",
):
    """
    Append tag_results to a JSON file under the model key, merging with existing content.
    """
    if os.path.exists(filename):
        with open(filename, "r") as f:
            try:
                data = json.load(f)
            except Exception:
                data = {}
    else:
        data = {}

    if model not in data:
        data[model] = {}

    if filing_key not in data[model]:
        data[model][filing_key] = []

    data[model][filing_key].append({"meta": meta, "tag_results": tag_results})

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
