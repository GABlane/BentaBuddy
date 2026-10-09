"""Business-specific validation; confirmed accommodation stays reserve one catalog unit."""
import json
from datetime import date
from fastapi import HTTPException


def stay_dates(check_in, check_out):
    try:
        start, end = date.fromisoformat(check_in), date.fromisoformat(check_out)
    except (ValueError, TypeError):
        raise HTTPException(400, 'Enter valid check-in and check-out dates.')
    nights = (end-start).days
    if not 1 <= nights <= 365:
        raise HTTPException(400, 'Check-out must be after check-in, within 365 nights.')
    return nights


def conflicts(db, reservation, exclude=None):
    stay_dates(reservation['check_in'], reservation['check_out'])
    result = []
    for row in db.execute('SELECT payload FROM orders'):
        order = json.loads(row['payload'])
        other = order.get('reservation')
        if (order['id'] == exclude or not other or order['state']=='canceled'
                or order['fulfillment'] not in ('preparing','ready')):
            continue
        if (other['product_id']==reservation['product_id'] and
                reservation['check_in'] < other['check_out'] and other['check_in'] < reservation['check_out']):
            result.append(order['number'])
    return result


def check_available(db, reservation, exclude=None):
    blocked = conflicts(db, reservation, exclude)
    if blocked:
        raise HTTPException(409, 'This accommodation overlaps a confirmed booking: '+', '.join(blocked))


def reservation_items(db, items, reservation):
    nights = stay_dates(reservation['check_in'], reservation['check_out'])
    row = db.execute('SELECT payload FROM products WHERE id=?', (reservation['product_id'],)).fetchone()
    product = json.loads(row['payload']) if row else None
    if not product or product.get('business_kind')!='staycation' or product.get('offering_type')!='accommodation' or product['unit']!='night' or not product['active']:
        raise HTTPException(400, 'Choose an active accommodation priced per night.')
    remaining = []
    for item in items:
        entry = db.execute('SELECT payload FROM products WHERE id=?', (item.get('product_id'),)).fetchone()
        if entry and json.loads(entry['payload']).get('offering_type')=='accommodation':
            continue
        remaining.append(item)
    return [dict(product_id=product['id'], quantity=nights, unit='night')] + remaining
