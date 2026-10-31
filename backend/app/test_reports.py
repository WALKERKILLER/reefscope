import io
import json
import tempfile
from copy import deepcopy
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from app.analysis.training import parse_csv, ingest
from app.analysis.reports import make_report, SECTION_NAMES
from app.models import ModelVersion, TrainingRun, TrainingReport, EvaluationRun

CSV = 'epoch,metrics/mAP50(B),metrics/mAP50-95(B),train/box_loss\n1,0.8,0.4,2\n2,0.9,0.5,1\n3,0.85,0.6,0.5\n'


class ReportTests(TestCase):
    def setUp(self):
        self.model=ModelVersion.objects.create(id='fish:report',weight_path='private/weight.pt',sha256='a'*64,labels={'0':'fish'},framework_version='8.4.46')
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)
        (self.root/'results.csv').write_text(CSV)
        (self.root/'run_metadata.json').write_text(json.dumps({'best_fitness':0.6,'save_dir':'PRIVATE-SOURCE-NOT-FOR-EXPORT','metrics':{}}))

    def test_numeric_parser_separates_best_criteria_and_rejects_nonfinite(self):
        snapshot,hashes=ingest(self.root)
        self.assertEqual(snapshot['selection']['best_map50_epoch'],2)
        self.assertEqual(snapshot['selection']['best_map50_95_epoch'],3)
        self.assertIsNone(snapshot['selection']['framework_best_checkpoint_epoch'])
        self.assertEqual(snapshot['selection']['framework_best_fitness'],0.6)
        self.assertIn('results.csv',hashes)
        for text in (CSV.replace('0.8','nan'),CSV.replace('0.8','inf'),CSV.replace('2,0.9','1,0.9'),'epoch\n0\n','epoch,epoch\n1,2\n'):
            with self.assertRaises(ValueError):
                parse_csv(text)

    def test_missing_numeric_source_is_not_recovered_from_images(self):
        (self.root/'results.csv').unlink()
        snapshot,_=ingest(self.root)
        self.assertEqual(snapshot['epochs'],[])
        self.assertIn('numeric_training_curves',snapshot['missing_inputs'])
        payload,markdown,html=make_report(self.model)
        self.assertEqual([section['title'] for section in payload['sections']],list(SECTION_NAMES))
        self.assertIn('zero-finetune',markdown)
        self.assertIn('N/A',html)

    def test_cli_creates_readonly_records_and_exports_no_raw_paths(self):
        output=io.StringIO()
        call_command('import_fish_training',self.model.pk,str(self.root),stdout=output)
        report=TrainingReport.objects.get(pk=output.getvalue().strip())
        original=deepcopy(report.training_run.snapshot)
        for export in ('markdown','html'):
            response=self.client.get(f'/api/v1/reports/{report.pk}/export',{'export':export})
            self.assertEqual(response.status_code,200)
            body=response.content.decode()
            self.assertNotIn('PRIVATE-SOURCE',body)
            self.assertNotIn('private/weight.pt',body)
            self.assertIn('best',body)
            self.assertIn('0.6',body)
        self.assertEqual(self.client.post(f'/api/v1/reports/{report.pk}').status_code,405)
        report.training_run.snapshot={}
        with self.assertRaises(ValidationError):
            report.training_run.save()
        self.assertEqual(TrainingRun.objects.get().snapshot,original)
        response=self.client.get(f'/api/v1/model-versions/{self.model.pk}/history')
        self.assertEqual(len(response.json()['reports']),1)
        self.assertNotIn('weight_path',response.content.decode())

    def test_report_copies_metrics_and_rejects_incomparable_baselines(self):
        def evaluation(digest):
            return EvaluationRun.objects.create(model=self.model,dataset_version='synthetic-reviewed-test',dataset_sha256=digest,protocol_id='toy-v1',metrics={'ap50':{'value':0.5,'unit':'fraction'}},config={'iou':0.5},source_hashes={})
        current,baseline=evaluation('b'*64),evaluation('c'*64)
        before=deepcopy(current.metrics)
        payload,markdown,html=make_report(self.model,evaluation=current)
        payload['metrics']['ap50']['value']=0.9
        self.assertEqual(current.metrics,before)
        self.assertIn('0.5',markdown)
        self.assertIn('0.5',html)
        with self.assertRaisesMessage(ValueError,'incomparable_evaluations'):
            make_report(self.model,evaluation=current,baseline=baseline)

    def test_yaml_paths_are_excluded_and_object_tags_never_execute(self):
        path=self.root/'args.yaml'
        path.write_text('epochs: 100\nimgsz: 640\noptimizer: AdamW\ndata: /PRIVATE/DATA\nproject: /PRIVATE/PROJECT\n')
        snapshot,_=ingest(self.root)
        self.assertEqual(snapshot['arguments'],{'epochs':100,'imgsz':640,'optimizer':'AdamW'})
        self.assertNotIn('PRIVATE',json.dumps(snapshot))
        path.write_text('!!python/object/apply:builtins.exec ["raise AssertionError(\'executed\')"]')
        with self.assertRaisesMessage(ValueError,'invalid_training_args'):
            ingest(self.root)
