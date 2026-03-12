"""Tests for Markdown-based skill implementations."""
from skills.loader import Skill
from skills.registry import get_skill


def test_research_report_skill_properties():
    """Test research report skill has correct properties."""
    skill = get_skill("research_report")
    assert skill is not None
    assert skill.name == "research_report"
    assert len(skill.description) > 0
    assert len(skill.system_prompt) > 0
    assert len(skill.allowed_tools) > 0
    assert "browser.open" in skill.allowed_tools
    assert "web.fetch" in skill.allowed_tools
    assert len(skill.output_format) > 0
    assert len(skill.example_tasks) > 0


def test_webpage_skill_properties():
    """Test webpage skill has correct properties."""
    skill = get_skill("webpage")
    assert skill is not None
    assert skill.name == "webpage"
    assert len(skill.description) > 0
    assert len(skill.system_prompt) > 0
    assert len(skill.allowed_tools) > 0
    assert "file.write" in skill.allowed_tools
    assert len(skill.output_format) > 0
    assert len(skill.example_tasks) > 0


def test_file_analysis_skill_properties():
    """Test file analysis skill has correct properties."""
    skill = get_skill("file_analysis")
    assert skill is not None
    assert skill.name == "file_analysis"
    assert len(skill.description) > 0
    assert len(skill.system_prompt) > 0
    assert len(skill.allowed_tools) > 0
    assert "file.read" in skill.allowed_tools
    assert len(skill.output_format) > 0
    assert len(skill.example_tasks) > 0


def test_skill_allowed_tools_list():
    """Test all skills return list of tool names."""
    skill_names = ["research_report", "webpage", "file_analysis"]
    for name in skill_names:
        skill = get_skill(name)
        assert skill is not None
        assert isinstance(skill.allowed_tools, list)
        assert all(isinstance(tool, str) for tool in skill.allowed_tools)


def test_skill_system_prompt_not_empty():
    """Test all skills have non-empty system prompts."""
    skill_names = ["research_report", "webpage", "file_analysis"]
    for name in skill_names:
        skill = get_skill(name)
        assert skill is not None
        assert len(skill.system_prompt) > 50  # Should be substantial
