#!/usr/bin/env python3
"""Alias → export_static.py (Sat Oct 10 remaster ship pattern)."""
import runpy
runpy.run_path(__file__.replace("export_snapshot.py", "export_static.py"), run_name="__main__")
