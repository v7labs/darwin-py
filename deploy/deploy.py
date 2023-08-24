#! /usr/bin/env python3
import logging
import sys

logger = logging.getLogger(__name__)

logger.setLevel(logging.INFO)


def main() -> None:
    # TODO: Implement
    logger.info("This function is not yet implemented")
    logger.info(f"This file is {__file__}")
    logger.info("args: {}".format(sys.argv))


if __name__ == "__main__":
    main()
