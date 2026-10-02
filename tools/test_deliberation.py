import json
import unittest
from agent_deliberation import object_response, deliberate, vote_response, unanimous, DeliberationContractError
from agent_council_transport import safe_reason

class DeliberationTests(unittest.TestCase):
    def run_discussion(self, agree_from=1, blocking=False):
        calls=[]
        def call(system,user,slot):
            payload=json.loads(user); calls.append((slot,payload))
            if slot==3:
                return json.dumps({'proposal':'Evidence-backed proposal '+str(len(payload['previous_votes']))})
            if 'shared_proposal' in payload:
                accept=payload['round']>=agree_from or slot!=2
                objections=['source gap from reviewer 2'] if (not accept or blocking and slot==2) else []
                return json.dumps({'proposal_id':payload['shared_proposal']['proposal_id'],
                    'accept_shared_proposal':accept,'blocking_objections':objections,'revision':'fix evidence gap' if objections else ''})
            if slot==4: return 'ملخص التوصية والأدلة'
            return 'finding '+str(slot)
        result,counts=deliberate('task','context',[{'content':'evidence'}],call,'rules',['proposer','auditor','challenger'])
        return result,counts,calls

    def test_unanimous_first_round_stops_early(self):
        result,counts,calls=self.run_discussion()
        self.assertEqual(counts['model_requests'],8)
        self.assertEqual(counts['discussion_rounds'],1)
        self.assertTrue(counts['consensus'])
        self.assertIn('اتفق المراجعون الثلاثة',result)
        self.assertEqual([slot for slot,_ in calls].count(4),1)

    def test_second_round_shares_others_objections(self):
        result,counts,calls=self.run_discussion(agree_from=2)
        self.assertEqual(counts['model_requests'],12)
        self.assertTrue(counts['consensus'])
        second=[payload for slot,payload in calls if payload.get('round')==2]
        self.assertEqual(len(second),3)
        for payload in second:
            self.assertEqual(payload['reviewer_findings'],['finding 0','finding 1','finding 2'])
            self.assertEqual(payload['previous_votes'][2]['blocking_objections'],['source gap from reviewer 2'])
            self.assertIn('proposal_id',payload['shared_proposal'])

    def test_persistent_dissent_is_not_forced_consensus(self):
        result,counts,calls=self.run_discussion(agree_from=99)
        self.assertEqual(counts['model_requests'],16)
        self.assertEqual(counts['discussion_rounds'],3)
        self.assertFalse(counts['consensus'])
        self.assertIn('لا يوجد قرار جماعي نهائي',result)
        self.assertEqual(calls[-1][1]['outcome']['rounds'][-1]['votes'][2]['accept_shared_proposal'],False)

    def test_acceptance_with_blocking_objection_is_not_consensus(self):
        _,counts,_=self.run_discussion(blocking=True)
        self.assertFalse(counts['consensus'])
        self.assertEqual(counts['model_requests'],16)

    def test_invalid_vote_never_counts_as_agreement(self):
        for value in [
            {'proposal_id':'wrong','accept_shared_proposal':True,'blocking_objections':[]},
            {'proposal_id':'id','accept_shared_proposal':'true','blocking_objections':[]},
            {'proposal_id':'id','accept_shared_proposal':True,'blocking_objections':'none'},
        ]:
            with self.assertRaises(DeliberationContractError):vote_response(json.dumps(value),'id')
        self.assertEqual(safe_reason(DeliberationContractError('secret'))['code'],'deliberation_invalid_response')

    def test_three_valid_votes_required(self):
        vote={'accept_shared_proposal':True,'blocking_objections':[]}
        self.assertFalse(unanimous([vote,vote]))

    def test_one_valid_object_with_explanatory_wrapper_is_accepted(self):
        vote={'proposal_id':'id','accept_shared_proposal':False,'blocking_objections':['evidence gap'],'revision':''}
        text='Here is my vote:\n```json\n'+json.dumps(vote)+'\n```\nEnd.'
        self.assertFalse(vote_response(text,'id')['accept_shared_proposal'])

    def test_ambiguous_duplicate_truncated_and_plain_prose_are_rejected(self):
        cases=['I agree.', '{"proposal":"one"} {"proposal":"two"}',
               '{"proposal":"one","proposal":"two"}',
               '{"outer":{"proposal":"nested"}', '{"proposal":"unfinished']
        for text in cases:
            with self.assertRaises(DeliberationContractError):object_response(text)

    def test_round_cap_cannot_be_bypassed(self):
        for cap in [0,4,True]:
            with self.assertRaises(ValueError):
                deliberate('task','',[],lambda *args:'unused','rules',['a','b','c'],max_rounds=cap)

if __name__=='__main__':unittest.main()
