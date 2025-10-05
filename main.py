
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
from PyQt6 import QtWidgets, QtCore
from gui_scene import NodeScene, NodeView

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
        instr = QtWidgets.QLabel(
           "Double-clic gauche pour NodeType1, double-clic droit pour NodeType2.\n"
           "Drag depuis un connecteur → connecte un seul couple.\n"
           "Drag depuis le corps du node → connecte toutes les sorties aux entrées correspondantes d’un autre node."
        )
        instr.setStyleSheet("color: white; padding: 6px;")
        instr.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        dock = QtWidgets.QDockWidget("Instructions")
        dock.setWidget(instr)
        self.addDockWidget(QtCore.Qt.DockWidgetArea.TopDockWidgetArea, dock)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())
