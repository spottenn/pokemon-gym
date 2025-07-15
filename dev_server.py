#!/usr/bin/env python3
"""
Development server with live reload and automatic session resumption.

This script provides live reload functionality for the Pokemon Gym server,
automatically restarting when code changes and resuming the latest session.
"""

import argparse
import glob
import os
import logging
import uvicorn
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def get_latest_session():
    """Find the most recent session directory."""
    sessions = glob.glob("gameplay_sessions/session_*")
    if not sessions:
        return None
    
    # Sort by modification time to get the most recent
    latest_session = max(sessions, key=os.path.getmtime)
    logger.info(f"Found latest session: {latest_session}")
    return os.path.basename(latest_session)

def check_rom_exists(rom_path):
    """Check if the ROM file exists."""
    if not os.path.exists(rom_path):
        logger.error(f"ROM file not found: {rom_path}")
        logger.error("Please place Pokemon_Red.gb in the project root directory")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="Pokemon Gym Development Server with Live Reload")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on")
    parser.add_argument("--port", type=int, default=8080, help="Port to run the server on")
    parser.add_argument("--rom", type=str, default="Pokemon_Red.gb", help="Path to the Pokemon ROM file")
    parser.add_argument("--no-resume", action="store_true", help="Don't automatically resume latest session")
    parser.add_argument("--session", type=str, help="Specific session ID to resume")
    parser.add_argument("--no-streaming", action="store_true", help="Disable default streaming mode for development")
    
    args = parser.parse_args()
    
    # Check if ROM exists
    if not check_rom_exists(args.rom):
        return 1
    
    # Find latest session for resumption info
    latest_session = None
    if not args.no_resume:
        if args.session:
            latest_session = args.session
            logger.info(f"Will resume specified session: {latest_session}")
        else:
            latest_session = get_latest_session()
            if latest_session:
                logger.info(f"Will automatically resume latest session: {latest_session}")
            else:
                logger.info("No previous sessions found - will start fresh")
    
    # Set environment variables for the server
    os.environ["DEV_MODE"] = "true"
    os.environ["ROM_PATH"] = args.rom
    if latest_session and not args.no_resume:
        os.environ["AUTO_RESUME_SESSION"] = latest_session
    
    # Enable streaming mode by default in dev mode (unless disabled)
    if not args.no_streaming:
        os.environ["DEV_STREAMING_MODE"] = "true"
    
    logger.info("=" * 60)
    logger.info("🚀 Starting Pokemon Gym Development Server")
    logger.info("=" * 60)
    logger.info(f"Server: http://{args.host}:{args.port}")
    logger.info(f"ROM: {args.rom}")
    if latest_session and not args.no_resume:
        logger.info(f"Auto-resume: {latest_session}")
    logger.info("Live reload: ENABLED")
    logger.info("Watching: pokemon_env/, server/, evaluator/")
    if not args.no_streaming:
        logger.info("Streaming mode: ENABLED (default for dev)")
    else:
        logger.info("Streaming mode: DISABLED")
    logger.info("=" * 60)
    logger.info("💡 The server will automatically restart when you modify code")
    logger.info("💾 Sessions auto-save every 10 steps and will resume on restart")
    logger.info("🎮 Use Ctrl+C to stop the server")
    logger.info("=" * 60)
    
    try:
        uvicorn.run(
            "server.evaluator_server:app",
            host=args.host,
            port=args.port,
            reload=True,
            reload_dirs=["pokemon_env", "server", "evaluator"],
            reload_includes=["*.py"],
            reload_excludes=["**/.*", "**/__pycache__", "**/gameplay_sessions/**"],
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("\n🛑 Server stopped by user")
        return 0
    except Exception as e:
        logger.error(f"❌ Server error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())