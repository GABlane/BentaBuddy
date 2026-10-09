"""Remove fictional activity while retaining the business catalog and real records."""
import json


def clear_demo(db):
    records = {table: [json.loads(row['payload']) for row in db.execute('SELECT payload FROM '+table)]
               for table in ('orders', 'customers', 'conversations', 'jobs')}
    deleted = {table: {r['id'] for r in records[table] if r.get('is_demo') or r.get('source') == 'demo'}
               for table in records}
    deleted['jobs'].update(r['id'] for r in records['jobs']
                           if r.get('conversation_id') in deleted['conversations'] or r.get('order_id') in deleted['orders'])
    referenced_customers = {r.get('customer_id') for table in ('orders', 'conversations')
                            for r in records[table] if r['id'] not in deleted[table]}
    deleted['customers'] -= referenced_customers
    for order_id in deleted['orders']:
        db.execute('DELETE FROM events WHERE order_id=?', (order_id,))
    for table, ids in deleted.items():
        db.executemany('DELETE FROM '+table+' WHERE id=?', [(key,) for key in ids])
    return {table: len(ids) for table, ids in deleted.items()}
