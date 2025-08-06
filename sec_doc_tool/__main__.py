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
    return parser.parse_args(args)


if __name__ == "__main__":
    init_logging()

    args = parse_args(sys.argv[1:])
    print(args)
    print("processing not implemented yet")
