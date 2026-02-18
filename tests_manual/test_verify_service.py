"""Manual test script for VerifyService.

Run with: conda run -n cjm-transcript-verify python tests_manual/test_verify_service.py

Tests the VerifyService against the test graph database to verify:
- Document verification results
- Integrity check computation
- Sample segment extraction
- Jump-to-index functionality
"""

import asyncio
from pathlib import Path

# Plugin system
from cjm_plugin_system.core.manager import PluginManager
from cjm_plugin_system.core.scheduling import SafetyScheduler

# VerifyService
from cjm_transcript_verify.services.verify import VerifyService, DEBUG_VERIFY_SERVICE

# Enable debug output
import cjm_transcript_verify.services.verify as verify_module
verify_module.DEBUG_VERIFY_SERVICE = True


# Test data paths
PROJECT_ROOT = Path(__file__).parent.parent
TEST_GRAPH_DB = PROJECT_ROOT / "test_files" / "graph.db"
MANIFESTS_DIR = PROJECT_ROOT / ".cjm" / "manifests"

# Known document ID from test database
TEST_DOCUMENT_ID = "3e5f5cd8-3e26-4eb0-a744-2089a7a310ef"


def print_separator(title: str):
    """Print a section separator."""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print('=' * 60)


async def main():
    """Run VerifyService tests."""

    print_separator("VerifyService Test")
    print(f"Test graph DB: {TEST_GRAPH_DB}")
    print(f"Manifests dir: {MANIFESTS_DIR}")
    print(f"Test document ID: {TEST_DOCUMENT_ID}")

    # -------------------------------------------------------------------------
    # Initialize plugin manager
    # -------------------------------------------------------------------------
    print_separator("Plugin Manager Setup")

    manager = PluginManager(
        scheduler=SafetyScheduler(),
        search_paths=[MANIFESTS_DIR]
    )
    manager.discover_manifests()

    print(f"Discovered {len(manager.discovered)} plugins")

    # Load the graph plugin
    graph_plugin_name = "cjm-graph-plugin-sqlite"
    graph_meta = manager.get_discovered_meta(graph_plugin_name)

    if not graph_meta:
        print(f"ERROR: Plugin {graph_plugin_name} not found!")
        return

    print(f"Found plugin: {graph_meta.name} v{graph_meta.version}")

    success = manager.load_plugin(graph_meta, {
        "db_path": str(TEST_GRAPH_DB),
        "readonly": True,
    })

    print(f"Plugin loaded: {success}")

    if not success:
        print("ERROR: Failed to load plugin!")
        return

    # -------------------------------------------------------------------------
    # Create VerifyService
    # -------------------------------------------------------------------------
    print_separator("VerifyService Creation")

    verify_service = VerifyService(manager)
    print(f"Plugin available: {verify_service.is_available()}")

    # -------------------------------------------------------------------------
    # Test verify_document
    # -------------------------------------------------------------------------
    print_separator("Test: verify_document")

    result = await verify_service.verify_document_async(TEST_DOCUMENT_ID)

    if result is None:
        print("ERROR: verify_document returned None!")
    else:
        print("\n--- Document Info ---")
        print(f"  ID: {result.document_id}")
        print(f"  Title: {result.document_title}")
        print(f"  Media Type: {result.document_media_type}")

        print("\n--- Segment Stats ---")
        print(f"  Count: {result.segment_count}")
        print(f"  Total Duration: {result.total_duration:.2f}s")
        print(f"  Avg Duration: {result.avg_segment_duration:.2f}s")

        print("\n--- Integrity Checks ---")
        print(f"  STARTS_WITH: {result.starts_with_count} (expected 1) -> {'PASS' if result.has_starts_with else 'FAIL'}")
        print(f"  NEXT chain: {result.next_count}/{result.segment_count - 1} -> {'PASS' if result.next_chain_complete else 'FAIL'}")
        print(f"  PART_OF: {result.part_of_count}/{result.segment_count} -> {'PASS' if result.part_of_complete else 'FAIL'}")
        print(f"  Timing: {result.segments_missing_timing} missing -> {'PASS' if result.all_have_timing else 'FAIL'}")
        print(f"  Sources: {result.segments_missing_sources} missing -> {'PASS' if result.all_have_sources else 'FAIL'}")

        print("\n--- Source Plugins ---")
        for plugin in result.source_plugins:
            print(f"  - {plugin}")

        print("\n--- All Checks Passed ---")
        print(f"  {result.all_checks_passed}")

        print("\n--- First Segments ---")
        for sample in result.first_segments:
            dur = f"{sample.duration:.2f}s" if sample.duration else "N/A"
            print(f"  [{sample.index}] {sample.text[:40]}... ({dur})")

        print("\n--- Last Segments ---")
        for sample in result.last_segments:
            dur = f"{sample.duration:.2f}s" if sample.duration else "N/A"
            print(f"  [{sample.index}] {sample.text[:40]}... ({dur})")

    # -------------------------------------------------------------------------
    # Test get_segment_by_index
    # -------------------------------------------------------------------------
    print_separator("Test: get_segment_by_index")

    # Test valid index
    sample = await verify_service.get_segment_by_index_async(TEST_DOCUMENT_ID, 5)
    if sample:
        print(f"Index 5: [{sample.index}] {sample.text}")
        print(f"  Time: {sample.start_time}s - {sample.end_time}s")
    else:
        print("Index 5: Not found")

    # Test invalid index
    sample_invalid = await verify_service.get_segment_by_index_async(TEST_DOCUMENT_ID, 999)
    print(f"Index 999 (invalid): {'Found' if sample_invalid else 'Not found (expected)'}")

    # Test negative index
    sample_negative = await verify_service.get_segment_by_index_async(TEST_DOCUMENT_ID, -1)
    print(f"Index -1 (negative): {'Found' if sample_negative else 'Not found (expected)'}")

    # -------------------------------------------------------------------------
    # Test get_segment_count
    # -------------------------------------------------------------------------
    print_separator("Test: get_segment_count")

    count = await verify_service.get_segment_count_async(TEST_DOCUMENT_ID)
    print(f"Segment count: {count}")

    # -------------------------------------------------------------------------
    # Test with invalid document
    # -------------------------------------------------------------------------
    print_separator("Test: Invalid Document ID")

    invalid_result = await verify_service.verify_document_async("invalid-uuid-12345")
    print(f"Invalid document result: {invalid_result} (expected None)")

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------
    print_separator("Cleanup")

    manager.unload_all()
    print("Plugins unloaded")

    print_separator("Tests Complete")


if __name__ == "__main__":
    asyncio.run(main())
