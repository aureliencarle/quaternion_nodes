"""
Core mathematical implementation for number nodes.
This module contains the mathematical logic separated from GUI concerns.
"""

from __future__ import annotations
from typing import List, Tuple
from enum import Enum


class MathUnitType(Enum):
    """Enumeration of supported unit types (box)."""
    R = "real"
    C1 = "complex 1"
    CI = "complex i"
    Q1 = "quaternion 1"
    QI = "quaternion i"
    QJ = "quaternion j"
    QK = "quaternion k"

class PortCategory(Enum):
    """Enumeration of port categories (in/out)."""
    INPUT = "input"
    OUTPUT = "output"

class PortType(Enum):
    """Enumeration of port types (number flowing through)."""
    R = "real"
    I = "complex i"
    QI = "quaternion i"
    QJ = "quaternion j"
    QK = "quaternion k"

class MathUnitConfig:
    """Configuration for number units defining their properties and behavior."""
    def __init__(self, number_type: MathUnitType, ports: List[PortType], title: str, 
                 wiring_connections: List[Tuple[int, int, bool]]):
        self.number_type = number_type
        self.ports = ports
        self.title = title
        self.wiring_connections = wiring_connections

class Port:
    """
    Core port implementation without GUI dependencies.
    Represents a connection point with type validation.
    """
    
    def __init__(self, node: MathUnit, port_category: PortCategory, index: int, port_type: PortType):
        self.node = node
        self.port_category = port_category
        self.index = index  # 0-based index within the node
        self.type = port_type  # e.g., PortType.R, PortType.I, etc.
        self.connections: List[Port] = []
        self.enabled = True
    
    def can_connect_to(self, other: Port) -> bool:
        """Check if this port can connect to another port."""
        if not self.enabled or not other.enabled:
            return False
        
        # Can't connect to self or same node
        if other is self or other.node is self.node:
            return False
        
        # Must be different port types (input <-> output)
        if self.port_category == other.port_category:
            return False

        # Must be compatible port types
        if self.type != other.type:
            return False

        return True
    
    def connect_to(self, other: Port) -> bool:
        """Attempt to connect this port to another port."""
        if not self.can_connect_to(other):
            return False
        
        # Add bidirectional connection
        if other not in self.connections:
            self.connections.append(other)
        if self not in other.connections:
            other.connections.append(self)
        
        return True
    
    def disconnect_from(self, other: Port) -> bool:
        """Disconnect this port from another port."""
        if other not in self.connections:
            return False
        
        # Remove bidirectional connection
        self.connections.remove(other)
        if self in other.connections:
            other.connections.remove(self)
        
        return True
    
    @property
    def is_connected(self) -> bool:
        """Check if this port has any connections."""
        return len(self.connections) > 0


class MathUnit:
    """
    Generic mathematical number node that can be configured for different types.
    Contains core logic without GUI dependencies.
    """
    
    def __init__(self, config: MathUnitConfig):
        self.number_type = config.number_type
        self.title = config.title
        self.dimension = len(config.ports)
        
        # Create ports
        self.input_ports: List[Port] = []
        self.output_ports: List[Port] = []
        self._create_ports(config.ports)
        
        # Internal wiring pattern - direct integration
        self.wiring_connections = config.wiring_connections


    def _create_ports(self, port_types: List[PortType]) -> None:
        """Create input and output ports for this node."""
        self.input_ports = [
            Port(self, PortCategory.INPUT, i, port_type)
            for i, port_type in enumerate(port_types)
        ]
        self.output_ports = [
            Port(self, PortCategory.OUTPUT, i, port_type)
            for i, port_type in enumerate(port_types)
        ]
    
    def get_wiring_connections(self) -> List[Tuple[int, int, bool]]:
        """Get the internal wiring connections for this mathematical unit."""
        return self.wiring_connections
    
    def is_input_port_active(self, index: int) -> bool:
        """Check if a specific input port is active (connected)."""
        if 0 <= index and index < len(self.input_ports):
            return self.input_ports[index].is_connected
        return False

    def get_output_values(self, input_values: List[float]) -> List[float]:
        """
        Calculate output values based on input values and wiring pattern.
        
        Args:
            input_values: List of input values
            
        Returns:
            List of output values
        """
        # Determine output dimension from connections
        max_output_idx = max(conn[1] for conn in self.wiring_connections) if self.wiring_connections else -1
        output_values = [0.0] * (max_output_idx + 1)
        
        for input_idx, output_idx, invert_sign in self.wiring_connections:
            if input_idx < len(input_values):
                value = input_values[input_idx]
                if invert_sign:
                    value = -value
                output_values[output_idx] = value
        
        return output_values
    

# Predefined configurations for different number units
# Predefined configurations for different number units as a dictionary

MATH_UNIT_CONFIGS = {
    MathUnitType.R: MathUnitConfig(
        MathUnitType.R, [PortType.R], "1",
        [(0, 0, False)]
    ),
    MathUnitType.C1: MathUnitConfig(
        MathUnitType.C1, [PortType.R, PortType.I], "1",
        [(0, 0, False), (1, 1, False)]
    ),
    MathUnitType.CI: MathUnitConfig(
        MathUnitType.CI, [PortType.R, PortType.I], "i",
        [
            (0, 1, False),  # real -> imag
            (1, 0, True),   # imag -> -real
        ]
    ),
    MathUnitType.Q1: MathUnitConfig(
        MathUnitType.Q1, [PortType.R, PortType.QI, PortType.QJ, PortType.QK], "1",
        [(0, 0, False), (1, 1, False), (2, 2, False), (3, 3, False)]
    ),
    MathUnitType.QI: MathUnitConfig(
        MathUnitType.QI, [PortType.R, PortType.QI, PortType.QJ, PortType.QK], "i",
        [
            (0, 1, False),  # w -> x
            (1, 0, True),   # x -> -w
            (2, 3, False),  # y -> z
            (3, 2, True),   # z -> -y
        ]
    ),
    MathUnitType.QJ: MathUnitConfig(
        MathUnitType.QJ, [PortType.R, PortType.QI, PortType.QJ, PortType.QK], "j",
        [
            (0, 2, False),  # w -> y
            (1, 3, True),   # x -> -z
            (2, 0, True),   # y -> -w
            (3, 1, False),  # z -> x
        ]
    ),
    MathUnitType.QK: MathUnitConfig(
        MathUnitType.QK, [PortType.R, PortType.QI, PortType.QJ, PortType.QK], "k",
        [
            (0, 3, False),  # w -> z
            (1, 2, False),  # x -> y
            (2, 1, True),   # y -> -x
            (3, 0, True),   # z -> -w
        ]
    ),
}

def create_math_unit(unit_type: MathUnitType) -> MathUnit:
    """Factory function to create a MathUnit based on type."""
    config = MATH_UNIT_CONFIGS.get(unit_type)
    if config is None:
        raise ValueError(f"Unsupported MathUnitType: {unit_type}")
    return MathUnit(config)
