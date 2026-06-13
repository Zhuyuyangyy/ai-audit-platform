# Database initialization and session management
import sqlite3
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
import os

_DB_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DB_PATH = os.path.normpath(os.path.join(_DB_DIR, "..", "..", "ai_audit_platform.db"))
_DATABASE_FILE = os.environ.get("DATABASE_PATH", _DEFAULT_DB_PATH)
DATABASE_URL = f"sqlite:///{_DATABASE_FILE}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database with all tables"""
    # Create tables using raw SQL first to avoid dependency on models
    conn = sqlite3.connect(_DATABASE_FILE)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id TEXT UNIQUE NOT NULL,
            rule_type TEXT NOT NULL,
            description TEXT,
            severity TEXT NOT NULL,
            penalty TEXT,
            enabled INTEGER DEFAULT 1
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            prompt TEXT,
            output TEXT,
            risk_score REAL DEFAULT 0,
            risk_level TEXT DEFAULT 'safe',
            fuse_action TEXT DEFAULT 'allow',
            prompt_rules TEXT,
            output_rules TEXT,
            rag_trace TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS policy_documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            source TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rag_trace (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id INTEGER NOT NULL,
            claim TEXT,
            evidence TEXT,
            policy_doc_id INTEGER,
            created_at TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fuse_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            audit_id INTEGER NOT NULL,
            fuse_reason TEXT,
            action_taken TEXT,
            created_at TEXT NOT NULL
        )
    """)
    
    conn.commit()
    
    # Now seed default data
    _seed_rules(conn)
    
    conn.close()

def _seed_rules(conn):
    """Seed default compliance rules if not exists"""
    cursor = conn.cursor()
    
    # Check if rules already seeded
    cursor.execute("SELECT COUNT(*) FROM rules")
    if cursor.fetchone()[0] > 0:
        return
    
    default_rules = [
        ("RULE_AI_001", "secret_query", "涉密信息查询 - 检测用户是否试图查询敏感涉密信息", "critical", "拒绝回答并记录审计", 1),
        ("RULE_AI_002", "policy_mislead", "敏感政策误导 - 检测模型输出是否曲解国家政策", "critical", "拒绝输出并转人工审核", 1),
        ("RULE_AI_003", "privacy_leak_induce", "隐私数据泄露诱导 - 检测是否诱导泄露个人隐私", "high", "拒绝回答", 1),
        ("RULE_AI_004", "hallucination", "幻觉内容生成 - 检测输出内容是否有政策依据", "high", "标记并要求溯源", 1),
        ("RULE_AI_005", "unauthorized_answer", "越权回答 - 检测是否回答超出范围的问题", "medium", "部分屏蔽", 1),
        ("RULE_AI_006", "policy_error_interpret", "政策错误解读 - 检测对政策的错误理解", "high", "拒绝输出", 1),
        ("RULE_AI_007", "leak_induce", "诱导泄密问题 - 检测社会工程学类诱导泄密", "critical", "拒绝并警告", 1),
    ]
    
    cursor.executemany(
        "INSERT OR IGNORE INTO rules (rule_id, rule_type, description, severity, penalty, enabled) VALUES (?, ?, ?, ?, ?, ?)",
        default_rules
    )
    
    # Seed sample policy documents
    policy_docs = [
        ("中华人民共和国网络安全法", "为了保障网络安全，维护网络空间主权、国家安全、社会公共利益，保护公民、法人和其他组织的合法权益，促进经济社会信息化健康发展，制定本法。", "全国人大常委会", "2017-06-01"),
        ("中华人民共和国数据安全法", "为了规范数据处理活动，保障数据安全，促进数据开发利用，保护个人、组织的合法权益，维护国家主权、安全和发展利益，制定本法。", "全国人大常委会", "2021-08-20"),
        ("中华人民共和国个人信息保护法", "为了保护个人信息权益，规范个人信息处理活动，促进个人信息合理利用，制定本法。", "全国人大常委会", "2021-08-20"),
        ("生成式人工智能服务管理暂行办法", "为了促进生成式人工智能健康发展和规范应用，维护国家安全和社会公共利益，保护公民、法人和其他组织的合法权益，制定本办法。", "国家互联网信息办公室", "2023-07-10"),
    ]
    
    cursor.executemany(
        "INSERT OR IGNORE INTO policy_documents (title, content, source, created_at) VALUES (?, ?, ?, ?)",
        policy_docs
    )
    
    conn.commit()