import json
import hashlib
import logging
import time
import zlib
from typing import Any, Dict, Optional, Tuple, Callable
from multiprocessing import Queue
from multiprocessing.connection import Connection
import socket
import struct
from enum import Enum

try:
    import msgpack
    MSGPACK_AVAILABLE = True
except ImportError:
    msgpack = None
    MSGPACK_AVAILABLE = False


class MessageType(Enum):
    """Message types for IPC communication."""
    DATA = "DATA"
    ERROR = "ERROR"
    ACK = "ACK"
    PING = "PING"
    PONG = "PONG"


class IPCError(Exception):
    """Base exception for IPC-related errors."""
    pass


class IPCValidationError(IPCError):
    """Exception for message validation failures."""
    pass


class IPCConnectionError(IPCError):
    """Exception for connection-related errors."""
    pass


class IPCProtocol:
    """
    Secure inter-process communication protocol for safe context/data passing.
    
    This class provides methods for serializing, deserializing, validating,
    and transmitting data between processes with security and reliability.
    
    Features:
    - Secure serialization using JSON or MessagePack
    - Message validation and integrity checking
    - Bidirectional communication support
    - Error handling and recovery
    - Connection health monitoring
    """
    
    # Maximum message size in bytes (10MB)
    MAX_MESSAGE_SIZE = 10 * 1024 * 1024
    
    # Supported serialization formats
    SERIALIZATION_JSON = "json"
    SERIALIZATION_MSGPACK = "msgpack"
    
    def __init__(self, serialization_format: str = SERIALIZATION_JSON):
        """
        Initialize the IPC protocol.
        
        Args:
            serialization_format (str): Format to use ('json' or 'msgpack')
            
        Raises:
            ValueError: If unsupported serialization format is provided
        """
        if serialization_format not in [self.SERIALIZATION_JSON, self.SERIALIZATION_MSGPACK]:
            raise ValueError(f"Unsupported serialization format: {serialization_format}")
        if serialization_format == self.SERIALIZATION_MSGPACK and not MSGPACK_AVAILABLE:
            raise ValueError("msgpack not available, please install msgpack package")
        self.serialization_format = serialization_format
        self.logger = logging.getLogger(__name__)
    
    def serialize(self, data: Any) -> str:
        """
        Serialize data to a string using the configured format.
        
        Args:
            data: The data to serialize.
            
        Returns:
            str: The serialized data.
            
        Raises:
            IPCError: If serialization fails
        """
        try:
            if self.serialization_format == self.SERIALIZATION_JSON:
                return json.dumps(data, separators=(',', ':'))
            else:  # msgpack
                if msgpack is None:
                    raise IPCError("msgpack not available")
                return msgpack.dumps(data).decode('latin-1')
        except (TypeError, ValueError, OverflowError) as e:
            raise IPCError(f"Serialization failed: {str(e)}") from e
    
    def deserialize(self, serialized_data: str) -> Any:
        """
        Deserialize data from a string using the configured format.
        
        Args:
            serialized_data (str): The serialized data.
            
        Returns:
            The deserialized data.
            
        Raises:
            IPCError: If deserialization fails
        """
        try:
            if self.serialization_format == self.SERIALIZATION_JSON:
                return json.loads(serialized_data)
            else:  # msgpack
                if msgpack is None:
                    raise IPCError("msgpack not available")
                return msgpack.loads(serialized_data.encode('latin-1'))
        except (json.JSONDecodeError, ValueError) as e:
            raise IPCError(f"Deserialization failed: {str(e)}") from e
        except Exception as e:
            if hasattr(e, '__module__') and 'msgpack' in e.__module__:
                raise IPCError(f"Deserialization failed: {str(e)}") from e
            else:
                raise IPCError(f"Deserialization failed: {str(e)}") from e
    
    def validate_message(self, message: Dict[str, Any]) -> bool:
        """
        Validate the structure and content of an IPC message.
        
        Args:
            message (dict): The message to validate.
            
        Returns:
            bool: True if message is valid, False otherwise.
            
        Raises:
            IPCValidationError: If message validation fails
        """
        if not isinstance(message, dict):
            raise IPCValidationError("Message must be a dictionary")
        
        # Check required fields
        required_fields = ['type', 'data', 'timestamp', 'checksum']
        for field in required_fields:
            if field not in message:
                raise IPCValidationError(f"Missing required field: {field}")
        
        # Validate message type
        if not isinstance(message['type'], str):
            raise IPCValidationError("Message type must be a string")
        
        try:
            MessageType(message['type'])
        except ValueError:
            raise IPCValidationError(f"Invalid message type: {message['type']}")
        
        # Validate timestamp
        if not isinstance(message['timestamp'], (int, float)):
            raise IPCValidationError("Timestamp must be a number")
        
        # Validate checksum
        if not isinstance(message['checksum'], str) or len(message['checksum']) != 64:
            raise IPCValidationError("Checksum must be a 64-character hex string")
        
        # Verify checksum integrity
        self._verify_checksum(message)
        
        return True
    
    def _verify_checksum(self, message: Dict[str, Any]) -> None:
        """
        Verify the integrity of a message using its checksum.
        
        Args:
            message (dict): The message to verify.
            
        Raises:
            IPCValidationError: If checksum verification fails
        """
        # Create a copy without the checksum field
        message_copy = message.copy()
        checksum = message_copy.pop('checksum')
        
        # Serialize the message content for checksum calculation
        content_str = self.serialize(message_copy)
        
        # Calculate expected checksum
        expected_checksum = hashlib.sha256(content_str.encode('utf-8')).hexdigest()
        
        if checksum != expected_checksum:
            raise IPCValidationError("Checksum verification failed - message may be corrupted")
    
    def create_message(self, message_type: MessageType, data: Any, timestamp: Optional[float] = None) -> Dict[str, Any]:
        """
        Create a properly formatted IPC message with checksum.
        
        Args:
            message_type (MessageType): Type of the message.
            data: The message data.
            timestamp (float, optional): Message timestamp. Uses current time if None.
            
        Returns:
            dict: Formatted message with checksum.
        """
        import time
        if timestamp is None:
            timestamp = time.time()
        
        # Create base message
        message = {
            'type': message_type.value,
            'data': data,
            'timestamp': timestamp
        }
        
        # Calculate checksum
        content_str = self.serialize(message)
        checksum = hashlib.sha256(content_str.encode('utf-8')).hexdigest()
        
        # Add checksum to message
        message['checksum'] = checksum
        
        return message
    
    def send_data(self, queue: Queue, data: Any, message_type: MessageType = MessageType.DATA) -> None:
        """
        Send data through a multiprocessing queue with validation and error handling.
        
        Args:
            queue (Queue): The multiprocessing queue.
            data: The data to send.
            message_type (MessageType): Type of message (default: DATA).
            
        Raises:
            IPCError: If sending fails
            IPCConnectionError: If queue connection is broken
        """
        try:
            # Create and validate message
            message = self.create_message(message_type, data)
            self.validate_message(message)
            
            # Serialize and send
            serialized_message = self.serialize(message)
            
            # Compress large messages
            if len(serialized_message) > 1024:
                compressed_data = zlib.compress(serialized_message.encode('utf-8'))
                queue.put((True, compressed_data))  # (is_compressed, data)
            else:
                queue.put((False, serialized_message))
                
        except (BrokenPipeError, ConnectionError) as e:
            raise IPCConnectionError(f"Queue connection broken: {str(e)}") from e
        except Exception as e:
            raise IPCError(f"Failed to send data: {str(e)}") from e
    
    def receive_data(self, queue: Queue) -> Any:
        """
        Receive data from a multiprocessing queue with validation and error handling.
        
        Args:
            queue (Queue): The multiprocessing queue.
            
        Returns:
            The deserialized data.
            
        Raises:
            IPCError: If receiving or processing fails
            IPCConnectionError: If queue connection is broken
            IPCValidationError: If message validation fails
        """
        try:
            # Get raw data from queue
            raw_data = queue.get()
            
            if not isinstance(raw_data, tuple) or len(raw_data) != 2:
                raise IPCError("Invalid data format received from queue")
            
            is_compressed, data = raw_data
            
            # Decompress if needed
            if is_compressed:
                try:
                    data = zlib.decompress(data).decode('utf-8')
                except (zlib.error, UnicodeDecodeError) as e:
                    raise IPCError(f"Decompression failed: {str(e)}") from e
            
            # Deserialize message
            message = self.deserialize(data)
            
            # Validate message structure and integrity
            self.validate_message(message)
            
            # Handle different message types
            if message['type'] == MessageType.ERROR.value:
                error_data = message['data']
                if isinstance(error_data, dict) and 'error' in error_data:
                    raise IPCError(error_data['error'])
                else:
                    raise IPCError(str(error_data))
            
            return message['data']
            
        except (BrokenPipeError, ConnectionError) as e:
            raise IPCConnectionError(f"Queue connection broken: {str(e)}") from e
        except Exception as e:
            raise IPCError(f"Failed to receive data: {str(e)}") from e
    
    def send_error(self, queue: Queue, error: str) -> None:
        """
        Send an error message through the queue.
        
        Args:
            queue (Queue): The multiprocessing queue.
            error (str): The error message.
            
        Raises:
            IPCError: If sending fails
        """
        error_message = {
            'error': error,
            'timestamp': time.time()
        }
        self.send_data(queue, error_message, MessageType.ERROR)
    
    def ping(self, queue: Queue) -> bool:
        """
        Send a ping message to check connection health.
        
        Args:
            queue (Queue): The multiprocessing queue.
            
        Returns:
            bool: True if pong received, False otherwise.
        """
        try:
            self.send_data(queue, {"ping": True}, MessageType.PING)
            response = self.receive_data(queue)
            return response.get('pong', False)
        except Exception:
            return False
    
    def handle_connection_error(self, queue: Queue, max_retries: int = 3) -> bool:
        """
        Attempt to recover from a connection error.
        
        Args:
            queue (Queue): The multiprocessing queue.
            max_retries (int): Maximum number of retry attempts.
            
        Returns:
            bool: True if connection recovered, False otherwise.
        """
        for attempt in range(max_retries):
            try:
                if self.ping(queue):
                    self.logger.info(f"Connection recovered after {attempt + 1} attempts")
                    return True
                time.sleep(0.1 * (attempt + 1))  # Exponential backoff
            except Exception:
                if attempt == max_retries - 1:
                    self.logger.error("Failed to recover connection after maximum retries")
                    return False
        return False
    
    @staticmethod
    def create_queue_pair() -> Tuple[Queue, Queue]:
        """
        Create a pair of queues for bidirectional communication.
        
        Returns:
            tuple: (parent_queue, child_queue) for bidirectional communication.
        """
        parent_to_child = Queue()
        child_to_parent = Queue()
        return parent_to_child, child_to_parent
    
    def bidirectional_communication(
        self, 
        parent_queue: Queue, 
        child_queue: Queue,
        parent_func: Callable,
        child_func: Callable
    ) -> Any:
        """
        Establish bidirectional communication between parent and child processes.
        
        Args:
            parent_queue (Queue): Queue for parent to child communication.
            child_queue (Queue): Queue for child to parent communication.
            parent_func (callable): Function to run in parent process.
            child_func (callable): Function to run in child process.
            
        Returns:
            Result from parent function execution.
            
        Raises:
            IPCError: If communication fails
        """
        import multiprocessing
        
        def child_process_wrapper(p_queue, c_queue):
            """Wrapper function for child process."""
            try:
                result = child_func(p_queue, c_queue)
                self.send_data(c_queue, result)
            except Exception as e:
                self.send_error(c_queue, str(e))
        
        # Start child process
        child_process = multiprocessing.Process(
            target=child_process_wrapper, 
            args=(parent_queue, child_queue)
        )
        child_process.start()
        
        try:
            # Execute parent function
            result = parent_func(parent_queue, child_queue)
            return result
        finally:
            # Clean up child process
            child_process.join(timeout=1)
            if child_process.is_alive():
                child_process.terminate()
                child_process.join()