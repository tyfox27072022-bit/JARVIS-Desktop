from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

QSS = """
QMainWindow, QWidget {
  background: #07090d;
  color: #e8e4d8;
  font-family: "Segoe UI", "Georgia", sans-serif;
  font-size: 14px;
}
QTabWidget::pane {
  border: 1px solid #1c1910;
  background: #0c0e12;
  top: -1px;
}
QTabBar::tab {
  background: transparent;
  color: #8a8474;
  padding: 12px 22px;
  min-height: 20px;
  border: none;
  margin-right: 2px;
  letter-spacing: 0.04em;
}
QTabBar::tab:selected {
  color: #e8c547;
  border-bottom: 2px solid #e8c547;
  background: #12100a;
}
QTabBar::tab:hover:!selected {
  color: #d4cfc0;
}
QTextEdit {
  background: #0c0e12;
  color: #e8e4d8;
  border: 1px solid #1c1910;
  border-radius: 10px;
  padding: 14px;
  selection-background-color: #3a3218;
  font-size: 14px;
  line-height: 1.45;
}
QLineEdit {
  background: #12141a;
  color: #e8e4d8;
  border: 1px solid #2a2618;
  border-radius: 10px;
  padding: 10px 14px;
  min-height: 24px;
  selection-background-color: #3a3218;
}
QLineEdit:focus {
  border: 1px solid #e8c547;
}
QPushButton {
  background: #161410;
  color: #e8e4d8;
  border: 1px solid #2a2618;
  border-radius: 10px;
  padding: 10px 16px;
  min-height: 24px;
}
QPushButton:hover {
  background: #1e1a12;
  border-color: #e8c547;
  color: #f3ead0;
}
QPushButton:pressed {
  background: #12100a;
}
QPushButton#primary {
  background: #e8c547;
  color: #14110a;
  border: none;
  font-weight: 600;
}
QPushButton#primary:hover {
  background: #f0d56a;
  color: #14110a;
}
QCheckBox {
  color: #e8e4d8;
  spacing: 10px;
}
QCheckBox::indicator {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  border: 1px solid #2a2618;
  background: #12141a;
}
QCheckBox::indicator:checked {
  background: #e8c547;
  border-color: #e8c547;
}
QLabel#title {
  color: #e8c547;
  font-family: Georgia, "Palatino Linotype", serif;
  font-size: 28px;
  font-weight: 500;
  letter-spacing: 0.16em;
}
QLabel#status {
  color: #8a8474;
  font-size: 12px;
  letter-spacing: 0.08em;
}
QLabel#credit {
  color: #5c574c;
  font-size: 12px;
  letter-spacing: 0.06em;
}
QScrollBar:vertical {
  background: #07090d;
  width: 10px;
  margin: 4px;
}
QScrollBar::handle:vertical {
  background: #2a2618;
  border-radius: 5px;
  min-height: 32px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
  height: 0;
}
QMessageBox {
  background: #0c0e12;
}
QFormLayout {
  spacing: 12px;
}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    pal = QPalette()
    bg = QColor("#07090d")
    fg = QColor("#e8e4d8")
    gold = QColor("#e8c547")
    pal.setColor(QPalette.ColorRole.Window, bg)
    pal.setColor(QPalette.ColorRole.WindowText, fg)
    pal.setColor(QPalette.ColorRole.Base, QColor("#0c0e12"))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#12141a"))
    pal.setColor(QPalette.ColorRole.Text, fg)
    pal.setColor(QPalette.ColorRole.Button, QColor("#161410"))
    pal.setColor(QPalette.ColorRole.ButtonText, fg)
    pal.setColor(QPalette.ColorRole.Highlight, gold)
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#14110a"))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor("#12141a"))
    pal.setColor(QPalette.ColorRole.ToolTipText, fg)
    app.setPalette(pal)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(QSS)
