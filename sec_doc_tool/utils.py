"""
In order to compare the tagging result form different models,
the output is organized into the following data structure:

record_tagging_batch add tagging run to the following dataframe

| cik       | accession_number | batch_id  | chunk_nums |
|-----------|------------------|-----------|------------|
| 123456    | 1111-11-1111     | 123456    | "1,2,3"    |
| 223344    | 2222-22-2222     | 65432d1   | "4,5"      |

record_append_batch appends the tagging results to following dataframe
contains the model names as column, tag names and values as rows.

| batch_id  | chunk_num | tag          | model1 | model2 |
|-----------|-----------|--------------|--------|--------|
| 123456    |      0    | tag1         | yes    | no     |
| 123456    |      0    | tag2         | yes    | yes    |
| 123456    |      0    | summary      | ...    | ...    |
| 123456    |      0    | extra        | ...    | ...    |
| 123456    |      0    | _token_count | 1234   | 2345   |
| 123456    |      0    | _cost.       | 0.0012 | 0.0023 |
| 123456    |      0    | _text_size   | 12345  | 12345  |

"""


def record_tagging_batch(
    batch_id: str, cik: str, accessio_number: str, chunk_nums: list[int]
):
    pass


def record_append_batch(batch_id: str, tag_results: list[dict], meta: dict):
    pass
