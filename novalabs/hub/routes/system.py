from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring/load balancers"""
    return {
        'status': 'healthy',
        'service': 'novalabs-hub'
    }
