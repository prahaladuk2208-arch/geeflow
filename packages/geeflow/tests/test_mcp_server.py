"""The MCP server must register fully-typed tools without touching the network."""

import asyncio

from geeflow.mcp.server import mcp

CORE_TOOLS = {
    "gee_init",
    "catalog_search",
    "dataset_info",
    "scene_availability",
    "build_composite",
    "compute_indices",
    "thumbnail",
    "region_stats",
    "export_composite",
    "export_tasks",
    "sample_polygons",
    "execute_code",
}

LULC_TOOLS = {
    "lulc_validate",
    "lulc_check",
    "lulc_feature_stack",
    "lulc_analyze",
    "lulc_classify",
    "lulc_collector_script",
}


def _tools():
    return asyncio.run(mcp.list_tools())


def test_core_tools_registered():
    names = {t.name for t in _tools()}
    assert CORE_TOOLS <= names


def test_lulc_tools_registered_when_installed():
    try:
        import lulc_engine  # noqa: F401
    except ImportError:
        return  # optional dependency absent; nothing to assert
    names = {t.name for t in _tools()}
    assert LULC_TOOLS <= names


def test_every_tool_has_typed_schema_and_description():
    for tool in _tools():
        assert tool.description, f"{tool.name} is missing a description"
        schema = tool.inputSchema
        assert schema.get("type") == "object", f"{tool.name} has no object schema"
        # the flaw we're fixing in other GEE MCP servers: tools with empty schemas
        params = schema.get("properties", {})
        required_free = {"export_tasks", "gee_init"}
        if tool.name not in required_free:
            assert params, f"{tool.name} has an empty parameter schema"


def test_unknown_composite_id_message():
    from geeflow.mcp import server

    try:
        server._get("composite_999")
    except ValueError as e:
        assert "build_composite" in str(e)
    else:
        raise AssertionError("expected ValueError for unknown composite id")
