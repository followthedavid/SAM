"""SAM API Facts Routes - Intelligence stats, user facts, fact management."""

from datetime import datetime
from shared_state import get_feedback_db


def api_intelligence_stats() -> dict:
    """Get intelligence core statistics (distillation, feedback, memory)."""
    try:
        from learn.intelligence_core import get_intelligence_core
        core = get_intelligence_core()
        stats = core.get_stats()

        return {
            "success": True,
            "intelligence": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_user_facts(user_id: str = "david") -> dict:
    """Get facts known about a user."""
    try:
        from learn.intelligence_core import get_intelligence_core
        core = get_intelligence_core()
        facts = core.get_user_facts(user_id)
        context = core.get_context_for_user(user_id)

        return {
            "success": True,
            "user_id": user_id,
            "facts": facts,
            "context_snippet": context[:500] if context else "",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_remember_fact(user_id: str, fact: str, category: str = "preference") -> dict:
    """Remember a fact about a user."""
    try:
        from learn.intelligence_core import get_intelligence_core, FactCategory
        core = get_intelligence_core()

        try:
            cat = FactCategory(category)
        except ValueError:
            cat = FactCategory.PREFERENCE

        fact_id = core.remember_fact(user_id, fact, cat, source="api")

        return {
            "success": True,
            "fact_id": fact_id,
            "user_id": user_id,
            "fact": fact,
            "category": category,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_fact_context(user_id: str = "david") -> dict:
    """Get formatted fact context for prompt injection (Phase 1.3.6)."""
    try:
        from memory.fact_memory import get_fact_memory, build_user_context
        fm = get_fact_memory()

        context = build_user_context(user_id, min_confidence=0.3)
        stats = fm.get_stats()

        facts = fm.get_facts(user_id, min_confidence=0.3)
        categories = {}
        for fact in facts:
            cat = fact.category
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "success": True,
            "user_id": user_id,
            "context_string": context,
            "fact_count": len(facts),
            "categories": categories,
            "stats": stats,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_facts_list(user_id: str = "david", category: str = None, min_confidence: float = 0.0, limit: int = 50) -> dict:
    """List facts for a user with optional filtering."""
    try:
        from memory.fact_memory import get_fact_db

        db = get_fact_db()
        facts = db.get_facts(
            user_id=user_id,
            category=category,
            min_confidence=min_confidence,
            limit=limit,
        )

        facts_list = []
        for fact in facts:
            facts_list.append({
                "fact_id": fact.fact_id,
                "fact": fact.fact,
                "category": fact.category,
                "subcategory": fact.subcategory,
                "confidence": round(fact.confidence, 3),
                "source": fact.source,
                "reinforcement_count": fact.reinforcement_count,
                "first_seen": fact.first_seen,
                "last_reinforced": fact.last_reinforced,
                "is_active": fact.is_active,
            })

        return {
            "success": True,
            "user_id": user_id,
            "category_filter": category,
            "min_confidence": min_confidence,
            "count": len(facts_list),
            "facts": facts_list,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_facts_add(fact: str, category: str, user_id: str = "david", source: str = "explicit", confidence: float = None) -> dict:
    """Add a new fact about a user."""
    try:
        from memory.fact_memory import get_fact_db

        db = get_fact_db()
        saved_fact = db.save_fact(
            fact=fact,
            category=category,
            source=source,
            confidence=confidence,
            user_id=user_id,
        )

        return {
            "success": True,
            "action": "created" if saved_fact.reinforcement_count == 1 else "reinforced",
            "fact_id": saved_fact.fact_id,
            "fact": saved_fact.fact,
            "category": saved_fact.category,
            "confidence": round(saved_fact.confidence, 3),
            "source": saved_fact.source,
            "user_id": user_id,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_facts_remove(fact_id: str) -> dict:
    """Remove (deactivate) a fact by ID."""
    try:
        from memory.fact_memory import get_fact_db

        db = get_fact_db()

        fact = db.get_fact(fact_id)
        if not fact:
            return {
                "success": False,
                "error": f"Fact with ID '{fact_id}' not found",
            }

        success = db.deactivate_fact(fact_id, reason="removed_via_api")

        return {
            "success": success,
            "fact_id": fact_id,
            "fact": fact.fact,
            "category": fact.category,
            "action": "deactivated",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_facts_search(query: str, user_id: str = "david", limit: int = 10) -> dict:
    """Search facts by text content."""
    try:
        from memory.fact_memory import get_fact_db

        db = get_fact_db()
        facts = db.search_facts(
            query=query,
            user_id=user_id,
            limit=limit,
        )

        facts_list = []
        for fact in facts:
            facts_list.append({
                "fact_id": fact.fact_id,
                "fact": fact.fact,
                "category": fact.category,
                "subcategory": fact.subcategory,
                "confidence": round(fact.confidence, 3),
                "source": fact.source,
                "reinforcement_count": fact.reinforcement_count,
            })

        return {
            "success": True,
            "query": query,
            "user_id": user_id,
            "count": len(facts_list),
            "facts": facts_list,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def api_facts_get(fact_id: str) -> dict:
    """Get a single fact by ID."""
    try:
        from memory.fact_memory import get_fact_db

        db = get_fact_db()
        fact = db.get_fact(fact_id)

        if not fact:
            return {
                "success": False,
                "error": f"Fact with ID '{fact_id}' not found",
            }

        return {
            "success": True,
            "fact": {
                "fact_id": fact.fact_id,
                "user_id": fact.user_id,
                "fact": fact.fact,
                "category": fact.category,
                "subcategory": fact.subcategory,
                "confidence": round(fact.confidence, 3),
                "initial_confidence": round(fact.initial_confidence, 3),
                "source": fact.source,
                "source_context": fact.source_context,
                "first_seen": fact.first_seen,
                "last_reinforced": fact.last_reinforced,
                "last_accessed": fact.last_accessed,
                "reinforcement_count": fact.reinforcement_count,
                "contradiction_count": fact.contradiction_count,
                "decay_rate": fact.decay_rate,
                "decay_floor": fact.decay_floor,
                "is_active": fact.is_active,
                "metadata": fact.metadata,
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Route tables
GET_ROUTES = {
    "/api/intelligence": lambda params: api_intelligence_stats(),
    "/api/facts": lambda params: api_facts_list(
        user_id=params.get("user", ["david"])[0],
        category=params.get("category", [None])[0],
        min_confidence=float(params.get("min_confidence", ["0.0"])[0]),
        limit=int(params.get("limit", ["50"])[0])
    ),
    "/api/facts/context": lambda params: api_fact_context(params.get("user", ["david"])[0]),
    "/api/facts/search": lambda params: api_facts_search(params.get("q", [""])[0], params.get("user", ["david"])[0], int(params.get("limit", ["10"])[0])) if params.get("q", [""])[0] else {"success": False, "error": "Missing query parameter 'q'"},
}

# Prefix-matched GET routes (for /api/facts/<id>)
PREFIX_GET_ROUTES = {
    "/api/facts/": lambda path, params: api_facts_get(path.split("/")[-1]) if path.split("/")[-1] not in ["context", "search", "remember"] else {"success": False, "error": "Invalid fact ID"},
}

POST_ROUTES = {
    "/api/facts/remember": lambda data: api_remember_fact(data.get("user_id", "david"), data.get("fact", ""), data.get("category", "preference")) if data.get("fact") else {"success": False, "error": "Missing fact"},
    "/api/facts": lambda data: api_facts_add(data.get("fact", ""), data.get("category", ""), data.get("user_id", "david"), data.get("source", "explicit"), data.get("confidence")) if data.get("fact") and data.get("category") else {"success": False, "error": "Missing 'fact' or 'category'"},
}

DELETE_ROUTES = {
    "/api/facts/": lambda path: api_facts_remove(path.split("/")[-1]) if path.split("/")[-1] not in ["context", "search", "remember"] else {"success": False, "error": "Invalid fact ID"},
}
