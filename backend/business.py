"""Local business branding. A theme is not a separate shop or booking engine."""
import json

KINDS = ('bakery', 'gadgets', 'staycation', 'general')


def business_profile(db):
    row = db.execute("SELECT value FROM settings WHERE key='business_profile'").fetchone()
    if row:
        return json.loads(row['value'])
    return {'kind': 'bakery', 'name': 'My business'}

# Starter prices are illustrative PHP amounts, not researched market prices.
STARTERS = {
    'gadgets': [
        ('phone', 'Smartphone', 'Phones', 'unit', '📱', 'product', ['phone', 'cellphone', 'cp']),
        ('cable', 'USB-C cable', 'Accessories', 'piece', '🔌', 'product', ['charging cable', 'type c cable', 'usb c']),
        ('earbuds', 'Wireless earbuds', 'Audio', 'set', '🎧', 'product', ['earbuds', 'wireless earphones']),
        ('setup', 'Device setup', 'Services', 'service', '🛠️', 'service', ['phone setup', 'device setup']),
    ],
    'staycation': [
        ('studio', 'Studio stay', 'Accommodations', 'night', '🏡', 'accommodation', ['studio', 'studio unit', 'studio room']),
        ('family', 'Family room stay', 'Accommodations', 'night', '🛏️', 'accommodation', ['family room', 'family stay']),
        ('guest', 'Additional guest', 'Guest extras', 'guest', '👥', 'service', ['extra guest', 'additional pax', 'extra person']),
        ('cleaning', 'Cleaning service', 'Services', 'service', '🧹', 'service', ['cleaning', 'housekeeping']),
    ],
    'general': [
        ('product', 'Your product', 'Products', 'piece', '📦', 'product', []),
        ('service', 'Your service', 'Services', 'service', '🤝', 'service', []),
    ],
}
STARTER_PRICES = {
    'gadgets': {'phone': 799900, 'cable': 15000, 'earbuds': 99900, 'setup': 30000},
    'staycation': {'studio': 250000, 'family': 450000, 'guest': 50000, 'cleaning': 60000},
    'general': {'product': 10000, 'service': 50000},
}

UNITS = ('piece', 'cake', 'loaf', 'tray', 'box', 'unit', 'set', 'service', 'session', 'night', 'stay', 'guest')
OFFERING_TYPES = ('product', 'service', 'accommodation')


def catalog_for(products, kind):
    return [p for p in products if p.get('business_kind', 'bakery') == kind]


def ensure_catalog(db, kind):
    for slug, name, category, unit, emoji, offering_type, aliases in STARTERS.get(kind, []):
        key = 'p_' + kind + '_starter_' + slug
        legacy = dict(id=key, business_kind=kind, name=name, category=category, unit=unit,
                      units={unit: 1}, emoji=emoji, offering_type=offering_type, aliases=aliases,
                      description='Suggested offering. Edit the details and price before enabling requests.',
                      price_cents=0, active=False)
        value = dict(legacy, description='Starter offering with an example price. Customize for your business.',
                     price_cents=STARTER_PRICES[kind][slug], active=True, sample_pricing=True)
        existing = db.execute('SELECT payload FROM products WHERE id=?', (key,)).fetchone()
        if not existing:
            db.execute('INSERT INTO products(id,payload) VALUES (?,?)', (key, json.dumps(value, ensure_ascii=False)))
        elif json.loads(existing['payload']) == legacy:
            # Upgrade only an untouched placeholder; never reset owner edits or disabled items.
            db.execute('UPDATE products SET payload=? WHERE id=?', (json.dumps(value, ensure_ascii=False), key))
