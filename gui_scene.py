
from typing import List, Optional
from PyQt6 import QtWidgets, QtGui, QtCore

import core
from utils import (
    NODE_WIDTH, NODE_HEIGHT, HEADER_HEIGHT, ANCHOR_RADIUS
)
from gui_items import (
    NumberBox, 
    Anchor,
    ConnectionItem
)


class NodeScene(QtWidgets.QGraphicsScene):
    def __init__(self, parent: Optional[QtWidgets.QGraphicsItem] = None) -> None:
        super().__init__(parent)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(30, 30, 30)))

        self.nodes: List[NumberBox] = []
        self.connections: List[ConnectionItem] = []

        # Éléments d’état pour le drag de connexions
        self.dragging_connection: Optional[ConnectionItem] = None
        self.drag_start_anchor: Optional[Anchor] = None
        self.drag_start_node: Optional[NumberBox] = None

        # Clipboard
        self.clipboard_nodes: List[NumberBox] = []

    # ───────────────────────────────
    # NODE CREATION
    # ───────────────────────────────
    def contextMenuEvent(self, event: QtWidgets.QGraphicsSceneContextMenuEvent):
        """Menu contextuel pour ajouter des nodes."""
        pos = event.scenePos()
        item = self.itemAt(pos, QtGui.QTransform())
        if item:
            return super().contextMenuEvent(event)

        menu = QtWidgets.QMenu()
        node_unit_types = {
            "Real Unit 1": core.MathUnitType.R,
            "Complex Unit 1": core.MathUnitType.C1,
            "Complex Unit i": core.MathUnitType.CI,
            "Quaternion Unit 1": core.MathUnitType.Q1,
            "Quaternion Unit i": core.MathUnitType.QI,
            "Quaternion Unit j": core.MathUnitType.QJ,
            "Quaternion Unit k": core.MathUnitType.QK,
        }

        for name, unit_type in node_unit_types.items():
            menu.addAction(name, lambda checked=False, type=unit_type: self.add_node_from_unit_type(type, pos))

        menu.exec(event.screenPos())

    def add_node_from_unit_type(self, unit_type: core.MathUnitType, pos: QtCore.QPointF) -> NumberBox:
        """Ajoute un node à la scène en utilisant une fonction factory."""
        node = NumberBox(core_node=core.create_math_unit(unit_type=unit_type))
        node.setPos(pos - QtCore.QPointF(NODE_WIDTH / 2, NODE_HEIGHT / 2))
        self.addItem(node)
        self.nodes.append(node)
        return node

    # ───────────────────────────────
    # CONNECTION CREATION
    # ───────────────────────────────
    def start_connection_from_anchor(self, anchor: Anchor) -> None:
        """Commence un drag de connexion depuis un anchor."""
        self.drag_start_anchor = anchor
        self.dragging_connection = QtWidgets.QGraphicsPathItem()
        pen = QtGui.QPen(QtGui.QColor(200, 200, 255))
        pen.setWidth(2)
        self.dragging_connection.setPen(pen)
        self.addItem(self.dragging_connection)
        self.views()[0].setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)

    def start_connection_from_node(self, node: NumberBox) -> None:
        """Commence un drag de connexion depuis un node (connect all)."""
        self.drag_start_node = node
        self.dragging_connection = QtWidgets.QGraphicsPathItem()
        pen = QtGui.QPen(QtGui.QColor(200, 255, 200))
        pen.setWidth(2)
        self.dragging_connection.setPen(pen)
        self.addItem(self.dragging_connection)
        self.views()[0].setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)

    def update_drag_connection(self, pos: QtCore.QPointF) -> None:
        """Met à jour la courbe de prévisualisation pendant le drag."""
        if not self.dragging_connection:
            return

        path = QtGui.QPainterPath()
        node = self.drag_start_anchor.node if self.drag_start_anchor else self.drag_start_node

        start_points = (
            [self.drag_start_anchor.pos]
            if self.drag_start_anchor
            else [a.pos for a in self.drag_start_node.outputs]
        )

        for sp in start_points:
            start_pt = node.mapToScene(sp)
            end_pt = pos
            dx = end_pt.x() - start_pt.x()
            ctrl1 = QtCore.QPointF(start_pt.x() + dx * 0.5, start_pt.y())
            ctrl2 = QtCore.QPointF(end_pt.x() - dx * 0.5, end_pt.y())
            path.moveTo(start_pt)
            path.cubicTo(ctrl1, ctrl2, end_pt)

        self.dragging_connection.setPath(path)

    def add_connection(self, src_anchor: Anchor, tgt_anchor: Anchor) -> None:
        """Ajoute une connexion valide entre deux anchors."""
        # Check if connection already exists
        for existing_conn in src_anchor.gui_connections:
            if existing_conn.dst == tgt_anchor:
                return  # Connection already exists
        
        # Check if target input already has a connection (inputs should typically have only one)
        if tgt_anchor.kind == "input" and tgt_anchor.gui_connections:
            # Remove existing connection to input before adding new one
            for old_conn in list(tgt_anchor.gui_connections):
                old_conn.remove()
                if old_conn in self.connections:
                    self.connections.remove(old_conn)

        conn = ConnectionItem(src_anchor, tgt_anchor)
        self.addItem(conn)
        self.connections.append(conn)
        src_anchor.connect_to(tgt_anchor, connection=conn)
        conn.update_path()

        # mise à jour des états internes
        src_anchor.update_node_state()
        tgt_anchor.update_node_state()

    def finalize_connection(self, pos: QtCore.QPointF) -> None:
        """Termine une connexion après un drag."""
        if not self.dragging_connection:
            return

        targets = []
        target_node = next(
            (n for n in self.nodes if n.rect.contains(n.mapFromScene(pos))),
            None
        )

        if target_node:
            if self.drag_start_anchor:
                for in_anchor in target_node.inputs:
                    global_pos = target_node.mapToScene(in_anchor.pos)
                    if (pos - global_pos).manhattanLength() < ANCHOR_RADIUS * 2 \
                        and in_anchor.can_connect_to(self.drag_start_anchor):
                        targets.append(in_anchor)
            elif self.drag_start_node:
                # Only connect if both nodes have the same dimension
                max_connections = min(len(self.drag_start_node.outputs), len(target_node.inputs))
                for i in range(max_connections):
                    out_a = self.drag_start_node.outputs[i]
                    in_a = target_node.inputs[i]
                    if out_a.can_connect_to(in_a):
                        targets.append(in_a)

        for tgt in targets:
            try:
                src = (
                    self.drag_start_anchor
                    if self.drag_start_anchor
                    else next((o for o in self.drag_start_node.outputs if o.can_connect_to(tgt)), None)
                )
                if src:  # Only add connection if source anchor is found
                    self.add_connection(src, tgt)
            except StopIteration:
                # Handle case where no matching output anchor is found
                continue

        self.cleanup_drag_state()

    def cleanup_drag_state(self):
        """Nettoie les états après un drag de connexion."""
        if self.dragging_connection:
            self.removeItem(self.dragging_connection)
        self.dragging_connection = None
        self.drag_start_anchor = None
        self.drag_start_node = None
        self.views()[0].setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)

    # ───────────────────────────────
    # MOUSE EVENTS
    # ───────────────────────────────
    def mousePressEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent):
        pos = event.scenePos()

        for node in self.nodes:
            # clic sur un output : toggle ou drag
            for out_anchor in node.outputs:
                global_pos = node.mapToScene(out_anchor.pos)
                if (pos - global_pos).manhattanLength() < ANCHOR_RADIUS * 2:
                    if event.button() == QtCore.Qt.MouseButton.RightButton:
                        out_anchor.enabled = not out_anchor.enabled
                        for conn in out_anchor.gui_connections:
                            conn.update_path()
                        self.update()
                        return
                    self.start_connection_from_anchor(out_anchor)
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        self.update_drag_connection(event.scenePos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        self.finalize_connection(event.scenePos())
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QtWidgets.QGraphicsSceneMouseEvent) -> None:
        pos = event.scenePos()
        for node in self.nodes:
            title_rect = QtCore.QRectF(node.pos(), QtCore.QSizeF(node.rect.width(), HEADER_HEIGHT))
            if node.rect.contains(node.mapFromScene(pos)) and not title_rect.contains(pos):
                self.start_connection_from_node(node)
                return
        super().mouseDoubleClickEvent(event)

    # ───────────────────────────────
    # KEYBOARD EVENTS
    # ───────────────────────────────
    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        key = event.key()
        mod = event.modifiers()

        if key == QtCore.Qt.Key.Key_Delete:
            self.delete_selected_nodes()
        elif key == QtCore.Qt.Key.Key_C and mod == QtCore.Qt.KeyboardModifier.ControlModifier:
            self.copy_selected_nodes()
        elif key == QtCore.Qt.Key.Key_V and mod == QtCore.Qt.KeyboardModifier.ControlModifier:
            self.paste_nodes()
        else:
            super().keyPressEvent(event)

    def delete_selected_nodes(self):
        for item in list(self.selectedItems()):
            if isinstance(item, NumberBox):
                for anchor in item.inputs + item.outputs:
                    for conn in list(anchor.gui_connections):
                        conn.remove()
                        if conn in self.connections:
                            self.connections.remove(conn)
                if item in self.nodes:
                    self.nodes.remove(item)
                self.removeItem(item)

    def copy_selected_nodes(self):
        self.clipboard_nodes = [i for i in self.selectedItems() if isinstance(i, NumberBox)]

    def paste_nodes(self):
        offset = QtCore.QPointF(30, 30)
        new_nodes = []
        for node in self.clipboard_nodes:
            cls = type(node)
            new_node = cls()
            new_node.setPos(node.pos() + offset)
            self.addItem(new_node)
            self.nodes.append(new_node)
            new_nodes.append(new_node)

        for n in new_nodes:
            n.setSelected(True)

class NodeView(QtWidgets.QGraphicsView):
    def __init__(self, scene: NodeScene, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(scene, parent)
        
        self.setRenderHints(
            QtGui.QPainter.RenderHint.Antialiasing
            | QtGui.QPainter.RenderHint.TextAntialiasing
        )
        self.setViewportUpdateMode(
            QtWidgets.QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        self.setDragMode(QtWidgets.QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(
            QtWidgets.QGraphicsView.ViewportAnchor.AnchorUnderMouse
        )
        self._panning = False
        self._last_pan_point = None

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        angle = event.angleDelta().y()
        factor = 1.001**angle
        self.scale(factor, factor)

    # ─────────────── PAN (clic milieu) ───────────────
    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self._panning = True
            self._last_pan_point = event.pos()
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            event.ignore()
            return

        if self._panning and self._last_pan_point:
            delta = event.pos() - self._last_pan_point
            self._last_pan_point = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        # Relâche le clic milieu
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self._panning = False
            self._last_pan_point = None
            self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)