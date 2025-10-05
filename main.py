
# node_blueprint_pyqt6.py
# Node editor UI using PyQt6/QGraphicsView
# - Double-click left mouse button to create a NodeType1
# - Double-click right mouse button to create a NodeType2
# - Nodes are displayed first without connections
# - Drag from a node's output to another node's input to create a connection
#   - Drag on a specific connector = single connection
#   - Drag on node body = connect all outputs to corresponding inputs at once
# - Internal wiring of nodes uses Bezier curves

import sys
from PyQt6 import QtWidgets, QtGui, QtCore

from utils import *
from number import *


class ConnectionItem(QtWidgets.QGraphicsPathItem):
    def __init__(self, src, dst, parent=None):
        super().__init__(parent)
        self.src = src
        self.dst = dst
        pen = QtGui.QPen(QtGui.QColor(60, 160, 255))
        pen.setWidth(3)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
        self.setPen(pen)
        self.setZValue(-1)
        self.update_path()


    def remove(self):
        # retirer la connexion des anchors
        if self in self.src.connections:
            self.src.connections.remove(self)
        if self in self.dst.connections:
            self.dst.connections.remove(self)

        # mettre à jour les nodes connectés
        if hasattr(self.src, "update_node_state"):
            self.src.update_node_state()
        if hasattr(self.dst, "update_node_state"):
            self.dst.update_node_state()

        # supprimer du scene
        scene = self.scene()
        if scene:
            scene.removeItem(self)

    def update_path(self):
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

##########################################################################################

class NodeScene(QtWidgets.QGraphicsScene):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(30, 30, 30)))

        self.nodes = []
        self.connections = []

        # Éléments d’état pour le drag de connexions
        self.dragging_connection = None
        self.drag_start_anchor = None
        self.drag_start_node = None

        # Clipboard
        self.clipboard_nodes = []

    # ───────────────────────────────
    # NODE CREATION
    # ───────────────────────────────
    def contextMenuEvent(self, event):
        """Menu contextuel pour ajouter des nodes."""
        pos = event.scenePos()
        item = self.itemAt(pos, QtGui.QTransform())
        if item:
            return super().contextMenuEvent(event)

        menu = QtWidgets.QMenu()
        nodes = {
            "Real": Real,
            "ComplexUnit1": ComplexUnit1,
            "ComplexUnitI": ComplexUnitI,
            "QuaternionUnit1": QuaternionUnit1,
            "QuaternionUnitI": QuaternionUnitI,
            "QuaternionUnitJ": QuaternionUnitJ,
            "QuaternionUnitK": QuaternionUnitK,
        }

        for name, cls in nodes.items():
            menu.addAction(name, lambda checked=False, c=cls: self.add_node(c, pos))

        menu.exec(event.screenPos())

    def add_node(self, node_class, pos):
        """Ajoute un node à la scène."""
        node = node_class()
        node.setPos(pos - QtCore.QPointF(NODE_WIDTH / 2, NODE_HEIGHT / 2))
        self.addItem(node)
        self.nodes.append(node)
        return node

    # ───────────────────────────────
    # CONNECTION CREATION
    # ───────────────────────────────
    def start_connection_from_anchor(self, anchor):
        """Commence un drag de connexion depuis un anchor."""
        self.drag_start_anchor = anchor
        self.dragging_connection = QtWidgets.QGraphicsPathItem()
        pen = QtGui.QPen(QtGui.QColor(200, 200, 255))
        pen.setWidth(2)
        self.dragging_connection.setPen(pen)
        self.addItem(self.dragging_connection)
        self.views()[0].setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)

    def start_connection_from_node(self, node):
        """Commence un drag de connexion depuis un node (connect all)."""
        self.drag_start_node = node
        self.dragging_connection = QtWidgets.QGraphicsPathItem()
        pen = QtGui.QPen(QtGui.QColor(200, 255, 200))
        pen.setWidth(2)
        self.dragging_connection.setPen(pen)
        self.addItem(self.dragging_connection)
        self.views()[0].setDragMode(QtWidgets.QGraphicsView.DragMode.NoDrag)

    def update_drag_connection(self, pos):
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

    def add_connection(self, src_anchor, tgt_anchor):
        """Ajoute une connexion valide entre deux anchors."""
        conn = ConnectionItem(src_anchor, tgt_anchor)
        self.addItem(conn)
        self.connections.append(conn)
        src_anchor.connections.append(conn)
        tgt_anchor.connections.append(conn)
        conn.update_path()

        # mise à jour des états internes
        src_anchor.update_node_state()
        tgt_anchor.update_node_state()

    def finalize_connection(self, pos):
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
                        and in_anchor.name == self.drag_start_anchor.name:
                        targets.append(in_anchor)
            elif self.drag_start_node:
                for out_a, in_a in zip(self.drag_start_node.outputs, target_node.inputs):
                    if out_a.name == in_a.name:
                        targets.append(in_a)

        for tgt in targets:
            src = (
                self.drag_start_anchor
                if self.drag_start_anchor
                else next(o for o in self.drag_start_node.outputs if o.name == tgt.name)
            )
            self.add_connection(src, tgt)

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
    def mousePressEvent(self, event):
        pos = event.scenePos()

        for node in self.nodes:
            # clic sur un output : toggle ou drag
            for out_anchor in node.outputs:
                global_pos = node.mapToScene(out_anchor.pos)
                if (pos - global_pos).manhattanLength() < ANCHOR_RADIUS * 2:
                    if event.button() == QtCore.Qt.MouseButton.RightButton:
                        out_anchor.enabled = not out_anchor.enabled
                        for conn in out_anchor.connections:
                            conn.update_path()
                        self.update()
                        return
                    self.start_connection_from_anchor(out_anchor)
                    return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self.update_drag_connection(event.scenePos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.finalize_connection(event.scenePos())
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
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
    def keyPressEvent(self, event):
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
            if isinstance(item, Number):
                for anchor in item.inputs + item.outputs:
                    for conn in list(anchor.connections):
                        conn.remove()
                        if conn in self.connections:
                            self.connections.remove(conn)
                if item in self.nodes:
                    self.nodes.remove(item)
                self.removeItem(item)

    def copy_selected_nodes(self):
        self.clipboard_nodes = [i for i in self.selectedItems() if isinstance(i, Number)]

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
    def __init__(self, scene, parent=None):
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

    def wheelEvent(self, event):
        angle = event.angleDelta().y()
        factor = 1.001**angle
        self.scale(factor, factor)

    # ─────────────── PAN (clic milieu) ───────────────
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self._panning = True
            self._last_pan_point = event.pos()
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
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

    def mouseReleaseEvent(self, event):
        # Relâche le clic milieu
        if event.button() == QtCore.Qt.MouseButton.MiddleButton:
            self._panning = False
            self._last_mouse_pos = None
            self.setCursor(QtCore.Qt.CursorShape.ArrowCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Node Blueprint - PyQt6")
        self.resize(1600, 900)

        # Création de la scène et de la vue
        self.scene = NodeScene()
        self.view = NodeView(self.scene)
        self.setCentralWidget(self.view)

        # Instructions utilisateur
        #instr = QtWidgets.QLabel(
        #    "Double-clic gauche pour NodeType1, double-clic droit pour NodeType2.\n"
        #    "Drag depuis un connecteur → connecte un seul couple.\n"
        #    "Drag depuis le corps du node → connecte toutes les sorties aux entrées correspondantes d’un autre node."
        #)
        #instr.setStyleSheet("color: white; padding: 6px;")
        #instr.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        dock = QtWidgets.QDockWidget("Instructions")
        #dock.setWidget(instr)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.TopDockWidgetArea, dock)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
