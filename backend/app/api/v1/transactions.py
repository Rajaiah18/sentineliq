"""
SentinelIQ Transactions API Router
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.app.database.repository import repo

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("")
def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    customer_id: Optional[str] = None,
    account_id: Optional[str] = None,
    transaction_type: Optional[str] = None,
    status: Optional[str] = None,
    sort_by: str = "transaction_timestamp",
    sort_desc: bool = True
):
    items, total = repo.get_transactions(
        page=page,
        page_size=page_size,
        search=search,
        customer_id=customer_id,
        account_id=account_id,
        transaction_type=transaction_type,
        status=status,
        sort_by=sort_by,
        sort_desc=sort_desc
    )
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "data": items
    }


@router.get("/{transaction_id}")
def get_transaction(transaction_id: str):
    txn = repo.get_transaction_by_id(transaction_id)
    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Transaction {transaction_id} not found.")

    cust = repo.get_customer_by_id(txn.get("customer_id", ""))
    src_acc = repo.get_account_by_id(txn.get("source_account_id", ""))
    dst_acc = repo.get_account_by_id(txn.get("destination_account_id", "")) if txn.get("destination_account_id") else None

    return {
        "transaction": txn,
        "customer": cust,
        "source_account": src_acc,
        "destination_account": dst_acc
    }


@router.get("/{transaction_id}/related")
def get_related_transactions(transaction_id: str):
    txn = repo.get_transaction_by_id(transaction_id)
    if not txn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Transaction {transaction_id} not found.")

    related_txns = []
    # If transfer group exists, find reciprocal legs
    grp_id = txn.get("transfer_group_id")
    if grp_id:
        items, _ = repo.get_transactions(account_id=txn.get("source_account_id"), page_size=20)
        related_txns = [t for t in items if t.get("transfer_group_id") == grp_id and t.get("transaction_id") != transaction_id]

    return {
        "transaction_id": transaction_id,
        "transfer_group_id": grp_id,
        "related": related_txns
    }


@router.get("/{transaction_id}/alerts")
def get_transaction_alerts(transaction_id: str):
    all_alerts, _ = repo.get_alerts(page_size=100)
    matched = [a for a in all_alerts if transaction_id in a.get("triggered_transaction_ids", [])]
    return {
        "transaction_id": transaction_id,
        "alerts": matched
    }
