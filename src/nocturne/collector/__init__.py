"""Source-aware free-data collector (Phase 3U).

Official documented APIs first; HTML crawling only where a source's rules are
verified to permit it. Every acquisition is content-addressed, timestamped and
compared against the previous snapshot so provider revisions stay visible.
"""
