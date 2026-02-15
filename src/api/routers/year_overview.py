#
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 m2-eng
# Author: m2-eng
# Co-Author: GitHub Copilot
# License: GNU Affero General Public License v3.0 (AGPL-3.0-only)
# Purpose: Year overview API router - exposes balances at the start of each month for a given year.
#
"""Year overview API router - exposes balances at the start of each month for a given year."""

from fastapi import APIRouter, Depends, Query

from api.dependencies import get_db_cursor
from api.error_handling import handle_db_errors
from repositories.year_overview_repository import YearOverviewRepository

router = APIRouter(prefix="/year-overview", tags=["year-overview"])
years_router = APIRouter(prefix="/years", tags=["years"])


@router.get("/account-balances")
@handle_db_errors("fetch account balances")
async def get_account_balances(
  year: int = Query(..., ge=1900, le=3000, description="Year for which balances are requested"),
  cursor = Depends(get_db_cursor)
):
    """Return monthly starting balances per account for the selected year.
    Includes future planning entries (tbl_planningEntry) only for dates after today.
    Real accounting entries (tbl_accountingEntry) are included only up to today.
    """
    repository = YearOverviewRepository(cursor)
    data = repository.get_account_balances(year)

    return {"year": year, "rows": data}


@router.get("/account-balances-monthly")
@handle_db_errors("fetch monthly account balances")
async def get_account_balances_monthly(
  year: int = Query(..., ge=1900, le=3000, description="Year for which monthly balances are requested"),
  cursor = Depends(get_db_cursor)
):
    """Return monthly delta balances per account for the selected year (Grafana 'Bilanz').
    Real accounting entries are counted only up to today; planning entries only after today.
    """
    repository = YearOverviewRepository(cursor)
    data = repository.get_account_balances_monthly(year)

    return {"year": year, "rows": data}


@router.get("/investments")
@handle_db_errors("fetch investments overview")
async def get_investments(
  year: int = Query(..., ge=1900, le=3000, description="Year for which investments overview is requested"),
  cursor = Depends(get_db_cursor)
):
    """Return investment platform account balances per month for the selected year (Investment-Plattform - Typ 5).
    
    Shows cumulative balance for each month (sum of all transactions up to and including that month).
    Jahresbilanz shows the change from start of year to end of year.
    Only includes accounts of type 'Investment-Plattform' (type = 5).
    """
    repository = YearOverviewRepository(cursor)
    data = repository.get_investments(year)

    return {"year": year, "rows": data}


@router.get("/loans")
@handle_db_errors("fetch loans overview")
async def get_loans(
  year: int = Query(..., ge=1900, le=3000, description="Year for which loans overview is requested"),
  cursor = Depends(get_db_cursor)
):
    """Return loan account balances per month for the selected year (Darlehen - Typ 3).
    
    Shows cumulative balance for each month (sum of all transactions up to and including that month).
    Jahresbilanz shows the change from start of year to end of year.
    Only includes accounts of type 'Darlehen' (type = 3).
    """
    repository = YearOverviewRepository(cursor)
    data = repository.get_loans(year)

    return {"year": year, "rows": data}


@router.get("/securities")
@handle_db_errors("fetch securities overview")
async def get_securities_overview(year: int = Query(...), cursor=Depends(get_db_cursor)):
    """Get securities portfolio values for each month-end of the given year.
    Only includes shares that have at least one month with volume > 0 (were actually held)."""
    repository = YearOverviewRepository(cursor)
    data = repository.get_securities_overview(year)

    return {"year": year, "rows": data}


@router.get("/assets-month-end")
@handle_db_errors("fetch assets month-end overview")
async def get_assets_month_end(
  year: int = Query(..., ge=1900, le=3000, description="Year for which assets month-end overview is requested"),
  cursor = Depends(get_db_cursor)
):
    """Aggregated assets at month-end, split into categories: Kontostand (Girokonto), Darlehen, Wertpapiere.
    
    For each month of the given year, compute the end-of-month value:
    - Kontostand: sum across accounts of type 'Girokonto' (cash accounts)
    - Darlehen: sum across accounts of type 'Darlehen'
    - Wertpapiere: sum of portfolio values from view_shareMonthlySnapshot

    Past/present months include all real transactions up to month end + startAmount;
    Future months use real up to today + planned entries after today up to month end + startAmount.
    Jahresbilanz reflects the end-of-year value using the same blending logic.
    """
    repository = YearOverviewRepository(cursor)
    data = repository.get_assets_month_end(year)

    return {"year": year, "rows": data}


@years_router.get("/")
@handle_db_errors("fetch available years")
async def get_available_years(cursor=Depends(get_db_cursor)):
    """Get all available years from transactions."""
    repository = YearOverviewRepository(cursor)
    years = repository.get_available_years()
    return {"years": years}

