#!/usr/bin/env python3
import sys
import os

file_path = os.path.realpath(__file__)
current_dir = os.path.dirname(file_path)
project_root = os.path.abspath(os.path.join(current_dir, ".."))

if '/usr/local/bin' in sys.path:
    sys.path.remove('/usr/local/bin')

if project_root not in sys.path:
    sys.path.insert(0, project_root)

from zonc import run_cli

run_cli()