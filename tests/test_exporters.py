"""CZML 내보내기 테스트"""

import json
import os
import tempfile
import pytest

from modules.model import AirDefenseModel
from modules.exporters import CZMLExporter


@pytest.fixture
def snapshot_result():
    m = AirDefenseModel(
        architecture="killweb", scenario="scenario_1_saturation",
        seed=42, record_snapshots=True,
    )
    return m.run_full()


class TestCZMLExporter:
    def test_build_czml_nonempty(self, snapshot_result):
        exporter = CZMLExporter(
            snapshot_result["snapshots"], snapshot_result["config"]
        )
        czml = exporter.build_czml()
        assert len(czml) > 1  # 최소 document + entities

    def test_document_packet(self, snapshot_result):
        exporter = CZMLExporter(
            snapshot_result["snapshots"], snapshot_result["config"]
        )
        czml = exporter.build_czml()
        doc = czml[0]
        assert doc["id"] == "document"
        assert "clock" in doc

    def test_threat_packets_exist(self, snapshot_result):
        exporter = CZMLExporter(
            snapshot_result["snapshots"], snapshot_result["config"]
        )
        czml = exporter.build_czml()
        threat_packets = [p for p in czml if p["id"].startswith("threat_")]
        assert len(threat_packets) > 0

    def test_sensor_packets_exist(self, snapshot_result):
        exporter = CZMLExporter(
            snapshot_result["snapshots"], snapshot_result["config"]
        )
        czml = exporter.build_czml()
        sensor_packets = [p for p in czml if p["id"].startswith("sensor_")]
        assert len(sensor_packets) > 0

    def test_export_file(self, snapshot_result):
        exporter = CZMLExporter(
            snapshot_result["snapshots"], snapshot_result["config"]
        )
        with tempfile.NamedTemporaryFile(suffix=".czml", delete=False) as f:
            filepath = f.name

        try:
            exporter.export(filepath)
            assert os.path.exists(filepath)
            with open(filepath) as f:
                data = json.load(f)
            assert isinstance(data, list)
            assert data[0]["id"] == "document"
        finally:
            os.unlink(filepath)

    def test_to_json(self, snapshot_result):
        exporter = CZMLExporter(
            snapshot_result["snapshots"], snapshot_result["config"]
        )
        json_str = exporter.to_json()
        data = json.loads(json_str)
        assert isinstance(data, list)

    def test_empty_snapshots(self):
        exporter = CZMLExporter([], {"defense_target": (100, 50)})
        czml = exporter.build_czml()
        assert len(czml) == 1  # document only

    def test_defense_target_packet(self, snapshot_result):
        exporter = CZMLExporter(
            snapshot_result["snapshots"], snapshot_result["config"]
        )
        czml = exporter.build_czml()
        target_packets = [p for p in czml if p["id"] == "defense_target"]
        assert len(target_packets) == 1
