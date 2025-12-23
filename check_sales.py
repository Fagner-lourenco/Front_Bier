#!/usr/bin/env python
import sqlite3

conn = sqlite3.connect('saas-backend/bierpass.db')
cursor = conn.cursor()

print('='*70)
print('VENDAS REGISTRADAS (ultimas 5)')
print('='*70)
cursor.execute('SELECT id, machine_id, volume_ml, total_value, status, created_at FROM sales ORDER BY created_at DESC LIMIT 5')
for row in cursor.fetchall():
    print(f'ID: {str(row[0])[:8]}... | Machine: {str(row[1])[:8]}... | Volume: {row[2]}ml | Value: R${row[3]:.2f} | {row[4]} | {row[5]}')

print()
print('='*70)
print('CONSUMOS REGISTRADOS (ultimas 5)')
print('='*70)
cursor.execute('SELECT id, sale_id, machine_id, ml_served, ml_authorized, status, created_at FROM consumptions ORDER BY created_at DESC LIMIT 5')
for row in cursor.fetchall():
    print(f'ID: {str(row[0])[:8]}... | Sale: {str(row[1])[:8]}... | Machine: {str(row[2])[:8]}... | {row[3]}/{row[4]}ml | {row[5]} | {row[6]}')

print()
print('='*70)
print('RESUMO')
print('='*70)
cursor.execute('SELECT COUNT(*) FROM sales')
print(f'Total de Vendas: {cursor.fetchone()[0]}')
cursor.execute('SELECT COUNT(*) FROM consumptions')
print(f'Total de Consumos: {cursor.fetchone()[0]}')
cursor.execute('SELECT SUM(total_value) FROM sales')
total = cursor.fetchone()[0] or 0
print(f'Valor Total Vendido: R${total:.2f}')

conn.close()

