import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, timezone, timedelta
from groq import AsyncGroq

from app.database import get_db
from app.models import User, Transaction, Goal
from app.models.ai_insight import AIInsight
from app.schemas import BaseResponse, AIInsightResponse, AIInsightsRequest
from app.routers.auth import get_current_user
from app.config import settings

router = APIRouter(
    prefix="/api/v1",
    tags=["AI Insights"],
)

logger = logging.getLogger(__name__)

INSIGHT_TTL_DAYS = settings.insight_ttl_days

CATEGORY_LABELS = {
    "groceries": "Groceries",
    "dining": "Dining",
    "transport": "Transport",
    "entertainment": "Entertainment",
    "utilities_bills": "Utilities & Bills",
    "education": "Education",
    "subscriptions": "Subscriptions",
    "salary_wages": "Salary & Wages",
    "returns": "Returns",
    "gift": "Gift",
    "other": "Other",
}


async def fetch_fresh_insights(
    user: User,
    db: AsyncSession,
) -> list[AIInsight]:
    # Fetch last 30 transactions
    tx_result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.date.desc())
        .limit(30)
    )
    transactions = tx_result.scalars().all()

    if not transactions:
        return []

    # Fetch goals
    goal_result = await db.execute(
        select(Goal).where(Goal.user_id == user.id)
    )
    goals = goal_result.scalars().all()

    tx_context = [
        {
            "date": str(t.date),
            "type": t.transaction_type,
            "category": CATEGORY_LABELS.get(t.category, t.category),
            "amount": float(t.amount),
            "note": t.note,
        }
        for t in transactions
    ]

    goal_context = [
        {
            "category": CATEGORY_LABELS.get(g.category, g.category),
            "monthly_limit": float(g.monthly_limit),
        }
        for g in goals
    ]

    prompt = f"""You are a personal finance assistant. Analyze the following user data and return exactly 3 insights as a JSON array.

Each insight must have:
- "type": one of "flag", "pattern", or "goal_warning"
- "message": a concise, specific, actionable insight (1-2 sentences, no emojis)

Use natural category names exactly as provided. Keep each message under 2 sentences and concise.

Use exactly one of each type, defined as follows:

- "flag": A spending alert or anomaly that needs the user's attention. Examples: a category significantly over budget, an unusual spike in spending compared to recent history, or a large single transaction.
- "pattern": A behavioural trend observed across the transaction history. Examples: recurring high spend on a particular day, category, or time period. Should describe what the user consistently does with their money.
- "goal_warning": A direct assessment of progress toward one of the user's monthly goals. Reference the specific category, how much has been spent, the limit, and whether they are on track or at risk.

Base all insights strictly on the data provided. Do not invent figures or categories not present in the data. Be specific — use actual amounts and category names from the data.

Transactions (most recent 30):
{json.dumps(tx_context, indent=2)}

Goals:
{json.dumps(goal_context, indent=2)}

Respond ONLY with a valid JSON array. No preamble, no markdown, no explanation."""
    client = AsyncGroq(api_key=settings.groq_api_key)

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=512,
        )
        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.exception("Groq returned invalid JSON")
        raise HTTPException(status_code=502, detail="AI service returned an invalid response")
    except Exception:
        logger.exception("Groq API call failed")
        raise HTTPException(status_code=502, detail="AI service unavailable")

    if not isinstance(parsed, list) or len(parsed) != 3:
        raise HTTPException(status_code=502, detail="AI service returned unexpected response shape")

    valid_types = {"flag", "pattern", "goal_warning"}
    for item in parsed:
        if item.get("type") not in valid_types or not item.get("message"):
            raise HTTPException(status_code=502, detail="AI service returned invalid insight types")

    # Store new insights
    new_insights = [
        AIInsight(
            user_id=user.id,
            type=item["type"],
            message=item["message"],
        )
        for item in parsed
    ]
    db.add_all(new_insights)
    await db.commit()
    for insight in new_insights:
        await db.refresh(insight)

    return new_insights

@router.get("/ai-insights/history", response_model=BaseResponse[list[AIInsightResponse]])
async def get_ai_insights_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(AIInsight)
        .where(AIInsight.user_id == current_user.id)
        .order_by(AIInsight.created_at.desc())
    )
    insights = result.scalars().all()
    return BaseResponse(data=insights)


@router.post("/ai-insights", response_model=BaseResponse[list[AIInsightResponse]])
async def get_ai_insights(
    payload: AIInsightsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not payload.force_refresh:
        # Check for cached insights within TTL
        result = await db.execute(
            select(AIInsight)
            .where(AIInsight.user_id == current_user.id)
            .order_by(AIInsight.created_at.desc())
        )
        cached = result.scalars().all()

        if cached:
            latest_created_at = cached[0].created_at
            # Ensure timestamp is timezone-aware for comparison
            if latest_created_at.tzinfo is None:
                latest_created_at = latest_created_at.replace(tzinfo=timezone.utc)
            
            age = datetime.now(timezone.utc) - latest_created_at
            if age < timedelta(days=INSIGHT_TTL_DAYS):
                return BaseResponse(data=cached)

    insights = await fetch_fresh_insights(current_user, db)
    return BaseResponse(data=insights)