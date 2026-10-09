"""Explicitly requested sample inbox conversations for each business type. Customers are fictional."""
import json
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=8))


def _samples(today):
    day = lambda n: (today + timedelta(days=n)).strftime('%b %-d')
    # (customer, [(minutes before now, message text), ...]) — Taglish, with corrections and inquiries mixed in.
    return {
        'bakery': [
            ('Joy Villanueva', [(180, 'Hi ate! Pa-order po 3 dozen cheese pandesal for bukas, pickup 7am po.'),
                                (170, 'Tapos 1 chocolate cake din po. Pang-birthday ng anak ko, pakisulat "Happy 7th Birthday, Ella" 🎂')]),
            ('Ramon Tan', [(95, 'Magkano po ensaymada? Pwede po ba i-deliver sa Kamuning?')]),
            ('Liza Mercado', [(60, 'Good morning! Order po 2 banana loaf, pickup bukas 10am.'),
                              (40, 'Ay sorry po, gawin na lang 3 banana loaf. 11am na lang po pickup.')]),
            ('Carlo Bautista', [(20, 'Pa-order po 12 cinnamon rolls at 1 dozen chocolate chip cookies. Deliver po sa 12 Mabini St., Brgy. San Roque, bukas 3pm. GCash na lang po bayad.')]),
        ],
        'gadgets': [
            ('Paolo Reyes', [(200, 'Boss, available pa po yung wireless earbuds? Pa-reserve po 1, kulay black.'),
                             (190, 'Pickup ko po bukas 2pm.')]),
            ('Trisha Gomez', [(120, 'Hello po! Order po 2 USB-C cable, pa-deliver po sa Cubao. Magkano po shipping?')]),
            ('Mark Santiago', [(75, 'Bibili po ako ng smartphone, yung 128GB po sana. Pwede rin po ba i-setup niyo na? Pickup bukas 11am.'),
                               (50, 'Pwede po bang 3pm na lang?')]),
            ('Bea Lim', [(15, 'Meron po kayong charger para sa iPhone 15? Fast charging po sana.')]),
        ],
        'staycation': [
            ('Andrea Cruz', [(240, f'Hi! Available po ba yung studio for {day(14)}–{day(16)}? 2 adults po kami.'),
                             (230, 'Pwede rin po ba early check-in?')]),
            ('Dizon family', [(130, f'Good day po! Family room po sana for 4 adults, {day(22)} to {day(24)}. May extra guest charge po ba kung may kasama kaming isa pa?')]),
            ('Kevin Ong', [(70, f'Pa-book po studio, {day(7)} to {day(8)}, 1 night lang. Pwede pa-add ng cleaning service sa checkout?'),
                           (45, f'Correction po, {day(8)} to {day(9)} na lang.')]),
        ],
        'general': [
            ('Grace Aquino', [(150, 'Hello po, pa-order po 5 pieces, pickup bukas 10am.')]),
            ('Dennis Lopez', [(90, 'Available po ba kayo for a service this Saturday morning? Sa Marikina po location.')]),
            ('Mia Fernandez', [(30, 'Pa-order po 2 pieces, pa-deliver sa Pasig.'),
                               (25, 'Ay gawin niyo na lang palang 4 pieces. Salamat po!')]),
        ],
    }


def seed_sample_conversations(db):
    """Add each sample conversation once. Existing conversations and orders are never changed."""
    now = datetime.now(TZ)
    count = 0
    for kind, conversations in _samples(now.date()).items():
        for index, (name, messages) in enumerate(conversations):
            key = 'conv_sample_' + kind + '_' + str(index)
            if db.execute('SELECT 1 FROM conversations WHERE id=?', (key,)).fetchone():
                continue
            customer = dict(id='c_sample_msg_' + kind + '_' + str(index), name=name, source='sample', contact='',
                            is_demo=False, is_sample=True, business_kind=kind, created_at=now.isoformat(timespec='seconds'))
            conversation = dict(id=key, customer_id=customer['id'], customer_name=name, source='sample',
                                is_demo=False, is_sample=True, business_kind=kind, linked_order_id=None,
                                created_at=(now - timedelta(minutes=messages[0][0])).isoformat(timespec='seconds'),
                                messages=[dict(id=key + '_m' + str(n), text=text,
                                               created_at=(now - timedelta(minutes=ago)).isoformat(timespec='seconds'))
                                          for n, (ago, text) in enumerate(messages)],
                                version=len(messages))
            for table, value in [('customers', customer), ('conversations', conversation)]:
                db.execute('INSERT OR IGNORE INTO ' + table + '(id,payload) VALUES (?,?)', (value['id'], json.dumps(value, ensure_ascii=False)))
            count += 1
    return count


def remove_sample_conversations(db):
    """Remove sample conversations and their AI jobs. Orders you confirmed from them are kept, with their customers."""
    conversations = [r['id'] for r in db.execute("SELECT id FROM conversations WHERE id LIKE 'conv_sample_%'")]
    for row in db.execute('SELECT id,payload FROM jobs').fetchall():
        if json.loads(row['payload']).get('conversation_id') in conversations:
            db.execute('DELETE FROM jobs WHERE id=?', (row['id'],))
    db.executemany('DELETE FROM conversations WHERE id=?', [(key,) for key in conversations])
    used = {json.loads(r['payload']).get('customer_id') for r in db.execute('SELECT payload FROM orders')}
    customers = [r['id'] for r in db.execute("SELECT id FROM customers WHERE id LIKE 'c_sample_msg_%'") if r['id'] not in used]
    db.executemany('DELETE FROM customers WHERE id=?', [(key,) for key in customers])
    return len(conversations)
