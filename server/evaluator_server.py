import argparse
import base64
import io
import logging
import os
import time
from typing import Dict, List, Any, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pokemon_env import PokemonEnvironment
from pokemon_env.action import Action, PressKey, Wait, ActionType

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Global variables
ROM_PATH = "pokemon.gb"  # Default ROM path
env = None

# Create FastAPI app
app = FastAPI(
    title="Pokemon Evaluator API",
    description="API for evaluating AI agents on Pokemon Red gameplay",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models for API requests and responses
class InitializeRequest(BaseModel):
    headless: bool = True
    sound: bool = False


class ActionRequest(BaseModel):
    action_type: str  # "press_key" or "wait"
    # For press_key
    keys: Optional[List[str]] = None
    wait: Optional[bool] = True
    # For wait
    frames: Optional[int] = None


class GameStateResponse(BaseModel):
    memory_info: Dict[str, Any]
    screenshot_base64: str
    location: str
    coordinates: List[int]
    party_pokemon: List[Dict[str, Any]]
    collision_map: Optional[str] = None
    valid_moves: Optional[List[str]] = None
    step_number: int
    execution_time: float


# API Endpoints
@app.post("/initialize", response_model=GameStateResponse)
async def initialize(request: InitializeRequest):
    """
    Initialize the Pokemon environment and return the initial state.
    
    Args:
        request: Initialization parameters
    
    Returns:
        The initial game state
    """
    global env
    
    # Check if ROM file exists
    if not os.path.exists(ROM_PATH):
        raise HTTPException(
            status_code=404, 
            detail=f"ROM file not found: {ROM_PATH}"
        )
    
    # Initialize environment
    try:
        logger.info(f"Initializing environment with ROM: {ROM_PATH}")
        env = PokemonEnvironment(
            rom_path=ROM_PATH,
            headless=request.headless,
            sound=request.sound
        )
        
        # Get initial state
        state = env.state
        
        # Get collision map and valid moves
        collision_map = env.get_collision_map()
        valid_moves = env.get_valid_moves()
        
        # Prepare response
        response = GameStateResponse(
            memory_info=state.memory_info,
            screenshot_base64=state.screenshot_base64,
            location=state.location,
            coordinates=list(state.coordinates),  # Convert tuple to list
            party_pokemon=state.party_pokemon,
            collision_map=collision_map,
            valid_moves=valid_moves,
            step_number=0,
            execution_time=0.0
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error initializing environment: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initialize environment: {str(e)}"
        )


@app.post("/action", response_model=GameStateResponse)
async def take_action(request: ActionRequest):
    """
    Take an action in the environment and return the new state.
    
    Args:
        request: Action parameters
    
    Returns:
        The new game state after taking the action
    """
    global env
    
    # Check if environment is initialized
    if env is None:
        raise HTTPException(
            status_code=400,
            detail="Environment not initialized. Call /initialize first."
        )
    
    # Create action based on request
    try:
        if request.action_type == "press_key":
            if not request.keys:
                raise HTTPException(
                    status_code=400,
                    detail="Keys parameter is required for press_key action."
                )
            action = PressKey(keys=request.keys, wait=request.wait if request.wait is not None else True)
        
        elif request.action_type == "wait":
            if not request.frames:
                raise HTTPException(
                    status_code=400,
                    detail="Frames parameter is required for wait action."
                )
            action = Wait(frames=request.frames)
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown action type: {request.action_type}"
            )
        
        # Execute action and measure time
        start_time = time.time()
        state = env.step(action)
        execution_time = time.time() - start_time
        
        # Get collision map and valid moves
        collision_map = env.get_collision_map()
        valid_moves = env.get_valid_moves()
        
        # Prepare response
        response = GameStateResponse(
            memory_info=state.memory_info,
            screenshot_base64=state.screenshot_base64,
            location=state.location,
            coordinates=list(state.coordinates),  # Convert tuple to list
            party_pokemon=state.party_pokemon,
            collision_map=collision_map,
            valid_moves=valid_moves,
            step_number=env.steps_taken,
            execution_time=execution_time
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error taking action: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to take action: {str(e)}"
        )


@app.get("/status")
async def get_status():
    """Get the current status of the environment."""
    if env is None:
        return {"status": "not_initialized"}
    return {"status": "running", "steps_taken": env.steps_taken}


@app.post("/stop")
async def stop_environment():
    """Stop the environment."""
    global env
    
    if env is None:
        return {"status": "not_initialized"}
    
    try:
        env.stop()
        env = None
        return {"status": "stopped"}
    
    except Exception as e:
        logger.error(f"Error stopping environment: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop environment: {str(e)}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pokemon Evaluator API Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--rom", type=str, default="pokemon.gb", help="Path to the Pokemon ROM file")
    
    args = parser.parse_args()
    
    # Run the server
    uvicorn.run(app, host=args.host, port=args.port) 