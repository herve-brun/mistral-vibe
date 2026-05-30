# Plugin Isolation and Sandboxing Examples

"""
This file demonstrates the Plugin Isolation and Sandboxing feature in Mistral Vibe.
It includes practical examples for enabling sandboxing, setting resource limits,
configuring sandboxing in config.toml, and safely passing data between processes.
"""

# Example 1: Basic Sandboxing
"""
Enable and configure sandboxing for a plugin.
"""

from vibe.core.plugins.sandbox import PluginSandbox
from vibe.core.plugins.ipc import IPCProtocol
from multiprocessing import Queue

# Example function to be executed in a sandbox
def example_plugin_function():
    """A simple function that simulates plugin behavior."""
    return "Plugin executed successfully"

# Create a sandbox with a timeout
sandbox = PluginSandbox(timeout=10)

# Execute the function in the sandbox
try:
    result = sandbox.execute(example_plugin_function)
    print(f"Plugin function executed successfully: {result}")
except TimeoutError as e:
    print(f"Plugin execution timed out: {e}")
except Exception as e:
    print(f"Plugin execution failed: {e}")

# Example 2: Resource Limits
"""
Set and enforce resource limits for plugins.
"""

# Configure resource limits through the sandbox timeout
sandbox_with_limits = PluginSandbox(timeout=5)  # 5 second timeout

# Example function that might exceed resource limits
def resource_intensive_function():
    """Simulate a function that might exceed resource limits."""
    import time
    time.sleep(10)  # This will exceed the 5-second timeout
    return "This should not be reached"

# Execute the function with resource limits
try:
    result = sandbox_with_limits.execute(resource_intensive_function)
    print(f"Function completed: {result}")
except TimeoutError as e:
    print(f"Function exceeded resource limits: {e}")

# Example 3: IPC Communication
"""
Pass data safely between processes using IPC.
"""

# Create a multiprocessing queue for IPC
ipc_queue = Queue()

# Data to be sent
data_to_send = {"command": "analyze_code", "file_path": "example.py", "priority": "high"}

# Serialize and send data
IPCProtocol.send_data(ipc_queue, data_to_send)
print(f"Data sent through IPC: {data_to_send}")

# Receive and deserialize data
received_data = IPCProtocol.receive_data(ipc_queue)
print(f"Data received through IPC: {received_data}")

# Example 4: Configuration in config.toml
"""
Demonstrate how to configure sandboxing in config.toml.
"""

# Example config.toml content for enabling plugin isolation and setting resource limits
config_toml_content = """
[plugins]
# Enable plugin isolation for security
enable_isolation = true

# Resource limits for plugins
# cpu_limit = 1.0              # Maximum CPU usage (1.0 = 100% of a single core)
# memory_limit = 512           # Maximum memory usage in MB
# timeout = 30                # Maximum execution time in seconds

# Plugin capability filtering
# enabled_plugins = ["lsp", "hello"]
# disabled_plugins = ["experimental"]

# Plugin paths (in addition to built-ins)
# plugin_paths = [
#   "~/custom_plugins",
#   "/opt/vibe/plugins"
# ]
"""

print("Example config.toml for plugin sandboxing:")
print(config_toml_content)

# Save the example config to a file
with open("config_example.toml", "w") as config_file:
    config_file.write(config_toml_content)

print("Example config.toml saved to 'config_example.toml'")

# Example 5: Full Plugin Sandboxing Workflow
"""
A complete example of executing a plugin with sandboxing, resource limits,
and IPC communication.
"""

def full_sandboxing_workflow():
    # Step 1: Create a sandbox with resource limits
    sandbox = PluginSandbox(timeout=15)
    print(f"Sandbox created with timeout: {sandbox.timeout} seconds")

    # Step 2: Define a plugin function to execute
    def plugin_task(context):
        """Simulate a plugin task that processes context."""
        import time
        time.sleep(2)  # Simulate work
        return {"status": "success", "result": f"Processed {context}"}

    # Step 3: Execute the plugin function in the sandbox
    try:
        context_data = {"file": "example.py", "action": "analyze"}
        result = sandbox.execute(plugin_task, context_data)
        print(f"Plugin task completed successfully: {result}")
    except TimeoutError as e:
        print(f"Plugin task timed out: {e}")
        return None
    except Exception as e:
        print(f"Plugin task failed: {e}")
        return None

    # Step 4: Demonstrate IPC communication
    ipc_queue = Queue()
    
    # Send result through IPC
    IPCProtocol.send_data(ipc_queue, result)
    print(f"Result sent through IPC")
    
    # Receive result through IPC
    received_result = IPCProtocol.receive_data(ipc_queue)
    print(f"Result received through IPC: {received_result}")
    
    return received_result

# Run the full workflow
if __name__ == "__main__":
    print("=" * 60)
    print("Running Plugin Isolation and Sandboxing Examples")
    print("=" * 60)
    
    print("\n1. Basic Sandboxing Example:")
    print("-" * 40)
    
    print("\n2. Resource Limits Example:")
    print("-" * 40)
    
    print("\n3. IPC Communication Example:")
    print("-" * 40)
    
    print("\n4. Configuration Example:")
    print("-" * 40)
    
    print("\n5. Full Sandboxing Workflow:")
    print("-" * 40)
    full_sandboxing_workflow()
    
    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)