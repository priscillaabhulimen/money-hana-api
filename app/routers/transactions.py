from fastapi import Depends, HTTPException, Query, status, APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import date
from sqlalchemy import select, func

from app.schemas import TransactionCreate, TransactionResponse, TransactionUpdate, BaseResponse, TransactionType, PaginatedResponse, ExpenseCategory, IncomeCategory
from app.database import get_db
from app.models import Transaction, User
from app.routers.auth import get_current_user

router = APIRouter(
    prefix="/api/v1/transactions",
    tags=["Transactions"],
)

@router.get("/", response_model=PaginatedResponse[list[TransactionResponse]])
async def get_transactions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=30, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
):
    offset = (page - 1) * limit

    filters = [Transaction.user_id == current_user.id]
    if start_date:
        filters.append(Transaction.date >= start_date)
    if end_date:
        filters.append(Transaction.date <= end_date)

    total_result = await db.execute(
        select(func.count()).select_from(Transaction).where(*filters)
    )
    total = total_result.scalar()

    result = await db.execute(
        select(Transaction)
        .where(*filters)
        .order_by(Transaction.date.desc())
        .limit(limit)
        .offset(offset)
    )
    transactions = result.scalars().all()
    return PaginatedResponse(data=transactions, total=total, limit=limit, page=page)


@router.get("/{transaction_id}", response_model=BaseResponse[TransactionResponse])
async def get_transaction(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return BaseResponse(data=TransactionResponse.model_validate(transaction))


@router.post("/", response_model=BaseResponse[TransactionResponse], status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_transaction = Transaction(**transaction.model_dump(), user_id=current_user.id)
    db.add(new_transaction)
    await db.commit()
    await db.refresh(new_transaction)
    return BaseResponse(data=new_transaction)


@router.patch("/{transaction_id}", response_model=BaseResponse[TransactionResponse])
async def update_transaction(
    transaction_id: UUID,
    transaction_update: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    effective_type = (
        transaction_update.transaction_type
        if transaction_update.transaction_type is not None
        else transaction.transaction_type
    )
    category_to_validate = (
        transaction_update.category
        if transaction_update.category is not None
        else transaction.category
    )
    if effective_type and category_to_validate is not None:
        if effective_type == TransactionType.expense:
            try:
                ExpenseCategory(category_to_validate)
            except ValueError:
                raise HTTPException(status_code=422, detail="Invalid category for expense transaction")
        elif effective_type == TransactionType.income:
            try:
                IncomeCategory(category_to_validate)
            except ValueError:
                raise HTTPException(status_code=422, detail="Invalid category for income transaction")

    for field, value in transaction_update.model_dump(exclude_unset=True).items():
        setattr(transaction, field, value)

    await db.commit()
    await db.refresh(transaction)
    return BaseResponse(data=transaction)


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.user_id == current_user.id,
        )
    )
    transaction = result.scalar_one_or_none()
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await db.delete(transaction)
    await db.commit()
