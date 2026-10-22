import csv
import io
import json
from pathlib import Path
from unittest import TestCase

from app.analysis.heatmap import integrate
from app.analysis.queue import claim_run, finish
from app.analysis.storage import attempt_directory
from app.test_analysis import RunFixture
from django.test import TestCase as DjangoTestCase


def point(time, x=0.25, y=0.25, identity=1, frame=None, observed=True):
    return {"track_id":identity,"frame":int(time) if frame is None else frame,"timestamp_ms":time,
            "center_xyn":[x,y], "observed":observed,"class_id":0,"confidence":0.8}


class IntegrationTests(TestCase):
    def test_hand_calculated_mass_and_clipped_segment(self):
        records = [point(0,0.25),point(100,0.75)]
        result = integrate(records,width=2,height=1)
        self.assertAlmostEqual(result["values_raw"][0][0],0.05)
        self.assertAlmostEqual(result["values_raw"][0][1],0.05)
        clipped = integrate(records,start_ms=25,end_ms=75,width=2,height=1)
        self.assertAlmostEqual(clipped["track_seconds_total"],0.05)
        self.assertAlmostEqual(clipped["sampled_duration_seconds"],0.05)
        self.assertAlmostEqual(sum(clipped["values_raw"][0]),0.05)

    def test_zero_singleton_duplicates_gaps_and_multiple_ids(self):
        self.assertEqual(integrate([])["track_seconds_total"],0)
        self.assertEqual(integrate([point(0)])["track_seconds_total"],0)
        sequence = [point(0),point(100),point(100),point(1100),point(0,identity=2),point(200,identity=2)]
        result = integrate(sequence)
        self.assertAlmostEqual(result["track_seconds_total"],0.3)
        self.assertAlmostEqual(integrate(sequence,track_id=1)["track_seconds_total"],0.1)
        self.assertEqual(integrate([point(0,observed=False),point(100)])["track_seconds_total"],0)

    def test_roi_boundary_and_normalization(self):
        result=integrate([point(0,1,1),point(100,1,1)],width=2,height=2,roi=[[0.5,0.5],[1,0.5],[1,1],[0.5,1]])
        self.assertAlmostEqual(result["values_raw"][1][1],0.1)
        self.assertEqual(result["values_display"][1][1],1)
        self.assertEqual(integrate([point(0),point(100)],roi=[[0.5,0.5],[1,0.5],[1,1]])["track_seconds_total"],0)

    def test_rejects_invalid_scientific_inputs(self):
        for record in (point(float("nan"),frame=0),point(0,x=-0.1),point(0,x=float("inf"))):
            with self.assertRaises(ValueError):
                integrate([record])
        for config in ({"width":0},{"steps":0},{"end_ms":0},{"allowed_gap_seconds":float("inf")},{"roi":[[0,0]]}):
            with self.assertRaises(ValueError):
                integrate([],**config)
        with self.assertRaises(ValueError):
            integrate([point(100),point(50)])
        with self.assertRaises(ValueError):
            integrate([point(0),point(0,x=0.5)])


class TrackApiTests(RunFixture, DjangoTestCase):
    def prepare_tracks(self):
        self.enqueue()
        run=claim_run()
        output=attempt_directory(run)
        records=[point(0),point(100),point(200)]
        (output/"tracks.jsonl").write_text("".join(json.dumps(record)+"\n" for record in records))
        finish(run,{})
        return run

    def test_pages_are_stable_and_cursors_bind_filters(self):
        run=self.prepare_tracks()
        url=f"/api/v1/analysis-runs/{run.pk}/tracks"
        first=self.client.get(url,{"limit":1}).json()
        second=self.client.get(url,{"limit":1,"cursor":first["next_cursor"]}).json()
        self.assertEqual(first["items"][0]["frame"],0)
        self.assertEqual(second["items"][0]["frame"],100)
        self.assertEqual(self.client.get(url,{"cursor":first["next_cursor"],"start_ms":50}).status_code,400)
        self.assertEqual(self.client.get(url,{"limit":2001}).status_code,400)
        self.assertEqual(self.client.get(url,{"end_ms":0}).status_code,400)
        window=self.client.get(url,{"start_ms":100,"end_ms":200}).json()
        self.assertEqual([p["frame"] for p in window["items"]],[100])

    def test_csv_and_json_share_raw_values(self):
        run=self.prepare_tracks()
        url=f"/api/v1/analysis-runs/{run.pk}/heatmap"
        options={"width":2,"height":2,"start_ms":25,"end_ms":175}
        data=self.client.get(url,options).json()
        response=self.client.get(url,options|{"export":"csv"})
        rows=list(csv.DictReader(io.StringIO(response.content.decode())))
        self.assertAlmostEqual(sum(float(row["track_seconds"]) for row in rows),data["track_seconds_total"])
        self.assertAlmostEqual(data["track_seconds_total"],0.15)
        self.assertIn("非海底地理坐标",data["interpretation"])
        self.assertEqual(self.client.get(url,{"start_ms":"nan"}).status_code,400)

    def test_summary_export_preserves_values_and_missing_reasons(self):
        run=self.prepare_tracks()
        url=f"/api/v1/analysis-runs/{run.pk}/summary"
        options={"start_ms":25,"end_ms":175}
        result=self.client.get(url,options).json()
        exported=self.client.get(url,options|{"export":"json"})
        self.assertEqual(result,exported.json())
        self.assertIn("analysis_report.json",exported["Content-Disposition"])
        self.assertEqual(result["metrics"]["tracked_observation_count"]["value"],1)
        self.assertAlmostEqual(result["metrics"]["track_seconds"]["value"],0.15)
        self.assertAlmostEqual(result["metrics"]["mean_confidence"]["value"],0.8)
        self.assertIsNone(result["metrics"]["ap50"]["value"])
        self.assertEqual(result["metrics"]["ap50"]["reason"],"missing_independent_ground_truth")
        empty=self.client.get(url,{"start_ms":500,"end_ms":600}).json()
        self.assertEqual(empty["metrics"]["observed_track_count"]["value"],0)
        self.assertIsNone(empty["metrics"]["mean_confidence"]["value"])
