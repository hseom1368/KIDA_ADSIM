"""v0.7 신규 파라미터 유효성 검증 테스트"""

import pytest
from modules.config import (
    SHOOTER_PARAMS, SENSOR_PARAMS, C2_PARAMS,
    TOPOLOGY_RELATIONS, SENSOR_CUEING_DELAYS,
    DEFENSE_ZONES, SIMULATION_MAP, REALISTIC_DEPLOYMENT,
    THREAT_ORIGINS,
)


class TestV07ShooterParams:
    """v0.7 신규 무기체계 파라미터 검증"""

    @pytest.mark.parametrize("weapon", [
        "THAAD", "LSAM_ABM", "LSAM_AAM", "CHEONGUNG1", "CHUNMA",
    ])
    def test_new_weapons_exist(self, weapon):
        assert weapon in SHOOTER_PARAMS

    def test_thaad_high_altitude_only(self):
        t = SHOOTER_PARAMS["THAAD"]
        assert t["min_altitude"] == 40
        assert t["max_altitude"] == 150
        assert t["pk_table"]["SRBM"] == 0.90
        assert t["pk_table"]["CRUISE_MISSILE"] == 0.0

    def test_lsam_abm_high_altitude_only(self):
        t = SHOOTER_PARAMS["LSAM_ABM"]
        assert t["min_altitude"] == 40
        assert t["max_altitude"] == 60
        assert t["pk_table"]["SRBM"] == 0.85
        assert t["pk_table"]["AIRCRAFT"] == 0.0

    def test_lsam_aam_anti_air(self):
        t = SHOOTER_PARAMS["LSAM_AAM"]
        assert t["min_altitude"] == 0
        assert t["pk_table"]["SRBM"] == 0.0
        assert t["pk_table"]["AIRCRAFT"] == 0.90

    def test_cheongung1_no_bmd(self):
        t = SHOOTER_PARAMS["CHEONGUNG1"]
        assert t["pk_table"]["SRBM"] == 0.0
        assert t["pk_table"]["AIRCRAFT"] == 0.85

    def test_chunma_short_range(self):
        t = SHOOTER_PARAMS["CHUNMA"]
        assert t["max_range"] == 9
        assert t["max_altitude"] == 5

    def test_all_shooters_have_min_altitude(self):
        for name, params in SHOOTER_PARAMS.items():
            assert "min_altitude" in params, f"{name} missing min_altitude"

    def test_all_shooters_have_intercept_method(self):
        for name, params in SHOOTER_PARAMS.items():
            assert "intercept_method" in params, f"{name} missing intercept_method"

    def test_pac3_mse_updated_specs(self):
        t = SHOOTER_PARAMS["PATRIOT_PAC3"]
        assert t["max_altitude"] == 40  # 30→40
        assert t["max_range"] == 90     # 120→90


class TestV07SensorParams:
    """v0.7 신규 센서 파라미터 검증"""

    @pytest.mark.parametrize("sensor", ["GREEN_PINE", "FPS117", "TPS880K"])
    def test_new_sensors_exist(self, sensor):
        assert sensor in SENSOR_PARAMS

    def test_green_pine_early_warning(self):
        gp = SENSOR_PARAMS["GREEN_PINE"]
        assert gp["role"] == "early_warning"
        assert gp["detection_range"] == 800
        assert gp["detectable_types"] == ["SRBM"]
        assert "KAMD_OPS" in gp["provides_cueing_to"]

    def test_fps117_surveillance(self):
        fps = SENSOR_PARAMS["FPS117"]
        assert fps["role"] == "surveillance"
        assert fps["min_detection_altitude"] == 1.0
        assert "AIRCRAFT" in fps["detectable_types"]

    def test_tps880k_local_surveillance(self):
        tps = SENSOR_PARAMS["TPS880K"]
        assert tps["role"] == "local_surveillance"
        assert tps["min_detection_altitude"] == 0.05
        assert "UAS" in tps["detectable_types"]

    def test_existing_sensors_have_role(self):
        for name in ["EWR", "PATRIOT_RADAR", "MSAM_MFR", "SHORAD_RADAR"]:
            assert SENSOR_PARAMS[name].get("role") == "weapon_fc"


class TestV07C2Params:
    """v0.7 신규 C2 노드 검증"""

    @pytest.mark.parametrize("c2", ["KAMD_OPS", "ARMY_LOCAL_AD", "IAOC"])
    def test_new_c2_exist(self, c2):
        assert c2 in C2_PARAMS

    def test_iaoc_killweb_only(self):
        iaoc = C2_PARAMS["IAOC"]
        assert iaoc["auth_delay_linear"] is None
        assert iaoc["auth_delay_killweb"] is not None


class TestV07TopologyRelations:
    """v0.7 토폴로지 관계 매핑 검증"""

    def test_new_sensor_mappings(self):
        s2c = TOPOLOGY_RELATIONS["sensor_to_c2"]
        assert s2c["GREEN_PINE"] == "KAMD_OPS"
        assert s2c["FPS117"] == "MCRC"
        assert s2c["TPS880K"] == "ARMY_LOCAL_AD"

    def test_new_shooter_mappings(self):
        sh2c = TOPOLOGY_RELATIONS["shooter_to_c2"]
        assert sh2c["THAAD"] == "KAMD_OPS"
        assert sh2c["LSAM_ABM"] == "KAMD_OPS"
        assert sh2c["CHEONGUNG1"] == "MCRC"
        assert sh2c["CHUNMA"] == "ARMY_LOCAL_AD"


class TestV07DeploymentAndMap:
    """v0.7 배치 모델 및 좌표계 검증"""

    def test_simulation_map_keys(self):
        assert "x_range" in SIMULATION_MAP
        assert "dmz_y" in SIMULATION_MAP
        assert SIMULATION_MAP["dmz_y"] == 0

    def test_defense_zones(self):
        assert len(DEFENSE_ZONES) == 4
        assert "ZONE_A" in DEFENSE_ZONES
        assert DEFENSE_ZONES["ZONE_A"]["y_range"] == (0, 30)

    def test_realistic_deployment_structure(self):
        d = REALISTIC_DEPLOYMENT
        assert "sensors" in d
        assert "c2_nodes" in d
        assert "shooters" in d
        assert "defense_target" in d
        assert "linear" in d["c2_nodes"]
        assert "killweb" in d["c2_nodes"]

    def test_realistic_deployment_has_new_assets(self):
        d = REALISTIC_DEPLOYMENT
        shooter_types = {s["type"] for s in d["shooters"]}
        assert "THAAD" in shooter_types
        assert "LSAM_ABM" in shooter_types
        assert "CHUNMA" in shooter_types
        sensor_types = {s["type"] for s in d["sensors"]}
        assert "GREEN_PINE" in sensor_types
        assert "FPS117" in sensor_types
        assert "TPS880K" in sensor_types

    def test_threat_origins(self):
        assert "DMZ_FRONT" in THREAT_ORIGINS
        assert "PYONGYANG_AREA" in THREAT_ORIGINS
        assert THREAT_ORIGINS["PYONGYANG_AREA"]["y"] == -180

    def test_sensor_cueing_delays(self):
        assert "early_warning_to_c2" in SENSOR_CUEING_DELAYS
        assert "weapon_radar_acquisition" in SENSOR_CUEING_DELAYS
