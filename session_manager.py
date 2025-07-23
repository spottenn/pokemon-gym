"""
Session Management for Pokemon-Gym
Handles session creation, saving, loading, and auto-resume functionality
"""
import os
import time
import json
import logging
import shutil
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages Pokemon gameplay sessions including save/load and auto-resume"""
    
    def __init__(
        self,
        base_dir: str = "gameplay_sessions",
        autosave_interval: int = 50,
        autosave_filename: str = "autosave.state"
    ):
        self.base_dir = Path(base_dir)
        self.autosave_interval = autosave_interval
        self.autosave_filename = autosave_filename
        
        # Current session state
        self.current_session_id: Optional[str] = None
        self.current_session_dir: Optional[Path] = None
        self.last_autosave_step = 0
        
        # Ensure base directory exists
        self.base_dir.mkdir(exist_ok=True)
        logger.info(f"SessionManager initialized with base directory: {self.base_dir}")
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        """
        Create a new gameplay session
        
        Args:
            session_id: Optional custom session ID, otherwise generates timestamp-based ID
            
        Returns:
            The session ID that was created
        """
        if not session_id:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            session_id = f"session_{timestamp}"
        
        session_dir = self.base_dir / session_id
        session_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (session_dir / "images").mkdir(exist_ok=True)
        (session_dir / "states").mkdir(exist_ok=True)
        
        # Create session metadata
        metadata = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "total_steps": 0,
            "status": "active"
        }
        
        metadata_file = session_dir / "session_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        self.current_session_id = session_id
        self.current_session_dir = session_dir
        self.last_autosave_step = 0
        
        logger.info(f"Created new session: {session_id} at {session_dir}")
        return session_id
    
    def load_session(self, session_id: str) -> bool:
        """
        Load an existing session
        
        Args:
            session_id: The session ID to load
            
        Returns:
            True if session was loaded successfully, False otherwise
        """
        session_dir = self.base_dir / session_id
        
        if not session_dir.exists():
            logger.warning(f"Session directory not found: {session_dir}")
            return False
        
        metadata_file = session_dir / "session_metadata.json"
        if not metadata_file.exists():
            logger.warning(f"Session metadata not found: {metadata_file}")
            return False
        
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
            
            self.current_session_id = session_id
            self.current_session_dir = session_dir
            self.last_autosave_step = metadata.get("total_steps", 0)
            
            # Update metadata
            metadata["last_updated"] = datetime.now().isoformat()
            metadata["status"] = "active"
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Loaded session: {session_id} with {self.last_autosave_step} steps")
            return True
            
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}")
            return False
    
    def get_latest_session(self) -> Optional[str]:
        """
        Get the most recently created or updated session
        
        Returns:
            Session ID of the latest session, or None if no sessions exist
        """
        if not self.base_dir.exists():
            return None
        
        latest_session = None
        latest_time = 0
        
        for session_dir in self.base_dir.iterdir():
            if not session_dir.is_dir():
                continue
                
            metadata_file = session_dir / "session_metadata.json"
            if not metadata_file.exists():
                continue
            
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Check last updated time
                last_updated = metadata.get("last_updated", metadata.get("created_at", ""))
                if last_updated:
                    update_time = datetime.fromisoformat(last_updated).timestamp()
                    if update_time > latest_time:
                        latest_time = update_time
                        latest_session = session_dir.name
                        
            except Exception as e:
                logger.warning(f"Error reading session metadata for {session_dir.name}: {e}")
                continue
        
        if latest_session:
            logger.info(f"Latest session found: {latest_session}")
        else:
            logger.info("No sessions found")
            
        return latest_session
    
    def save_state(
        self,
        env,
        step_count: int,
        state_name: Optional[str] = None,
        is_autosave: bool = False
    ) -> str:
        """
        Save the current game state
        
        Args:
            env: The Pokemon environment instance
            step_count: Current step count
            state_name: Optional name for the state file
            is_autosave: Whether this is an automatic save
            
        Returns:
            Path to the saved state file
        """
        if not self.current_session_dir:
            raise ValueError("No active session - create or load a session first")
        
        # Generate filename
        if is_autosave:
            filename = self.autosave_filename
            save_dir = self.current_session_dir
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if state_name:
                filename = f"{state_name}_{timestamp}.state"
            else:
                filename = f"game_state_{timestamp}.state"
            save_dir = self.current_session_dir / "states"
        
        state_path = save_dir / filename
        
        try:
            # Save the state using the environment's save_state method
            env.save_state(str(state_path))
            
            # Update session metadata
            self._update_metadata(step_count)
            
            if is_autosave:
                self.last_autosave_step = step_count
                logger.debug(f"Autosaved game state at step {step_count}")
            else:
                logger.info(f"Saved game state to {state_path}")
            
            return str(state_path)
            
        except Exception as e:
            logger.error(f"Error saving game state: {e}")
            raise
    
    def load_state(
        self,
        env,
        state_path: Optional[str] = None,
        load_autosave: bool = False
    ) -> bool:
        """
        Load a game state
        
        Args:
            env: The Pokemon environment instance
            state_path: Optional path to a specific state file
            load_autosave: Whether to load the autosave file
            
        Returns:
            True if state was loaded successfully
        """
        if not self.current_session_dir:
            raise ValueError("No active session - create or load a session first")
        
        try:
            # Determine which state file to load
            if state_path:
                if not os.path.exists(state_path):
                    logger.warning(f"State file not found: {state_path}")
                    return False
                load_path = state_path
            elif load_autosave:
                load_path = str(self.current_session_dir / self.autosave_filename)
                if not os.path.exists(load_path):
                    logger.warning(f"Autosave file not found: {load_path}")
                    return False
            else:
                # Look for final_state.state first, then latest autosave
                final_state = self.current_session_dir / "final_state.state"
                autosave_path = self.current_session_dir / self.autosave_filename
                
                if final_state.exists():
                    load_path = str(final_state)
                    logger.info("Loading final state from previous session")
                elif autosave_path.exists():
                    load_path = str(autosave_path)
                    logger.info("Loading autosave from previous session")
                else:
                    logger.warning("No saved state found in session")
                    return False
            
            # Load the state
            env.load_state(load_path)
            logger.info(f"Loaded game state from {load_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading game state: {e}")
            return False
    
    def should_autosave(self, current_step: int) -> bool:
        """
        Check if it's time for an autosave
        
        Args:
            current_step: Current step number
            
        Returns:
            True if autosave should be performed
        """
        return (current_step > 0 and 
                current_step % self.autosave_interval == 0 and 
                current_step != self.last_autosave_step)
    
    def finalize_session(self, env, final_step_count: int) -> Dict[str, Any]:
        """
        Finalize the current session (save final state and update metadata)
        
        Args:
            env: The Pokemon environment instance
            final_step_count: Final step count
            
        Returns:
            Session summary dictionary
        """
        if not self.current_session_dir:
            raise ValueError("No active session to finalize")
        
        try:
            # Save final state
            final_state_path = self.current_session_dir / "final_state.state"
            env.save_state(str(final_state_path))
            logger.info(f"Saved final state to {final_state_path}")
            
            # Also update autosave
            autosave_path = self.current_session_dir / self.autosave_filename
            env.save_state(str(autosave_path))
            
            # Update metadata
            metadata = self._update_metadata(final_step_count, status="completed")
            
            # Create session summary
            summary = {
                "session_id": self.current_session_id,
                "session_dir": str(self.current_session_dir),
                "total_steps": final_step_count,
                "duration": metadata.get("duration", "unknown"),
                "status": "completed"
            }
            
            logger.info(f"Finalized session {self.current_session_id} with {final_step_count} steps")
            
            # Clear current session
            self.current_session_id = None
            self.current_session_dir = None
            self.last_autosave_step = 0
            
            return summary
            
        except Exception as e:
            logger.error(f"Error finalizing session: {e}")
            raise
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all available sessions
        
        Returns:
            List of session information dictionaries
        """
        sessions = []
        
        if not self.base_dir.exists():
            return sessions
        
        for session_dir in self.base_dir.iterdir():
            if not session_dir.is_dir():
                continue
                
            metadata_file = session_dir / "session_metadata.json"
            if not metadata_file.exists():
                continue
            
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                sessions.append({
                    "session_id": session_dir.name,
                    "created_at": metadata.get("created_at"),
                    "last_updated": metadata.get("last_updated"),
                    "total_steps": metadata.get("total_steps", 0),
                    "status": metadata.get("status", "unknown"),
                    "has_autosave": (session_dir / self.autosave_filename).exists(),
                    "has_final_state": (session_dir / "final_state.state").exists()
                })
                
            except Exception as e:
                logger.warning(f"Error reading session metadata for {session_dir.name}: {e}")
                continue
        
        # Sort by last updated time (newest first)
        sessions.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its data
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if deletion was successful
        """
        session_dir = self.base_dir / session_id
        
        if not session_dir.exists():
            logger.warning(f"Session not found: {session_id}")
            return False
        
        try:
            shutil.rmtree(session_dir)
            logger.info(f"Deleted session: {session_id}")
            
            # Clear current session if it was deleted
            if self.current_session_id == session_id:
                self.current_session_id = None
                self.current_session_dir = None
                self.last_autosave_step = 0
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    def _update_metadata(self, step_count: int, status: str = "active") -> Dict[str, Any]:
        """Update session metadata file"""
        if not self.current_session_dir:
            return {}
        
        metadata_file = self.current_session_dir / "session_metadata.json"
        
        try:
            # Load existing metadata
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {
                    "session_id": self.current_session_id,
                    "created_at": datetime.now().isoformat()
                }
            
            # Update metadata
            metadata["last_updated"] = datetime.now().isoformat()
            metadata["total_steps"] = step_count
            metadata["status"] = status
            
            # Calculate duration if created_at exists
            if "created_at" in metadata:
                created_time = datetime.fromisoformat(metadata["created_at"])
                current_time = datetime.now()
                duration_seconds = (current_time - created_time).total_seconds()
                metadata["duration"] = f"{duration_seconds:.1f}s"
            
            # Save updated metadata
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error updating session metadata: {e}")
            return {}
    
    @property
    def current_session_path(self) -> Optional[str]:
        """Get the current session directory path"""
        return str(self.current_session_dir) if self.current_session_dir else None
    
    @property
    def is_active(self) -> bool:
        """Check if there's an active session"""
        return self.current_session_id is not None