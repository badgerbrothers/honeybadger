"""Minimal schema validation tests."""
import pytest
from pydantic import ValidationError
from app.schemas.project import ProjectCreate
from app.schemas.conversation import MessageCreate
from app.models.conversation import MessageRole

def test_project_create_valid():
    schema = ProjectCreate(name="Test", description="Desc")
    assert schema.name == "Test"

def test_project_create_name_required():
    with pytest.raises(ValidationError):
        ProjectCreate(name="")

def test_message_create_valid():
    schema = MessageCreate(role=MessageRole.USER, content="Hello")
    assert schema.content == "Hello"

def test_message_create_content_required():
    with pytest.raises(ValidationError):
        MessageCreate(role=MessageRole.USER, content="")
