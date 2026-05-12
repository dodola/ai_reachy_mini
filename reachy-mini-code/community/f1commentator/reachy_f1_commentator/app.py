"""
Standalone app runner for development and testing.

This is a convenience wrapper. You can also run directly:
    python -m reachy_f1_commentator.main
"""

if __name__ == "__main__":
    # Run the main module
    import runpy
    runpy.run_module("reachy_f1_commentator.main", run_name="__main__")


