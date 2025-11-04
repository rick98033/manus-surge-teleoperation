"""
Manus glove data models for integration with motion capture system
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime


class Vector3(BaseModel):
    """3D vector for position data"""
    x: float = Field(..., description="X coordinate")
    y: float = Field(..., description="Y coordinate") 
    z: float = Field(..., description="Z coordinate")


class Quaternion(BaseModel):
    """Quaternion for rotation data"""
    x: float = Field(..., description="X component")
    y: float = Field(..., description="Y component")
    z: float = Field(..., description="Z component")
    w: float = Field(..., description="W component")


class ManusFingerData(BaseModel):
    """Individual finger data from Manus glove"""
    thumb: float = Field(..., description="Thumb bend value (0-1)")
    index: float = Field(..., description="Index finger bend value (0-1)")
    middle: float = Field(..., description="Middle finger bend value (0-1)")
    ring: float = Field(..., description="Ring finger bend value (0-1)")
    pinky: float = Field(..., description="Pinky finger bend value (0-1)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "thumb": 0.2,
                "index": 0.8,
                "middle": 0.6,
                "ring": 0.4,
                "pinky": 0.1
            }
        }


class ManusGloveData(BaseModel):
    """Data from a single Manus glove"""
    glove_id: int = Field(..., description="Unique glove identifier")
    hand_type: str = Field(..., description="left or right")
    position: Vector3 = Field(..., description="Hand position in 3D space")
    rotation: Quaternion = Field(..., description="Hand rotation as quaternion")
    fingers: ManusFingerData = Field(..., description="Finger bend data")
    battery_level: Optional[float] = Field(None, description="Battery level (0-1)")
    connection_quality: Optional[float] = Field(None, description="Connection quality (0-1)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "glove_id": 12345,
                "hand_type": "right",
                "position": {"x": 0.1, "y": 0.2, "z": 0.3},
                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                "fingers": {
                    "thumb": 0.2,
                    "index": 0.8,
                    "middle": 0.6,
                    "ring": 0.4,
                    "pinky": 0.1
                },
                "battery_level": 0.85,
                "connection_quality": 0.95
            }
        }


class ManusSkeletonNode(BaseModel):
    """Individual skeleton node from Manus SDK"""
    node_id: int = Field(..., description="Node identifier")
    name: str = Field(..., description="Node name")
    position: Vector3 = Field(..., description="Node position")
    rotation: Quaternion = Field(..., description="Node rotation")
    parent_id: Optional[int] = Field(None, description="Parent node ID")
    semantic_name: Optional[str] = Field(None, description="Semantic joint name (e.g., 'LeftThumbMCP')")
    chain_type: Optional[str] = Field(None, description="Chain type (e.g., 'FingerThumb', 'Hand')")
    finger_joint_type: Optional[str] = Field(None, description="Joint type (e.g., 'Metacarpal', 'Proximal')")
    side: Optional[str] = Field(None, description="Side (Left, Right, Center)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "node_id": 1,
                "name": "node_1",
                "position": {"x": 0.1, "y": 0.2, "z": 0.3},
                "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                "parent_id": 0,
                "semantic_name": "LeftThumbMCP",
                "chain_type": "FingerThumb",
                "finger_joint_type": "Metacarpal",
                "side": "Left"
            }
        }


class ManusFrame(BaseModel):
    """Complete frame of data from Manus Core"""
    timestamp: datetime = Field(..., description="Frame timestamp")
    frame_number: int = Field(..., description="Sequential frame number")
    user_id: int = Field(..., description="User identifier")
    gloves: List[ManusGloveData] = Field(default_factory=list, description="Glove data")
    skeleton_nodes: List[ManusSkeletonNode] = Field(default_factory=list, description="Skeleton node data")
    frame_rate: Optional[float] = Field(None, description="Current frame rate")
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-08-16T10:30:45.123456",
                "frame_number": 12345,
                "user_id": 0,
                "gloves": [
                    {
                        "glove_id": 12345,
                        "hand_type": "right",
                        "position": {"x": 0.1, "y": 0.2, "z": 0.3},
                        "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                        "fingers": {
                            "thumb": 0.2,
                            "index": 0.8,
                            "middle": 0.6,
                            "ring": 0.4,
                            "pinky": 0.1
                        },
                        "battery_level": 0.85,
                        "connection_quality": 0.95
                    }
                ],
                "skeleton_nodes": [
                    {
                        "node_id": 1,
                        "name": "rightHand",
                        "position": {"x": 0.1, "y": 0.2, "z": 0.3},
                        "rotation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
                        "parent_id": 0
                    }
                ],
                "frame_rate": 60.0
            }
        }