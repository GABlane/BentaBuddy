import json
import sqlite3
import unittest
from backend.demo_data import clear_demo


class DemoCleanup(unittest.TestCase):
    def test_removes_demo_activity_and_preserves_live_records_and_catalog(self):
        with sqlite3.connect(':memory:') as db:
            db.row_factory = sqlite3.Row
            for table in ('orders','customers','conversations','jobs','products'):
                db.execute('CREATE TABLE '+table+' (id TEXT PRIMARY KEY,payload TEXT)')
            db.execute('CREATE TABLE events (id TEXT,order_id TEXT)')
            records = {
                'orders':[{'id':'demo_order','is_demo':True,'customer_id':'demo_customer'}, {'id':'real_order','is_demo':False,'customer_id':'real_customer'}],
                'customers':[{'id':'demo_customer','is_demo':True}, {'id':'real_customer','is_demo':False}],
                'conversations':[{'id':'demo_chat','is_demo':True,'customer_id':'demo_customer'}, {'id':'real_chat','is_demo':False,'customer_id':'real_customer'}],
                'jobs':[{'id':'demo_job','conversation_id':'demo_chat'}, {'id':'real_job','conversation_id':'real_chat'}],
                'products':[{'id':'starter','sample_pricing':True,'active':True}],
            }
            for table, values in records.items():
                db.executemany('INSERT INTO '+table+' VALUES (?,?)', [(r['id'],json.dumps(r)) for r in values])
            db.executemany('INSERT INTO events VALUES (?,?)', [('e_demo','demo_order'),('e_real','real_order')])
            self.assertEqual(clear_demo(db), {'orders':1,'customers':1,'conversations':1,'jobs':1})
            for table in records:
                retained = [json.loads(r['payload']) for r in db.execute('SELECT payload FROM '+table)]
                self.assertEqual(retained, [records[table][-1]])
            self.assertEqual([r['id'] for r in db.execute('SELECT id FROM events')], ['e_real'])
            self.assertTrue(all(n==0 for n in clear_demo(db).values()))
