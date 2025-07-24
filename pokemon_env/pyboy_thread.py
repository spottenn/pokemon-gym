"""
PyBoy Thread Manager - Handles PyBoy emulator in a dedicated thread for thread-safe operations.
Based on LLM Pokemon Scaffold's proven threading architecture.
"""
import threading
import queue
import time
import logging
from typing import Optional, Tuple, Any
from PIL import Image
import numpy as np
from pyboy import PyBoy

logger = logging.getLogger(__name__)


class PriorityLock:
    """Priority-based lock for thread synchronization."""
    def __init__(self):
        self._lock = threading.Lock()
        self._queue = queue.PriorityQueue()

    def acquire(self, priority):
        self._queue.put((priority, threading.get_ident()))
        with self._lock:
            _, current_thread = self._queue.get()
            if current_thread != threading.get_ident():
                raise RuntimeError("Priority lock acquired out of order")

    def release(self):
        with self._lock:
            self._queue.task_done()

    class PriorityLockContextHandler:
        def __init__(self, priority_lock, priority):
            self.priority_lock = priority_lock
            self.priority = priority

        def __enter__(self):
            self.priority_lock.acquire(self.priority)
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.priority_lock.release()
            return False

    def __call__(self, priority):
        return self.PriorityLockContextHandler(self, priority)


class PyBoyThread:
    """Manages PyBoy emulator in a dedicated thread with queue-based communication."""
    
    def __init__(self):
        self.pyboy: Optional[PyBoy] = None
        self.pyboy_lock = PriorityLock()
        self.button_queue: Optional[queue.Queue] = None
        self.button_queue_clear = threading.Event()
        self.run_thread: Optional[threading.Thread] = None
        self.running = False
        self.initialized = threading.Event()
        
    def _pyboy_worker(self, rom_path: str, headless: bool = True, sound: bool = False):
        """Worker thread that owns and operates the PyBoy instance."""
        self.button_queue = queue.Queue()
        
        try:
            # Initialize PyBoy in this thread
            if headless:
                self.pyboy = PyBoy(
                    rom_path,
                    window="null",
                    cgb=True
                )
            else:
                self.pyboy = PyBoy(
                    rom_path,
                    cgb=True,
                    sound=sound
                )
            
            # Run for a short time to ensure it's ready
            self.pyboy.set_emulation_speed(0)
            for _ in range(60):
                self.pyboy.tick()
            self.pyboy.set_emulation_speed(1)
            
            # Signal that PyBoy is initialized
            self.initialized.set()
            logger.info("PyBoy initialized in dedicated thread")
            
            # Main loop - process button queue and tick
            while self.running:
                with self.pyboy_lock(10):
                    try:
                        # Process queued commands
                        item, data = self.button_queue.get(block=False)
                        
                        if item == "stop":
                            logger.info("Received stop command")
                            break
                        elif item == "wait":
                            frames = data
                            for _ in range(frames):
                                if not self.pyboy.tick():
                                    self.running = False
                                    break
                        elif item == "press_button":
                            button = data["button"]
                            frames = data.get("frames", 10)
                            self.pyboy.button_press(button)
                            for _ in range(frames):
                                self.pyboy.tick()
                            self.pyboy.button_release(button)
                        elif item == "save_state":
                            file_like = data
                            self.pyboy.save_state(file_like)
                        elif item == "load_state":
                            file_like = data
                            self.pyboy.load_state(file_like)
                        elif item == "set_emulation_speed":
                            speed = data
                            self.pyboy.set_emulation_speed(speed)
                            
                    except queue.Empty:
                        # No commands, just tick
                        if not self.pyboy.tick():
                            self.running = False
                            
                    # Signal queue is clear if empty
                    if self.button_queue.empty():
                        self.button_queue_clear.set()
                        
        except Exception as e:
            logger.error(f"Error in PyBoy thread: {e}")
            raise
        finally:
            if self.pyboy:
                self.pyboy.stop()
                self.pyboy = None
            self.button_queue_clear.set()
            logger.info("PyBoy thread terminated")
    
    def start(self, rom_path: str, headless: bool = True, sound: bool = False):
        """Start the PyBoy thread."""
        if self.running:
            logger.warning("PyBoy thread already running")
            return
            
        self.running = True
        self.initialized.clear()
        self.run_thread = threading.Thread(
            target=self._pyboy_worker,
            args=(rom_path, headless, sound),
            daemon=True
        )
        self.run_thread.start()
        
        # Wait for PyBoy to initialize
        if not self.initialized.wait(timeout=10):
            raise RuntimeError("PyBoy failed to initialize within timeout")
            
    def stop(self):
        """Stop the PyBoy thread."""
        if not self.running:
            return
            
        self.running = False
        if self.button_queue:
            with self.pyboy_lock(1):
                self.button_queue_clear.clear()
                self.button_queue.put(("stop", None))
                
        if self.run_thread:
            self.run_thread.join(timeout=5)
            if self.run_thread.is_alive():
                logger.warning("PyBoy thread did not terminate gracefully")
                
    def queue_action(self, action_type: str, data: Any):
        """Queue an action for the PyBoy thread to process."""
        if not self.running or not self.button_queue:
            raise RuntimeError("PyBoy thread not running")
            
        with self.pyboy_lock(5):
            self.button_queue_clear.clear()
            self.button_queue.put((action_type, data))
            
    def wait_for_queue(self, timeout: Optional[float] = None) -> bool:
        """Wait for the button queue to be processed."""
        return self.button_queue_clear.wait(timeout)
    
    def get_screen_ndarray(self) -> np.ndarray:
        """Get the current screen as a numpy array (thread-safe)."""
        if not self.pyboy:
            raise RuntimeError("PyBoy not initialized")
            
        # Wait for queue to clear to ensure we get a stable frame
        self.wait_for_queue(timeout=1)
        time.sleep(0.1)  # Small delay for frame stability
        
        # The screen.ndarray property is thread-safe for reading
        return self.pyboy.screen.ndarray.copy()
    
    def get_screen_image(self) -> Image.Image:
        """Get the current screen as a PIL Image (thread-safe)."""
        return Image.fromarray(self.get_screen_ndarray())
    
    def tick(self, frames: int = 1):
        """Queue a wait/tick action."""
        self.queue_action("wait", frames)
        self.wait_for_queue()
        
    def press_button(self, button: str, frames: int = 10):
        """Queue a button press action."""
        self.queue_action("press_button", {"button": button, "frames": frames})
        
    def save_state(self, file_like):
        """Save the emulator state."""
        self.queue_action("save_state", file_like)
        self.wait_for_queue()
        
    def load_state(self, file_like):
        """Load an emulator state."""
        self.queue_action("load_state", file_like)
        self.wait_for_queue()
        
    def set_emulation_speed(self, speed: int):
        """Set the emulation speed."""
        self.queue_action("set_emulation_speed", speed)
        
    @property
    def memory(self):
        """Access PyBoy memory (read-only operations are thread-safe)."""
        if not self.pyboy:
            raise RuntimeError("PyBoy not initialized")
        return self.pyboy.memory
    
    @property 
    def game_wrapper(self):
        """Access PyBoy game wrapper (read-only operations are thread-safe)."""
        if not self.pyboy:
            raise RuntimeError("PyBoy not initialized")
        return self.pyboy.game_wrapper
    
    def get_sprite(self, sprite_id: int):
        """Get sprite information (thread-safe read operation)."""
        if not self.pyboy:
            raise RuntimeError("PyBoy not initialized")
        return self.pyboy.get_sprite(sprite_id)
        
    @property
    def screen(self):
        """Access PyBoy screen for compatibility."""
        if not self.pyboy:
            raise RuntimeError("PyBoy not initialized")
        return self.pyboy.screen