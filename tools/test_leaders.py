import json
import threading
import unittest
from agent_leaders import Workspace,coordinate_leaders,MAX_REQUESTS,final_report,failure_record,LeaderContractError

SOURCES=[{'path':'README.md','commit':'fixed','blob_sha':'blob','content':'first evidence\nsecond fact\nthird detail'}]
def finish(decision='approve',blockers=None,relation='equivalent'):
    return json.dumps({'action':'finish','summary':'finding README.md:L1-L2 @fixed',
                       'decision':decision,'blockers':blockers or [],'needs_consultation':False,'peer_relation':relation})

class LeaderTests(unittest.TestCase):
    def test_each_leader_uses_tools_and_shared_board_without_unneeded_consultation(self):
        barrier=threading.Barrier(2);calls=[];saved=[]
        def call(system,user,slot,deadline):
            payload=json.loads(user);calls.append((slot,payload))
            if slot==0:return 'final answer'
            if payload['step']==1:
                barrier.wait(timeout=1)
                return json.dumps({'action':'read','path':'README.md','start':1,'end':2})
            self.assertEqual(payload['recent_tool_results'][0]['result']['commit'],'fixed')
            self.assertIn('README.md:L1-L2',payload['workspace']['evidence'])
            return finish()
        result,counts=coordinate_leaders('task','',SOURCES,call,'rules',checkpoint=lambda *args:saved.append(args),require_tool=True)
        self.assertEqual(counts['model_requests'],5)
        self.assertEqual(counts['tool_steps'],2)
        self.assertEqual(counts['discussion_rounds'],0)
        self.assertFalse(counts['unresolved_disagreement'])
        self.assertEqual(len(saved[-1][0]),2)
        self.assertIn('README.md:L1-L2',saved[-1][2]['evidence'])

    def test_decision_conflict_triggers_one_targeted_consultation(self):
        calls=[]
        def call(system,user,slot,deadline):
            payload=json.loads(user);calls.append(payload)
            if slot==0:return 'final'
            if 'peer_report' in payload:
                self.assertNotEqual(payload['own_report']['decision'],payload['peer_report']['decision'])
                self.assertEqual(payload['evidence']['source_excerpts'][0]['commit'],'fixed')
                return finish('approve')
            return finish('approve' if slot==1 else 'reject')
        _,counts=coordinate_leaders('task','',SOURCES,call,'rules')
        self.assertEqual(counts['model_requests'],5)
        self.assertEqual(counts['discussion_rounds'],1)
        self.assertFalse(counts['unresolved_disagreement'])

    def test_persistent_dissent_stops_at_two_rounds_without_forcing_agreement(self):
        def call(system,user,slot,deadline):
            payload=json.loads(user)
            if slot==0:
                self.assertTrue(payload['unresolved_disagreement']);return 'dissent remains'
            return finish('approve' if slot==1 else 'reject',['source gap'] if slot==2 else [])
        result,counts=coordinate_leaders('task','',SOURCES,call,'rules')
        self.assertEqual(counts['discussion_rounds'],2)
        self.assertEqual(counts['model_requests'],7)
        self.assertIn('لا يُدّعى اتفاق نهائي',result)

    def test_consultation_failure_keeps_prior_findings(self):
        checkpoints=[]
        def call(system,user,slot,deadline):
            payload=json.loads(user)
            if slot==0:
                self.assertEqual(len(payload['leaders']),2);return 'partial audit'
            if 'peer_report' in payload and slot==2:raise TimeoutError('private provider message')
            return finish('approve' if slot==1 else 'reject')
        _,counts=coordinate_leaders('task','',SOURCES,call,'rules',checkpoint=lambda *args:checkpoints.append(args))
        self.assertTrue(counts['partial'])
        self.assertTrue(counts['unresolved_disagreement'])
        self.assertEqual(len(checkpoints[-1][0]),2)
        self.assertNotIn('private provider',json.dumps(checkpoints))

    def test_read_search_publish_are_scoped_and_literal(self):
        board=Workspace(SOURCES)
        self.assertEqual(board.execute(1,{'action':'search','query':'evidence'})['hits'][0]['line'],1)
        self.assertEqual(board.execute(1,{'action':'search','query':'.*'})['hits'],[])
        board.execute(1,{'action':'publish','note':'question with README.md:L1-L1'})
        self.assertIn('question',board.snapshot()['notes']['1'])
        for action in [{'action':'shell','command':'delete'}, {'action':'read','path':'keys.toml','start':1,'end':1},
                       {'action':'search','query':'test','path':'../README.md'},
                       {'action':'read','path':'README.md','start':True,'end':2},
                       {'action':'read','path':'README.md','start':1,'end':99}]:
            with self.assertRaises(ValueError):board.execute(1,action)

    def test_never_ending_tool_loop_is_bounded_and_cannot_block_successful_peer(self):
        def call(system,user,slot,deadline):
            if slot==0:return 'partial answer'
            if slot==1:return json.dumps({'action':'publish','note':'still checking'})
            return finish()
        _,counts=coordinate_leaders('task','',SOURCES,call,'rules')
        self.assertEqual(counts['completed_subagents'],1)
        self.assertTrue(counts['partial'])
        self.assertEqual(counts['tool_steps'],8)
        self.assertLessEqual(counts['model_requests'],MAX_REQUESTS)

    def test_diagnostic_requires_actual_tool_use(self):
        with self.assertRaises(TimeoutError):
            coordinate_leaders('task','',SOURCES,lambda *args:finish(),'rules',require_tool=True)

    def test_different_labels_can_be_equivalent_without_silent_alias_rewrite(self):
        def call(system,user,slot,deadline):
            payload=json.loads(user)
            if slot==0:
                self.assertFalse(payload['unresolved_disagreement'])
                self.assertNotEqual(payload['leaders'][0]['decision'],payload['leaders'][1]['decision'])
                return 'equivalent scoped decisions'
            if 'peer_report' in payload:
                self.assertIn('"action":"finish"',system)
                self.assertIn('peer_relation',system)
            return finish('conditional-report-order' if slot==1 else 'report-order-by-audience')
        _,counts=coordinate_leaders('task','',SOURCES,call,'rules')
        self.assertEqual(counts['discussion_rounds'],1)
        self.assertFalse(counts['unresolved_disagreement'])
        self.assertFalse(counts['partial'])

    def test_equivalence_does_not_override_blockers_or_missing_evidence(self):
        for uncited in (False,True):
            def call(system,user,slot,deadline):
                if slot==0:return 'unresolved'
                value=json.loads(finish('label'+str(slot),[] if uncited else ['real blocker']))
                if uncited:value['summary']='uncited claim'
                return json.dumps(value)
            _,counts=coordinate_leaders('task','',SOURCES,call,'rules')
            self.assertTrue(counts['unresolved_disagreement'])
            self.assertEqual(counts['discussion_rounds'],2)

    def test_same_label_does_not_override_explicit_substantive_difference(self):
        from agent_leaders import disagreement
        reports=[final_report(json.loads(finish('same-label',relation=r)),i+1,consultation=True)
                 for i,r in enumerate(('equivalent','different'))]
        self.assertTrue(disagreement(reports))

    def test_contract_rejection_records_specific_code_location_without_response_values(self):
        cases=[('action',None,'leader_finish_action_missing'),
               ('action','read','leader_finish_action_invalid'),
               ('summary','x'*3001,'leader_summary_invalid'),
               ('decision',None,'leader_decision_invalid'),
               ('blockers','private invalid value','leader_blockers_invalid'),
               ('needs_consultation','false','leader_consultation_flag_invalid'),
               ('peer_relation','private invalid value','leader_peer_relation_invalid')]
        for field,value,expected in cases:
            action=json.loads(finish())
            if value is None:action.pop(field)
            else:action[field]=value
            try:final_report(action,1,consultation=True)
            except LeaderContractError as exc:
                record=failure_record(exc,1,'consultation_1')
            else:self.fail('Invalid report accepted')
            self.assertEqual(record['reason_code'],expected)
            self.assertIn('agent_leaders.py:',record['error_location'])
            self.assertNotIn('private invalid',json.dumps(record))

    def test_failed_consultation_checkpoint_contains_field_specific_diagnostics(self):
        saved=[]
        def call(system,user,slot,deadline):
            payload=json.loads(user)
            if slot==0:return 'partial'
            if 'peer_report' in payload:
                value=json.loads(finish());value.pop('action');return json.dumps(value)
            return finish('label'+str(slot))
        _,counts=coordinate_leaders('task','',SOURCES,call,'rules',checkpoint=lambda *args:saved.append(args))
        self.assertTrue(counts['partial'])
        self.assertEqual(len(counts['unavailable_subagents']),2)
        for record in saved[-1][1]:
            self.assertEqual(record['reason_code'],'leader_finish_action_missing')
            self.assertIn('final_report',record['error_location'])

    def test_consultation_and_synthesis_explicitly_include_complete_findings_summaries(self):
        originals={1:'analysis final summary README.md:L1-L2 @fixed',
                   2:'audit final summary README.md:L1-L2 @fixed'}
        def call(system,user,slot,deadline):
            payload=json.loads(user)
            if slot==0:
                self.assertEqual(payload['report_inputs']['included_workers'],[1,2])
                self.assertEqual({r['findings'] for r in payload['leaders']},set(originals.values()))
                self.assertFalse(payload['unresolved_disagreement'])
                return 'scope comparison completed'
            if 'peer_report' in payload:
                self.assertEqual(payload['report_inputs']['kind'],'complete_leader_final_findings_summaries')
                self.assertEqual(payload['own_report']['findings'],originals[slot])
                self.assertEqual(payload['peer_report']['findings'],originals[3-slot])
                self.assertFalse(payload['report_inputs']['private_transcripts_included'])
                self.assertIn('Do not widen scope',system)
                value=json.loads(finish('audience-'+str(slot)))
            else:
                value=json.loads(finish('audience-'+str(slot)))
            value['summary']=originals[slot]
            return json.dumps(value)
        _,counts=coordinate_leaders('Compare presentation templates,not external authored reports','',SOURCES,call,'rules')
        self.assertEqual(counts['discussion_rounds'],1)
        self.assertFalse(counts['unresolved_disagreement'])

    def test_a_genuine_requested_input_gap_remains_blocking(self):
        def call(system,user,slot,deadline):
            payload=json.loads(user)
            if slot==0:
                self.assertTrue(payload['unresolved_disagreement'])
                return 'cannot verify requested backtest'
            self.assertIn('BACKTEST.csv',payload['task'])
            return finish('cannot_verify',['BACKTEST.csv is missing; the requested numeric comparison cannot be checked'],relation='uncertain')
        result,counts=coordinate_leaders('Verify the measured results in BACKTEST.csv','',SOURCES,call,'rules')
        self.assertTrue(counts['unresolved_disagreement'])
        self.assertEqual(counts['discussion_rounds'],2)
        self.assertIn('لا يُدّعى اتفاق نهائي',result)

    def test_operational_metrics_are_controller_counts_not_leader_estimates(self):
        def call(system,user,slot,deadline):
            payload=json.loads(user)
            if slot==0:
                metrics=payload['execution_metrics']
                self.assertEqual(metrics['origin'],'controller_measured')
                self.assertEqual(metrics['tool_steps'],4)
                self.assertEqual(metrics['tool_action_counts'],{'read':2,'search':0,'publish':2,'rejected':0})
                self.assertEqual(metrics['consultation_rounds'],0)
                self.assertEqual(metrics['completed_model_requests_before_synthesis'],6)
                self.assertFalse(metrics['final_runtime_available'])
                self.assertTrue(metrics['measured_footer_added_by_service'])
                self.assertIn('Omit operational counts and durations',system)
                return 'source-based conclusion'
            if payload['step']==1:return json.dumps({'action':'read','path':'README.md','start':1,'end':2})
            if payload['step']==2:return json.dumps({'action':'publish','note':'finding,not an operational count'})
            value=json.loads(finish());value['summary']+=' leader estimate: 99 calls'
            return json.dumps(value)
        _,counts=coordinate_leaders('source audit','',SOURCES,call,'rules')
        self.assertEqual(counts['model_requests'],7)
        self.assertEqual(sum(counts['tool_action_counts'].values()),counts['tool_steps'])

    def test_malformed_reply_is_corrected_without_losing_prior_evidence(self):
        saved=[]
        def call(system,user,slot,deadline):
            payload=json.loads(user)
            if slot==0:return 'final'
            if slot==2:return finish()
            if payload['step']==1:return json.dumps({'action':'read','path':'README.md','start':1,'end':2})
            if 'format_repair' not in payload:return 'invalid response marker'
            self.assertEqual(payload['format_repair']['reason_code'],'deliberation_invalid_response')
            self.assertIn('README.md:L1-L2',payload['workspace']['evidence'])
            self.assertEqual(payload['recent_tool_results'][0]['result']['commit'],'fixed')
            self.assertIn('Keep genuine blockers and dissent',system)
            return finish()
        _,counts=coordinate_leaders('task','',SOURCES,call,'rules',checkpoint=lambda *args:saved.append(args))
        self.assertEqual(counts['completed_subagents'],2)
        self.assertFalse(counts['partial'])
        self.assertEqual(counts['model_requests'],5)
        self.assertEqual(counts['tool_steps'],1)
        self.assertEqual(counts['format_repairs'][0]['outcome'],'corrected')
        self.assertNotIn('invalid response marker',json.dumps(saved))
        self.assertNotIn('invalid response marker',json.dumps(counts))

    def test_invalid_finish_field_has_one_correction_and_preserves_blocker(self):
        def call(system,user,slot,deadline):
            payload=json.loads(user)
            if slot==0:return 'real gap remains'
            value=json.loads(finish('unverified',['required source missing']))
            if slot==1 and 'format_repair' not in payload and 'peer_report' not in payload:
                value['needs_consultation']='false'
            if 'format_repair' in payload:
                self.assertEqual(payload['format_repair']['reason_code'],'leader_consultation_flag_invalid')
            return json.dumps(value)
        _,counts=coordinate_leaders('task','',SOURCES,call,'rules')
        self.assertEqual(len(counts['format_repairs']),1)
        self.assertTrue(counts['unresolved_disagreement'])
        self.assertFalse(counts['partial'])

    def test_failed_correction_stays_partial_without_unbounded_retry(self):
        calls=[]
        def call(system,user,slot,deadline):
            calls.append(slot)
            if slot==0:return 'partial'
            if slot==1:return 'invalid response marker'
            return finish()
        _,counts=coordinate_leaders('task','',SOURCES,call,'rules')
        self.assertEqual(calls.count(1),2)
        self.assertEqual(counts['completed_subagents'],1)
        self.assertTrue(counts['partial'])
        self.assertEqual(counts['format_repairs'][0]['outcome'],'failed')
        self.assertEqual(counts['unavailable_subagents'][0]['reason_code'],'deliberation_invalid_response')
        self.assertNotIn('invalid response marker',json.dumps(counts))

    def test_repair_allowance_is_shared_between_steps_and_consultations(self):
        repairs=[]
        def call(system,user,slot,deadline):
            payload=json.loads(user)
            if slot==0:return 'partial audit'
            if 'format_repair' in payload:
                repairs.append(slot)
                return finish('decision-'+str(slot))
            if slot==1:return 'broken JSON'
            return finish('decision-'+str(slot))
        _,counts=coordinate_leaders('task','',SOURCES,call,'rules')
        self.assertEqual(repairs,[1])
        self.assertEqual(counts['discussion_rounds'],1)
        self.assertTrue(counts['partial'])
        self.assertEqual(counts['completed_subagents'],2)

    def test_consultation_format_repair_uses_original_reports_and_same_deadline(self):
        deadlines={}
        def call(system,user,slot,deadline):
            payload=json.loads(user)
            if slot==0:return 'complete'
            deadlines.setdefault(slot,deadline)
            self.assertEqual(deadlines[slot],deadline)
            if 'peer_report' in payload:
                if slot==1 and 'format_repair' not in payload:return '{unfinished'
                self.assertEqual(payload['own_report']['decision'],'decision-'+str(slot))
                return finish('agreed')
            return finish('decision-'+str(slot))
        _,counts=coordinate_leaders('task','',SOURCES,call,'rules')
        self.assertEqual(counts['discussion_rounds'],1)
        self.assertFalse(counts['partial'])
        self.assertFalse(counts['unresolved_disagreement'])
        self.assertEqual(counts['model_requests'],6)
        self.assertEqual(counts['format_repairs'][0]['phase'],'consultation_1')

    def test_large_sources_are_read_in_excerpts_and_manifest_exposes_line_count(self):
        sources=[dict(SOURCES[0],content=('long source marker '+('x'*200)+'\n')*450)]
        def call(system,user,slot,deadline):
            payload=json.loads(user)
            if slot==0:return 'scoped result'
            self.assertLess(len(user),10000)
            self.assertEqual(payload['workspace']['manifest'][0]['line_count'],450)
            if payload['step']==1:
                self.assertNotIn('long source marker',user)
                return json.dumps({'action':'read','path':'README.md','start':449,'end':450})
            self.assertIn('L450:',payload['recent_tool_results'][0]['result']['content'])
            return finish()
        _,counts=coordinate_leaders('check last lines','',sources,call,'rules',require_tool=True)
        self.assertEqual(counts['completed_subagents'],2)
        self.assertEqual(counts['tool_action_counts']['read'],2)

    def test_transport_failure_does_not_trigger_format_correction(self):
        calls=[]
        def call(system,user,slot,deadline):
            calls.append(slot)
            if slot==0:return 'partial'
            if slot==1:raise TimeoutError('provider timeout')
            return finish()
        _,counts=coordinate_leaders('task','',SOURCES,call,'rules')
        self.assertEqual(calls.count(1),1)
        self.assertEqual(counts['format_repairs'],[])
        self.assertTrue(counts['partial'])

if __name__=='__main__':unittest.main()
