"""Tests for the survey metadata endpoint (frontend contract) and MCP wiring."""

import inspect

import pytest

from backend.mcp import server as mcp_server
from backend.mcp import tools as mcp_tools
from backend.mcp.server import create_mcp_server
from backend.schemas.fields import (
    ADDITIONAL_INFORMATION_MAX_LENGTH,
    AGE_MAX,
    AGE_MIN,
    HEIGHT_MAX_CM,
    HEIGHT_MIN_CM,
    MAX_ALLERGIES,
    MAX_CONDITIONS,
    MAX_MEDICATIONS,
    MAX_SYMPTOMS,
    WEIGHT_MAX_KG,
    WEIGHT_MIN_KG,
)

METADATA = "/api/v1/assessments/metadata"


def test_metadata_is_public(client) -> None:
    """The wizard can fetch its definition before the patient signs in."""
    response = client.get(METADATA)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "Patient Health Assessment"


def test_metadata_describes_the_six_steps(client) -> None:
    """Step order and titles match the healthcare onboarding flow."""
    steps = client.get(METADATA).json()["steps"]

    assert [step["step"] for step in steps] == [1, 2, 3, 4, 5, 6]
    assert [step["key"] for step in steps] == [
        "basic_information",
        "medical_history",
        "current_symptoms",
        "medications",
        "allergies",
        "review",
    ]
    assert [step["title"] for step in steps] == [
        "Basic Information",
        "Medical History",
        "Current Symptoms",
        "Medications",
        "Allergies",
        "Review & Submit",
    ]
    required = {step["key"] for step in steps if step["required"]}
    assert required == {"basic_information", "medical_history", "review"}


def test_metadata_lists_the_survey_options(client) -> None:
    """Controlled vocabularies are served by the backend, not hard-coded."""
    options = client.get(METADATA).json()["options"]

    assert [gender["value"] for gender in options["genders"]] == [
        "male",
        "female",
        "other",
        "prefer_not_to_say",
    ]
    assert [item["value"] for item in options["medical_conditions"]] == [
        "diabetes",
        "hypertension",
        "asthma",
        "heart_related",
        "kidney_related",
        "allergies",
        "other",
        "none",
    ]
    other = next(
        item for item in options["medical_conditions"] if item["value"] == "other"
    )
    assert other["requires_details"] is True
    assert [item["value"] for item in options["severities"]] == [
        "mild",
        "moderate",
        "severe",
    ]


def test_metadata_limits_match_the_validation_rules(client) -> None:
    """The advertised limits are the ones the schemas enforce."""
    limits = client.get(METADATA).json()["limits"]

    assert limits["age"] == {"min": AGE_MIN, "max": AGE_MAX}
    assert limits["height_cm"] == {"min": HEIGHT_MIN_CM, "max": HEIGHT_MAX_CM}
    assert limits["weight_kg"] == {"min": WEIGHT_MIN_KG, "max": WEIGHT_MAX_KG}
    assert (
        limits["additional_information_max_length"]
        == ADDITIONAL_INFORMATION_MAX_LENGTH
    )
    assert limits["max_conditions"] == MAX_CONDITIONS
    assert limits["max_symptoms"] == MAX_SYMPTOMS
    assert limits["max_medications"] == MAX_MEDICATIONS
    assert limits["max_allergies"] == MAX_ALLERGIES


def test_every_mcp_tool_documents_itself() -> None:
    """MCP exposes the docstrings as tool descriptions, so they must exist."""
    assert len(mcp_tools.TOOL_FUNCTIONS) == 4
    for tool in mcp_tools.TOOL_FUNCTIONS:
        docstring = inspect.getdoc(tool)
        assert docstring, f"{tool.__name__} is missing a docstring"
        for section in ("Args:", "Returns:", "Raises:"):
            assert section in docstring, f"{tool.__name__} lacks a {section} section"


def test_mcp_server_requires_the_optional_dependency() -> None:
    """The MCP server fails with a clear message when no MCP package is installed."""
    if mcp_server.FastMCP is None:
        with pytest.raises(RuntimeError, match="'fastmcp' package is required"):
            create_mcp_server()
    else:  # pragma: no cover - only when the optional dependency is present
        server = create_mcp_server()
        assert server is not None
        # Registration succeeded; the docstrings supply the tool descriptions.
        for tool in mcp_tools.TOOL_FUNCTIONS:
            assert inspect.getdoc(tool)