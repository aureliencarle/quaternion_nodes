from __future__ import annotations
from typing import List, Optional, Tuple, Any
from utils import *

from PyQt6 import QtWidgets, QtGui, QtCore

class Anchor:
    def __init__(self, node: Number, kind: str, name: str, x: float, y: float):
        self.node = node
        self.kind = kind  # 'input' or 'output'
        self.name = name  # 'real' or 'complex'
        self.pos = QtCore.QPointF(x, y)
        self.connections = []
        self.enabled = True  # ⚡ nouveau

    def update_node_state(self):
        """Met à jour l’état du node parent selon les connexions."""
        if self.kind == "input":
            node = self.node
            idx = node.inputs.index(self)
            node.input_activity[idx] = bool(self.connections)
            node.update()


class Number(QtWidgets.QGraphicsItem):
    def __init__(self, parent: Optional[QtWidgets.QGraphicsItem] = None) -> None:
        super().__init__(parent)
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
        self.title: str = ""

        self.inputs: List[Anchor] = []
        self.outputs: List[Anchor] = []
        self.input_activity: List[bool] = []
        self.active_internal: bool = False  # True si une entrée est connectée

    def _build_anchor(self, dimension: int) -> None:
        h = self.rect.height() - HEADER_HEIGHT
        step = h / (dimension + 1)

        self.inputs = [
            Anchor(self, "input", f"unit_{i}", ANCHOR_RADIUS / 2, HEADER_HEIGHT + (i + 1) * step)
            for i in range(dimension)
        ]
        self.outputs = [
            Anchor(
                self,
                "output",
                f"unit_{i}",
                self.rect.width() - ANCHOR_RADIUS / 2,
                HEADER_HEIGHT + (i + 1) * step,
            )
            for i in range(dimension)
        ]
        self.input_activity = [False for _ in self.inputs]

    def _draw_internal_wiring(self, painter: QtGui.QPainter, conns: List[Tuple[int, int, bool]]) -> None:
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)

        for inp_idx, out_idx, switch in conns:
            pen = QtGui.QPen()
            pen.setWidth(2)
            if self.input_activity[inp_idx]:
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

        for i, anchor in enumerate(self.inputs + self.outputs):
            if not anchor.enabled:
                color = QtGui.QColor(100, 100, 100)
            else:
                color = COLORS.get(anchor.name, QtGui.QColor(200, 200, 200))
            painter.setBrush(QtGui.QBrush(color))
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.drawEllipse(anchor.pos, ANCHOR_RADIUS, ANCHOR_RADIUS)

        self.draw_internal_wiring(painter)

    def itemChange(self, change: QtWidgets.QGraphicsItem.GraphicsItemChange, value: Any) -> Any:
        if change == QtWidgets.QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for anchor in self.inputs + self.outputs:
                for conn in anchor.connections:
                    conn.update_path()
        return super().itemChange(change, value)

    def boundingRect(self) -> QtCore.QRectF:
        return self.rect.adjusted(-2, -2, 2, 2)

    def draw_internal_wiring(self, painter):
        pass


class Real(Number):
    def __init__(self, title: str = "Real", parent: Optional[QtWidgets.QGraphicsItem] = None):
        super().__init__(parent)
        self.title = title
        h = self.rect.height()
        step = h / 2

        self.inputs = [Anchor(self, "input", "unit_0", ANCHOR_RADIUS / 2, step)]
        self.outputs = [
            Anchor(self, "output", "unit_0", self.rect.width() - ANCHOR_RADIUS / 2, step)
        ]
        self.input_activity = [False for _ in self.inputs]


class RealUnit(Real):
    def __init__(self):
        super().__init__("1")

    def draw_internal_wiring(self, painter: QtGui.QPainter) -> None:
        pen = QtGui.QPen(QtGui.QColor(180, 180, 180))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)  # évite remplissage parasite

        draw_bezier(painter, self.inputs[0].pos, self.outputs[0].pos)


class ComplexUnit(Number):
    def __init__(self, title: str = "Complex", parent: Optional[QtWidgets.QGraphicsItem] = None):
        super().__init__(parent)
        self.title = title
        self._build_anchor(2)


class ComplexUnit1(ComplexUnit):
    def __init__(self):
        super().__init__("1")

    def draw_internal_wiring(self, painter: QtGui.QPainter) -> None:
        conns = [
            (0, 1, False), # in, out, switch
            (1, 0, False),
        ]
        self._draw_internal_wiring(painter, conns)

class ComplexUnitI(ComplexUnit):
    def __init__(self):
        super().__init__("i")

    def draw_internal_wiring(self, painter: QtGui.QPainter) -> None:
        conns = [
            (0, 1, False), # in, out, switch
            (1, 0, True),
        ]
        self._draw_internal_wiring(painter, conns)


#############################################################################


class QuaternionUnit(Number):
    def __init__(self, title: str = "Quaternion", parent: Optional[QtWidgets.QGraphicsItem] = None):
        super().__init__(parent)
        self.title = title
        self._build_anchor(4)


class QuaternionUnit1(QuaternionUnit):
    def __init__(self):
        super().__init__("1")

    def draw_internal_wiring(self, painter: QtGui.QPainter) -> None:
        conns = [
            (0, 0, False), # in, out, switch
            (1, 1, False),
            (2, 2, False),
            (3, 3, False),
        ]
        self._draw_internal_wiring(painter, conns)

class QuaternionUnitI(QuaternionUnit):
    def __init__(self):
        super().__init__("i")

    def draw_internal_wiring(self, painter: QtGui.QPainter) -> None:
        conns = [
            (0, 1, False), # in, out, switch
            (1, 0, True),
            (2, 3, False),
            (3, 2, True),
        ]
        self._draw_internal_wiring(painter, conns)


class QuaternionUnitJ(QuaternionUnit):
    def __init__(self):
        super().__init__("j")

    def draw_internal_wiring(self, painter: QtGui.QPainter) -> None:
        conns = [
            (0, 2, False), # in, out, switch
            (1, 3, True),
            (2, 0, True),
            (3, 1, False),
        ]
        self._draw_internal_wiring(painter, conns)

class QuaternionUnitK(QuaternionUnit):
    def __init__(self):
        super().__init__("k")

    def draw_internal_wiring(self, painter: QtGui.QPainter) -> None:
        conns = [
            (0, 3, False), # in, out, switch
            (1, 2, False),
            (2, 1, True),
            (3, 0, True),
        ]
        self._draw_internal_wiring(painter, conns)

#############################################################################

class BiQuaternionUnit(Number):
    def __init__(self, title: str = "BiQuaternion", parent: Optional[QtWidgets.QGraphicsItem] = None):
        super().__init__(parent)
        self.title = title
        self._build_anchor(8)




class BiQuaternionUnit1(BiQuaternionUnit):
    def __init__(self):
        super().__init__("1")

    def draw_internal_wiring(self, painter: QtGui.QPainter) -> None:
        conns = [
            (0, 0, False), # in, out, switch
            (1, 1, False),
            (2, 2, False),
            (3, 3, False),
            (4, 4, False),
            (5, 5, False),
            (6, 6, False),
            (7, 7, False),
        ]
        self._draw_internal_wiring(painter, conns)

class BiQuaternionUniti(BiQuaternionUnit):
    def __init__(self):
        super().__init__("i")

    def draw_internal_wiring(self, painter: QtGui.QPainter) -> None:
        conns = [
            (0, 1, False), # in, out, switch
            (1, 0, True),
            (2, 5, False),
            (3, 6, False),
            (4, 7, False), 
            (5, 2, True),
            (6, 3, True),
            (7, 4, True),
        ]
        self._draw_internal_wiring(painter, conns)

class BiQuaternionUnitI(BiQuaternionUnit):
    def __init__(self):
        super().__init__("I")

    def draw_internal_wiring(self, painter: QtGui.QPainter) -> None:
        conns = [
            (0, 2, False), # in, out, switch
            (1, 5, False),
            (2, 0, True),
            (3, 4, False),
            (4, 3, False), 
            (5, 1, False),
            (6, 7, True),
            (7, 6, True),
        ]
        self._draw_internal_wiring(painter, conns)

class BiQuaternionUnitiI(BiQuaternionUnit):
    def __init__(self):
        super().__init__("iI")

    def draw_internal_wiring(self, painter: QtGui.QPainter) -> None:
        conns = [
            (0, 5, False), # in, out, switch
            (1, 2, True),
            (2, 1, True),
            (3, 7, False),
            (4, 6, True), 
            (5, 0, True),
            (6, 4, True),
            (7, 3, False),
        ]
        self._draw_internal_wiring(painter, conns)

class BiQuaternionUnitJ(BiQuaternionUnit):
    def __init__(self):
        super().__init__("J")

    def draw_internal_wiring(self, painter: QtGui.QPainter) -> None:
        conns = [
            (0, 3, False),  # 1 * J = J
            (1, 6, False),  # i * J = iJ
            (2, 4, False),  # I * J = K
            (3, 0, True),   # J * J = -1
            (4, 2, True),   # K * J = -I
            (5, 7, False),  # iI * J = iK
            (6, 1, True),   # iJ * J = -i
            (7, 5, True),   # iK * J = -iI
        ]
        self._draw_internal_wiring(painter, conns)


class BiQuaternionUnitiJ(BiQuaternionUnit):
    def __init__(self):
        super().__init__("iJ")

    def draw_internal_wiring(self, painter: QtGui.QPainter) -> None:
        conns = [
            (0, 6, False),  # 1 * iJ = iJ
            (1, 3, True),   # i * iJ = -J
            (2, 7, False),  # I * iJ = iK
            (3, 1, False),  # J * iJ = i
            (4, 5, False),  # K * iJ = iI
            (5, 4, True),   # iI * iJ = -K
            (6, 0, True),   # iJ * iJ = -1
            (7, 2, True),   # iK * iJ = -I
        ]
        self._draw_internal_wiring(painter, conns)


class BiQuaternionUnitK(BiQuaternionUnit):
    def __init__(self):
        super().__init__("K")

    def draw_internal_wiring(self, painter: QtGui.QPainter) -> None:
        conns = [
            (0, 4, False),  # 1 * K = K
            (1, 7, False),  # i * K = iK
            (2, 3, True),   # I * K = -J
            (3, 2, False),  # J * K = I
            (4, 0, True),   # K * K = -1
            (5, 6, False),  # iI * K = iJ
            (6, 5, True),   # iJ * K = -iI
            (7, 1, True),   # iK * K = -i
        ]
        self._draw_internal_wiring(painter, conns)


class BiQuaternionUnitiK(BiQuaternionUnit):
    def __init__(self):
        super().__init__("iK")

    def draw_internal_wiring(self, painter: QtGui.QPainter) -> None:
        conns = [
            (0, 7, False),  # 1 * iK = iK
            (1, 4, True),   # i * iK = -K
            (2, 6, True),   # I * iK = -iJ
            (3, 5, False),  # J * iK = iI
            (4, 1, False),  # K * iK = i
            (5, 3, True),   # iI * iK = -J
            (6, 2, False),  # iJ * iK = I
            (7, 0, True),   # iK * iK = -1
        ]
        self._draw_internal_wiring(painter, conns)
