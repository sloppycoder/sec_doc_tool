import shlex
from pathlib import Path

from sec_doc_tool.__main__ import get_doc_list


def test_get_doc_list_single():
    docs = get_doc_list(shlex.split("123/45567890-13-2333333"))
    assert docs[0] == ("123", "45567890-13-2333333")


def test_get_doc_list_file():
    test_file = str(Path(__file__).parent / "mockdata/doc.lst")
    docs = get_doc_list(shlex.split(f"--file {test_file}"))
    # Should exclude comments and blank lines
    assert len(docs) == 1 and docs[0] == ("123", "45567890-13-2333333")
