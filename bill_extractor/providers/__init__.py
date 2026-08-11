"""Registered electricity-provider adapters."""

from .pgvcl import PGVCLParser
from .torrent import TorrentParser
from .ugvcl import UGVCLParser

PARSERS = (UGVCLParser(), TorrentParser(), PGVCLParser())

__all__ = ["PARSERS"]
