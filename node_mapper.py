"""
Manus glove service for streaming right-hand skeleton data.
Interfaces with Manus SDK via C++ bridge DLL.
"""

import ctypes
import threading
import time
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass


@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass
class Quaternion:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0
    
    def to_dict(self) -> Dict[str, float]:
        return {"x": self.x, "y": self.y, "z": self.z, "w": self.w}


@dataclass
class HandNode:
    node_id: int = 0
    position: Vector3 = None
    rotation: Quaternion = None
    semantic_name: str = ""
    chain_type: str = ""
    finger_joint_type: Optional[str] = None
    side: str = "Right"
    
    def __post_init__(self):
        if self.position is None:
            self.position = Vector3()
        if self.rotation is None:
            self.rotation = Quaternion()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "semantic_name": self.semantic_name,
            "chain_type": self.chain_type,
            "finger_joint_type": self.finger_joint_type,
            "side": self.side,
            "position": self.position.to_dict(),
            "rotation": self.rotation.to_dict()
        }


class ManusNodeMapper:
    """Maps raw SDK node IDs to semantic hand structure based on actual Manus glove structure.
    
    Corrected mapping based on distance analysis and geometric validation:
    - Node 0: Hand center/root
    - Nodes 1-4: Thumb (4 joints: CMC, MCP, IP, Tip)
    - Nodes 5-9: Index finger (5 joints: Metacarpal, MCP, PIP, DIP, Tip) 
    - Nodes 10-14: Middle finger (5 joints: Metacarpal, MCP, PIP, DIP, Tip) - longest finger
    - Nodes 15-19: Ring finger (5 joints: Metacarpal, MCP, PIP, DIP, Tip)
    - Nodes 20-24: Pinky finger (5 joints: Metacarpal, MCP, PIP, DIP, Tip)
    """
    
    @staticmethod
    def get_node_info(node_id: int) -> Dict[str, Any]:
        """Get semantic information for a node ID based on corrected finger mapping."""
        
        # Node 0: Hand/Wrist Root
        if node_id == 0:
            return {
                "semantic_name": "RightHand",
                "chain_type": "Hand", 
                "finger_joint_type": None,
                "side": "Right"
            }
        
        # Nodes 1-4: Thumb (4 joints: CMC, MCP, IP, Tip)
        elif 1 <= node_id <= 4:
            joint_mappings = {
                1: ("CMC", "Metacarpal"),   # Carpometacarpal (base)
                2: ("MCP", "Proximal"),     # Metacarpophalangeal
                3: ("IP", "Intermediate"),  # Interphalangeal (thumbs only have one IP)
                4: ("Tip", "Tip")          # Tip
            }
            joint_suffix, joint_type = joint_mappings[node_id]
            return {
                "semantic_name": f"RightThumb{joint_suffix}",
                "chain_type": "FingerThumb",
                "finger_joint_type": joint_type,
                "side": "Right"
            }
        
        # Nodes 5-9: Index finger (5 joints: Metacarpal, MCP, PIP, DIP, Tip)
        elif 5 <= node_id <= 9:
            joint_mappings = {
                5: ("Metacarpal", "Metacarpal"),  # Metacarpal base (closest to hand center)
                6: ("MCP", "Proximal"),           # Metacarpophalangeal
                7: ("PIP", "Intermediate"),       # Proximal Interphalangeal
                8: ("DIP", "Distal"),            # Distal Interphalangeal
                9: ("Tip", "Tip")                # Fingertip
            }
            joint_suffix, joint_type = joint_mappings[node_id]
            return {
                "semantic_name": f"RightIndex{joint_suffix}",
                "chain_type": "FingerIndex",
                "finger_joint_type": joint_type,
                "side": "Right"
            }
        
        # Nodes 10-14: Middle finger (5 joints: Metacarpal, MCP, PIP, DIP, Tip) - longest finger
        elif 10 <= node_id <= 14:
            joint_mappings = {
                10: ("Metacarpal", "Metacarpal"),  # Metacarpal base
                11: ("MCP", "Proximal"),           # Metacarpophalangeal
                12: ("PIP", "Intermediate"),       # Proximal Interphalangeal
                13: ("DIP", "Distal"),            # Distal Interphalangeal
                14: ("Tip", "Tip")                # Fingertip (longest)
            }
            joint_suffix, joint_type = joint_mappings[node_id]
            return {
                "semantic_name": f"RightMiddle{joint_suffix}",
                "chain_type": "FingerMiddle",
                "finger_joint_type": joint_type,
                "side": "Right"
            }
        
        # Nodes 15-19: Ring finger (5 joints: Metacarpal, MCP, PIP, DIP, Tip)
        elif 15 <= node_id <= 19:
            joint_mappings = {
                15: ("Metacarpal", "Metacarpal"),  # Metacarpal base
                16: ("MCP", "Proximal"),           # Metacarpophalangeal
                17: ("PIP", "Intermediate"),       # Proximal Interphalangeal
                18: ("DIP", "Distal"),            # Distal Interphalangeal
                19: ("Tip", "Tip")                # Fingertip
            }
            joint_suffix, joint_type = joint_mappings[node_id]
            return {
                "semantic_name": f"RightRing{joint_suffix}",
                "chain_type": "FingerRing",
                "finger_joint_type": joint_type,
                "side": "Right"
            }
        
        # Nodes 20-24: Pinky finger (5 joints: Metacarpal, MCP, PIP, DIP, Tip)
        elif 20 <= node_id <= 24:
            joint_mappings = {
                20: ("Metacarpal", "Metacarpal"),  # Metacarpal base
                21: ("MCP", "Proximal"),           # Metacarpophalangeal
                22: ("PIP", "Intermediate"),       # Proximal Interphalangeal
                23: ("DIP", "Distal"),            # Distal Interphalangeal
                24: ("Tip", "Tip")                # Fingertip
            }
            joint_suffix, joint_type = joint_mappings[node_id]
            return {
                "semantic_name": f"RightPinky{joint_suffix}",
                "chain_type": "FingerPinky",
                "finger_joint_type": joint_type,
                "side": "Right"
            }
        
        # Unknown node
        else:
            return {
                "semantic_name": f"RightHandNode{node_id}",
                "chain_type": "Unknown",
                "finger_joint_type": None,
                "side": "Right"
            }
