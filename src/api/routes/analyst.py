from fastapi import APIRouter, Query, HTTPException, status
from src.modules.cw_pricing.prompts.analyst_prompt import build_analyst_prompt

router = APIRouter(tags=["analyst"])

@router.get("/api/analyst-prompt/{ticker}")
def get_analyst_prompt(ticker: str, cw_symbol: str = Query(default=None)):
    """
    Get auto-injected CW analyst prompt for a given underlying ticker and optional specific CW symbol.
    """
    try:
        res = build_analyst_prompt(ticker, cw_symbol)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate analyst prompt: {str(e)}"
        )
