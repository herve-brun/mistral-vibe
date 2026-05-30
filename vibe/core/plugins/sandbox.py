"""
Plugin Sandbox implementation with resource limits and process isolation.
"""

import multiprocessing
import os
import signal
import sys
import time
import traceback
import platform
from multiprocessing import Process, Queue
from typing import Any, Callable

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None  # type: ignore

try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False
    resource = None  # type: ignore


class PluginSandbox:
    """
    A sandbox for executing plugins in isolated processes with resource limits.
    
    Attributes:
        timeout (int): Maximum execution time in seconds.
        memory_limit_mb (int): Maximum memory usage in MB.
        cpu_limit (float): Maximum CPU usage as percentage or core count.
    """

    def __init__(self, timeout=10, memory_limit_mb=100, cpu_limit=1.0):
        self.timeout = timeout
        self.memory_limit_mb = memory_limit_mb
        self.cpu_limit = cpu_limit
        # Use 'spawn' context on Windows for better compatibility
        if platform.system() == 'Windows':
            self.context = multiprocessing.get_context('spawn')
        else:
            self.context = multiprocessing.get_context()

    def _worker_function(self, func, args, kwargs, result_queue, memory_limit_mb, cpu_limit):
        """
        Worker function that runs in a separate process with resource limits.
        
        Args:
            func (callable): The function to execute.
            args (tuple): Positional arguments for the function.
            kwargs (dict): Keyword arguments for the function.
            result_queue (Queue): Queue to communicate result or exception back.
            memory_limit_mb (int): Maximum memory usage in MB.
            cpu_limit (float): Maximum CPU usage as percentage or core count.
        """
        try:
            # Apply resource limits if psutil is available
            if HAS_PSUTIL and psutil is not None:
                current_process = psutil.Process(os.getpid())
                
                # Set memory limit
                try:
                    current_process.memory_info()
                    # Note: psutil doesn't directly support setting memory limits,
                    # but we can monitor and terminate if exceeded
                except Exception:
                    pass
                
                # Set CPU affinity if cpu_limit is less than available cores
                try:
                    num_cores = psutil.cpu_count(logical=True) or 1
                    if cpu_limit < num_cores:
                        # Convert cpu_limit to integer number of cores
                        cpu_cores = max(1, int(cpu_limit))
                        current_process.cpu_affinity(list(range(cpu_cores)))
                except Exception:
                    pass
            
            # Apply Unix-specific resource limits if available
            if HAS_RESOURCE and resource is not None and sys.platform != "win32":
                try:
                    # Set memory limit (in bytes)
                    soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_AS)
                    memory_limit_bytes = memory_limit_mb * 1024 * 1024
                    resource.setrlimit(resource.RLIMIT_AS, (memory_limit_bytes, hard_limit))
                    
                    # Set CPU time limit (in seconds)
                    # Convert cpu_limit percentage to seconds (e.g., 1.0 = 100% of one core for cpu_limit seconds)
                    cpu_time_limit = int(cpu_limit)
                    if cpu_time_limit > 0:
                        soft_cpu, hard_cpu = resource.getrlimit(resource.RLIMIT_CPU)
                        resource.setrlimit(resource.RLIMIT_CPU, (cpu_time_limit, hard_cpu))
                except Exception:
                    pass
            
            result = func(*args, **kwargs)
            result_queue.put(("success", result))
        except MemoryError as e:
            result_queue.put(("exception", ("MemoryError", f"Plugin exceeded memory limit of {memory_limit_mb} MB: {e}", traceback.format_exc())))
        except Exception as e:
            # Serialize exception for cross-process transfer
            result_queue.put(("exception", (type(e).__name__, str(e), traceback.format_exc())))

    def execute(self, func, *args, **kwargs):
        """
        Execute a function in a sandboxed process with resource limits.
        
        Args:
            func (callable): The function to execute.
            *args: Positional arguments for the function.
            **kwargs: Keyword arguments for the function.
            
        Returns:
            The result of the function execution.
            
        Raises:
            TimeoutError: If the function execution exceeds the timeout.
            Exception: Any exception raised by the function.
        """
        # Create a queue for inter-process communication
        result_queue = self.context.Queue()
        
        # Create and start the process
        process = self.context.Process(
            target=self._worker_function,
            args=(func, args, kwargs, result_queue, self.memory_limit_mb, self.cpu_limit)
        )
        process.start()
        
        # Wait for the process to complete or timeout
        process.join(timeout=self.timeout)
        
        # Check if process is still alive (timed out)
        if process.is_alive():
            # Terminate the process if it timed out
            process.terminate()
            process.join()
            if not result_queue.empty():
                result_queue.get_nowait()  # Clear the queue
            raise TimeoutError(f"Function execution exceeded the timeout of {self.timeout} seconds.")
        
        # Get the result from the queue
        try:
            if not result_queue.empty():
                status, result = result_queue.get_nowait()
                if status == "success":
                    return result
                elif status == "exception":
                    exc_type_name, exc_message, exc_traceback = result
                    # Create and raise the exception
                    exc_class = getattr(sys.modules['__main__'], exc_type_name, Exception)
                    raise exc_class(exc_message)
        finally:
            # Clean up the queue
            while not result_queue.empty():
                try:
                    result_queue.get_nowait()
                except:
                    break
        
        # If queue is empty but process finished, raise an error
        raise RuntimeError("Plugin execution completed but no result was returned")

    def from_config(self, config: Any) -> 'PluginSandbox':
        """Create a PluginSandbox instance from configuration."""
        return PluginSandbox(
            timeout=getattr(config, 'plugin_sandbox_timeout_sec', 10),
            memory_limit_mb=getattr(config, 'plugin_sandbox_memory_limit_mb', 100),
            cpu_limit=getattr(config, 'plugin_sandbox_cpu_limit', 1.0),
        )