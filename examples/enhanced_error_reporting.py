'''
Enhanced Error Reporting Examples

This file demonstrates practical usage of the Enhanced Error Reporting feature
in Mistral Vibe plugins. Each example shows a different aspect of error handling
and reporting.
'''

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

# Example 1: Basic Structured Logging
# ====================================

def configure_structured_logging():
    '''
    Configure structured logging for a plugin.
    
    This example shows how to set up structured logging that outputs
    errors in JSON format for easy parsing and integration with monitoring tools.
    '''
    # Create a custom formatter for JSON output
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_record = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": record.levelname,
                "message": record.getMessage(),
                "logger": record.name,
            }
            if record.exc_info:
                log_record["stack_trace"] = self.formatException(record.exc_info)
            return json.dumps(log_record)
    
    # Configure the logger
    logger = logging.getLogger("plugin.example")
    logger.setLevel(logging.DEBUG)
    
    # Create console handler with JSON formatter
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    return logger

def example_basic_structured_logging():
    '''
    Demonstrate basic structured logging usage.
    '''
    logger = configure_structured_logging()
    
    try:
        # Simulate a plugin operation that might fail
        result = 1 / 0
    except Exception as e:
        logger.error("Division by zero error", exc_info=True)

# Example 2: Error Context Capture
# ================================

def log_error_with_context(
    logger: logging.Logger,
    message: str,
    context: Dict[str, Any],
    exception: Optional[Exception] = None
):
    '''
    Log an error with additional context information.
    
    Args:
        logger: The logger instance
        message: Error message
        context: Dictionary containing context information
        exception: Optional exception to include in the log
    '''
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "ERROR",
        "message": message,
        "context": context,
    }
    
    if exception:
        log_entry["exception"] = str(exception)
        log_entry["stack_trace"] = "".join(
            traceback.format_exception(type(exception), exception, exception.__traceback__)
        )
    
    logger.error(json.dumps(log_entry))

def example_error_context():
    '''
    Demonstrate error logging with rich context information.
    '''
    logger = configure_structured_logging()
    
    # Simulate a plugin operation with context
    plugin_name = "data_processor"
    operation = "transform_data"
    input_data = {"file": "data.csv", "rows": 1000}
    
    try:
        # This would normally be the actual operation
        raise ValueError("Invalid data format in column 'timestamp'")
        
    except Exception as e:
        context = {
            "plugin_name": plugin_name,
            "operation": operation,
            "input": input_data,
            "line_number": 42,
            "file_path": __file__
        }
        log_error_with_context(logger, "Data processing failed", context, e)

# Example 3: Error Propagation to Agent Loop
# ==========================================

class AgentLoop:
    '''
    Simplified representation of the agent loop that handles error propagation.
    '''
    
    def __init__(self):
        self.logger = configure_structured_logging()
        self.errors = []
    
    def handle_error(self, error_data: Dict[str, Any]):
        '''
        Handle an error propagated from a plugin or tool.
        
        Args:
            error_data: Dictionary containing error information
        '''
        self.errors.append(error_data)
        
        # Log the error in the agent loop
        self.logger.error("Error propagated to agent loop", extra={"error": error_data})
        
        # In a real implementation, this might trigger:
        # - Retry logic
        # - User notification
        # - Recovery mechanisms
    
    def get_error_count(self) -> int:
        return len(self.errors)

def example_error_propagation():
    '''
    Demonstrate how errors propagate from plugins to the agent loop.
    '''
    agent_loop = AgentLoop()
    
    # Simulate a plugin operation
    plugin_name = "code_analyzer"
    operation = "analyze_syntax"
    
    try:
        # This would be the actual plugin code that fails
        raise RuntimeError("Syntax analysis timeout after 30 seconds")
        
    except Exception as e:
        # Create error context
        error_context = {
            "plugin_name": plugin_name,
            "operation": operation,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "error_type": type(e).__name__,
            "error_message": str(e),
            "severity": "high",
            "recoverable": True
        }
        
        # Propagate error to agent loop
        agent_loop.handle_error(error_context)
        
        print(f"Agent loop has handled {agent_loop.get_error_count()} errors")

# Example 4: Circuit Breaker Integration
# =====================================

class CircuitBreaker:
    '''
    Simplified circuit breaker implementation.
    '''
    
    def __init__(self, name: str, max_failures: int = 3, reset_timeout: int = 60):
        self.name = name
        self.max_failures = max_failures
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.last_failure_time = None
    
    def call(self, operation, fallback=None):
        '''
        Execute an operation with circuit breaker protection.
        '''
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                return fallback
        
        try:
            result = operation()
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failures = 0
            return result
            
        except Exception as e:
            self.failures += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.failures >= self.max_failures:
                self.state = "OPEN"
            
            raise CircuitBreakerError(
                f"Circuit breaker '{self.name}' is now {self.state}",
                circuit_breaker=self
            ) from e
    
    def _should_attempt_reset(self) -> bool:
        if self.last_failure_time is None:
            return True
        
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.reset_timeout

class CircuitBreakerError(Exception):
    '''
    Exception raised when a circuit breaker trips.
    '''
    
    def __init__(self, message: str, circuit_breaker: CircuitBreaker):
        super().__init__(message)
        self.circuit_breaker = circuit_breaker

def log_circuit_breaker_error(
    logger: logging.Logger,
    error: CircuitBreakerError,
    context: Dict[str, Any]
):
    '''
    Log a circuit breaker error with state information.
    '''
    cb = error.circuit_breaker
    
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "level": "ERROR",
        "message": str(error),
        "context": context,
        "circuit_breaker": {
            "name": cb.name,
            "state": cb.state,
            "failures": cb.failures,
            "max_failures": cb.max_failures,
            "reset_timeout": cb.reset_timeout,
            "last_failure_time": cb.last_failure_time.isoformat() + "Z" if cb.last_failure_time else None
        }
    }
    
    logger.error(json.dumps(log_entry))

def example_circuit_breaker_integration():
    '''
    Demonstrate circuit breaker error logging with state information.
    '''
    logger = configure_structured_logging()
    
    # Create a circuit breaker for a plugin
    cb = CircuitBreaker("database_connector", max_failures=2)
    
    def unreliable_operation():
        # Simulate an operation that might fail
        raise ConnectionError("Database connection timeout")
    
    try:
        # This will eventually trip the circuit breaker
        for i in range(3):
            print(f"Attempt {i + 1}")
            cb.call(unreliable_operation)
            
    except CircuitBreakerError as e:
        context = {
            "plugin_name": "database_plugin",
            "operation": "query_database",
            "attempt": 3,
            "file_path": __file__
        }
        
        log_circuit_breaker_error(logger, e, context)

# Main execution
# ==============

if __name__ == "__main__":
    import traceback
    
    print("=== Enhanced Error Reporting Examples ===\n")
    
    print("1. Basic Structured Logging:")
    print("-" * 50)
    example_basic_structured_logging()
    print()
    
    print("2. Error Context Capture:")
    print("-" * 50)
    example_error_context()
    print()
    
    print("3. Error Propagation to Agent Loop:")
    print("-" * 50)
    example_error_propagation()
    print()
    
    print("4. Circuit Breaker Integration:")
    print("-" * 50)
    example_circuit_breaker_integration()
    print()
    
    print("Examples completed. Check the console output for structured error logs.")