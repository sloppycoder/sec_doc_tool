from sec_doc_tool.tagging.parser import TaggingResponseParser


def test_tagging_response_parser():
    """Test the parser with the provided examples."""

    # Sample responses
    gpt4_response = """The snippet from the SEC 485BPOS filing provides an overview of the Morgan Stanley Insight Fund, focusing on its management and share purchase details. The fund is managed by Morgan Stanley Investment Management Inc., with a team of portfolio managers including Dennis P. Lynch, Sam G. Chainani, and others, who have been managing the fund since the early 2000s. The document notes that the offering of Class L shares has been suspended, while outlining the minimum investment requirements for various share classes, including Class I, Class A, Class C, and Class R6 shares. Investors can purchase or sell shares on days when the NYSE is open, with specific instructions provided for transactions.
- **fund_names**: Insight Fund
- **fund_tickers**:
- **is_prospectus**: yes
- **is_sai**: no
- **has_portfolio_manager_bio**: yes
- **has_portfolio_manager_ownership**: no
- **has_fund_management_info**: yes
- **has_trustee_bio**: no
- **has_trustee_compensation**: no
- **has_minimum_investment_info**: yes
- **has_share_purchase_info**: yes"""

    phi4_response = """Summary:
The Morgan Stanley Prospectus for the Insight Fund provides information about the fund's management, share purchase and sale, and minimum investment amounts. The fund is managed by members of Counterpoint Global, including Dennis P. Lynch, Sam G. Chainani, Jason C. Yeung, Armistead B. Nash, David S. Cohen, and Alexander T. Norton. The fund has suspended offering Class L shares for sale to all investors, but existing Class L shareholders can invest in additional Class L shares through reinvestment of dividends and distributions. The minimum initial investment generally is $1 million for Class I shares and $1,000 for each of Class A and Class C shares of the Fund. The minimum initial investment requirements may be waived for certain investments. Investors can purchase or sell Fund shares on any day the New York Stock Exchange is open for business directly from the Fund by mail, telephone, or through a Morgan Stanley Financial Advisor or an authorized third-party.
Tags:
- fund_names: Insight Fund
- fund_tickers: Not provided
- is_prospectus: yes
- is_sai: no
- has_portfolio_manager_bio: yes
- has_portfolio_manager_ownership: no
- has_fund_management_info: yes
- has_trustee_bio: no
- has_trustee_compensation: no
- additional_tags: minimum investment amounts, share purchase and sale, New York Stock Exchange, Morgan Stanley Financial Advisor, authorized third-party, reinvestment of dividends and distributions, suspended offering Class L shares"""

    gemini_25_response = """
This snippet, extracted from the Morgan Stanley Prospectus's Fund Summary, focuses on the Insight Fund. It details the fund's management structure, identifying Morgan Stanley Investment Management Inc. as the investment adviser. A key section provides biographical information for the fund's six portfolio managers, including Dennis P. Lynch and Sam G. Chainani, listing their titles and the dates they began managing the fund, highlighting their tenure. The document also outlines the procedures for purchasing and selling fund shares. It specifies that Class L shares are no longer offered for sale to new investors, though existing shareholders can reinvest dividends. Minimum initial investment amounts are detailed for Class I ($1 million), Class A and C ($1,000), and Class R6 ($5 million or specific employer plans). Investors can transact shares directly via mail or phone, or through financial advisors and authorized intermediaries.
```json
{
  "fund_names": "Insight Fund",
  "fund_tickers": "N/A",
  "is_prospectus": "yes",
  "is_sai": "no",
  "has_portfolio_manager_bio": "yes",
  "has_portfolio_manager_ownership": "no",
  "has_fund_management_info": "yes",
  "has_trustee_bio": "no",
  "has_trustee_compensation": "no",
  "fund_share_classes": "Class L, Class I, Class A, Class C, Class R6",
  "minimum_investment_info": "yes",
  "purchase_sale_procedures": "yes",
  "investment_adviser": "Morgan Stanley Investment Management Inc."
}
```
"""
    parser = TaggingResponseParser()

    result1 = parser.parse_response(gpt4_response)
    assert (
        result1
        and "Morgan Stanley" in result1["summary"]
        and "Insight Fund" in result1["tags"]["fund_names"]
    )

    result2 = parser.parse_response(phi4_response)
    assert (
        result2
        and "Morgan Stanley" in result2["summary"]
        and "Insight Fund" in result2["tags"]["fund_names"]
    )

    result3 = parser.parse_response(gemini_25_response)
    assert (
        result3
        and "Morgan Stanley" in result3["summary"]
        and "Insight Fund" in result3["tags"]["fund_names"]
    )
