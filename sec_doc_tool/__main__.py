import argparse
import logging
import os
import sys
import time

from dotenv import load_dotenv

from sec_doc_tool import ChunkedDocument

load_dotenv()


def init_logging():
    logging.basicConfig(
        stream=sys.stdout,
        level=getattr(logging, os.getenv("LOG_LEVEL", "").upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # suppress noisy logs
    for logger_name in ("httpcore", "httpx", "openai", "requests", "urllib3"):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


def tag_filing(cik: str, accession_number: str):
    filing = ChunkedDocument.init(cik, accession_number)
    if filing:
        start_t = time.time()
        llm_token_count, llm_cost = filing.tag_all_chunks()
        elasped_t = time.time() - start_t
        logger.info(
            f"{cik}/{accession_number} tagged in {elasped_t:.1f} seconds, {len(filing.chunks)} chunks, {llm_token_count} tokens, ${llm_cost:.4f}"
        )
        filing._save()  # save the new tags
    else:
        logger.warning(f"{cik}/{accession_number} cannot be processed")


def parse_args(args):
    parser = argparse.ArgumentParser(description="SEC Document Tagging Tool")
    parser.add_argument(
        "doc", nargs="?", help="cik/accession pair (e.g. 1002427/0001133228-24-004879)"
    )
    parser.add_argument(
        "-f", "--file", type=str, help="File containing cik/accession pairs, one per line"
    )
    return parser.parse_args(args)


def get_doc_list(args):
    args = parse_args(args)

    doc_list = []
    if args.file:
        try:
            with open(args.file, "r") as f:
                doc_list = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]
        except Exception as e:
            logger.error(f"Failed to read file {args.file}: {e}")
            sys.exit(1)
    elif args.doc:
        doc_list = [args.doc]
    else:
        logger.error("Usage: python -m sec_doc_tool <cik/accession> [-f FILE]")
        sys.exit(1)

    return [tuple(entry.strip().split("/")) for entry in doc_list]


if __name__ == "__main__":
    init_logging()

    doc_list = get_doc_list(sys.argv[1:])
    if len(doc_list) == 0:
        logger.error("No valid documents found.")
        sys.exit(1)

    for cik, accession_number in doc_list:
        tag_filing(cik, accession_number)
