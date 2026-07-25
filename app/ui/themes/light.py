"""Light glassmorphism theme for the application shell."""

APP_STYLESHEET = """
QMainWindow, QWidget#applicationRoot {
    background: #EEF3FF;
    color: #18213A;
    font-family: "Segoe UI";
    font-size: 14px;
}

QFrame#sidebar {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 0.92, y2: 1,
        stop: 0 #182746,
        stop: 0.42 #2F4D7B,
        stop: 0.74 #5478AB,
        stop: 1 #9EB4E8
    );
    border: 1px solid rgba(202, 218, 255, 62);
    border-radius: 18px;
}

QFrame#iconRail {
    background: rgba(25, 42, 76, 72);
    border: 1px solid rgba(210, 224, 255, 42);
    border-radius: 16px;
}

QScrollArea#navigationScroll, QWidget#navigationContent {
    background: transparent;
    border: 0;
}

QLabel#brandName {
    color: #F7FAFF;
    font-size: 13px;
    font-weight: 700;
}

QToolButton#navigationButton {
    background: transparent;
    border: 0;
    border-radius: 9px;
    color: #F5F8FF;
    font-size: 10px;
    font-weight: 600;
    padding: 0 8px;
    text-align: left;
}

QToolButton#navigationButton[expanded="false"] {
    padding: 0;
    text-align: center;
}

QToolButton#navigationButton[expanded="true"] {
    padding: 0 5px;
    text-align: left;
}

QToolButton#navigationButton:hover {
    background: rgba(113, 143, 211, 42);
    color: white;
}

QToolButton#navigationButton[active="true"] {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 rgba(124, 105, 244, 115),
        stop: 1 rgba(196, 211, 255, 72)
    );
    border: 1px solid rgba(225, 232, 255, 82);
    border-radius: 9px;
    color: white;
}

QToolButton#navigationButton[expanded="true"][active="true"] {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 transparent,
        stop: 0.30 transparent,
        stop: 0.305 rgba(124, 105, 244, 100),
        stop: 1 rgba(196, 211, 255, 68)
    );
    border: 0;
}

QToolButton#sidebarToggle {
    background: rgba(126, 153, 216, 42);
    border: 1px solid rgba(215, 227, 255, 58);
    border-radius: 9px;
    padding: 0;
}

QToolButton#sidebarToggle:hover {
    background: rgba(131, 112, 239, 105);
    border-color: rgba(230, 236, 255, 105);
}

QFrame#topBar, QFrame#glassCard {
    background: rgba(255, 255, 255, 205);
    border: 1px solid rgba(255, 255, 255, 220);
    border-radius: 20px;
}

QLabel#pageTitle {
    color: #18213A;
    font-size: 24px;
    font-weight: 700;
}

QLabel#pageSubtitle {
    color: #7A84A3;
    font-size: 13px;
}

QLabel#statusPill {
    background: rgba(66, 211, 255, 28);
    border: 1px solid rgba(79, 124, 255, 45);
    border-radius: 12px;
    color: #3764B7;
    font-size: 12px;
    font-weight: 600;
    padding: 5px 10px;
}

QLabel#cardTitle {
    color: #273151;
    font-size: 18px;
    font-weight: 700;
}

QLabel#cardBody {
    color: #7A84A3;
    font-size: 14px;
}

QFrame#loginCard {
    background: rgba(255, 255, 255, 225);
    border: 1px solid rgba(255, 255, 255, 235);
    border-radius: 24px;
}

QLabel#loginTitle {
    color: #18213A;
    font-size: 28px;
    font-weight: 700;
}

QLineEdit#loginInput {
    min-height: 46px;
    background: rgba(238, 243, 255, 175);
    border: 1px solid rgba(108, 92, 231, 35);
    border-radius: 13px;
    color: #25304F;
    padding: 0 14px;
    selection-background-color: #6C5CE7;
}

QLineEdit#loginInput:focus {
    border: 1px solid #6C5CE7;
    background: rgba(255, 255, 255, 245);
}

QLabel#loginError {
    color: #C33B68;
    font-size: 12px;
}

QPushButton#primaryButton {
    min-height: 46px;
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #6C5CE7,
        stop: 0.55 #4F7CFF,
        stop: 1 #42D3FF
    );
    border: 0;
    border-radius: 13px;
    color: white;
    font-size: 14px;
    font-weight: 700;
}

QPushButton#primaryButton:hover {
    background: #5D6FEF;
}

QPushButton#secondaryButton {
    min-height: 32px;
    background: rgba(108, 92, 231, 18);
    border: 1px solid rgba(108, 92, 231, 42);
    border-radius: 11px;
    color: #5147B8;
    font-size: 12px;
    font-weight: 600;
    padding: 0 12px;
}

QFrame#dashboardFilterBar {
    background: rgba(255, 255, 255, 180);
    border: 1px solid rgba(255, 255, 255, 220);
    border-radius: 16px;
}

QLabel#filterLabel, QLabel#panelTitle {
    color: #29345C;
    font-size: 15px;
    font-weight: 700;
}

QComboBox#periodCombo {
    min-width: 130px;
    min-height: 34px;
    background: rgba(238, 243, 255, 210);
    border: 1px solid rgba(108, 92, 231, 38);
    border-radius: 10px;
    color: #455071;
    padding: 0 10px;
}

QScrollArea#dashboardScroll, QWidget#dashboardContent {
    background: transparent;
}

QFrame#kpiCard, QFrame#dashboardPanel {
    background: rgba(255, 255, 255, 205);
    border: 1px solid rgba(255, 255, 255, 225);
    border-radius: 18px;
}

QFrame#kpiCard[accent="purple"] {
    border-top: 3px solid #6C5CE7;
}

QFrame#kpiCard[accent="blue"] {
    border-top: 3px solid #4F7CFF;
}

QFrame#kpiCard[accent="cyan"] {
    border-top: 3px solid #42D3FF;
}

QFrame#kpiCard[accent="green"] {
    border-top: 3px solid #40C9A2;
}

QFrame#kpiCard[accent="pink"] {
    border-top: 3px solid #F45CB4;
}

QLabel#kpiLabel {
    color: #7A84A3;
    font-size: 12px;
    font-weight: 600;
}

QLabel#kpiValue {
    color: #202A49;
    font-size: 25px;
    font-weight: 700;
}

QFrame#pipelineStage {
    background: rgba(238, 243, 255, 155);
    border: 1px solid rgba(79, 124, 255, 24);
    border-radius: 11px;
}

QLabel#stageName, QLabel#activityDetail, QLabel#emptyState {
    color: #7A84A3;
    font-size: 11px;
}

QLabel#stageCount {
    color: #4F61A8;
    font-size: 18px;
    font-weight: 700;
}

QFrame#activityRow {
    background: rgba(238, 243, 255, 120);
    border: 0;
    border-radius: 9px;
}

QLabel#activityAction {
    color: #455071;
    font-size: 12px;
    font-weight: 700;
}

QPushButton#dashboardAction {
    min-height: 36px;
    background: rgba(108, 92, 231, 18);
    border: 1px solid rgba(108, 92, 231, 35);
    border-radius: 10px;
    color: #5147B8;
    font-weight: 600;
}

QPushButton#dashboardAction:hover {
    background: rgba(108, 92, 231, 32);
}

QLabel#dashboardError {
    background: rgba(244, 92, 180, 20);
    border: 1px solid rgba(244, 92, 180, 45);
    border-radius: 10px;
    color: #B43869;
    padding: 8px 12px;
}

QFrame#customerToolbar {
    background: rgba(255, 255, 255, 205);
    border: 1px solid rgba(255, 255, 255, 225);
    border-radius: 16px;
}

QLineEdit#customerSearch, QLineEdit#customerInput, QTextEdit#customerNotes {
    min-height: 38px;
    background: rgba(238, 243, 255, 180);
    border: 1px solid rgba(108, 92, 231, 35);
    border-radius: 10px;
    color: #25304F;
    padding: 0 12px;
}

QTableWidget#customerTable {
    background: rgba(255, 255, 255, 205);
    alternate-background-color: rgba(238, 243, 255, 120);
    border: 1px solid rgba(255, 255, 255, 225);
    border-radius: 16px;
    gridline-color: rgba(79, 124, 255, 20);
    color: #3D4868;
}

QTableWidget#customerTable::item {
    min-height: 38px;
    padding: 6px;
}

QTableWidget#customerTable::item:selected {
    background: rgba(108, 92, 231, 38);
    color: #41379F;
}

QLabel#detailsTitle {
    color: #202A49;
    font-size: 22px;
    font-weight: 700;
}
"""
