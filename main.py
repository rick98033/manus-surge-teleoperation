# manus_probe_connect_wait.py (Windows)
import ctypes, time, json, socket, struct, sys, atexit, logging
from ctypes import c_int, c_double, c_uint, c_float
from datetime import datetime
from typing import List, Dict, Any

# Import required components for node mapping and surge conversion
from node_mapper import ManusNodeMapper
from manus_to_surge_converter import ManusToSurgeConverter
from manus_models import ManusFrame, ManusSkeletonNode, Vector3, Quaternion
from config import Config

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format=Config.LOG_FORMAT,
    datefmt=Config.LOG_DATE_FORMAT
)
logger = logging.getLogger(__name__)

# ======== Manus bridge ctypes =========
class BridgeNode(ctypes.Structure):
    _fields_ = [
        ("id", c_uint),
        ("pos_x", c_float), ("pos_y", c_float), ("pos_z", c_float),
        ("rot_x", c_float), ("rot_y", c_float), ("rot_z", c_float), ("rot_w", c_float),
    ]

class BridgeHandData(ctypes.Structure):
    _fields_ = [
        ("glove_id", c_uint),
        ("node_count", c_uint),
        ("nodes", BridgeNode * 32),  # Max 32 nodes
        ("timestamp", c_double),
        ("is_valid", c_int),
    ]

# Load Manus bridge DLL
dll = ctypes.CDLL(Config.DLL_PATH)

# Function signatures
dll.Manus_Initialize.restype = c_int
dll.Manus_StartStreaming.restype = c_int
dll.Manus_StopStreaming.restype = c_int
dll.Manus_IsConnected.restype = c_int
dll.Manus_IsStreaming.restype = c_int
dll.Manus_GetLatestHandData.argtypes = [ctypes.POINTER(BridgeHandData)]
dll.Manus_GetLatestHandData.restype = c_int
dll.Manus_GetLastError.restype = ctypes.c_char_p
dll.Manus_Shutdown.restype = c_int

# ======== TCP client helpers =========
sock = None

def tcp_connect():
    global sock
    close_socket()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Optional: quick reconnects
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    sock.connect((Config.SERVER_HOST, Config.SERVER_PORT))
    logger.info(f"Connected to server {Config.SERVER_HOST}:{Config.SERVER_PORT}")

def close_socket():
    global sock
    if sock:
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            sock.close()
        except Exception:
            pass
    sock = None

def send_json_message(obj):
    """Send a single JSON message framed with 4-byte big-endian length."""
    data = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    header = struct.pack(">I", len(data))
    sock.sendall(header + data)
    sock.flush() if hasattr(sock, 'flush') else None

# ======== Node to Surge Conversion =========
def convert_bridge_data_to_surge_commands(bridge_data: BridgeHandData, node_mapper: ManusNodeMapper, surge_converter: ManusToSurgeConverter) -> Dict[str, int]:
    """
    Convert raw bridge data to surge motor commands.
    Combines Step 1 (nodes to names) and Step 2 (names to angles).
    """
    try:
        # Step 1: Convert nodes to semantic skeleton nodes
        skeleton_nodes = []
        node_count = min(int(bridge_data.node_count), Config.MAX_NODES)
        
        for i in range(node_count):
            bridge_node = bridge_data.nodes[i]
            node_id = int(bridge_node.id)
            
            # Get semantic information from node mapper
            semantic_info = node_mapper.get_node_info(node_id)
            
            # Create ManusSkeletonNode with semantic information
            skeleton_node = ManusSkeletonNode(
                node_id=node_id,
                name=f"node_{node_id}",
                position=Vector3(
                    x=float(bridge_node.pos_x),
                    y=float(bridge_node.pos_y), 
                    z=float(bridge_node.pos_z)
                ),
                rotation=Quaternion(
                    x=float(bridge_node.rot_x),
                    y=float(bridge_node.rot_y),
                    z=float(bridge_node.rot_z),
                    w=float(bridge_node.rot_w)
                ),
                semantic_name=semantic_info["semantic_name"],
                chain_type=semantic_info["chain_type"],
                finger_joint_type=semantic_info["finger_joint_type"],
                side=semantic_info["side"]
            )
            skeleton_nodes.append(skeleton_node)
        
        # Create ManusFrame for the converter
        manus_frame = ManusFrame(
            timestamp=datetime.now(),
            frame_number=0,
            user_id=0,
            skeleton_nodes=skeleton_nodes
        )
        
        # Step 2: Convert to surge motor commands
        surge_commands = surge_converter.convert_frame_to_surge_commands(manus_frame)
        
        return surge_commands
        
    except Exception as e:
        logger.error(f"Error converting bridge data to surge commands: {e}")
        return {}

# ======== Serialization =========
def handdata_to_dict(h: BridgeHandData):
    n = int(h.node_count)
    n = max(0, min(n, Config.MAX_NODES))
    nodes = []
    for i in range(n):
        node = h.nodes[i]
        nodes.append({
            "id": int(node.id),
            "pos": [float(node.pos_x), float(node.pos_y), float(node.pos_z)],
            "rot": [float(node.rot_x), float(node.rot_y), float(node.rot_z), float(node.rot_w)],
        })
    return {
        "glove_id": int(h.glove_id),        # 0 = right, 1 = left (per your note)
        "node_count": n,
        "nodes": nodes,
        "timestamp": float(h.timestamp),    # seconds
        "is_valid": bool(h.is_valid),
    }

# ======== Cleanup on exit =========
def shutdown_manus():
    try:
        if dll.Manus_IsStreaming():
            dll.Manus_StopStreaming()
    except Exception:
        pass
    try:
        dll.Manus_Shutdown()
    except Exception:
        pass
    close_socket()
    logger.info("Cleaned up Manus + socket")

atexit.register(shutdown_manus)

# ======== Main =========
def main():
    # Initialize converter components
    node_mapper = ManusNodeMapper()
    surge_converter = ManusToSurgeConverter()
    logger.info("Initialized node mapper and surge converter")
    
    # Initialize Manus Core
    res = dll.Manus_Initialize()
    if res != 0:
        err = dll.Manus_GetLastError()
        logger.error(f"Manus_Initialize failed: {err.decode('utf-8') if err else res}")
        sys.exit(1)

    # Wait up to 5 seconds for connection
    for _ in range(Config.MAX_WAIT_ITERATIONS):
        if dll.Manus_IsConnected():
            logger.info("Connected to Manus Core")
            break
        time.sleep(Config.WAIT_INTERVAL)
    else:
        logger.warning("Not connected to Manus Core after 5 seconds (continuing anyway)")

    # Start streaming
    res = dll.Manus_StartStreaming()
    if res != 0:
        err = dll.Manus_GetLastError()
        logger.error(f"Manus_StartStreaming failed: {err.decode('utf-8') if err else res}")
        sys.exit(1)

    # Connect to TCP server
    tcp_connect()

    bridge_data = BridgeHandData()

    logger.info("Streaming… Press Ctrl+C to stop.")
    try:
        while True:
            # Try to fetch latest data
            logger.info("Fetching latest hand data...")
            rc = dll.Manus_GetLatestHandData(ctypes.byref(bridge_data))
            if rc != 0:
                # Non-zero = error in this SDK
                err = dll.Manus_GetLastError()
                logger.error(f"Manus_GetLatestHandData error: {err.decode('utf-8') if err else rc}")
                time.sleep(Config.ERROR_RETRY_DELAY)
                continue
            # Convert nodes to semantic names and then to surge commands
            surge_commands = convert_bridge_data_to_surge_commands(bridge_data, node_mapper, surge_converter)
            
            # Create simplified packet with only surge commands
            packet = {
                "timestamp": float(bridge_data.timestamp),
                "glove_id": int(bridge_data.glove_id),
                "surge_commands": surge_commands
            }
            
            try:
                logger.info("Sending surge commands to server...")
                send_json_message(packet)
                

                logger.info(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] Sent commands: {packet['surge_commands']}")
            except (BrokenPipeError, ConnectionResetError, OSError):
                logger.warning("Lost connection to server, retrying in 1s…")
                time.sleep(Config.RECONNECT_DELAY)
                try:
                    tcp_connect()
                except Exception as e:
                    logger.warning(f"Reconnect failed: {e}; will retry…")
                    time.sleep(Config.RECONNECT_DELAY)

            # Throttle as desired; 50 Hz → 0.02, 30 Hz → ~0.033, etc.
            time.sleep(Config.STREAM_THROTTLE)
    except KeyboardInterrupt:
        logger.info("Stopping…")

if __name__ == "__main__":
    main()
