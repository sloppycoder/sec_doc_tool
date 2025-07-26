from sec_doc_tool.tagging.text_tagger import tag_with_ner

_sample_text = """
Portfolio Managers
Douglas R. Ramsey, CFA, Chun Wang, CFA, Jun Zhu, CFA, and Greg M. Swenson, CFA, are the portfolio managers
of the Fund. Mr. Ramsey is the chief investment officer and a portfolio manager of the Adviser and has
been a senior analyst of The Leuthold Group since 2005. Mr. Wang is a portfolio manager of the Adviser
and has been a senior analyst of The Leuthold Group since 2009. Ms. Zhu is a portfolio manager of
the Adviser and has been a senior analyst of The Leuthold Group since 2008. Mr. Swenson is a portfolio
manager of the Adviser and has been a senior analyst of The Leuthold Group since 2006.

For important information about purchase and sale of Fund shares, tax information, and payments to
financial intermediaries, please turn to “Important Additional Fund Information” on page 26 of this
Prospectus. """  # noqa: E501


def test_tag_with_ner():
    tags = tag_with_ner(_sample_text)
    assert tags and tags["person_unique"] == 9
