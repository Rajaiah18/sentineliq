"""
SentinelIQ Customers & Accounts API Routers
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.app.database.repository import repo

customers_router = APIRouter(prefix="/customers", tags=["Customers"])
accounts_router = APIRouter(prefix="/accounts", tags=["Accounts"])


# =============================================================================
# Customers Endpoints
# =============================================================================
@customers_router.get("")
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    risk_profile: Optional[str] = None
):
    items, total = repo.get_customers(page=page, page_size=page_size, search=search, risk_profile=risk_profile)
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "data": items
    }


@customers_router.get("/{customer_id}")
def get_customer(customer_id: str):
    cust = repo.get_customer_by_id(customer_id)
    if not cust:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Customer {customer_id} not found.")
    accounts, _ = repo.get_accounts(customer_id=customer_id, page_size=100)
    return {
        "customer": cust,
        "accounts": accounts
    }


@customers_router.get("/{customer_id}/transactions")
def get_customer_transactions(customer_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    items, total = repo.get_transactions(page=page, page_size=page_size, customer_id=customer_id)
    return {
        "customer_id": customer_id,
        "page": page,
        "page_size": page_size,
        "total": total,
        "data": items
    }


@customers_router.get("/{customer_id}/alerts")
def get_customer_alerts(customer_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    items, total = repo.get_alerts(page=page, page_size=page_size, customer_id=customer_id)
    return {
        "customer_id": customer_id,
        "page": page,
        "page_size": page_size,
        "total": total,
        "data": items
    }


# =============================================================================
# Accounts Endpoints
# =============================================================================
@accounts_router.get("")
def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: Optional[str] = None,
    status: Optional[str] = None
):
    items, total = repo.get_accounts(page=page, page_size=page_size, customer_id=customer_id, status=status)
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "data": items
    }


@accounts_router.get("/{account_id}")
def get_account(account_id: str):
    acc = repo.get_account_by_id(account_id)
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Account {account_id} not found.")
    cust = repo.get_customer_by_id(acc.get("customer_id", ""))
    return {
        "account": acc,
        "customer": cust
    }


@accounts_router.get("/{account_id}/transactions")
def get_account_transactions(account_id: str, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    items, total = repo.get_transactions(page=page, page_size=page_size, account_id=account_id)
    return {
        "account_id": account_id,
        "page": page,
        "page_size": page_size,
        "total": total,
        "data": items
    }
