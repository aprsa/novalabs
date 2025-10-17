from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import toml
import os

from .database import init_db
from .routes import api_router

# Load config
config_path = os.path.join(os.path.dirname(__file__), 'config.toml')
config = toml.load(config_path)


# Handle pre-API-startup and post-API-shutdown actions to set up/clean up
# (see https://fastapi.tiangolo.com/advanced/events/#lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-API-startup actions go here:
    init_db()
    print('NovaLabs database initialized')
    yield
    # Post-API-shutdown actions would go here

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
    allow_origins=config['cors']['origins'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# Include all API routes
app.include_router(api_router)


def main():
    """Entry point for running the hub server"""
    import uvicorn
    uvicorn.run(app, host=config['server']['host'], port=config['server']['port'])


if __name__ == "__main__":
    main()
