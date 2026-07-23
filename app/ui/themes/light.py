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
"""
