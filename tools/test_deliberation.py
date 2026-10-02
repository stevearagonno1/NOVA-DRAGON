import json
import unittest
import threading
from agent_deliberation import object_response, deliberate, vote_response, unanimous, DeliberationContractError, evidence_packet
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
        result,counts=deliberate('task','context',[],call,'rules',['proposer','auditor','challenger'])
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

    def test_all_three_initial_reviewers_start_together(self):
        barrier=threading.Barrier(3)
        def call(system,user,slot):
            payload=json.loads(user)
            if slot<3 and 'shared_proposal' not in payload:
                barrier.wait(timeout=2)
                return 'finding'
            if slot==3:return json.dumps({'proposal':'proposal'})
            if 'shared_proposal' in payload:
                return json.dumps({'proposal_id':payload['shared_proposal']['proposal_id'],
                                   'accept_shared_proposal':True,'blocking_objections':[]})
            return 'summary'
        _,counts=deliberate('task','',[],call,'rules',['a','b','c'])
        self.assertTrue(counts['consensus'])

    def test_round_cap_cannot_be_bypassed(self):
        for cap in [0,4,True]:
            with self.assertRaises(ValueError):
                deliberate('task','',[],lambda *args:'unused','rules',['a','b','c'],max_rounds=cap)

    def test_pinned_excerpts_replace_full_files_after_independent_phase(self):
        sources=[{'path':'CONSTITUTION.md','commit':'fixed','blob_sha':'blob',
                  'content':'rule\nrequired step\ncontext\n'+('unrelated material\n'*2000)}]
        calls=[]
        def call(system,user,slot):
            payload=json.loads(user); calls.append((slot,payload))
            if slot==3:return json.dumps({'proposal':'Use required step CONSTITUTION.md:L2-L2 @fixed'})
            if 'shared_proposal' in payload:
                return json.dumps({'proposal_id':payload['shared_proposal']['proposal_id'],
                                   'accept_shared_proposal':True,'blocking_objections':[]})
            if slot==4:return 'summary'
            return 'Required step: CONSTITUTION.md:L2-L2 @fixed'
        _,counts=deliberate('task','binding context',sources,call,'rules',['a','b','c'])
        self.assertTrue(counts['consensus'])
        for slot,payload in calls:
            material=payload.get('material',payload)
            self.assertEqual(material['lead_context'],'binding context')
            if slot<3 and 'shared_proposal' not in payload:
                self.assertIn('L2003: unrelated material',material['sources'][0]['content'])
            else:
                self.assertNotIn('sources',material)
                self.assertEqual(material['source_excerpts'][0]['content'],'L1: rule\nL2: required step\nL3: context')
                self.assertEqual(material['source_excerpts'][0]['commit'],'fixed')
                self.assertLess(len(json.dumps(payload)),5000)
        self.assertEqual(sources[0]['content'].splitlines()[0],'rule')

    def test_evidence_budget_and_invalid_ranges_are_explicit(self):
        source={'path':'README.md','content':'one\ntwo\n'+('x'*17000)}
        for citation in ['README.md:L99-L99','README.md:L3-L3']:
            packet=evidence_packet([source],[citation])
            self.assertFalse(packet['evidence_complete'])
            self.assertEqual(packet['source_excerpts'],[])
            self.assertEqual(packet['unavailable_citations'],[citation])
        self.assertFalse(evidence_packet([source],['uncited claim'])['evidence_complete'])
        self.assertTrue(evidence_packet([],[])['evidence_complete'])

    def test_uncited_source_claims_cannot_become_validated_consensus(self):
        def call(system,user,slot):
            payload=json.loads(user)
            if slot==3:return json.dumps({'proposal':'unsupported proposal'})
            if 'shared_proposal' in payload:
                return json.dumps({'proposal_id':payload['shared_proposal']['proposal_id'],
                                   'accept_shared_proposal':True,'blocking_objections':[]})
            return 'uncited finding'
        result,counts=deliberate('task','',[{'path':'README.md','content':'evidence'}],
                                 call,'rules',['a','b','c'])
        self.assertFalse(counts['consensus'])
        self.assertEqual(counts['discussion_rounds'],3)
        self.assertIn('لا يوجد قرار جماعي نهائي',result)

if __name__=='__main__':unittest.main()
