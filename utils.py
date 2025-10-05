
import math
from typing import Dict, List
from PyQt6 import QtWidgets, QtGui, QtCore

NODE_WIDTH: int = 180
NODE_HEIGHT: int = 150
HEADER_HEIGHT: int = 30
RADIUS: int = 6
ANCHOR_RADIUS: int = 6

COLORS: Dict[str, QtGui.QColor] = {
    "unit_0": QtGui.QColor(255, 180, 120),   # orange clair
    "unit_1": QtGui.QColor(120, 200, 255),   # bleu
    "unit_2": QtGui.QColor(180, 255, 120),   # vert
    "unit_3": QtGui.QColor(200, 120, 255),   # violet
}


def draw_bezier(painter: QtGui.QPainter, p1: QtCore.QPointF, p2: QtCore.QPointF, switch: bool = False) -> None:
    path = QtGui.QPainterPath()
    # moveTo précis
    path.moveTo(QtCore.QPointF(p1.x(), p1.y()))
    dx = p2.x() - p1.x()
    ctrl1 = QtCore.QPointF(p1.x() + dx * 0.5, p1.y())
    ctrl2 = QtCore.QPointF(p2.x() - dx * 0.5, p2.y())
    path.cubicTo(ctrl1, ctrl2, QtCore.QPointF(p2.x(), p2.y()))
    painter.drawPath(path)

    if switch:
        # position au milieu (t=0.5)
        t: float = 0.1
        x: float = (1-t)**3 * p1.x() + 3*(1-t)**2*t * ctrl1.x() + 3*(1-t)*t**2 * ctrl2.x() + t**3 * p2.x()
        y: float = (1-t)**3 * p1.y() + 3*(1-t)**2*t * ctrl1.y() + 3*(1-t)*t**2 * ctrl2.y() + t**3 * p2.y()
        pos = QtCore.QPointF(x, y)

        # direction de la tangente (dérivée en t)
        dx_dt: float = (
            3*(1-t)**2*(ctrl1.x()-p1.x())
            + 6*(1-t)*t*(ctrl2.x()-ctrl1.x())
            + 3*t**2*(p2.x()-ctrl2.x())
        )
        dy_dt: float = (
            3*(1-t)**2*(ctrl1.y()-p1.y())
            + 6*(1-t)*t*(ctrl2.y()-ctrl1.y())
            + 3*t**2*(p2.y()-ctrl2.y())
        )
        angle: float = math.atan2(dy_dt, dx_dt)

        # petit triangle
        size: int = 8
        pts: List[QtCore.QPointF] = [
            QtCore.QPointF(0, 0),
            QtCore.QPointF(-size/2, -size/2),
            QtCore.QPointF(-size/2, size/2),
        ]

        # rotation + translation
        transform = QtGui.QTransform()
        transform.translate(pos.x(), pos.y())
        transform.rotateRadians(angle)
        poly = QtGui.QPolygonF([transform.map(p) for p in pts])

        painter.drawPolygon(poly)