"""Light glassmorphism theme for the application shell."""

APP_STYLESHEET = """
QMainWindow {
    background: #101A47;
    color: #18213A;
    font-family: "Segoe UI";
    font-size: 14px;
}

QWidget#applicationRoot {
    background: transparent;
}

QFrame#glassSidebar, QWidget#sidebarContent, QScrollArea#sidebarScroll,
QScrollArea#sidebarScroll > QWidget > QWidget {
    background: transparent;
    border: 0;
}

QFrame#glassBrand {
    background: rgba(87, 93, 168, 44);
    border: 1px solid rgba(255, 255, 255, 35);
    border-radius: 15px;
}

QLabel#glassBrandName {
    color: rgba(255, 255, 255, 242);
    font-size: 15px;
    font-weight: 700;
}

QFrame#glassDivider {
    background: rgba(255, 255, 255, 31);
    border: 0;
}

QToolButton#glassNavigationButton {
    background: transparent;
    border: 0;
    padding: 0;
}

QToolButton#themeToggleButton {
    background: transparent;
    border: 0;
    border-radius: 23px;
}

QToolButton#themeToggleButton:hover {
    background: rgba(110, 120, 220, 35);
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

QLabel#studioTitle {
    color: #EEF4FF;
    font-size: 20px;
    font-weight: 700;
    padding-right: 8px;
}

QGroupBox#studioPanel {
    background: rgba(31, 46, 88, 205);
    border: 1px solid rgba(122, 151, 225, 80);
    border-radius: 16px;
    color: #DCE8FF;
    font-weight: 700;
    margin-top: 10px;
    padding-top: 10px;
}

QGroupBox#studioPanel::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
}

QGraphicsView#artworkStudioCanvas {
    background: #FFFFFF;
    border: 1px solid rgba(130, 154, 220, 95);
    border-radius: 16px;
}

QListWidget#studioDesignList {
    background: rgba(22, 35, 72, 180);
    border: 1px solid rgba(125, 151, 220, 65);
    border-radius: 11px;
    color: #E9F1FF;
    padding: 5px;
}

QPushButton#studioPrimaryButton, QPushButton#studioSecondaryButton {
    min-height: 34px;
    border-radius: 10px;
    color: white;
    font-weight: 600;
    padding: 0 11px;
}

QPushButton#studioPrimaryButton {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 0,
        stop: 0 #7758E8, stop: 0.55 #4F7CFF, stop: 1 #36BEEB
    );
    border: 1px solid rgba(255, 255, 255, 45);
}

QPushButton#studioSecondaryButton {
    background: rgba(91, 113, 185, 70);
    border: 1px solid rgba(160, 180, 235, 65);
}

QLabel#studioMetric {
    color: #CFE2FF;
    font-size: 15px;
    font-weight: 700;
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
