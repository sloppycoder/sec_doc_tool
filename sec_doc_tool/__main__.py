import argparse
import logging
import os
import sys

from dotenv import load_dotenv

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


def parse_args(args):
    parser = argparse.ArgumentParser(description="SEC Document Tagging Tool")
    parser.add_argument(
        "doc",
        nargs="?",
        help="cik/accession pair (e.g. 1002427/0001133228-24-004879)",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=str,
        help="File containing cik/accession pairs, one per line",
    )
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default="vertex_ai/gemini-2.5-flash",
        help="Model to use for tagging",
    )
    parser.add_argument(
        "--api-base",
        type=str,
        help="API base for hosted vLLM server",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="API key hosted vLLM server or OpenAI",
    )
    return parser.parse_args(args)


def get_doc_list(args):
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

    args = parse_args(sys.argv[1:])

    doc_list = get_doc_list(args)
    if len(doc_list) == 0:
        logger.error("No valid documents found.")
        sys.exit(1)

    for cik, accession_number in doc_list:
        print(f"{cik}/{accession_number}")
