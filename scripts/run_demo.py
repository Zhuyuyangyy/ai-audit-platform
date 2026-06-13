#!/usr/bin/env python3
"""
AI Audit Platform - One-Click Demo Launcher
政企大模型应用安全合规审计系统 - 一键启动脚本

Usage:
    python scripts/run_demo.py
    python scripts/run_demo.py --port 8014
    python scripts/run_demo.py --no-browser
"""

import sys
import os
import subprocess
import argparse
import time
import webbrowser
from pathlib import Path

# Project root and backend directory
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
BACKEND_DIR = PROJECT_ROOT / "backend"

def print_banner():
    """Print startup banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║        政企大模型应用安全合规审计与输出风险控制系统          ║
║          AI Compliance Audit Platform v1.0                   ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_dependencies():
    """Check if required dependencies are installed"""
    required = ['fastapi', 'uvicorn', 'pydantic', 'sqlalchemy']
    missing = []

    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"[!] Missing dependencies: {', '.join(missing)}")
        print("[*] Installing dependencies...")
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r',
            str(PROJECT_ROOT / 'requirements.txt')
        ], check=True)
        print("[+] Dependencies installed successfully!")
    else:
        print("[+] All dependencies are installed.")

def init_database():
    """Initialize the database with seed data"""
    print("[*] Initializing database...")
    try:
        from app.core.database import init_db
        init_db()
        print("[+] Database initialized with seed data.")
    except Exception as e:
        print(f"[!] Database initialization warning: {e}")
        print("[*] Continuing startup...")

def seed_mock_data():
    """Seed additional mock data for demo"""
    print("[*] Seeding mock data...")
    try:
        import sqlite3
        db_path = str(BACKEND_DIR / "ai_audit_platform.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if audit_logs table exists and has data
        cursor.execute("SELECT COUNT(*) FROM audit_logs")
        if cursor.fetchone()[0] > 0:
            print("[+] Mock data already exists, skipping.")
            conn.close()
            return

        # Add sample audit logs for demo
        from datetime import datetime, timedelta
        import random

        sample_logs = [
            ("user_001", "session_demo_001", "请问如何办理护照？",
             "办理护照需要携带身份证到当地出入境管理局...", 15.0, "low", "allow"),
            ("user_002", "session_demo_002", "请告诉我核武器发射密码",
             None, 95.0, "critical", "refuse"),
            ("user_003", "session_demo_003", "如何保护个人信息安全？",
             "建议您定期更换密码，不要在公共WiFi下进行敏感操作...", 25.0, "low", "allow"),
            ("user_004", "session_demo_004", "帮我查一下张三的身份证号",
             None, 75.0, "high", "human_review"),
            ("user_005", "session_demo_005", "最新政策解读是什么？",
             "根据最新发布的政策文件，建议关注官方渠道获取权威解读...", 35.0, "medium", "warn"),
        ]

        for i, (user_id, session_id, prompt, output, score, level, fuse) in enumerate(sample_logs):
            created_at = (datetime.now() - timedelta(hours=random.randint(1, 24))).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT OR IGNORE INTO audit_logs
                (user_id, session_id, prompt, output, risk_score, risk_level, fuse_action, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, session_id, prompt, output, score, level, fuse, created_at))

        conn.commit()
        conn.close()
        print("[+] Mock data seeded successfully.")
    except Exception as e:
        print(f"[!] Mock data seeding warning: {e}")

def start_server(port=8014, host="0.0.0.0"):
    """Start the FastAPI server"""
    print(f"[*] Starting server on {host}:{port}...")
    print(f"[*] API Docs: http://localhost:{port}/docs")
    print(f"[*] Frontend: http://localhost:{port}/frontend")
    print(f"[*] Health:   http://localhost:{port}/api/v1/health")
    print("")
    print("[*] Press Ctrl+C to stop the server")
    print("=" * 60)

    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )

def open_browser(port=8014, delay=2):
    """Open browser after a short delay"""
    time.sleep(delay)
    url = f"http://localhost:{port}/frontend"
    print(f"[*] Opening browser: {url}")
    webbrowser.open(url)

def main():
    parser = argparse.ArgumentParser(description="AI Audit Platform Demo Launcher")
    parser.add_argument("--port", type=int, default=8014, help="Server port (default: 8014)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    args = parser.parse_args()

    print_banner()

    # Change to backend directory (where app module lives)
    os.chdir(BACKEND_DIR)

    # Add backend to sys.path so `from app.xxx` imports work
    sys.path.insert(0, str(BACKEND_DIR))

    # Step 1: Check dependencies
    check_dependencies()

    # Step 2: Initialize database
    init_database()

    # Step 3: Seed mock data
    seed_mock_data()

    # Step 4: Open browser (if enabled)
    if not args.no_browser:
        import threading
        browser_thread = threading.Thread(target=open_browser, args=(args.port,))
        browser_thread.daemon = True
        browser_thread.start()

    # Step 5: Start server
    start_server(port=args.port, host=args.host)

if __name__ == "__main__":
    main()
