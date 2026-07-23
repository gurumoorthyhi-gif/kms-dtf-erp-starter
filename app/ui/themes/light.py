"""Light glassmorphism theme for the application shell."""

APP_STYLESHEET = """
QMainWindow, QWidget#applicationRoot {
    background: #EEF3FF;
    color: #18213A;
    font-family: "Segoe UI";
    font-size: 14px;
}

QFrame#sidebar {
    background: rgba(255, 255, 255, 232);
    border: 1px solid rgba(255, 255, 255, 185);
    border-radius: 22px;
}

QLabel#brandName {
    color: #29345C;
    font-size: 16px;
    font-weight: 700;
}

QToolButton#navigationButton {
    background: transparent;
    border: 0;
    border-radius: 14px;
    color: #687292;
    font-size: 14px;
    font-weight: 600;
    padding: 8px 12px;
    text-align: left;
}

QToolButton#navigationButton:hover {
    background: rgba(108, 92, 231, 20);
    color: #4B55A5;
}

QToolButton#navigationButton[active="true"] {
    background: qlineargradient(
        x1: 0, y1: 0, x2: 1, y2: 1,
        stop: 0 rgba(108, 92, 231, 45),
        stop: 0.58 rgba(79, 124, 255, 38),
        stop: 1 rgba(66, 211, 255, 30)
    );
    border: 1px solid rgba(108, 92, 231, 62);
    color: #5147B8;
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
"""
