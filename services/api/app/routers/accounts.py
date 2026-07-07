from fastapi import APIRouter, HTTPException

from app.data.accounts import get_account_detail
from app.schemas.accounts import AccountDetail


router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("/{account_id}", response_model=AccountDetail)
def get_account(account_id: str) -> AccountDetail:
    account = get_account_detail(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    return account
