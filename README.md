# Manus to Surge Hand Teleoperation

Python bridge for real-time teleoperation of the Surge robotic hand using Manus VR gloves. This system interfaces with the Manus SDK to capture hand tracking data and converts it to motor commands for the Surge hand.

## Overview

This project provides a complete pipeline for controlling a Surge robotic hand using Manus motion capture gloves:

1. **Manus SDK Interface**: Connects to Manus Core via C++ bridge DLL
2. **Node Mapping**: Maps raw SDK node IDs to semantic joint names (thumb, index, middle, ring, pinky)
3. **Motion Conversion**: Converts hand tracking data to Surge motor commands using biomechanical models
4. **TCP Streaming**: Sends motor commands to remote Surge controller over TCP

## Features

- **Real-time Conversion**: Low-latency conversion from Manus glove data to Surge commands
- **Accurate Joint Mapping**: Corrected finger joint mapping based on geometric validation
- **Intelligent Angle Calculation**: Uses bone vector analysis for accurate finger flexion
- **Gripper Mode**: Automatic gripper mode detection and optimization
- **Configurable**: Easy configuration of network settings, DLL paths, and performance parameters
- **Robust Error Handling**: Automatic reconnection and error recovery

## Requirements

### Hardware
- Manus VR Gloves (right hand)
- Surge robotic hand
- Windows PC for running Manus Core
- Network connection to Surge controller

### Software
- Python 3.8+
- Manus Core (from Manus VR)
- Manus SDK DLLs:
  - `ManusBridge.dll` (custom bridge interface)
  - `ManusSDK.dll` (official Manus SDK)

## Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd manus-surge-teleoperation
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Obtain Manus SDK DLLs**
   - `ManusSDK.dll` - Obtain from Manus VR SDK
   - `ManusBridge.dll` - Custom bridge (contact repository maintainer or build from source)

   Place both DLLs in the project directory.

4. **Configure settings**

   Edit `config.py` to match your setup:
   ```python
   class Config:
       DLL_PATH = r".\ManusBridge.dll"  # Path to ManusBridge DLL
       SERVER_HOST = "192.168.1.100"    # IP of Surge controller
       SERVER_PORT = 50070               # TCP port
   ```

## Usage

### Basic Usage

1. **Start Manus Core** and ensure your glove is connected

2. **Run the teleoperation script**
   ```bash
   python main.py
   ```

3. The system will:
   - Connect to Manus Core
   - Wait for glove data
   - Convert hand tracking to Surge commands
   - Stream commands over TCP to the Surge controller

4. Press `Ctrl+C` to stop

### Command Output

Motor commands are sent as JSON over TCP:
```json
{
  "timestamp": 1234567890.123,
  "glove_id": 0,
  "surge_commands": {
    "I": 45,  // Index finger (0-90°)
    "M": 60,  // Middle finger (0-90°)
    "R": 15,  // Ring finger (0-90°)
    "P": 0,   // Pinky finger (0-90°)
    "T": 20,  // Thumb flexion (15-35°)
    "X": 25   // Thumb rotation (14-39°)
  }
}
```

## Architecture

### Components

#### `main.py`
Main entry point that:
- Initializes Manus SDK
- Manages TCP connection
- Coordinates data flow from glove to Surge commands

#### `node_mapper.py`
Maps Manus node IDs to semantic joint names:
- Node 0: Hand center
- Nodes 1-4: Thumb (CMC, MCP, IP, Tip)
- Nodes 5-9: Index finger (Metacarpal, MCP, PIP, DIP, Tip)
- Nodes 10-14: Middle finger
- Nodes 15-19: Ring finger
- Nodes 20-24: Pinky finger

#### `manus_to_surge_converter.py`
Converts Manus tracking data to Surge motor angles:
- **Finger Flexion**: Calculated from bone vectors between metacarpal, MCP, and PIP joints
- **Thumb Angles**: Special handling for thumb flexion and rotation using cylindrical coordinates
- **Gripper Mode**: Automatic optimization when thumb rotation exceeds 30°

#### `manus_models.py`
Pydantic data models for type safety and validation

#### `config.py`
Centralized configuration for all system parameters

## Finger Angle Calculation

### Standard Fingers (Index, Middle, Ring, Pinky)

Angles are calculated using bone vector analysis:
```
angle = arccos(dot(bone1, bone2) / (|bone1| * |bone2|))
```

Where:
- `bone1` = vector from metacarpal to MCP joint
- `bone2` = vector from MCP to PIP joint

The angle is then:
1. Converted to degrees
2. Boosted by 1.4x for better sensitivity
3. Clamped to 0-90°

### Ring Finger
Special handling: `ring_angle = min(90, pinky_angle + 15)`

### Thumb

**Flexion (T)**:
- Calculated from angle between thumb CMC→MCP and index metacarpal→MCP vectors
- Mapped to 15-35° range

**Rotation (X)**:
- Uses cylindrical coordinates (phi angle)
- Calculated from thumb MCP position relative to hand center
- Mapped to 14-39° range

### Gripper Mode

Activated when thumb rotation (X) ≥ 30°:
1. Set X=36, P=0, R=0
2. Round I to nearest 20°, add 4, clip to (14, 64)
3. Set M=I
4. Set T = 1.5 × T (max 27)

This provides optimized power grip control.

## Configuration Options

### Network Settings
- `SERVER_HOST`: IP address of Surge controller
- `SERVER_PORT`: TCP port (default: 50070)

### Connection Settings
- `MAX_WAIT_ITERATIONS`: Max wait time for Manus connection (default: 5 seconds)
- `WAIT_INTERVAL`: Polling interval (default: 0.1s)

### Streaming Settings
- `STREAM_THROTTLE`: Update rate throttle (default: 0.1s = 10Hz)
- `ERROR_RETRY_DELAY`: Retry delay on errors (default: 0.05s)
- `RECONNECT_DELAY`: TCP reconnection delay (default: 1.0s)

### Data Processing
- `MAX_NODES`: Maximum skeleton nodes to process (default: 32)

### Logging
- `LOG_LEVEL`: Logging level (INFO, DEBUG, WARNING, ERROR)

## Troubleshooting

### "Manus_Initialize failed"
- Ensure Manus Core is running
- Check that `ManusSDK.dll` and `ManusBridge.dll` are in the correct path
- Verify DLL compatibility (32-bit vs 64-bit)

### "Not connected to Manus Core"
- Start Manus Core before running the script
- Check that your glove is paired and connected in Manus Core
- Increase `MAX_WAIT_ITERATIONS` if connection is slow

### "Connection refused" / TCP errors
- Verify `SERVER_HOST` and `SERVER_PORT` in config
- Ensure Surge controller is running and listening
- Check firewall settings

### Poor tracking quality
- Calibrate gloves in Manus Core
- Ensure good lighting and clear tracking environment
- Check battery levels on gloves

### Jerky or delayed movements
- Reduce `STREAM_THROTTLE` for higher update rate
- Check network latency to Surge controller
- Ensure Manus Core is running smoothly

## Data Flow

```
Manus Glove
    ↓
Manus Core (SDK)
    ↓
ManusBridge.dll (C++ Bridge)
    ↓
main.py (Python ctypes)
    ↓
node_mapper.py (ID → Semantic Names)
    ↓
manus_to_surge_converter.py (Angles Calculation)
    ↓
TCP Socket (JSON Messages)
    ↓
Surge Hand Controller
    ↓
Surge Robotic Hand
```

## Performance

- **Latency**: ~10-20ms from glove motion to command transmission
- **Update Rate**: Configurable 10-50Hz (default: 10Hz)
- **CPU Usage**: Minimal (~2-5% on modern processors)

## Development

### Adding New Finger Mappings

Edit `node_mapper.py` to modify the semantic joint mapping based on your specific Manus glove configuration.

### Customizing Angle Calculations

Modify `manus_to_surge_converter.py`:
- `_calculate_finger_angles()` for finger flexion logic
- `_calculate_thumb_angles()` for thumb calculations
- `_apply_gripper_mode()` for gripper mode behavior

### Extending Protocol

The TCP protocol can be extended by modifying the message structure in `main.py:convert_bridge_data_to_surge_commands()`.

## Credits

Developed for teleoperation research with Manus VR gloves and Surge robotic hands.

## Contributing

Contributions welcome! Please submit pull requests with:
- Clear description of changes
- Testing on actual hardware
- Updated documentation

## Support

For issues, questions, or contributions, please open an issue on GitHub.
