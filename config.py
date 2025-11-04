"""
Configuration for Manus Glove System
"""

class Config:
    # Manus Bridge DLL settings
    DLL_PATH = r".\ManusBridge.dll"  # Path to ManusBridge.dll

    # Network settings
    SERVER_HOST = "127.0.0.1"  # Change to your server IP
    SERVER_PORT = 50070
    
    # Connection settings  
    MAX_WAIT_ITERATIONS = 50  # Wait up to 5 seconds for connection (50 * 0.1s)
    WAIT_INTERVAL = 0.1  # seconds
    
    # Streaming settings
    STREAM_THROTTLE = 0.1  # seconds (50 Hz → 0.02, 30 Hz → ~0.033, etc.)
    ERROR_RETRY_DELAY = 0.05  # seconds
    RECONNECT_DELAY = 1.0  # seconds
    
    # Data processing settings
    MAX_NODES = 32  # Maximum number of nodes to process
    
    # Logging settings
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"