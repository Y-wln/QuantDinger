from app.utils.db import get_db_connection
db = get_db_connection()
cur = db.cursor()
cur.execute('SELECT COUNT(*) FROM qd_exchange_credentials')
print('count:', cur.fetchone()[0])
cur.close()
