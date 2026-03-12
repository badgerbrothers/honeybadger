"""Tests for skill registry."""
from skills.registry import get_skill, list_skills, is_valid_skill, SKILL_REGISTRY


def test_get_skill_valid_name():
    """Test getting skill with valid name."""
    skill = get_skill("research_report")
    assert skill is not None
    assert skill.name == "research_report"


def test_get_skill_invalid_name():
    """Test getting skill with invalid name returns None."""
    skill = get_skill("nonexistent_skill")
    assert skill is None


def test_list_skills_returns_all():
    """Test list_skills returns all registered skills."""
    skills = list_skills()
    assert len(skills) == 3
    assert "research_report" in skills
    assert "webpage" in skills
    assert "file_analysis" in skills


def test_is_valid_skill():
    """Test skill name validation."""
    assert is_valid_skill("research_report") is True
    assert is_valid_skill("webpage") is True
    assert is_valid_skill("file_analysis") is True
    assert is_valid_skill("invalid_skill") is False


def test_registry_has_three_skills():
    """Test registry contains exactly three skills."""
    assert len(SKILL_REGISTRY) == 3
    assert all(skill.name in ["research_report", "webpage", "file_analysis"] for skill in SKILL_REGISTRY.values())
