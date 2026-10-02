import json
import threading
import unittest
from agent_background import coordinate

class BackgroundTests(unittest.TestCase):
    def test_two_parallel_workers_then_one_lead_without_votes(self):
        barrier=threading.Barrier(2); calls=[]
        def call(system,user,slot,deadline):
            payload=json.loads(user);calls.append((slot,payload))
            if slot:
                barrier.wait(timeout=1)
                return 'finding README.md:L1-L1 @fixed'
            self.assertEqual(len(payload['workers']),2)
            self.assertEqual(payload['evidence']['source_excerpts'][0]['commit'],'fixed')
            self.assertNotIn('sources',payload)
            return 'نتيجة مختصرة'
        result,counts=coordinate('task','context',[{'path':'README.md','commit':'fixed','content':'evidence'}],call,'rules')
        self.assertEqual(sorted(slot for slot,_ in calls),[0,1,2])
        self.assertEqual(counts['model_requests'],3)
        self.assertEqual(counts['discussion_rounds'],0)
        self.assertFalse(counts['partial'])
        self.assertIn('لا توجد حلقة إجماع',result)

    def test_failed_worker_does_not_discard_other_findings(self):
        def call(system,user,slot,deadline):
            if slot==2:raise ValueError('secret must not appear')
            if slot:return 'finding'
            payload=json.loads(user)
            self.assertEqual(len(payload['workers']),1)
            self.assertNotIn('secret',user)
            return 'partial result'
        result,counts=coordinate('task','',[],call,'rules')
        self.assertTrue(counts['partial'])
        self.assertEqual(counts['completed_subagents'],1)
        self.assertEqual(counts['model_requests'],2)
        self.assertIn('النتيجة جزئية',result)

    def test_pending_worker_does_not_hold_lead_or_change_final_counts(self):
        release=threading.Event();started=threading.Event()
        def call(system,user,slot,deadline):
            if slot==2:
                started.set();release.wait(timeout=2);return 'late result'
            if slot==1:return 'ready result'
            self.assertFalse(release.is_set())
            return 'lead result'
        try:
            result,counts=coordinate('task','',[],call,'rules',worker_seconds=.03)
            self.assertTrue(started.is_set())
            self.assertEqual(counts['completed_subagents'],1)
            self.assertEqual(counts['unavailable_subagents'][0]['reason_code'],'worker_deadline')
            self.assertTrue(counts['partial'])
        finally:release.set()

    def test_both_fail_blocks_without_a_lead_call(self):
        calls=[]
        def call(system,user,slot,deadline):
            calls.append(slot);raise TimeoutError('private error')
        with self.assertRaises(TimeoutError):coordinate('task','',[],call,'rules')
        self.assertEqual(sorted(calls),[1,2])

    def test_missing_source_evidence_is_explicit_in_final_label(self):
        result,counts=coordinate('task','',[{'path':'README.md','content':'evidence'}],
                                 lambda *args:'uncited finding','rules')
        self.assertFalse(counts['evidence_complete'])
        self.assertIn('التحقق من الأدلة المصدرية غير مكتمل',result)

if __name__=='__main__':unittest.main()
