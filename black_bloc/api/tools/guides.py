from __future__ import annotations

import base64
import binascii
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request, Response

from ... import guides
from ...logkinds import FEATURE_PAGES
from ...settings_store import KEY_TYPES
from ..auth import Refused
from ..names import resolve_one
from ..writes import (
    member_read_dependency,
    note,
    reader_dependency,
    require_db,
    require_guild,
    writer_dependency,
)

log = logging.getLogger(__name__)

CREATED_SAID = "**{title}** is made. It is unpublished until you press Publish."
SAVED_SAID = "**{title}** is saved."
PUBLISHED_SAID = "**{title}** is published — members and `/help` can see it now."
UNPUBLISHED_SAID = "**{title}** is unpublished. Staff still see it; members and `/help` do not."
DELETED_SAID = "**{title}** is gone."
RESET_SAID = "**{title}** is back to the words it shipped with."
CONFIRMED_SAID = (
    "Thank you — **{title}** is marked as working. Staff read the count; nothing else was sent."
)
MEDIA_SAID = "The picture on step {position} is replaced."
MEDIA_GUIDE_SAID = "The picture on **{title}** is replaced."
ALL_STALE_SAID = (
    "{count} screenshots are marked for re-shooting. The capture runbook's stale list is the "
    "whole job."
)
ONE_STALE_SAID = (
    "1 screenshot is marked for re-shooting. The capture runbook's stale list is the whole job."
)
ALREADY_ALL_STALE = "Every screenshot was already marked."
NOT_SEEDED = (
    "**{slug}** was written here rather than shipped with Black Bloc, so there is no original to "
    "put back. Nothing was changed."
)
NO_SUCH_STEP = (
    "That step is not part of **{slug}**, so the picture was not uploaded. Reload the guide and "
    "try again."
)
GUIDES_ARE_OFF_FOR_STAFF = (
    "Guides are off for members right now, so nobody but staff can open this page. A Lead turns "
    "them back on from the Settings page under **guides**."
)
NOT_A_NUMBER = (
    "The {what} that arrived is not a number, so nothing was saved. It is a fault in the page "
    "rather than in what you typed — reload the guide and try again."
)
NOTHING_TO_SAVE = (
    "That change arrived with nothing in it, so nothing was saved. It is a fault in the page "
    "rather than in what you typed — reload the guide and try again."
)


def now() -> str:
    return datetime.now(UTC).isoformat()


def person(guild: Any, user_id: Any) -> str | None:
    if not user_id:
        return None
    return resolve_one(guild, user_id)["display_name"] or str(user_id)


def media_url(row: Any) -> str:
    return f"/api/guides/media/{int(row['id'])}"


def media_row(guild: Any, row: Any, alt: str = "") -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "url": media_url(row),
        "step_id": str(row["step_id"]) if row["step_id"] else None,
        "source": row["source"],
        "surface": row["surface"],
        "caption": row["caption"],
        "width": row["width"],
        "height": row["height"],
        "bytes": int(row["bytes"] or 0),
        "sha256": row["sha256"],
        "shot_release": row["shot_release"],
        "shot_at": row["shot_at"],
        "shot_by": str(row["shot_by"]) if row["shot_by"] else None,
        "shot_by_name": person(guild, row["shot_by"]),
        "stale": bool(row["stale"]),
        "stale_since": row["stale_since"],
        "alt": alt,
    }


def step_row(row: Any, pictures: dict[int, Any], guild: Any) -> dict[str, Any]:
    media_id = row["media_id"]
    picture = pictures.get(int(media_id)) if media_id else None
    seed_do, seed_expect = row["seed_do"], row["seed_expect"]
    return {
        "id": str(row["id"]),
        "position": int(row["position"]),
        "do_text": row["do_text"],
        "expect_text": row["expect_text"],
        "media_id": str(media_id) if media_id else None,
        "media": media_row(guild, picture, row["do_text"]) if picture is not None else None,
        "seed_do": seed_do,
        "seed_expect": seed_expect,
        "can_restore": bool(seed_do)
        and (seed_do != row["do_text"] or seed_expect != row["expect_text"]),
        "warnings": guides.lint_step(row["do_text"], row["expect_text"]),
    }


def fault_row(row: Any) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "position": int(row["position"]),
        "symptom": row["symptom"],
        "answer": row["answer"],
    }


def guide_row(
    bot: Any, guild: Any, row: Any, *, steps: int = 0, media: int = 0, stale: int = 0
) -> dict[str, Any]:
    slug = str(row["slug"])
    feature = str(row["feature"])
    return {
        "id": str(row["id"]),
        "slug": slug,
        "title": row["title"],
        "goal": row["goal"],
        "audience": row["audience"],
        "feature": feature,
        "feature_page": FEATURE_PAGES.get(feature),
        "feature_mode": guides.feature_mode(bot.store, guild.id, feature) if guild else None,
        "command": row["command"],
        "sort": int(row["sort"] or 0),
        "published": bool(row["published"]),
        "seeded": guides.is_seeded(row),
        "url": guides.guide_url(bot.settings.origin, slug),
        "step_count": int(steps),
        "media_count": int(media),
        "stale_count": int(stale),
        "updated_at": row["updated_at"],
        "updated_by": str(row["updated_by"]) if row["updated_by"] else None,
        "updated_by_name": person(guild, row["updated_by"]),
    }


def wanted_int(value: Any, what: str) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        raise Refused(400, "bad_number", NOT_A_NUMBER.format(what=what)) from None


def wanted_text(payload: dict[str, Any], name: str, limit: int) -> str:
    return guides.clamp(payload.get(name), limit)


def wanted_steps(payload: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for position, raw in enumerate(payload.get("steps") or (), start=1):
        if position > guides.STEPS_MAX:
            break
        do_text = guides.clamp(raw.get("do_text"), guides.DO_MAX)
        if not do_text:
            raise Refused(400, "no_step_text", guides.STEP_NEEDS_TEXT.format(position=position))
        found.append(
            {
                "id": raw.get("id"),
                "do_text": do_text,
                "expect_text": guides.clamp(raw.get("expect_text"), guides.EXPECT_MAX) or None,
                "media_id": wanted_int(raw.get("media_id"), "picture id"),
            }
        )
    return found


def wanted_faults(payload: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for raw in (payload.get("faults") or ())[: guides.FAULTS_MAX]:
        symptom = guides.clamp(raw.get("symptom"), guides.SYMPTOM_MAX)
        answer = guides.clamp(raw.get("answer"), guides.ANSWER_MAX)
        if symptom and answer:
            found.append({"symptom": symptom, "answer": answer})
    return found


def wanted_facts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw_facts = list(payload.get("facts") or ())
    if len(raw_facts) > guides.FACTS_MAX:
        raise Refused(
            400,
            "too_many_facts",
            guides.TOO_MANY_FACTS.format(limit=guides.FACTS_MAX, count=len(raw_facts)),
        )
    found: list[dict[str, Any]] = []
    for raw in raw_facts:
        kind = str(raw.get("kind") or "").strip().lower()
        ref = str(raw.get("ref") or "").strip()
        if kind not in guides.FACT_KINDS or not ref:
            continue
        refused = guides.refused_fact(kind, ref)
        if refused is not None:
            raise Refused(400, "bad_fact", refused)
        found.append({"kind": kind, "ref": ref})
    return found


def wanted_audience(given: Any, fallback: str) -> str:
    text = str(given or "").strip().lower()
    return text if text in guides.AUDIENCES else fallback


def wanted_feature(given: Any, fallback: str) -> str:
    text = str(given or "").strip().lower()
    return text if text in FEATURE_PAGES else fallback


def wanted_command(given: Any) -> str | None:
    text = str(given or "").strip().lower()
    if not text:
        return None
    return text if text.startswith("/") else f"/{text}"


def picture_bytes(payload: dict[str, Any]) -> bytes:
    raw = str(payload.get("data") or "")
    if raw.startswith("data:"):
        raw = raw.partition(",")[2]
    try:
        return base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        raise Refused(400, "bad_picture", guides.MEDIA_UNREADABLE) from None


def fact_choices() -> dict[str, Any]:
    """What the editor's fact picker may offer — the API's own answer, not a second list."""
    return {
        "settings": sorted(
            key for key in KEY_TYPES if guides.refused_fact(guides.SETTING, key) is None
        ),
        "probes": [
            {"ref": ref, "label": guides.PROBE_LABELS.get(ref, ref)}
            for ref in sorted(guides.PROBES)
        ],
    }


def bytes_word(count: int) -> str:
    if count >= 1024 * 1024:
        return f"{count / (1024 * 1024):.1f} MB"
    return f"{max(1, count // 1024)} KB"


def build_router(bot: Any) -> APIRouter:
    reading_member = member_read_dependency(bot)
    reader = reader_dependency(bot)
    writer = writer_dependency(bot)
    router = APIRouter(prefix="/api/guides", tags=["guides"])

    def _may_edit(who: dict[str, Any], guild: Any) -> None:
        """Read at save time, never at render time — a Lead can lose the role mid-page."""
        if bot.store.get(guild.id, "guides_who_edits") != "manage_guild":
            return
        member = guild.get_member(int(who["id"])) if guild is not None else None
        perms = getattr(member, "guild_permissions", None)
        if not getattr(perms, "manage_guild", False):
            raise Refused(403, "not_a_lead", guides.NOT_YOURS_TO_EDIT)

    async def _editor(request: Request) -> tuple[dict[str, Any], Any]:
        who = await writer(request)
        guild = require_guild(bot)
        require_db(bot)
        _may_edit(who, guild)
        return (who, guild)

    async def _wanted(guild: Any, slug: str, who: dict[str, Any] | None = None) -> Any:
        row = await guides.get_guide(bot.db, guild.id, slug)
        staff = bool(who is None or who.get("staff"))
        hidden = row is not None and not staff and (
            not row["published"] or row["audience"] == guides.STAFF
        )
        if row is None or hidden:
            raise Refused(404, "no_such_guide", guides.NO_SUCH_GUIDE.format(slug=slug[:60]))
        return row

    async def _counts(guide_id: int) -> tuple[int, int, int]:
        steps = await guides.steps_of(bot.db, guide_id)
        pictures = await guides.media_of(bot.db, guide_id)
        return (len(steps), len(pictures), len([one for one in pictures if one["stale"]]))

    async def _whole(guild: Any, row: Any, *, facts: bool = True) -> dict[str, Any]:
        guide_id = int(row["id"])
        steps = await guides.steps_of(bot.db, guide_id)
        pictures = await guides.media_of(bot.db, guide_id)
        by_id = {int(one["id"]): one for one in pictures}
        shown = [step_row(one, by_id, guild) for one in steps]
        resolved: list[dict[str, Any]] = []
        if facts and bot.store.get(guild.id, "guides_show_facts"):
            resolved = await guides.resolve_facts(
                bot, guild, await guides.facts_of(bot.db, guide_id)
            )
        return {
            "guide": guide_row(
                bot,
                guild,
                row,
                steps=len(steps),
                media=len(pictures),
                stale=len([one for one in pictures if one["stale"]]),
            ),
            "steps": shown,
            "faults": [fault_row(one) for one in await guides.faults_of(bot.db, guide_id)],
            "facts": resolved,
            "chosen_facts": [
                {"kind": one["kind"], "ref": one["ref"]}
                for one in await guides.facts_of(bot.db, guide_id)
            ],
            "media": [media_row(guild, one) for one in pictures],
            "read_at": now(),
        }

    @router.get("")
    async def guides_index(request: Request) -> dict[str, Any]:
        """The hub. F-G3: a member sees member guides, published, and nothing else."""
        who = await reading_member(request)
        guild = require_guild(bot)
        require_db(bot)
        staff = bool(who.get("staff"))
        on = guides.guides_on(bot.store, guild.id)
        if not on and not staff:
            raise Refused(409, "guides_off", guides.GUIDES_OFF)
        rows = await guides.list_guides(bot.db, guild.id)
        if not staff:
            rows = [
                row for row in rows if row["published"] and row["audience"] == guides.MEMBER
            ]
        found: list[dict[str, Any]] = []
        for row in rows:
            steps, pictures, stale = await _counts(int(row["id"]))
            found.append(
                guide_row(bot, guild, row, steps=steps, media=pictures, stale=stale)
            )
        return {
            "guides": found,
            "audience": guides.STAFF if staff else guides.MEMBER,
            "may_edit": staff,
            "mode": bot.store.get(guild.id, "guides_mode"),
            "stale": sum(one["stale_count"] for one in found) if staff else 0,
            "features": [
                {"feature": name, "page": page} for name, page in FEATURE_PAGES.items()
            ],
            "fact_choices": fact_choices() if staff else {"settings": [], "probes": []},
            "right_now": guides.right_now(bot, guild),
            "notes": [] if on else [GUIDES_ARE_OFF_FOR_STAFF],
            "checked_at": now(),
        }

    @router.get("/stale", dependencies=[Depends(reader)])
    async def guides_stale() -> dict[str, Any]:
        """The capture session's to-do list, read with the operator token before a browser."""
        guild = require_guild(bot)
        require_db(bot)
        rows = await guides.stale_media(bot.db, guild.id)
        return {
            "shots": [
                media_row(guild, row)
                | {"slug": row["slug"], "title": row["title"], "feature": row["feature"]}
                for row in rows
            ],
            "count": len(rows),
            "checked_at": now(),
        }

    @router.post("/stale/all")
    async def guides_stale_all(
        request: Request, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """A settings flip or a channel rename is not a deploy, so nothing else can mark these."""
        who, guild = await _editor(request)
        reason = wanted_text(payload or {}, "reason", guides.REASON_MAX) or None
        marked = await guides.mark_all_stale(bot.db, guild.id)
        release = guides.read_release(bot) or {}
        await note(
            bot,
            guild,
            "web.guide.shots_stale",
            who,
            reason=reason,
            details={
                "release": release.get("release"),
                "features": ["all"],
                "count": marked,
                "reason": reason,
            },
        )
        said = ALREADY_ALL_STALE
        if marked == 1:
            said = ONE_STALE_SAID
        elif marked:
            said = ALL_STALE_SAID.format(count=marked)
        return {"marked": marked, "message": said}

    @router.get("/media/{media_id}")
    async def guide_picture(request: Request, media_id: int) -> Response:
        await reading_member(request)
        guild = require_guild(bot)
        require_db(bot)
        row = await guides.get_media(bot.db, guild.id, media_id)
        if row is None:
            raise Refused(404, "no_such_media", guides.NO_SUCH_MEDIA)
        tag = f'"{row["sha256"]}"'
        headers = {"Cache-Control": guides.MEDIA_CACHE, "ETag": tag}
        if request.headers.get("if-none-match") == tag:
            return Response(status_code=304, headers=headers)
        path = guides.media_path(bot, row["file"])
        try:
            raw = path.read_bytes()
        except OSError:
            log.warning("guides: %s is recorded but not on disk", path)
            raise Refused(404, "no_such_media", guides.NO_SUCH_MEDIA) from None
        kind = guides.media_kind(row["file"]) or "application/octet-stream"
        return Response(raw, media_type=kind, headers=headers)

    @router.post("")
    async def guide_new(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
        who, guild = await _editor(request)
        title = wanted_text(payload, "title", guides.TITLE_MAX)
        goal = wanted_text(payload, "goal", guides.GOAL_MAX)
        if not title or not goal:
            raise Refused(400, "no_title", guides.TITLE_NEEDED)
        slug = guides.slugify(payload.get("slug") or title)
        if not slug:
            raise Refused(400, "no_slug", guides.SLUG_NEEDED)
        if await guides.get_guide(bot.db, guild.id, slug) is not None:
            raise Refused(409, "slug_taken", guides.SLUG_TAKEN.format(slug=slug))
        guide_id = await guides.create_guide(
            bot.db,
            guild.id,
            slug=slug,
            title=title,
            goal=goal,
            audience=wanted_audience(payload.get("audience"), guides.MEMBER),
            feature=wanted_feature(payload.get("feature"), "core"),
            command=wanted_command(payload.get("command")),
            sort=wanted_int(payload.get("sort"), "sort order") or 0,
            published=False,
            by=int(who["id"]),
        )
        await note(
            bot, guild, "web.guide.created", who, details={"slug": slug, "guide_id": guide_id}
        )
        row = await guides.get_guide_by_id(bot.db, guide_id)
        return await _whole(guild, row) | {"message": CREATED_SAID.format(title=title)}

    @router.get("/{slug}")
    async def guide_one(request: Request, slug: str) -> dict[str, Any]:
        who = await reading_member(request)
        guild = require_guild(bot)
        require_db(bot)
        staff = bool(who.get("staff"))
        if not guides.guides_on(bot.store, guild.id) and not staff:
            raise Refused(409, "guides_off", guides.GUIDES_OFF)
        row = await _wanted(guild, slug, who)
        whole = await _whole(guild, row)
        whole["may_edit"] = staff
        whole["fault_files_request"] = guides.fault_files_request(bot.store, guild.id)
        whole["notes"] = (
            [] if guides.guides_on(bot.store, guild.id) else [GUIDES_ARE_OFF_FOR_STAFF]
        )
        return whole

    @router.post("/{slug}/confirmed")
    async def guide_confirmed(request: Request, slug: str) -> dict[str, Any]:
        """§C8's left-hand button: one routine row a member leaves, and nothing else."""
        who = await reading_member(request)
        guild = require_guild(bot)
        require_db(bot)
        staff = bool(who.get("staff"))
        if not guides.guides_on(bot.store, guild.id) and not staff:
            raise Refused(409, "guides_off", guides.GUIDES_OFF)
        row = await _wanted(guild, slug, who)
        release = guides.read_release(bot) or {}
        await note(
            bot,
            guild,
            "web.guide.confirmed",
            who,
            details={
                "slug": slug,
                "guide_id": int(row["id"]),
                "release": release.get("release"),
            },
        )
        return {
            "slug": slug,
            "release": release.get("release"),
            "message": CONFIRMED_SAID.format(title=row["title"]),
        }

    @router.put("/{slug}")
    async def guide_save(request: Request, slug: str, payload: dict[str, Any]) -> dict[str, Any]:
        """The WHOLE guide, synced to in one write and one `web.guide.edited` row."""
        who, guild = await _editor(request)
        row = await _wanted(guild, slug)
        title = wanted_text(payload, "title", guides.TITLE_MAX) or str(row["title"])
        goal = wanted_text(payload, "goal", guides.GOAL_MAX) or str(row["goal"])
        if not title or not goal:
            raise Refused(400, "no_title", guides.TITLE_NEEDED)
        steps = wanted_steps(payload)
        faults = wanted_faults(payload)
        facts = wanted_facts(payload)
        was = bool(row["published"])
        published = bool(payload.get("published", was))
        command = (
            wanted_command(payload.get("command")) if "command" in payload else row["command"]
        )
        audience = wanted_audience(payload.get("audience"), str(row["audience"]))
        guide_id = int(row["id"])
        moved_steps = await guides.put_steps(bot.db, guide_id, steps)
        moved_faults = await guides.put_faults(bot.db, guide_id, faults)
        moved_facts = await guides.put_facts(bot.db, guide_id, facts)
        await guides.set_guide_fields(
            bot.db,
            guide_id,
            by=int(who["id"]),
            title=title,
            goal=goal,
            audience=audience,
            feature=wanted_feature(payload.get("feature"), str(row["feature"])),
            command=command,
            sort=wanted_int(payload.get("sort", row["sort"]), "sort order") or 0,
            published=1 if published else 0,
        )
        summary = guides.diff_summary(moved_steps, moved_faults, moved_facts)
        await note(
            bot,
            guild,
            "web.guide.edited",
            who,
            details={"slug": slug, "guide_id": guide_id, "changed": summary},
        )
        said = SAVED_SAID.format(title=title)
        if published != was:
            await note(
                bot,
                guild,
                "web.guide.published" if published else "web.guide.unpublished",
                who,
                details={"slug": slug, "guide_id": guide_id},
            )
            said = (PUBLISHED_SAID if published else UNPUBLISHED_SAID).format(title=title)
        fresh = await guides.get_guide_by_id(bot.db, guide_id)
        return await _whole(guild, fresh) | {"message": said}

    @router.delete("/{slug}")
    async def guide_delete(request: Request, slug: str) -> dict[str, Any]:
        who, guild = await _editor(request)
        row = await _wanted(guild, slug)
        if guides.is_seeded(row):
            raise Refused(
                409, "seeded_guide", guides.SEEDED_CANNOT_BE_DELETED.format(slug=slug)
            )
        for picture in await guides.media_of(bot.db, int(row["id"])):
            await guides.drop_media(bot, picture)
        await guides.delete_guide(bot.db, int(row["id"]))
        await note(
            bot, guild, "web.guide.deleted", who, details={"slug": slug, "guide_id": row["id"]}
        )
        return {"deleted": slug, "message": DELETED_SAID.format(title=row["title"])}

    @router.post("/{slug}/reset")
    async def guide_reset(request: Request, slug: str) -> dict[str, Any]:
        who, guild = await _editor(request)
        row = await _wanted(guild, slug)
        if not await guides.reset_to_seed(bot.db, guild.id, row):
            raise Refused(409, "not_seeded", NOT_SEEDED.format(slug=slug))
        await note(
            bot, guild, "web.guide.reset", who, details={"slug": slug, "guide_id": row["id"]}
        )
        fresh = await guides.get_guide_by_id(bot.db, int(row["id"]))
        return await _whole(guild, fresh) | {
            "message": RESET_SAID.format(title=fresh["title"])
        }

    @router.post("/{slug}/media")
    async def guide_media(request: Request, slug: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Pillow is not installed here, so an over-size picture is refused in words (§C1)."""
        who, guild = await _editor(request)
        row = await _wanted(guild, slug)
        name = str(payload.get("filename") or "shot.png")
        suffix = name.rsplit(".", 1)[-1].lower()
        if guides.media_kind(name) is None:
            raise Refused(415, "bad_picture", guides.MEDIA_WRONG_TYPE.format(name=name[:60]))
        raw = picture_bytes(payload)
        if not raw:
            raise Refused(400, "bad_picture", guides.MEDIA_UNREADABLE)
        if len(raw) > guides.MEDIA_BYTES_MAX:
            raise Refused(
                413,
                "picture_too_big",
                guides.MEDIA_TOO_BIG.format(
                    size=bytes_word(len(raw)),
                    limit=bytes_word(guides.MEDIA_BYTES_MAX),
                    side=guides.MEDIA_SIDE_MAX,
                ),
            )
        size = guides.picture_size(raw)
        if size is None:
            raise Refused(400, "bad_picture", guides.MEDIA_UNREADABLE)
        if max(size) > guides.MEDIA_SIDE_MAX:
            raise Refused(
                413,
                "picture_too_wide",
                guides.MEDIA_TOO_WIDE.format(side=max(size), limit=guides.MEDIA_SIDE_MAX),
            )
        guide_id = int(row["id"])
        steps = await guides.steps_of(bot.db, guide_id)
        step_id = wanted_int(payload.get("step_id"), "step id")
        step = next((one for one in steps if int(one["id"]) == step_id), None)
        if step_id is not None and step is None:
            raise Refused(404, "no_such_step", NO_SUCH_STEP.format(slug=slug))
        old = [
            one
            for one in await guides.media_of(bot.db, guide_id)
            if (int(one["step_id"]) if one["step_id"] else None) == step_id
        ]
        media_id = await guides.save_media(
            bot,
            guild.id,
            guide_id,
            raw,
            step_id=step_id,
            suffix=suffix,
            source=str(payload.get("source") or guides.CAPTURE),
            surface=str(payload.get("surface") or guides.DISCORD),
            caption=payload.get("caption"),
            shot_release=payload.get("shot_release"),
            shot_by=int(who["id"]),
        )
        if step is not None:
            await bot.db.conn.execute(
                "UPDATE guide_steps SET media_id = ? WHERE id = ?", (media_id, int(step["id"]))
            )
            await bot.db.conn.commit()
        for one in old:
            await guides.drop_media(bot, one)
        await note(
            bot,
            guild,
            "web.guide.media_replaced",
            who,
            details={"slug": slug, "guide_id": guide_id, "media_id": media_id},
        )
        fresh = await guides.get_media(bot.db, guild.id, media_id)
        said = (
            MEDIA_SAID.format(position=int(step["position"]))
            if step is not None
            else MEDIA_GUIDE_SAID.format(title=row["title"])
        )
        return {"media": media_row(guild, fresh), "message": said}

    return router


__all__ = ["build_router", "fault_row", "guide_row", "media_row", "step_row"]
