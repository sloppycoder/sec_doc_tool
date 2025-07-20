prompt = """
You're a mutual fund researcher that analyze SEC filings and extract information from them.
The text below is a snippet from a SEC 485BPOS filing. Typically it contains several sections,
including Prospectus and Statement of Additoinal Information (a.k.a SAI).

Please read through it and produce a 150 words summary of the content.
In addition, label the contents with tags below:

- "fund_names": a list of fund names mentioned in the snippet, separated by comma
- "fund_tickers": a list of fund tickers mentioned in the snippet, separated by comma
- "is_prospectus": "yes" if the snippet contains a prospectus section, otherwise "no"
- "is_sai": "yes" if the snippet contains a sentence that indicates it is part of statement of additional information (SAI), otherwise "no"
- "has_portfolio_manager_bio": "yes" if the snippet contains a portfolio manager biography, otherwise "no"
- "has_portfolio_manager_ownership": "yes" if the snippet contains information about beneficial ownership by the portfolio manager ownership information, otherwise "no"
- "has_fund_management_info": "yes" if the snippet contains information about fund management, otherwise "no"
- "has_trustee_bio": "yes" if the snippet contains a trustee (a.k.a. independent trustee, interested person, chairman of commitee etc) biography, otherwise "no"
- "has_trustee_compensation": "yes" if the snippet contains information about trustee compensation, otherwise "no"

Please add a few more tags if you find them relevant to the content of the snippet.

<TEXT_TO_TAG>
{TEXT_TO_TAG}
</TEXT_TO_TAG>

use the below template for response, do NOT use JSON as output format

Summary:
<summary>

Tags:
- <tag1>: yes
- <tag2>: no
"""
