import argparse
import base64
import io
import logging
import os
import time
import csv
import datetime
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
ROM_PATH = "Pokemon_Red.gb"  # Default ROM path
env = None
csv_writer = None
csv_file = None
last_response_time = None

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


def initialize_csv_logger(filename=None):
    """Initialize the CSV logger with the given filename or a timestamped one."""
    global csv_writer, csv_file
    
    if filename is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"pokemon_gameplay_{timestamp}.csv"
    
    try:
        csv_file = open(filename, 'w', newline='')
        fieldnames = ['timestamp', 'step_number', 'action_type', 'action_details', 
                     'location', 'coordinates', 'party_size', 'execution_time']
        csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        csv_writer.writeheader()
        logger.info(f"Response data will be logged to {filename}")
    except Exception as e:
        logger.error(f"Error initializing CSV logger: {e}")
        csv_writer = None
        if csv_file:
            csv_file.close()
            csv_file = None


def log_response(response: GameStateResponse, action_type: str, action_details: Any):
    """Log a response to the CSV file."""
    global csv_writer
    
    if csv_writer is None:
        return
    
    try:
        row = {
            'timestamp': datetime.datetime.now().isoformat(),
            'step_number': response.step_number,
            'action_type': action_type,
            'action_details': str(action_details),
            'location': response.location,
            'coordinates': str(response.coordinates),
            'party_size': len(response.party_pokemon),
            'execution_time': response.execution_time
        }
        csv_writer.writerow(row)
        csv_file.flush()  # Ensure data is written immediately
        logger.info(f"Response data for step {response.step_number} logged to CSV")
    except Exception as e:
        logger.error(f"Error logging to CSV: {e}")


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
    global env, last_response_time
    
    # Reset the last response time
    last_response_time = time.time()
    
    # Check if ROM file exists
    if not os.path.exists(ROM_PATH):
        raise HTTPException(
            status_code=500, 
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
        logger.info("env initialized")
        
        # Get initial state
        state = env.state
        logger.info("state initialized")
        # Get collision map and valid moves
        collision_map = env.get_collision_map()
        logger.info("collision_map initialized")
        valid_moves = env.get_valid_moves()
        logger.info("valid_moves initialized")
        
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
        
        # Log initial state
        log_response(response, "initialize", request)
        
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
    global env, last_response_time
    
    # Calculate execution time (time since last response)
    current_time = time.time()
    if last_response_time is None:
        execution_time = 0.0  # First action has no previous time
    else:
        execution_time = current_time - last_response_time
    
    # Check if environment is initialized
    if env is None:
        raise HTTPException(
            status_code=400,
            detail="Environment not initialized. Call /initialize first."
        )
    
    logger.info(f"Taking action: {request.action_type}")
    logger.info(f"Keys: {request.keys}")
    logger.info(f"Frames: {request.frames}")
    # Create action based on request
    try:
        if request.action_type == "press_key":
            if not request.keys:
                raise HTTPException(
                    status_code=400,
                    detail="Keys parameter is required for press_key action."
                )
            logger.info(f"Creating PressKey action with keys: {request.keys}")
            action = PressKey(keys=request.keys)
            action_details = {"keys": request.keys}
        
        elif request.action_type == "wait":
            if not request.frames:
                raise HTTPException(
                    status_code=400,
                    detail="Frames parameter is required for wait action."
                )
            
            action = Wait(frames=request.frames)
            action_details = {"wait": request.frames}
        
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown action type: {request.action_type}"
            )
        
        # Execute action
        state = env.step(action)
        
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
            execution_time=execution_time  # Use the calculated time
        )
        
        # Log the action and response
        log_response(response, request.action_type, action_details)
        
        # Update the last response time
        last_response_time = time.time()
        
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
    global env, csv_file
    
    if env is None:
        return {"status": "not_initialized"}
    
    try:
        env.stop()
        env = None
        
        # Close CSV file if open
        if csv_file:
            csv_file.close()
            csv_file = None
            
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
    parser.add_argument("--port", type=int, default=8080, help="Port to run the server on")
    parser.add_argument("--rom", type=str, default="Pokemon_Red.gb", help="Path to the Pokemon ROM file")
    parser.add_argument("--log-file", type=str, help="CSV file to log responses (default: timestamped file)")
    
    args = parser.parse_args()
    
    # Set ROM path
    ROM_PATH = args.rom
    
    # Initialize CSV logger
    initialize_csv_logger(args.log_file)
    
    # Run the server
    uvicorn.run(app, host=args.host, port=args.port) 