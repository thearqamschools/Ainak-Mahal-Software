"""Offline backup, reconciliation and printable receipt helpers.
No network access; standard-library only.
"""
from pathlib import Path
from datetime import datetime
from html import escape
import sqlite3


def verified_backup(store, directory):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    stamp=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    dest=directory/f'ainak_mahal_{stamp}.sqlite3'
    store.backup(dest)
    with sqlite3.connect(dest) as conn:
        if conn.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
            dest.unlink(missing_ok=True)
            raise RuntimeError('Backup integrity check failed')
    return dest


def reconcile_stock(conn):
    """Opening stock + movements must equal current stock for all tracked SKUs."""
    return conn.execute('''SELECT p.id,p.sku,p.qty,COALESCE(SUM(m.delta),0) tracked
        FROM products p LEFT JOIN stock_movements m ON m.product_id=p.id
        GROUP BY p.id HAVING p.qty != tracked ORDER BY p.id''').fetchall()


def reconcile_payments(conn):
    """Check sale paid amounts against payment rows (refunds reported separately)."""
    return conn.execute('''SELECT s.id,s.paid,COALESCE(SUM(cp.amount),0) recorded
        FROM sales s LEFT JOIN customer_payments cp ON cp.sale_id=s.id
        GROUP BY s.id HAVING ABS(s.paid-recorded)>0.009 ORDER BY s.id''').fetchall()


def invoice_html(conn,sale_id,shop_name='AINAK MAHAL',shop_address='Millat Chowk, Faisalabad'):
    sale=conn.execute('''SELECT s.id,s.date,s.total,s.paid,c.name,c.phone
        FROM sales s LEFT JOIN customers c ON c.id=s.customer_id WHERE s.id=?''',(sale_id,)).fetchone()
    if sale is None:raise ValueError('Invoice not found')
    rows=conn.execute('''SELECT p.name,si.qty,si.price FROM sale_items si
        JOIN products p ON p.id=si.product_id WHERE si.sale_id=? ORDER BY si.id''',(sale_id,)).fetchall()
    tr=''.join('<tr><td>{}</td><td>{}</td><td>{:.2f}</td><td>{:.2f}</td></tr>'.format(escape(str(name)),int(qty),price,qty*price) for name,qty,price in rows)
    num,date,total,paid,name,phone=sale
    return '''<!doctype html><html><head><meta charset="utf-8"><title>Invoice {}</title>
    <style>body{{font:14px Arial,sans-serif;max-width:760px;margin:25px auto;color:#222}}h1{{margin-bottom:3px}}table{{width:100%;border-collapse:collapse;margin:22px 0}}td,th{{padding:9px;border-bottom:1px solid #ddd;text-align:left}}.right{{text-align:right}}@media print{{button{{display:none}}}}</style></head><body>
    <h1>{}</h1><div>{}</div><hr><div>Invoice #{} | {}</div><div>Customer: {} | Phone: {}</div>
    <table><thead><tr><th>Item</th><th>Qty</th><th>Unit Price (PKR)</th><th>Amount (PKR)</th></tr></thead><tbody>{}</tbody></table>
    <div class="right"><b>Total: PKR {:.2f}</b><p>Paid: PKR {:.2f}</p><p>Balance: PKR {:.2f}</p></div>
    <p>Thank you for shopping at Ainak Mahal.</p><button onclick="window.print()">Print</button></body></html>'''.format(num,escape(shop_name),escape(shop_address),num,escape(str(date)),escape(str(name or 'Walk-in')),escape(str(phone or '')),tr,total,paid,total-paid)


def export_invoice(conn,sale_id,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    path=directory/f'invoice_{int(sale_id)}.html'
    path.write_text(invoice_html(conn,sale_id),encoding='utf-8')
    return path
