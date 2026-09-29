"""Debate endpoints (/api/v1/debates, /local, /online)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

import qrcode
import io
import base64
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, get_optional_user
from app.core.exceptions import NotFoundError
from app.models.base import DebateMode, DebateStatus, Side, VoteChoice
from app.models.category import Category
from app.models.debate import Debate, DebateComment, DebateCommentReaction, DebateParticipant, DebateRules, DebateVote, ParticipantRole
from app.models.user import User
from app.schemas.common import Message, Paginated
from app.schemas.debate import (
    AcceptInvitationResponse,
    CastVoteRequest,
    CastVoteResponse,
    CommentCreate,
    CommentReactionIn,
    ConfirmSideRequest,
    CreateInvitationRequest,
    DebateBrief,
    DebateCreate,
    DebateDetail,
    InvitationOut,
    LockDebateResponse,
    ShareLinks,
    VoteCounts,
    VotersPage,
)
from app.services import debate_service

router = APIRouter(prefix="/debates", tags=["debates"])


async def _to_brief(db: AsyncSession, debate: Debate) -> DebateBrief:
    category_name = None
    if debate.category_id:
        cat = await db.get(Category, debate.category_id)
        category_name = cat.name if cat else None
    participants_count = len(
        (
            await db.execute(
                select(DebateParticipant).where(DebateParticipant.debate_id == debate.id)
            )
        ).scalars().all()
    )
    votes_count = (
        await db.execute(
            select(func.count(DebateVote.id)).where(DebateVote.debate_id == debate.id)
        )
    ).scalar_one()
    rules = (
        await db.execute(select(DebateRules).where(DebateRules.debate_id == debate.id))
    ).scalar_one_or_none()
    return DebateBrief(
        id=debate.id,
        mode=debate.mode,
        status=debate.status,
        question=debate.question,
        side_a_label=debate.side_a_label,
        side_b_label=debate.side_b_label,
        timezone=debate.timezone,
        start_at=debate.start_at,
        end_at=debate.end_at,
        views=debate.views,
        winner_side=debate.winner_side,
        category_name=category_name,
        participants_count=participants_count,
        votes_count=votes_count,
        required_voters=rules.required_voters if rules else 0,
        settlement_source=rules.settlement_source if rules else None,
        venue_city=(rules.city if rules else None),
    )


async def _to_detail(db: AsyncSession, debate: Debate, user: Optional[User]) -> DebateDetail:
    brief = await _to_brief(db, debate)
    data = brief.model_dump()

    participants = (
        await db.execute(
            select(DebateParticipant).where(DebateParticipant.debate_id == debate.id)
        )
    ).scalars().all()
    participant_out = []
    for p in participants:
        username = None
        if p.user_id:
            u = await db.get(User, p.user_id)
            username = u.username if u else None
        participant_out.append(
            {
                "id": p.id, "user_id": p.user_id, "role": p.role, "side": p.side,
                "confirmed": p.confirmed, "username": username,
            }
        )

    my_side = my_role = has_voted = None
    if user:
        mine = next((p for p in participants if p.user_id == user.id), None)
        if mine:
            my_side, my_role = mine.side, mine.role
        vote = (
            await db.execute(
                select(DebateVote).where(
                    DebateVote.debate_id == debate.id, DebateVote.voter_id == user.id
                )
            )
        ).scalar_one_or_none()
        if vote:
            has_voted = vote.choice

    rules = (
        await db.execute(select(DebateRules).where(DebateRules.debate_id == debate.id))
    ).scalar_one_or_none()

    reveal = my_role in (ParticipantRole.creator, ParticipantRole.challenger)
    tally = await debate_service.vote_counts(db, debate, reveal=reveal or debate.mode == DebateMode.local)

    return DebateDetail(
        **data,
        is_public=debate.is_public,
        locked_at=debate.locked_at,
        settled_at=debate.settled_at,
        result_summary=debate.result_summary,
        shares=debate.shares,
        comments_count=debate.comments_count,
        rules=rules,
        participants=participant_out,
        vote_tally=tally,
        my_side=my_side,
        my_role=my_role,
        has_voted=has_voted,
    )


@router.post("", response_model=DebateDetail, status_code=201)
async def create_debate(
    payload: DebateCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    debate = await debate_service.create_debate(db, user, payload)
    await db.commit()
    await db.refresh(debate)
    return await _to_detail(db, debate, user)


@router.get("", response_model=Paginated[DebateBrief])
async def list_debates(
    status: Optional[DebateStatus] = None,
    mode: Optional[DebateMode] = None,
    category_id: Optional[uuid.UUID] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    debates, total = await debate_service.list_debates(
        db, status=status, mode=mode, category_id=category_id,
        limit=page_size, offset=(page - 1) * page_size,
    )
    items = [await _to_brief(db, d) for d in debates]
    return Paginated.create(items, total, page, page_size)


@router.get("/trending", response_model=List[DebateBrief])
async def trending(db: AsyncSession = Depends(get_db)):
    debates = await debate_service.trending_debates(db, limit=10)
    return [await _to_brief(db, d) for d in debates]


@router.get("/search", response_model=Paginated[DebateBrief])
async def search(
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    debates, total = await debate_service.search_debates(
        db, q, limit=page_size, offset=(page - 1) * page_size
    )
    items = [await _to_brief(db, d) for d in debates]
    return Paginated.create(items, total, page, page_size)


@router.get("/{debate_id}", response_model=DebateDetail)
async def get_debate(
    debate_id: uuid.UUID,
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    debate = await debate_service.get_debate(db, debate_id)
    await debate_service.assert_can_view(debate, user)
    debate.views += 1
    await db.commit()
    return await _to_detail(db, debate, user)


@router.get("/{debate_id}/votes", response_model=VoteCounts)
async def get_votes(
    debate_id: uuid.UUID,
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    debate = await debate_service.get_debate(db, debate_id)
    await debate_service.assert_can_view(debate, user)
    reveal = False
    if user:
        p = next((x for x in debate.participants if x.user_id == user.id and x.role != ParticipantRole.voter), None)
        reveal = p is not None
    counts = await debate_service.vote_counts(db, debate, reveal=reveal)
    return VoteCounts(**counts)


@router.get("/{debate_id}/voters", response_model=VotersPage)
async def get_voters(
    debate_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user: Optional[User] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """People who voted (§5): participation only, never the chosen side."""
    debate = await debate_service.get_debate(db, debate_id)
    await debate_service.assert_can_view(debate, user)
    data = await debate_service.list_voters(
        db, debate, user, limit=page_size, offset=(page - 1) * page_size
    )
    return VotersPage(**data)


@router.post("/{debate_id}/vote", response_model=CastVoteResponse)
async def cast_vote(
    debate_id: uuid.UUID,
    payload: CastVoteRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    debate = await debate_service.get_debate(db, debate_id)
    await debate_service.assert_can_view(debate, user)
    recorded, message = await debate_service.cast_vote(db, debate, user, payload.choice)
    counts = await debate_service.vote_counts(db, debate, reveal=False)
    await db.commit()
    return CastVoteResponse(recorded=recorded, message=message, counts=VoteCounts(**counts))


@router.get("/{debate_id}/comments")
async def list_comments(debate_id: uuid.UUID, user: Optional[User] = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    debate = await debate_service.get_debate(db, debate_id)
    await debate_service.assert_can_view(debate, user)
    rows = (await db.execute(select(DebateComment).where(
        DebateComment.debate_id == debate_id, DebateComment.hidden.is_(False)
    ).order_by(DebateComment.pinned.desc(), DebateComment.created_at.asc()).limit(300))).scalars().all()
    output = []
    for row in rows:
        author = await db.get(User, row.user_id)
        counts = (await db.execute(select(DebateCommentReaction.reaction, func.count(DebateCommentReaction.id))
            .where(DebateCommentReaction.comment_id == row.id).group_by(DebateCommentReaction.reaction))).all()
        output.append({"id": row.id, "parent_id": row.parent_id, "body": row.body,
            "user_id": row.user_id, "username": author.username if author else "community member",
            "created_at": row.created_at, "pinned": row.pinned,
            "reactions": {key: count for key, count in counts}})
    return {"items": output, "total": len(output)}


@router.post("/{debate_id}/comments", status_code=201)
async def create_comment(debate_id: uuid.UUID, payload: CommentCreate,
                         user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    debate = await debate_service.get_debate(db, debate_id)
    await debate_service.assert_can_view(debate, user)
    recent = (await db.execute(select(DebateComment).where(
        DebateComment.user_id == user.id, DebateComment.debate_id == debate_id
    ).order_by(DebateComment.created_at.desc()).limit(1))).scalar_one_or_none()
    if recent and (datetime.now(timezone.utc) - recent.created_at.replace(tzinfo=timezone.utc)).total_seconds() < 5:
        from app.core.exceptions import RateLimitedError
        raise RateLimitedError()
    if payload.parent_id:
        parent = await db.get(DebateComment, payload.parent_id)
        if not parent or parent.debate_id != debate_id:
            raise NotFoundError("Reply target not found.")
    row = DebateComment(debate_id=debate_id, user_id=user.id, parent_id=payload.parent_id, body=payload.body.strip())
    db.add(row)
    debate.comments_count += 1
    await db.commit()
    await db.refresh(row)
    return {"id": row.id, "parent_id": row.parent_id, "body": row.body, "user_id": user.id,
            "username": user.username, "created_at": row.created_at, "pinned": False, "reactions": {}}


@router.put("/{debate_id}/comments/{comment_id}/reaction")
async def react_to_comment(debate_id: uuid.UUID, comment_id: uuid.UUID, payload: CommentReactionIn,
                           user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    row = await db.get(DebateComment, comment_id)
    if row is None or row.debate_id != debate_id:
        raise NotFoundError("Comment not found.")
    existing = (await db.execute(select(DebateCommentReaction).where(
        DebateCommentReaction.comment_id == comment_id, DebateCommentReaction.user_id == user.id
    ))).scalar_one_or_none()
    if existing:
        existing.reaction = payload.reaction
    else:
        db.add(DebateCommentReaction(comment_id=comment_id, user_id=user.id, reaction=payload.reaction))
    await db.commit()
    return {"message": "Reaction saved."}


@router.post("/{debate_id}/confirm", response_model=Message)
async def confirm_side(
    debate_id: uuid.UUID,
    payload: ConfirmSideRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    debate = await debate_service.get_debate(db, debate_id)
    await debate_service.confirm_side(db, debate, user, payload.side)
    await db.commit()
    return Message(message="Your side has been confirmed.")


@router.post("/{debate_id}/lock", response_model=LockDebateResponse)
async def lock_debate(
    debate_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    debate = await debate_service.get_debate(db, debate_id)
    debate = await debate_service.lock_debate(db, debate, user)
    await db.commit()
    return LockDebateResponse(locked=True, status=debate.status, message="This debate is now locked.")


# --- Invitations ---

@router.post("/{debate_id}/invitations", response_model=InvitationOut)
async def create_invitation(
    debate_id: uuid.UUID,
    payload: CreateInvitationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    debate = await debate_service.get_debate(db, debate_id)
    if user.id != debate.creator_id and not any(p.user_id == user.id and p.role == ParticipantRole.challenger for p in debate.participants):
        raise NotFoundError("Debate not found.")
    if payload.kind == "voter" and debate.mode != DebateMode.local:
        from app.core.exceptions import ConflictError
        raise ConflictError("Community invitations are available for community-voted debates.")
    invitation = await debate_service.create_invitation(
        db, debate, payload.kind, payload.max_uses, payload.expires_in_hours, payload.invited_email
    )
    await db.commit()
    return InvitationOut(
        id=invitation.id, token=invitation.token, kind=invitation.kind,
        invite_url=f"{settings.FRONTEND_URL}/join/{invitation.token}",
        max_uses=invitation.max_uses, use_count=invitation.use_count,
        expires_at=invitation.expires_at, used=invitation.used,
    )


@router.get("/{debate_id}/share", response_model=ShareLinks)
async def share_links(
    debate_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    debate = await debate_service.get_debate(db, debate_id)
    invitation = await debate_service.create_invitation(db, debate, "voter", 2_147_483_647, 72)
    debate.shares += 1
    await db.commit()
    links = debate_service.build_share_links(settings.FRONTEND_URL, invitation.token)
    return ShareLinks(**links)


@router.post("/invitations/accept", response_model=AcceptInvitationResponse)
async def accept_invitation(
    token: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    invitation = await debate_service.accept_invitation(db, token, user)
    await db.commit()
    return AcceptInvitationResponse(
        message="You've joined the debate.", debate_id=invitation.debate_id
    )


@router.get("/invitations/{token}")
async def invitation_details(token: str, db: AsyncSession = Depends(get_db)):
    from app.models.debate import DebateInvitation
    invitation = (await db.execute(select(DebateInvitation).where(DebateInvitation.token == token))).scalar_one_or_none()
    if not invitation or invitation.used or (invitation.expires_at and invitation.expires_at <= datetime.now(timezone.utc)):
        raise NotFoundError("This invitation is not available.")
    debate = await debate_service.get_debate(db, invitation.debate_id)
    return {"kind": invitation.kind, "debate_id": debate.id, "question": debate.question,
            "creator_id": debate.creator_id, "status": debate.status.value}


@router.post("/invitations/decline")
async def decline_invitation(token: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from app.models.debate import DebateInvitation
    from app.core.exceptions import ConflictError
    invitation = (await db.execute(select(DebateInvitation).where(DebateInvitation.token == token))).scalar_one_or_none()
    if not invitation or invitation.kind != "opponent" or invitation.used:
        raise NotFoundError("Opponent invitation not found.")
    invitation.response = "declined"
    invitation.used = True
    await db.commit()
    return {"message": "Challenge declined."}
