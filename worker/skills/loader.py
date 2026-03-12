"""Skill loader for Markdown-based skill definitions."""
from dataclasses import dataclass
import re


@dataclass
class Skill:
    """Skill configuration loaded from Markdown."""
    name: str
    description: str
    system_prompt: str
    allowed_tools: list[str]
    output_format: str
    example_tasks: list[str]


def parse_skill_md(file_path: str) -> Skill:
    """Parse a SKILL.md file and return Skill object."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split frontmatter and body
    parts = content.split('---', 2)
    if len(parts) < 3:
        raise ValueError(f"Invalid SKILL.md format in {file_path}")

    frontmatter = parts[1].strip()
    body = parts[2].strip()

    # Parse frontmatter (simple YAML parsing)
    metadata = {}
    current_key = None
    current_list = []

    for line in frontmatter.split('\n'):
        line = line.rstrip()
        if ':' in line and not line.startswith(' '):
            if current_key and current_list:
                metadata[current_key] = current_list
                current_list = []
            key, value = line.split(':', 1)
            current_key = key.strip()
            value = value.strip()
            if value:
                metadata[current_key] = value
        elif line.startswith('  - '):
            current_list.append(line[4:].strip())

    if current_key and current_list:
        metadata[current_key] = current_list

    # Extract system prompt from body
    system_prompt_match = re.search(r'## System Prompt\s+(.*?)(?=\n##|\Z)', body, re.DOTALL)
    system_prompt = system_prompt_match.group(1).strip() if system_prompt_match else ""

    # Extract example tasks
    example_tasks = []
    examples_match = re.search(r'## Example Tasks\s+(.*?)(?=\n##|\Z)', body, re.DOTALL)
    if examples_match:
        examples_text = examples_match.group(1).strip()
        example_tasks = [line.strip('- ').strip() for line in examples_text.split('\n') if line.strip().startswith('-')]

    return Skill(
        name=metadata.get('name', ''),
        description=metadata.get('description', ''),
        system_prompt=system_prompt,
        allowed_tools=metadata.get('allowed_tools', []),
        output_format=metadata.get('output_format', ''),
        example_tasks=example_tasks
    )
