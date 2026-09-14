"""Test suite configuration.

Force the app into demo mode regardless of the user's .env so tests
against MockMarket and the signal engine are deterministic.
"""
import os

os.environ["DATA_PROVIDER"] = "demo"
os.environ["GROWW_API_KEY"] = ""
os.environ["GROWW_API_SECRET"] = ""
os.environ["GROWW_ACCESS_TOKEN"] = ""
