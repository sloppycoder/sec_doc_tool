import shlex
from pathlib import Path

from sec_doc_tool.__main__ import get_doc_list, parse_args


def test_get_doc_list_single():
    args = parse_args(shlex.split("123/45567890-13-2333333"))
    docs = get_doc_list(args)
    assert docs[0] == ("123", "45567890-13-2333333")


def test_get_doc_list_file():
    test_file = str(Path(__file__).parent / "mockdata/doc.lst")
    args = parse_args(shlex.split(f"--file {test_file}"))
    docs = get_doc_list(args)
    # Should exclude comments and blank lines
    assert len(docs) == 1 and docs[0] == ("123", "45567890-13-2333333")
