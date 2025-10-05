from __future__ import annotations
from typing import List, Optional, Any
from utils import (
    NODE_WIDTH, NODE_HEIGHT, HEADER_HEIGHT, RADIUS, ANCHOR_RADIUS, draw_bezier)
import core

from PyQt6 import QtWidgets, QtGui, QtCore


class ConnectionItem(QtWidgets.QGraphicsPathItem):
    def __init__(self, src: Anchor, dst: Anchor, parent: Optional[QtWidgets.QGraphicsItem] = None) -> None:
        super().__init__(parent)
        self.src: Anchor = src
        self.dst: Anchor = dst
        pen = QtGui.QPen(QtGui.QColor(60, 160, 255))
        pen.setWidth(3)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)
        self.setZValue(-1)
        self.update_path()

    def remove(self) -> None:
        # retirer la connexion des anchors
        if self in self.src.gui_connections:
            self.src.gui_connections.remove(self)
        if self in self.dst.gui_connections:
            self.dst.gui_connections.remove(self)

        # mettre à jour les nodes connectés
        if hasattr(self.src, "update_node_state"):
            self.src.update_node_state()
        if hasattr(self.dst, "update_node_state"):
            self.dst.update_node_state()

        # supprimer du scene
        scene = self.scene()
        if scene:
            scene.removeItem(self)

    def update_path(self) -> None:
        if not (self.src.enabled and self.dst.enabled):
            self.setPath(QtGui.QPainterPath())  # vide
            return

        src_pt = self.src.node.mapToScene(self.src.pos)
        dst_pt = self.dst.node.mapToScene(self.dst.pos)
        path = QtGui.QPainterPath()
        path.moveTo(src_pt)
        dx = dst_pt.x() - src_pt.x()
        ctrl1 = QtCore.QPointF(src_pt.x() + dx * 0.5, src_pt.y())
        ctrl2 = QtCore.QPointF(dst_pt.x() - dx * 0.5, dst_pt.y())
        path.cubicTo(ctrl1, ctrl2, dst_pt)
        self.setPath(path)

class Anchor:
    """
    GUI wrapper for core.CorePort with visual positioning and connection management.
    """
    def __init__(self, node: NumberBox, core_port: core.Port, x: float, y: float):
        self.node = node
        self.core_port = core_port
        self.pos = QtCore.QPointF(x, y)
        self.gui_connections = []  # GUI connection objects (lines/curves)
    
    @property
    def color(self) -> QtGui.QColor:
        colors = {
            core.PortType.R: QtGui.QColor(255, 180, 120),   # orange clair
            core.PortType.I: QtGui.QColor(120, 200, 255),   # bleu
            core.PortType.QI: QtGui.QColor(180, 255, 120),   # vert
            core.PortType.QJ: QtGui.QColor(200, 120, 255),   # violet
            core.PortType.QK: QtGui.QColor(255, 120, 200),   # rose
        }
        return colors.get(self.core_port.type, QtGui.QColor(200, 200, 200))

    @property
    def kind(self) -> str:
        return "input" if self.core_port.port_category == core.PortCategory.INPUT else "output"
    
    def can_connect_to(self, other: Anchor) -> bool:
        return self.core_port.can_connect_to(other.core_port)
    
    def connect_to(self, other: Anchor, connection: ConnectionItem) -> bool:
        """Establish a connection to another anchor if valid."""
        if self.can_connect_to(other):
            self.core_port.connect_to(other.core_port)
            self.gui_connections.append(connection)
            other.gui_connections.append(connection)
            self.update_node_state()
            other.update_node_state()
            return True
        return False

    @property
    def enabled(self) -> bool:
        return self.core_port.enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self.core_port.enabled = value
    
    @property
    def connections(self) -> List[core.Port]:
        return self.core_port.connections

    def update_node_state(self):
        """Met à jour l'état du node parent selon les connexions."""
        self.node.update()

class NumberBox(QtWidgets.QGraphicsItem):
    """
    GUI node that wraps a core.CoreNumber implementation.
    Handles visual representation and user interaction.
    """
    def __init__(self, core_node: core.MathUnit, parent: Optional[QtWidgets.QGraphicsItem] = None) -> None:
        super().__init__(parent)
        self.core_node = core_node
        self.rect: QtCore.QRectF = QtCore.QRectF(0, 0, NODE_WIDTH, NODE_HEIGHT)
        self.setFlags(
            QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QtWidgets.QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self._bg_brush: QtGui.QBrush = QtGui.QBrush(QtGui.QColor(40, 40, 40))
        self._header_brush: QtGui.QBrush = QtGui.QBrush(QtGui.QColor(60, 60, 60))
        self._pen: QtGui.QPen = QtGui.QPen(QtGui.QColor(20, 20, 20))

        # Create GUI anchors from core ports
        self.inputs: List[Anchor] = []
        self.outputs: List[Anchor] = []
        self._create_gui_anchors()

    @property
    def title(self) -> str:
        return self.core_node.title

    def _create_gui_anchors(self) -> None:
        """Create GUI anchors from core ports."""
        h = self.rect.height()
        step = h / (self.core_node.dimension + 1)

        self.inputs = [
            Anchor(self, port, ANCHOR_RADIUS / 2, (i + 1) * step)
            for i, port in enumerate(self.core_node.input_ports)
        ]
        self.outputs = [
            Anchor(self, port, self.rect.width() - ANCHOR_RADIUS / 2, (i + 1) * step)
            for i, port in enumerate(self.core_node.output_ports)
        ]

    def _draw_internal_wiring(self, painter: QtGui.QPainter) -> None:
        """Draw internal wiring using core node's wiring pattern."""
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
        
        wiring_connections = self.core_node.get_wiring_connections()
        for inp_idx, out_idx, switch in wiring_connections:
            # Add bounds checking to prevent IndexError
            if inp_idx >= len(self.inputs) or out_idx >= len(self.outputs):
                continue
                
            pen = QtGui.QPen()
            pen.setWidth(2)
            if self.core_node.is_input_port_active(inp_idx):
                pen.setColor(QtGui.QColor(200, 255, 200))
            else:
                pen.setColor(QtGui.QColor(180, 180, 180))
            painter.setPen(pen)
            draw_bezier(
                painter,
                self.inputs[inp_idx].pos,
                self.outputs[out_idx].pos,
                switch=switch,
            )

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionGraphicsItem, widget: Optional[QtWidgets.QWidget] = None) -> None:
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Ombre
        shadow_color = QtGui.QColor(0, 0, 0, 140)
        painter.setBrush(shadow_color)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect.translated(3, 6), RADIUS, RADIUS)

        # Corps
        if self.isSelected():
            # couleur différente quand sélectionné (par ex. plus clair ou contour bleu)
            body_brush = QtGui.QBrush(QtGui.QColor(70, 70, 120))
            pen = QtGui.QPen(QtGui.QColor(100, 180, 255))
            pen.setWidth(2)
        else:
            body_brush = self._bg_brush
            pen = self._pen

        painter.setBrush(body_brush)
        painter.setPen(pen)
        painter.drawRoundedRect(self.rect, RADIUS, RADIUS)

        # Header
        header_rect = QtCore.QRectF(0, 0, self.rect.width(), HEADER_HEIGHT)
        painter.setBrush(self._header_brush)
        painter.drawRoundedRect(header_rect, RADIUS, RADIUS)
        painter.setBrush(self._bg_brush)
        rect_cover = QtCore.QRectF(
            0, HEADER_HEIGHT - RADIUS, self.rect.width(), float(RADIUS)
        )
        painter.drawRect(rect_cover)
        painter.setPen(QtGui.QColor(220, 220, 220))
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            header_rect.adjusted(6, 0, -6, 0),
            QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft,
            self.title,
        )

        for anchor in self.inputs + self.outputs:
            if not anchor.enabled:
                color = QtGui.QColor(100, 100, 100)
            else:
                color = anchor.color
            painter.setBrush(QtGui.QBrush(color))
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.drawEllipse(anchor.pos, ANCHOR_RADIUS, ANCHOR_RADIUS)

        self.draw_internal_wiring(painter)

    def draw_internal_wiring(self, painter):
        """Default implementation uses core wiring pattern."""
        self._draw_internal_wiring(painter)

    def itemChange(self, change: QtWidgets.QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for anchor in self.inputs + self.outputs:
                for conn in anchor.gui_connections:
                    conn.update_path()
        return super().itemChange(change, value)

    def boundingRect(self) -> QtCore.QRectF:
        return self.rect.adjusted(-2, -2, 2, 2)
