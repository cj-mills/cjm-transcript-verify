"""Demo application for cjm-transcript-verify library.

Demonstrates the Verify step with graph database verification,
integrity checks, and sample inspection. Works standalone for testing.

Run with: python demo_app.py
"""

from pathlib import Path
import asyncio
import tempfile

from fasthtml.common import (
    fast_app, Div, H1, P, Span,
    APIRouter,
)

# Plugin system
from cjm_plugin_system.core.manager import PluginManager
from cjm_plugin_system.core.scheduling import SafetyScheduler

# DaisyUI components
from cjm_fasthtml_daisyui.core.resources import get_daisyui_headers
from cjm_fasthtml_daisyui.core.testing import create_theme_persistence_script
from cjm_fasthtml_daisyui.components.data_display.badge import (
    badge, badge_colors, badge_styles, badge_sizes
)
from cjm_fasthtml_daisyui.utilities.semantic_colors import text_dui

# Tailwind utilities
from cjm_fasthtml_tailwind.utilities.spacing import p, m
from cjm_fasthtml_tailwind.utilities.sizing import h, container, max_w
from cjm_fasthtml_tailwind.utilities.typography import font_size, font_weight
from cjm_fasthtml_tailwind.utilities.flexbox_and_grid import (
    flex_display, flex_direction, justify, items, gap,
)
from cjm_fasthtml_tailwind.core.base import combine_classes

# App core
from cjm_fasthtml_app_core.core.routing import register_routes
from cjm_fasthtml_app_core.core.htmx import handle_htmx_request

# State store
from cjm_workflow_state.state_store import SQLiteWorkflowStateStore
from cjm_fasthtml_interactions.core.state_store import get_session_id

# Library imports
from cjm_transcript_verify.html_ids import VerifyHtmlIds
from cjm_transcript_verify.models import VerifyUrls, VerificationResult
from cjm_transcript_verify.services.verify import VerifyService
from cjm_transcript_verify.components.step_renderer import render_verify_step
from cjm_transcript_verify.routes.init import init_verify_routers


# =============================================================================
# Test Data
# =============================================================================

# Path to test graph database
TEST_GRAPH_DB = Path(__file__).parent / "test_files" / "graph.db"

# Demo workflow/session IDs
DEMO_WORKFLOW_ID = "verify-demo"
DEMO_SESSION_ID = "default"


# =============================================================================
# Async Helpers
# =============================================================================

async def find_and_verify_document(verify_service):
    """Find first Document node and verify it in a single async context."""
    if not verify_service.is_available():
        return None, None

    try:
        # Find Document nodes using find_nodes_by_label action
        result = await verify_service._manager.execute_plugin_async(
            verify_service._plugin_name,
            action="find_nodes_by_label",
            label="Document",
            limit=1,
        )

        # Result format: {"nodes": [...], "count": N}
        nodes = result.get("nodes", [])
        if not nodes or len(nodes) == 0:
            return None, None

        document_id = nodes[0].get("id")
        if not document_id:
            return None, None

        # Verify the document
        verification_result = await verify_service.verify_document_async(document_id)
        return document_id, verification_result

    except Exception as e:
        print(f"[Demo] Error: {e}")
        return None, None


def run_async(coro):
    """Run an async coroutine from sync context, creating a fresh event loop."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# =============================================================================
# Demo Page Renderer
# =============================================================================

def render_demo_page(verify_service, urls, state_store, session_id):
    """Create the demo page content with verification dashboard."""

    if not verify_service.is_available():
        return Div(
            # Header
            Div(
                H1("Verify Demo", cls=combine_classes(font_size._3xl, font_weight.bold)),
                Span(
                    "Plugin Not Available",
                    cls=combine_classes(badge, badge_styles.outline, badge_sizes.sm, badge_colors.error)
                ),
                cls=combine_classes(flex_display, justify.between, items.center, m.b(4))
            ),
            P(
                "The graph plugin is not available. Please check plugin configuration.",
                cls=combine_classes(text_dui.base_content.opacity(70), m.b(6))
            ),
            P(
                f"Graph DB: {TEST_GRAPH_DB}",
                cls=combine_classes(font_size.sm, text_dui.base_content.opacity(60))
            ),
            P(
                f"Exists: {TEST_GRAPH_DB.exists()}",
                cls=combine_classes(font_size.sm, text_dui.base_content.opacity(60))
            ),
            id=VerifyHtmlIds.VERIFY_CONTAINER,
            cls=combine_classes(
                container, max_w._4xl, m.x.auto,
                h.full, flex_display, flex_direction.col,
                p(4), gap(4)
            )
        )

    # Find Document and verify it in a single async call
    document_id, result = run_async(find_and_verify_document(verify_service))

    if not document_id:
        return Div(
            # Header
            Div(
                H1("Verify Demo", cls=combine_classes(font_size._3xl, font_weight.bold)),
                Span(
                    "No Document Found",
                    cls=combine_classes(badge, badge_styles.outline, badge_sizes.sm, badge_colors.warning)
                ),
                cls=combine_classes(flex_display, justify.between, items.center, m.b(4))
            ),
            P(
                "No Document node found in the graph database. "
                "Please run the cjm-transcript-review demo first to create test data.",
                cls=combine_classes(text_dui.base_content.opacity(70), m.b(6))
            ),
            P(
                f"Graph DB: {TEST_GRAPH_DB}",
                cls=combine_classes(font_size.sm, text_dui.base_content.opacity(60))
            ),
            id=VerifyHtmlIds.VERIFY_CONTAINER,
            cls=combine_classes(
                container, max_w._4xl, m.x.auto,
                h.full, flex_display, flex_direction.col,
                p(4), gap(4)
            )
        )

    if result is None:
        return Div(
            # Header
            Div(
                H1("Verify Demo", cls=combine_classes(font_size._3xl, font_weight.bold)),
                Span(
                    "Verification Failed",
                    cls=combine_classes(badge, badge_styles.outline, badge_sizes.sm, badge_colors.error)
                ),
                cls=combine_classes(flex_display, justify.between, items.center, m.b(4))
            ),
            P(
                f"Failed to verify document {document_id[:12]}...",
                cls=combine_classes(text_dui.base_content.opacity(70), m.b(6))
            ),
            id=VerifyHtmlIds.VERIFY_CONTAINER,
            cls=combine_classes(
                container, max_w._4xl, m.x.auto,
                h.full, flex_display, flex_direction.col,
                p(4), gap(4)
            )
        )

    # Store document_id in state for sample route to use
    workflow_state = state_store.get_state(DEMO_WORKFLOW_ID, session_id)
    step_states = workflow_state.get("step_states", {})
    step_states["verify"] = {"document_id": document_id}
    workflow_state["step_states"] = step_states
    state_store.update_state(DEMO_WORKFLOW_ID, session_id, workflow_state)

    return Div(
        # Header
        Div(
            H1("Verify Demo", cls=combine_classes(font_size._3xl, font_weight.bold)),
            Span(
                "Plugin Loaded",
                cls=combine_classes(badge, badge_styles.outline, badge_sizes.sm, badge_colors.success)
            ),
            cls=combine_classes(flex_display, justify.between, items.center, m.b(4))
        ),
        P(
            "Verify the context graph after commit. Displays integrity checks and sample segments.",
            cls=combine_classes(text_dui.base_content.opacity(70), m.b(6))
        ),

        # Verification dashboard
        render_verify_step(result=result, urls=urls),

        cls=combine_classes(
            container, max_w._5xl, m.x.auto,
            flex_display, flex_direction.col,
            p(4), gap(4)
        )
    )


# =============================================================================
# Main Application
# =============================================================================

def main():
    """Initialize the verify demo and start the server."""
    print("\n" + "=" * 70)
    print("Initializing cjm-transcript-verify Demo")
    print("=" * 70)

    # Initialize FastHTML app
    APP_ID = "txverify"

    app, rt = fast_app(
        pico=False,
        hdrs=[*get_daisyui_headers(), create_theme_persistence_script()],
        title="Verify Demo",
        htmlkw={'data-theme': 'light'},
        session_cookie=f'session_{APP_ID}_',
        secret_key=f'{APP_ID}-demo-secret',
    )

    router = APIRouter(prefix="")

    # -------------------------------------------------------------------------
    # Set up plugin manager
    # -------------------------------------------------------------------------
    print("\n[Plugin System]")

    project_root = Path(__file__).parent
    manifests_dir = project_root / ".cjm" / "manifests"

    plugin_manager = PluginManager(
        scheduler=SafetyScheduler(),
        search_paths=[manifests_dir]
    )
    plugin_manager.discover_manifests()

    # Load the graph plugin with test database
    graph_plugin_name = "cjm-graph-plugin-sqlite"
    graph_meta = plugin_manager.get_discovered_meta(graph_plugin_name)
    plugin_loaded = False

    if graph_meta:
        try:
            # Override db_path to use test database
            success = plugin_manager.load_plugin(graph_meta, {
                "db_path": str(TEST_GRAPH_DB),
                "readonly": True  # Read-only for verification
            })
            plugin_loaded = success
            status = "loaded" if success else "failed"
            print(f"  {graph_plugin_name}: {status}")
            print(f"  Database: {TEST_GRAPH_DB}")
        except Exception as e:
            print(f"  {graph_plugin_name}: error - {e}")
    else:
        print(f"  {graph_plugin_name}: not found")

    print(f"  Test database exists: {TEST_GRAPH_DB.exists()}")

    # -------------------------------------------------------------------------
    # Create State Store
    # -------------------------------------------------------------------------
    temp_db = Path(tempfile.gettempdir()) / "cjm_transcript_verify_demo_state.db"
    state_store = SQLiteWorkflowStateStore(temp_db)
    print(f"\n[State Store]")
    print(f"  Database: {temp_db}")

    # -------------------------------------------------------------------------
    # Create VerifyService
    # -------------------------------------------------------------------------
    verify_service = VerifyService(plugin_manager, graph_plugin_name)

    # -------------------------------------------------------------------------
    # Initialize Verify Routers
    # -------------------------------------------------------------------------
    verify_routers, urls, verify_routes = init_verify_routers(
        state_store=state_store,
        workflow_id=DEMO_WORKFLOW_ID,
        prefix="/verify",
        verify_service=verify_service,
    )

    print("\n[Verify Routes]")
    print(f"  urls.verify: {urls.verify}")
    print(f"  urls.sample: {urls.sample}")

    # -------------------------------------------------------------------------
    # Page routes
    # -------------------------------------------------------------------------
    @router
    def index(request, sess):
        """Demo homepage."""
        session_id = get_session_id(sess)
        return handle_htmx_request(
            request,
            lambda: render_demo_page(verify_service, urls, state_store, session_id)
        )

    # -------------------------------------------------------------------------
    # Register routes
    # -------------------------------------------------------------------------
    register_routes(app, router)

    # Register verify routers
    for verify_router in verify_routers:
        register_routes(app, verify_router)

    # Debug output
    print("\n" + "=" * 70)
    print("Registered Routes:")
    print("=" * 70)
    for route in app.routes:
        if hasattr(route, 'path'):
            print(f"  {route.path}")
    print("=" * 70)
    print("Demo App Ready!")
    print("=" * 70 + "\n")

    return app


if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading

    app = main()

    port = 5034
    host = "0.0.0.0"
    display_host = 'localhost' if host in ['0.0.0.0', '127.0.0.1'] else host

    print(f"Server: http://{display_host}:{port}")
    print()

    timer = threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{port}"))
    timer.daemon = True
    timer.start()

    uvicorn.run(app, host=host, port=port)
