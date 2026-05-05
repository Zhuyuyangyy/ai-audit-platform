import sqlite3
conn = sqlite3.connect('D:/ZYY Project/ai-audit-platform/backend/ai_audit_platform.db')
cur = conn.cursor()

cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [t[0] for t in cur.fetchall()]
print('tables:', tables)

cur.execute('''
CREATE TABLE IF NOT EXISTS document_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    embedding_id TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
''')

chunks_data = [
    (3, '处理个人信息应当遵循合法、正当、必要和诚信原则，不得通过误导、欺诈等不正当方式处理个人信息。', 0),
    (3, '处理个人信息应当取得个人的同意，并且应当明示处理个人信息的目的、方式和范围。', 1),
    (3, '个人信息的收集、存储、使用、传输、提供、公开等行为应当符合法律法规的规定。', 2),
    (3, '处理敏感个人信息应当取得个人的单独同意，并且应当加强保护措施。', 3),
    (3, '个人信息保护原则：合法性、正当性、必要性、诚信性、目的限制、数据最小化。', 4),
    (4, '生成式人工智能服务提供者应当加强内容护栏建设，防止出现违法和不良信息。', 0),
    (4, '生成式人工智能服务提供者应当对数据进行分类管理，采取相应的安全保护措施。', 1),
    (1, '网络运营者收集、使用个人信息，应当遵循合法、正当、必要原则。', 0),
    (2, '数据处理者应当采取合法、正当的方式收集数据，不得损害国家安全、公共利益。', 0),
]
for doc_id, text, idx in chunks_data:
    cur.execute('INSERT INTO document_chunks (document_id, chunk_text, chunk_index) VALUES (?, ?, ?)', (doc_id, text, idx))

conn.commit()

cur.execute("SELECT id, chunk_text FROM document_chunks WHERE document_id = 3")
chunks = cur.fetchall()
print('PIPL chunks available:', len(chunks))
for c in chunks:
    print(' ', c[0], ':', c[1][:60])
conn.close()