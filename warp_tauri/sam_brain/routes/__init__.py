"""SAM API Route Modules

Aggregates all route handlers from individual modules.
Each module exports GET_ROUTES, POST_ROUTES, and optionally DELETE_ROUTES and STREAM_POST_ROUTES dicts.
"""

from routes.core import GET_ROUTES as CORE_GET, POST_ROUTES as CORE_POST
from routes.intelligence import GET_ROUTES as INTEL_GET, POST_ROUTES as INTEL_POST, STREAM_POST_ROUTES as INTEL_STREAM
from routes.cognitive import GET_ROUTES as COG_GET, POST_ROUTES as COG_POST, STREAM_POST_ROUTES as COG_STREAM
from routes.facts import GET_ROUTES as FACTS_GET, POST_ROUTES as FACTS_POST, DELETE_ROUTES as FACTS_DELETE, PREFIX_GET_ROUTES as FACTS_PREFIX_GET
from routes.project import GET_ROUTES as PROJ_GET, POST_ROUTES as PROJ_POST
from routes.index import GET_ROUTES as INDEX_GET, POST_ROUTES as INDEX_POST
from routes.vision import GET_ROUTES as VIS_GET, POST_ROUTES as VIS_POST, STREAM_POST_ROUTES as VIS_STREAM
from routes.image_context import GET_ROUTES as IMG_GET, POST_ROUTES as IMG_POST
from routes.voice import GET_ROUTES as VOICE_GET, POST_ROUTES as VOICE_POST, STREAM_POST_ROUTES as VOICE_STREAM
from routes.distillation import GET_ROUTES as DIST_GET, POST_ROUTES as DIST_POST, PREFIX_GET_ROUTES as DIST_PREFIX_GET


def get_all_get_routes() -> dict:
    """Return combined GET route table."""
    routes = {}
    for module_routes in [CORE_GET, INTEL_GET, COG_GET, FACTS_GET, PROJ_GET, INDEX_GET, VIS_GET, IMG_GET, VOICE_GET, DIST_GET]:
        routes.update(module_routes)
    return routes


def get_all_post_routes() -> dict:
    """Return combined POST route table (non-streaming)."""
    routes = {}
    for module_routes in [CORE_POST, INTEL_POST, COG_POST, FACTS_POST, PROJ_POST, INDEX_POST, VIS_POST, IMG_POST, VOICE_POST, DIST_POST]:
        routes.update(module_routes)
    return routes


def get_all_delete_routes() -> dict:
    """Return combined DELETE route table."""
    routes = {}
    routes.update(FACTS_DELETE)
    return routes


def get_all_stream_post_routes() -> dict:
    """Return combined SSE streaming POST route table."""
    routes = {}
    for module_routes in [INTEL_STREAM, COG_STREAM, VIS_STREAM, VOICE_STREAM]:
        routes.update(module_routes)
    return routes


def get_all_prefix_get_routes() -> dict:
    """Return combined prefix-match GET route table."""
    routes = {}
    routes.update(FACTS_PREFIX_GET)
    routes.update(DIST_PREFIX_GET)
    return routes
