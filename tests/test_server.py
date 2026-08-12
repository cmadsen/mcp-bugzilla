import pytest
from fastmcp.exceptions import ToolError
from mcp_bugzilla.server import add_custom_fields


def test_custom_fields_are_merged_into_the_payload():
    fields = {"status": "RESOLVED"}
    add_custom_fields(fields, {"cf_test_case": "*Do this\n#That happens"})
    assert fields == {
        "status": "RESOLVED",
        "cf_test_case": "*Do this\n#That happens",
    }


def test_no_custom_fields_leaves_the_payload_alone():
    fields = {"status": "RESOLVED"}
    add_custom_fields(fields, None)
    add_custom_fields(fields, {})
    assert fields == {"status": "RESOLVED"}


def test_built_in_fields_are_rejected():
    fields = {}
    with pytest.raises(ToolError) as excinfo:
        add_custom_fields(fields, {"cf_ok": "yes", "status": "RESOLVED"})
    assert "status" in str(excinfo.value)
    assert fields == {}
