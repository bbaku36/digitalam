#!/usr/bin/env python3
"""CLI entrypoint for Digitalam Facebook autopost."""

from __future__ import annotations

import sys

from autopost.runner import main


if __name__ == "__main__":
    sys.exit(main())
