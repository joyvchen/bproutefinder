"""Supabase upsert helpers. All operations are idempotent (on_conflict=slug)."""
from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_SERVICE_KEY

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    return _client


def upsert_route(route: dict, dry_run: bool = False) -> None:
    """Insert or update a route record. Uses slug as the conflict key."""
    if dry_run:
        print(f"  [dry-run] Would upsert: {route.get('slug')}")
        return
    client = get_client()
    client.table("routes").upsert(route, on_conflict="slug").execute()


def upsert_editorial_feature(route_id: str, source_url: str, source_title: str, dry_run: bool = False) -> None:
    if dry_run:
        print(f"  [dry-run] Would upsert editorial: {route_id} from {source_url}")
        return
    client = get_client()
    client.table("editorial_features").upsert(
        {"route_id": route_id, "source_url": source_url, "source_title": source_title},
        on_conflict="route_id,source_url",
    ).execute()


def sync_scores(dry_run: bool = False) -> None:
    """Call the stored procedure that refreshes recommendation_score + is_top_pick."""
    if dry_run:
        print("  [dry-run] Would sync recommendation scores")
        return
    client = get_client()
    client.rpc("sync_recommendation_scores").execute()


def fetch_routes_needing_detail(limit: int | None = None) -> list[dict]:
    """Return routes that haven't had their detail page scraped yet."""
    client = get_client()
    q = (
        client.table("routes")
        .select("id, slug, source_url, name")
        .is_("detail_scraped_at", "null")
        .order("created_at")
    )
    if limit:
        q = q.limit(limit)
    result = q.execute()
    return result.data or []


def fetch_all_routes_for_editorial() -> list[dict]:
    """Return all routes with their source_url for editorial matching."""
    client = get_client()
    result = client.table("routes").select("id, slug, source_url, name").execute()
    return result.data or []


def mark_detail_scraped(route_id: str) -> None:
    client = get_client()
    from datetime import datetime, timezone
    client.table("routes").update(
        {"detail_scraped_at": datetime.now(timezone.utc).isoformat()}
    ).eq("id", route_id).execute()
