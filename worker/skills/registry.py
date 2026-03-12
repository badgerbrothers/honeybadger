"""Skill registry for Markdown-based skills."""
from pathlib import Path
from skills.loader import Skill, parse_skill_md


# Load skills from Markdown files
_SKILLS_DIR = Path(__file__).parent
_SKILL_REGISTRY: dict[str, Skill] = {}


def _load_skills():
    """Load all SKILL.md files from subdirectories."""
    for skill_dir in _SKILLS_DIR.iterdir():
        if skill_dir.is_dir() and not skill_dir.name.startswith('_'):
            skill_file = skill_dir / 'SKILL.md'
            if skill_file.exists():
                try:
                    skill = parse_skill_md(str(skill_file))
                    _SKILL_REGISTRY[skill.name] = skill
                except Exception as e:
                    print(f"Warning: Failed to load skill from {skill_file}: {e}")


# Load skills on module import
_load_skills()


def get_skill(name: str) -> Skill | None:
    """Get skill by name."""
    return _SKILL_REGISTRY.get(name)


def list_skills() -> list[str]:
    """List all available skill names."""
    return list(_SKILL_REGISTRY.keys())


def is_valid_skill(name: str) -> bool:
    """Check if skill name is valid."""
    return name in _SKILL_REGISTRY


# Export registry for testing
SKILL_REGISTRY = _SKILL_REGISTRY
