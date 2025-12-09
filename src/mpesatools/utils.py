#!/usr/bin/env python
"""
Shared utilities for mpesa-tools
"""

from pathlib import Path


def get_default_output_path(input_path, output_format):
    """Generate default output path based on input file and format"""
    input_path = Path(input_path)
    base_name = input_path.with_suffix("")
    return f"{base_name}.{output_format}"
