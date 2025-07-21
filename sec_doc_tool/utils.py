"""
In order to compare the tagging result form different models,
the output is organized into the following data structure:

record_tagging_batch add tagging run to the following table

CREATE TABLE tagging_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cik TEXT,
    accession_number TEXT,
    chunk_nums TEXT,
    run_at VARCHAR
);

record_append_batch appends the tagging results to following table
contains the model names as column, tag names and values as rows.

CREATE TABLE tagging_results (
    batch_id INTEGER,
    chunk_num TEXT,
    tag TEXT,
    [model_columns] TEXT,
    PRIMARY KEY (batch_id, chunk_num, tag),
    FOREIGN KEY (batch_id) REFERENCES tagging_batches (id)
);

"""

import sqlite3
from typing import Iterable


def record_tagging_batch(
    dbpath: str,
    cik: str,
    accessio_number: str,
    chunk_nums: list[int],
    run_at: str,
) -> int:
    """Record a new tagging batch run to the batches table."""
    # Connect to database
    conn = sqlite3.connect(dbpath)
    cursor = conn.cursor()

    # Create tagging_batches table if it doesn't exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tagging_batches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cik TEXT,
            accession_number TEXT,
            chunk_nums TEXT,
            run_at VARCHAR
        )
    """)

    # Check if this batch already exists
    cursor.execute(
        """
        SELECT id FROM tagging_batches
        WHERE cik = ? AND accession_number = ? AND run_at = ?
    """,
        (str(cik), str(accessio_number), str(run_at)),
    )
    existing = cursor.fetchone()
    if existing:
        conn.close()
        return existing[0]

    # Insert new batch
    cursor.execute(
        """
        INSERT INTO tagging_batches (cik, accession_number, chunk_nums, run_at)
        VALUES (?, ?, ?, ?)
    """,
        (str(cik), str(accessio_number), ",".join(map(str, chunk_nums)), str(run_at)),
    )

    batch_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return batch_id  # pyright: ignore


def record_append_batch(
    dbpath: str,
    batch_id: int,
    chunk_tag_pairs: Iterable[tuple[int, dict]],
    meta: dict,
    model: str,
):
    """Append tagging results to the results table.

    Args:
        batch_id: Batch record ID from batches table
        chunk_tag_pairs: Iterable of (chunk_number, tag_result) tuples
        meta: Metadata dict containing token_count, cost, text_size etc.
        model: Model name (e.g. "gemini-2.5-flash")
    """
    model_name = model

    # Connect to database
    conn = sqlite3.connect(dbpath)
    cursor = conn.cursor()

    # Create tagging_results table if it doesn't exist (initially with basic columns)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tagging_results (
            batch_id INTEGER,
            chunk_num TEXT,
            tag TEXT,
            PRIMARY KEY (batch_id, chunk_num, tag),
            FOREIGN KEY (batch_id) REFERENCES tagging_batches (id)
        )
    """)

    # Check if model column exists, if not add it
    cursor.execute("PRAGMA table_info(tagging_results)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    if model_name not in existing_columns:
        cursor.execute(f"ALTER TABLE tagging_results ADD COLUMN [{model_name}] TEXT")

    # Collect all rows to insert/update
    rows_to_process = []

    for chunk_num, tag_result in chunk_tag_pairs:
        rows_to_process.extend(
            _add_tag_result_rows(batch_id, chunk_num, tag_result, model_name)
        )
        rows_to_process.extend(_add_meta_rows(batch_id, chunk_num, meta, model_name))

    # Insert or update each row
    for row_data in rows_to_process:
        batch_id_val = row_data["batch_id"]
        chunk_num_val = row_data["chunk_num"]
        tag_val = row_data["tag"]
        model_value = row_data[model_name]

        # Check if row exists
        cursor.execute(
            """
            SELECT 1 FROM tagging_results
            WHERE batch_id = ? AND chunk_num = ? AND tag = ?
        """,
            (batch_id_val, chunk_num_val, tag_val),
        )

        if cursor.fetchone():
            # Update existing row
            cursor.execute(
                f"""
                UPDATE tagging_results
                SET [{model_name}] = ?
                WHERE batch_id = ? AND chunk_num = ? AND tag = ?
            """,
                (model_value, batch_id_val, chunk_num_val, tag_val),
            )
        else:
            # Insert new row
            cursor.execute(
                f"""
                INSERT INTO tagging_results (batch_id, chunk_num, tag, [{model_name}])
                VALUES (?, ?, ?, ?)
            """,
                (batch_id_val, chunk_num_val, tag_val, model_value),
            )

    conn.commit()
    conn.close()


def _add_tag_result_rows(
    batch_id: int, chunk_num: int, tag_result: dict, model_name: str
):
    """Helper function to create rows for a single chunk's tag results."""
    rows = []
    if not tag_result:
        return rows

    # Mandatory tags from llm_tagger_prompt.py
    mandatory_tags = {
        "fund_names",
        "fund_tickers",
        "is_prospectus",
        "is_sai",
        "has_portfolio_manager_bio",
        "has_portfolio_manager_ownership",
        "has_fund_management_info",
        "has_trustee_bio",
        "has_trustee_compensation",
    }

    # Add mandatory tags
    if "tags" in tag_result:
        extras = []
        for tag_name, tag_value in tag_result["tags"].items():
            if tag_name in mandatory_tags:
                rows.append(
                    {
                        "batch_id": batch_id,
                        "chunk_num": str(chunk_num),
                        "tag": str(tag_name),
                        model_name: str(tag_value),
                    }
                )
            else:
                # Collect non-mandatory tags for extras
                extras.append(f"{tag_name}: {tag_value}")

        # Add extras as a single concatenated field
        if extras:
            rows.append(
                {
                    "batch_id": batch_id,
                    "chunk_num": str(chunk_num),
                    "tag": "extras",
                    model_name: "; ".join(extras),
                }
            )

    # Add summary
    if "summary" in tag_result:
        rows.append(
            {
                "batch_id": batch_id,
                "chunk_num": str(chunk_num),
                "tag": "summary",
                model_name: str(tag_result["summary"]),
            }
        )

    return rows


def _add_meta_rows(batch_id: int, chunk_num: int, meta: dict, model_name: str):
    """Helper function to create rows for metadata."""
    rows = []
    for meta_key in ["token_count", "cost", "text_size"]:
        if meta_key in meta:
            rows.append(
                {
                    "batch_id": batch_id,
                    "chunk_num": str(chunk_num),
                    "tag": f"_{meta_key}",
                    model_name: str(meta[meta_key]),
                }
            )
    return rows
