"""Tests for community mechanics resources."""

from prun_mcp.resources.mechanics import (
    MECHANICS_DIR,
    TOPICS,
    _read_topic,
    format_topics_list,
)


class TestMechanicsData:
    """Tests for mechanics data constants."""

    def test_topics_list(self) -> None:
        """Should have the expected topics."""
        expected = {
            "arc",
            "building-degradation",
            "hq",
            "planet",
            "population-infrastructure",
            "ship-blueprints",
            "workforce",
        }
        assert set(TOPICS) == expected

    def test_mechanics_dir_exists(self) -> None:
        """Mechanics directory should exist."""
        assert MECHANICS_DIR.exists(), f"Expected {MECHANICS_DIR} to exist"

    def test_all_topic_files_exist(self) -> None:
        """All topic _index.md files should exist."""
        for topic in TOPICS:
            path = MECHANICS_DIR / topic / "_index.md"
            assert path.exists(), f"Expected {path} to exist"


class TestReadTopic:
    """Tests for _read_topic function."""

    def test_read_existing_topic(self) -> None:
        """Should read content from existing topic."""
        content = _read_topic("arc")
        assert isinstance(content, str)
        assert len(content) > 0

    def test_read_nonexistent_topic(self) -> None:
        """Should return error message for non-existent topic."""
        content = _read_topic("nonexistent-topic")
        assert "Content not found" in content

    def test_all_topics_readable(self) -> None:
        """All topics should be readable."""
        for topic in TOPICS:
            content = _read_topic(topic)
            assert isinstance(content, str)
            assert len(content) > 0
            assert "Content not found" not in content


class TestFormatTopicsList:
    """Tests for format_topics_list function."""

    def test_returns_string(self) -> None:
        """Should return a string."""
        result = format_topics_list()
        assert isinstance(result, str)

    def test_contains_header(self) -> None:
        """Should contain header text."""
        result = format_topics_list()
        assert "Available" in result
        assert "mechanics" in result

    def test_contains_all_topics(self) -> None:
        """Should contain all topic URIs."""
        result = format_topics_list()
        for topic in TOPICS:
            assert f"pct-mechanics://{topic}" in result
