"""Broker abstraction.

Design goal: swap providers via a single interface. The demo provider
is a thin adapter over the in-process MockMarket. Real providers
(Kite/Groww) implement the same protocol but are only active when
credentials are configured. We never fabricate a connection.
"""
