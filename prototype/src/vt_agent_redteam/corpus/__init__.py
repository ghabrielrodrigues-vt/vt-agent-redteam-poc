"""Corpus loading utilities and YAML scenario files."""

from pathlib import Path

from vt_agent_redteam.corpus.loader import filter_scenarios, load_corpus

CORPUS_DIR = Path(__file__).parent

__all__ = ["CORPUS_DIR", "load_corpus", "filter_scenarios"]
