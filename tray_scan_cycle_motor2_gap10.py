#!/usr/bin/env python3
"""Run the tray scan cycle with Motor 2/Y timing set to pulse=5us, gap=10us.

The implementation lives in tray_scan_cycle.py. This separate filename is
provided so the updated Motor 2 speed version is easy to identify and run.
"""

from tray_scan_cycle import main


if __name__ == "__main__":
    main()
