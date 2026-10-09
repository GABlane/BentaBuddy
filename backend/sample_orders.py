"""Explicitly requested sample orders for the live workspace; no payment claims."""
import json
from datetime import datetime, timedelta, timezone
from backend.business import ensure_catalog


def seed_sample_orders(db):
    timestamp = datetime.now(timezone(timedelta(hours=8)))
    created = timestamp.isoformat(timespec='seconds')
    specs = {
        'gadgets': [('Ana', [('cable', 2)], 0, '10:00'),
                    ('Marco', [('earbuds', 1)], 0, '14:00'),
                    ('Bea', [('phone', 1), ('setup', 1)], 1, '11:00')],
        'staycation': [('Lia', [('studio', 2)], 0, '14:00'),
                       ('Carlo', [('family', 1)], 1, '14:00'),
                       ('Nina', [('guest', 2), ('cleaning', 1)], 0, '15:00')],
    }
    numbers = [json.loads(r['payload']).get('number', '') for r in db.execute('SELECT payload FROM orders')]
    next_number = max([int(n[3:]) for n in numbers if n.startswith('BB-') and n[3:].isdigit()] or [1000]) + 1
    count = 0
    for kind, examples in specs.items():
        ensure_catalog(db, kind)
        for index, (name, requested, offset, due_time) in enumerate(examples):
            key = 'o_sample_' + kind + '_' + str(index)
            if db.execute('SELECT 1 FROM orders WHERE id=?', (key,)).fetchone():
                continue
            items = []
            for slug, quantity in requested:
                product_id = 'p_' + kind + '_starter_' + slug
                product = json.loads(db.execute('SELECT payload FROM products WHERE id=?', (product_id,)).fetchone()['payload'])
                items.append(dict(product_id=product_id, name=product['name'], emoji=product['emoji'],
                                  quantity=quantity, base_quantity=quantity, unit=product['unit'],
                                  price_cents=product['price_cents'], line_total=quantity*product['price_cents']))
            customer = dict(id='c_sample_'+kind+'_'+str(index), name='Sample · '+name,
                            is_demo=False, is_sample=True, business_kind=kind, source='sample', contact='', created_at=created)
            order = dict(id=key, number='BB-'+str(next_number), customer_id=customer['id'], customer_name=customer['name'],
                         business_kind=kind, is_demo=False, is_sample=True, items=items,
                         due_date=(timestamp+timedelta(days=offset)).date().isoformat(), due_time=due_time,
                         method='pickup', address='', notes='Sample order for walkthrough. No actual customer purchase or payment.' +
                         (' Accommodation rates are sample quotes; no room availability or booking is confirmed.' if kind=='staycation' else ''),
                         state='confirmed', fulfillment='queued', version=1, payments=[], fulfilled_at=None, created_at=created)
            for table, value in [('customers', customer), ('orders', order)]:
                db.execute('INSERT INTO '+table+'(id,payload) VALUES (?,?)', (value['id'], json.dumps(value, ensure_ascii=False)))
            next_number += 1
            count += 1
    return count
