from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .database import init_db, close_db
from .routes import api_router
from novalabs.common.config import NovaLabsConfig

# Load config
config = NovaLabsConfig()


# Handle pre-API-startup and post-API-shutdown actions to set up/clean up
# (see https://fastapi.tiangolo.com/advanced/events/#lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-API-startup actions go here:
    await init_db()
    print('NovaLabs database initialized')
    yield
    await close_db()

# Create FastAPI app
app = FastAPI(
    title="NovaLabs Hub",
    description="Central platform for astronomy lab management",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.data.get('cors', {}).get('origins', ['*']),
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Include all API routes
app.include_router(api_router)


def main():
    """Entry point for running the hub server"""
    import uvicorn
    uvicorn.run(app, host=config.data.get('server', {}).get('host', '0.0.0.0'), port=config.data.get('server', {}).get('port', 8100))


if __name__ == "__main__":
    main()
