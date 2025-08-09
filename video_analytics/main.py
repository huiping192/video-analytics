#!/usr/bin/env python3
"""
Video Analytics Main Entry Point - legacy-compatible entry point
"""

from .cli.main import main

# Backward compatibility
if __name__ == "__main__":
    main()