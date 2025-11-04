"""
Manus to Surge Converter

High-performance converter for Manus motion capture data to Surge hand commands.
Maps Manus semantic joint names to finger angles using bone vector analysis.

Migrated from helping_hands for remote teleoperation with integer angle outputs.
"""

import logging
import time
import numpy as np
from typing import Dict, Any, Optional, Tuple

from manus_models import ManusFrame

logger = logging.getLogger(__name__)


class SurgeRHJoint:
    """Surge RH joint identifiers"""
    INDEX = "I"
    MIDDLE = "M"
    RING = "R"
    PINKY = "P"
    THUMB_FLEX = "T"
    THUMB_ROTATION = "X"


class ManusToSurgeConverter:
    """
    High-performance converter for Manus motion capture data to Surge hand commands.
    
    Maps Manus semantic joint names to integer finger angles for remote UDP transmission.
    """
    
    def __init__(self):
        # Performance tracking
        self._conversion_times = []
        self._frames_converted = 0
        
        logger.info("Manus to Surge converter initialized")
    
    def convert_frame_to_surge_commands(self, frame: ManusFrame) -> Dict[str, int]:
        """
        Convert Manus frame to Surge hand integer commands for UDP transmission.
        
        Args:
            frame: Manus frame with semantic joint names
            
        Returns:
            Dictionary mapping joint identifiers to integer angles
        """
        start_time = time.perf_counter()
        commands = {}
        
        try:
            # Extract joint positions by semantic name
            joint_positions = self._extract_joint_positions(frame)
            
            if not joint_positions:
                logger.debug("No valid joint positions found in Manus frame")
                return commands
            
            # Calculate finger angles using the same approach as Rokoko converter
            finger_angles = self._calculate_finger_angles(joint_positions)
            
            # Convert finger angles to integer Surge commands
            finger_to_joint = {
                'index': SurgeRHJoint.INDEX,
                'middle': SurgeRHJoint.MIDDLE,
                'pinky': SurgeRHJoint.PINKY
            }
            
            for finger_name, joint_id in finger_to_joint.items():
                if finger_name in finger_angles:
                    angle = finger_angles[finger_name]
                    commands[joint_id] = int(round(angle))  # Convert to integer
            
            # Set ring finger angle to pinky + 15, clamped to 90 (R = min(90, P + 15))
            if SurgeRHJoint.PINKY in commands:
                ring_angle = min(90, commands[SurgeRHJoint.PINKY] + 15)
                commands[SurgeRHJoint.RING] = ring_angle
            
            # Calculate thumb angles
            thumb_flex, thumb_rotation = self._calculate_thumb_angles(joint_positions)
            
            if thumb_flex is not None and thumb_rotation is not None:
                commands[SurgeRHJoint.THUMB_FLEX] = int(round(thumb_flex))
                commands[SurgeRHJoint.THUMB_ROTATION] = int(round(thumb_rotation))
            
            # Apply gripper mode post-processing
            commands = self._apply_gripper_mode(commands)
                            
        except Exception as e:
            logger.error(f"Error converting Manus frame to Surge commands: {e}")
        
        return commands
    
    def _apply_gripper_mode(self, commands: Dict[str, int]) -> Dict[str, int]:
        """
        Apply gripper mode post-processing based on thumb rotation (X) angle.
        
        Logic:
        1. If X < 30, return commands as is
        2. If X >= 30, enter gripper mode:
           - Set X=36, P=R=0
           - Round I to nearest 20, add 4, clip to (14, 64)
           - Set M=I
           - Set T = 1.5 * T (max 27)
        """
        # Get thumb rotation angle (X)
        x_angle = commands.get(SurgeRHJoint.THUMB_ROTATION, 0)
        
        if x_angle < 30:
            # Normal mode - return commands as is
            return commands
        
        # Gripper mode
        modified_commands = commands.copy()
        
        # Set X=36, P=0, R=0
        modified_commands[SurgeRHJoint.THUMB_ROTATION] = 36
        modified_commands[SurgeRHJoint.PINKY] = 0
        modified_commands[SurgeRHJoint.RING] = 0
        
        # Process I: round to nearest 20, add 4, clip to (14, 64)
        i_angle = commands.get(SurgeRHJoint.INDEX, 0)
        i_rounded = round(i_angle / 20) * 20  # Round to nearest 20
        i_processed = i_rounded + 4
        i_clipped = max(14, min(64, i_processed))  # Clip to range (14, 64)
        modified_commands[SurgeRHJoint.INDEX] = i_clipped
        
        # Set M=I
        modified_commands[SurgeRHJoint.MIDDLE] = i_clipped
        
        # T (thumb flex) = 2 * T, max 27
        t_angle = commands.get(SurgeRHJoint.THUMB_FLEX, 0)
        t_extra = min(27, 1.5 * t_angle)
        modified_commands[SurgeRHJoint.THUMB_FLEX] = int(t_extra)
        
        return modified_commands
    
    def _extract_joint_positions(self, frame: ManusFrame) -> Dict[str, np.ndarray]:
        """
        Extract joint positions from Manus frame using semantic names.
        
        Returns:
            Dictionary mapping semantic joint names to 3D positions
        """
        joint_positions = {}
        
        for node in frame.skeleton_nodes:
            if node.semantic_name:
                position = np.array([
                    node.position.x,
                    node.position.y, 
                    node.position.z
                ], dtype=np.float32)
                joint_positions[node.semantic_name] = position
        
        return joint_positions
    
    def _calculate_finger_angles(self, joint_positions: Dict[str, np.ndarray]) -> Dict[str, float]:
        """
        Calculate finger angles using bone vector analysis.
        
        For each finger, calculates the angle between:
        - Vector from metacarpal to MCP joint
        - Vector from MCP to PIP joint
        """
        results = {}
        
        # Finger mapping: finger_name -> (Metacarpal, MCP, PIP) 
        finger_joints = {
            'index': ('RightIndexMetacarpal', 'RightIndexMCP', 'RightIndexPIP'),
            'middle': ('RightMiddleMetacarpal', 'RightMiddleMCP', 'RightMiddlePIP'),
            'pinky': ('RightPinkyMetacarpal', 'RightPinkyMCP', 'RightPinkyPIP')
        }
        
        for finger_name, (metacarpal_name, mcp_name, pip_name) in finger_joints.items():
            try:
                # Check if all required joints are available
                if all(joint in joint_positions for joint in [metacarpal_name, mcp_name, pip_name]):
                    metacarpal_pos = joint_positions[metacarpal_name]
                    mcp_pos = joint_positions[mcp_name]
                    pip_pos = joint_positions[pip_name]
                    
                    # Calculate bone vectors
                    bone1_vector = mcp_pos - metacarpal_pos   # metacarpal -> mcp
                    bone2_vector = pip_pos - mcp_pos          # mcp -> pip
                    
                    # Calculate bone lengths
                    bone1_length = np.linalg.norm(bone1_vector)
                    bone2_length = np.linalg.norm(bone2_vector)
                    
                    # Avoid division by zero
                    if bone1_length > 0 and bone2_length > 0:
                        # Calculate angle between vectors
                        dot_product = np.dot(bone1_vector, bone2_vector)
                        cos_angle = np.clip(dot_product / (bone1_length * bone2_length), -1.0, 1.0)
                        angle_rad = np.arccos(cos_angle)
                        angle_deg = np.degrees(angle_rad) * 1.4 # Apply boosting factor
                        
                        # Apply surge angle mapping (clamp to 0-90°)
                        surge_angle = np.clip(angle_deg, 0.0, 90.0)
                        results[finger_name] = float(surge_angle)
                        
                    else:
                        results[finger_name] = 0.0
                else:
                    results[finger_name] = 0.0
                    
            except Exception as e:
                logger.debug(f"Error calculating angle for {finger_name}: {e}")
                results[finger_name] = 0.0
        
        return results
    
    def _calculate_thumb_angles(self, joint_positions: Dict[str, np.ndarray]) -> Tuple[Optional[float], Optional[float]]:
        """
        Calculate thumb flexion and rotation angles using the same approach as Rokoko converter.
        """
        try:
            # Required joints for thumb calculation using new semantic names
            required_joints = ['RightHand', 'RightThumbCMC', 'RightThumbMCP', 'RightIndexMetacarpal', 'RightIndexMCP']
            
            if not all(joint in joint_positions for joint in required_joints):
                return None, None
            
            nodeA = joint_positions['RightThumbCMC']
            nodeB = joint_positions['RightThumbMCP']
            nodeX = joint_positions['RightIndexMetacarpal']  
            nodeY = joint_positions['RightIndexMCP']     
            
            # Shared vector: thumb CMC (meta) -> thumb MCP (proximal) (used by both calculations)
            thumb_vector = nodeB - nodeA
            
            # === FLEXION CALCULATION ===
            # index Meta -> index MCP (proximal)
            finger_vector = nodeY - nodeX

            # Calculate flexion angle
            flex_dot = np.dot(finger_vector, thumb_vector)
            flex_norms = np.linalg.norm(finger_vector) * np.linalg.norm(thumb_vector)
            
            if flex_norms == 0:
                return None, None
            
            flex_cos = np.clip(flex_dot / flex_norms, -1.0, 1.0)
            flex_mocap_angle = np.degrees(np.arccos(flex_cos))
            
            # Apply flexion transformation
            flex_surge_raw = 15 + (30 - flex_mocap_angle)  # line of slope -1
            thumb_flex = np.clip(flex_surge_raw, 15.0, 35.0)
            
            # === ROTATION CALCULATION ===
            # Use cylindrical coordinates: φ (phi) angle of thumb MCP relative to hand center
            # This provides stable rotation measurement independent of flexion
            
            # Get thumb MCP position relative to hand center (already at origin)
            thumb_mcp_pos = joint_positions['RightThumbMCP']
            
            # Calculate cylindrical coordinates
            x, y = float(thumb_mcp_pos[0]), float(thumb_mcp_pos[1])
            
            # φ (phi) = azimuthal angle around Z-axis = atan2(y, x)
            phi_angle_rad = np.arctan2(y, x)
            phi_angle_deg = np.degrees(phi_angle_rad)
                        
            # Apply existing rotation transformation (unchanged)
            rotation_surge_raw = - phi_angle_deg
            thumb_rotation = np.clip(rotation_surge_raw, 14.0, 39.0)
            
            return float(thumb_flex), float(thumb_rotation)
            
        except Exception as e:
            logger.error(f"Error in Manus thumb calculation: {e}")
            return None, None
    
