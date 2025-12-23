import sqlite3

print('=== D:\\Front_Bier\\bierpass.db ===')
conn = sqlite3.connect('bierpass.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM beverages')
count = cur.fetchone()[0]
print(f'Bebidas: {count}')
conn.close()

print('\n=== D:\\Front_Bier\\saas-backend\\bierpass.db ===')
conn = sqlite3.connect('saas-backend/bierpass.db')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM beverages')
count = cur.fetchone()[0]
print(f'Bebidas: {count}')
conn.close()
