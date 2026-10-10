import unittest
from backend.customer_replies import reply_choices, reply_request, status_text


def order(**changes):
    value=dict(id='owned',number='BB-1001',business_kind='bakery',state='confirmed',fulfillment='queued',method='pickup',due_date='2026-10-10',due_time='10:00',items=[dict(name='Pandesal',quantity=2,unit='dozen')])
    value.update(changes)
    return value


class GroundedReplies(unittest.TestCase):
    def test_business_status_words_are_authoritative_and_distinct(self):
        for kind,word in [('bakery','kitchen'),('gadgets','pinapack'),('general','ginagawa')]:
            self.assertIn(word,status_text(order(business_kind=kind,fulfillment='preparing')))
        self.assertIn('dispatch',status_text(order(fulfillment='ready',method='delivery')))
        self.assertIn('Wala pang live ETA',status_text(order(fulfillment='out_for_delivery')))
        self.assertIn('canceled',status_text(order(state='canceled')))

    def test_pending_booking_never_claims_confirmation(self):
        reservation=dict(status='pending',check_in='2026-11-20',check_out='2026-11-22',guests=2)
        value=order(business_kind='staycation',reservation=reservation)
        self.assertIn('hindi pa confirmed',status_text(value))
        for state,word in [('confirmed','Confirmed na'),('checked_in','checked in'),('completed','completed')]:
            value['reservation']['status']=state
            self.assertIn(word,status_text(value))

    def test_explicit_reference_excludes_other_status_choices(self):
        choices=reply_choices('Status BB-9999?', [order()])
        self.assertEqual(set(choices),{'receipt','clarify'})
        choices=reply_choices('Status bb-1001?', [order(),order(id='other',number='BB-1002')])
        self.assertIn('status:owned',choices)
        self.assertNotIn('status:other',choices)

    def test_both_runtimes_constrain_reply_ids_and_disable_thinking(self):
        for runtime in ('llamacpp','ollama'):
            _,body,choices=reply_request('Status?', [order()],runtime,'local-model')
            schema=body['response_format']['json_schema']['schema'] if runtime=='llamacpp' else body['format']
            self.assertEqual(set(schema['properties']['reply_id']['enum']),set(choices))
            self.assertFalse(schema['additionalProperties'])
            self.assertEqual(body['model'],'local-model')
