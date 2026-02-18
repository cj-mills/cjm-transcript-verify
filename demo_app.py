"""Demo application for cjm-transcript-verify library.

Demonstrates the Verify step with graph database verification,
integrity checks, and sample inspection. Works standalone for testing.

Run with: python demo_app.py
"""

from pathlib import Path

from fasthtml.common import (
    fast_app, Div, H1, H2, P, Span,
    APIRouter,
)

# Plugin system
from cjm_plugin_system.core.manager import PluginManager
from cjm_plugin_system.core.scheduling import SafetyScheduler

# DaisyUI components
from cjm_fasthtml_daisyui.core.resources import get_daisyui_headers
from cjm_fasthtml_daisyui.core.testing import create_theme_persistence_script
from cjm_fasthtml_daisyui.components.data_display.badge import badge, badge_styles, badge_sizes
from cjm_fasthtml_daisyui.components.data_display.card import card, card_body
from cjm_fasthtml_daisyui.utilities.semantic_colors import bg_dui, text_dui

# Tailwind utilities
from cjm_fasthtml_tailwind.utilities.spacing import p, m
from cjm_fasthtml_tailwind.utilities.sizing import w, h, container, max_w
from cjm_fasthtml_tailwind.utilities.typography import font_size, font_weight
from cjm_fasthtml_tailwind.utilities.flexbox_and_grid import (
    flex_display, flex_direction, justify, items, gap,
)
from cjm_fasthtml_tailwind.core.base import combine_classes

# App core
from cjm_fasthtml_app_core.core.routing import register_routes
from cjm_fasthtml_app_core.core.htmx import handle_htmx_request

# Library imports (will add more as phases progress)
from cjm_transcript_verify.html_ids import VerifyHtmlIds


# =============================================================================
# Test Data Path
# =============================================================================

# Path to test graph database
TEST_GRAPH_DB = Path(__file__).parent / "test_files" / "graph.db"


# =============================================================================
# Demo Page Renderer
# =============================================================================

def render_demo_page(plugin_loaded: bool):
    """Create the demo page content."""

    # Status badge
    if plugin_loaded:
        status_badge = Span(
            "Plugin Loaded",
            cls=combine_classes(badge, badge_styles.outline, badge_sizes.sm, "badge-success")
        )
    else:
        status_badge = Span(
            "Plugin Not Loaded",
            cls=combine_classes(badge, badge_styles.outline, badge_sizes.sm, "badge-error")
        )

    # Placeholder content card
    placeholder_card = Div(
        Div(
            H2(
                "Verification Dashboard",
                cls=combine_classes(font_size.xl, font_weight.semibold, m.b(2))
            ),
            P(
                "This is a placeholder for the verification dashboard. "
                "Components will be added in Phase 3.",
                cls=combine_classes(text_dui.base_content.opacity(70))
            ),
            Div(
                P(f"Graph DB: {TEST_GRAPH_DB}", cls=str(font_size.sm)),
                P(f"Exists: {TEST_GRAPH_DB.exists()}", cls=str(font_size.sm)),
                cls=combine_classes(m.t(4), p(3), bg_dui.base_200, "rounded-lg", font_size.sm)
            ),
            cls=str(card_body)
        ),
        id=VerifyHtmlIds.VERIFY_CONTENT,
        cls=combine_classes(card, bg_dui.base_100, "shadow-lg")
    )

    return Div(
        # Header
        Div(
            H1("Verify Demo", cls=combine_classes(font_size._3xl, font_weight.bold)),
            status_badge,
            cls=combine_classes(flex_display, justify.between, items.center, m.b(4))
        ),
        P(
            "Verify the context graph after commit. Displays integrity checks and sample segments.",
            cls=combine_classes(text_dui.base_content.opacity(70), m.b(6))
        ),

        # Content area
        placeholder_card,

        id=VerifyHtmlIds.VERIFY_CONTAINER,
        cls=combine_classes(
            container, max_w._4xl, m.x.auto,
            h.full,
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
    app, rt = fast_app(
        pico=False,
        hdrs=[*get_daisyui_headers(), create_theme_persistence_script()],
        title="Verify Demo",
        htmlkw={'data-theme': 'light'},
        secret_key="demo-secret-key"
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
    # Page routes
    # -------------------------------------------------------------------------
    @router
    def index(request, sess):
        """Demo homepage."""
        return handle_htmx_request(request, lambda: render_demo_page(plugin_loaded))

    # -------------------------------------------------------------------------
    # Register routes
    # -------------------------------------------------------------------------
    register_routes(app, router)

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
