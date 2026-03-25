/**
 * radar-volumes.js — 3D 레이더 탐지/교전 볼륨 렌더링
 *
 * viewer_config.json의 센서 파라미터를 기반으로
 * EllipsoidGeometry 구면 부채꼴 볼륨을 Primitive API로 렌더링.
 *
 * SSOT: 렌더링만 수행. 센서 파라미터는 백엔드가 생성한 JSON에서 로드.
 */

/* global Cesium */

const RadarVolumes = (() => {
    "use strict";

    // ── 상수 ─────────────────────────────────────────
    const DETECTION_COLOR = Cesium.Color.BLUE.withAlpha(0.08);
    const ENGAGEMENT_COLOR = Cesium.Color.GREEN.withAlpha(0.12);

    // 기본 레이더 볼륨 파라미터
    const DEFAULT_PARAMS = {
        minimumClock: Cesium.Math.toRadians(-60),   // 방위각 ±60°
        maximumClock: Cesium.Math.toRadians(60),
        minimumCone: Cesium.Math.toRadians(10),     // 고각 10°~80°
        maximumCone: Cesium.Math.toRadians(80),
        stackPartitions: 24,
        slicePartitions: 24,
    };

    // 센서 유형별 교전 범위 비율 (탐지 범위 대비)
    const ENGAGEMENT_RANGE_RATIO = {
        "EWR": 0,        // 조기경보 레이더는 교전 범위 없음
        "PAT_RADAR": 0.6,
        "MFR": 0.5,
        "SH_RADAR": 0.4,
    };

    // ── 상태 ─────────────────────────────────────────
    let _viewer = null;
    let _detectionPrimitives = [];
    let _engagementPrimitives = [];
    let _visible = true;
    let _azimuthDeg = 0;
    let _volumeData = [];  // { position, detectionRange, engagementRange, modelMatrix }

    /**
     * 레이더 볼륨 생성
     * @param {Cesium.Viewer} viewer
     * @param {Object} viewerConfig — viewer_config.json 파싱 결과
     */
    function create(viewer, viewerConfig) {
        _viewer = viewer;
        clear();

        if (!viewerConfig || !viewerConfig.radar_volumes) return;

        const coordRef = viewerConfig.coordinate_reference || {};

        viewerConfig.radar_volumes.forEach(function(sensor) {
            const pos = sensor.position;
            if (!pos) return;

            const cartesian = Cesium.Cartesian3.fromDegrees(pos.lon, pos.lat, 0);
            const detectionRange = sensor.detection_range_m;

            // 센서 유형에서 교전 범위 추정
            const sensorType = _inferSensorType(sensor.sensor_id);
            const engRatio = ENGAGEMENT_RANGE_RATIO[sensorType] || 0;
            const engagementRange = detectionRange * engRatio;

            const modelMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(cartesian);

            _volumeData.push({
                sensorId: sensor.sensor_id,
                position: cartesian,
                detectionRange: detectionRange,
                engagementRange: engagementRange,
                modelMatrix: modelMatrix,
            });

            // 탐지 볼륨
            _addVolume(detectionRange, modelMatrix, DETECTION_COLOR, _detectionPrimitives);

            // 교전 볼륨 (범위가 있는 경우만)
            if (engagementRange > 0) {
                _addVolume(engagementRange, modelMatrix, ENGAGEMENT_COLOR, _engagementPrimitives);
            }
        });
    }

    /**
     * EllipsoidGeometry 기반 볼륨 추가
     */
    function _addVolume(rangeM, modelMatrix, color, primitiveList) {
        var instance = new Cesium.GeometryInstance({
            geometry: new Cesium.EllipsoidGeometry({
                radii: new Cesium.Cartesian3(rangeM, rangeM, rangeM),
                innerRadii: new Cesium.Cartesian3(100, 100, 100),
                minimumClock: DEFAULT_PARAMS.minimumClock,
                maximumClock: DEFAULT_PARAMS.maximumClock,
                minimumCone: DEFAULT_PARAMS.minimumCone,
                maximumCone: DEFAULT_PARAMS.maximumCone,
                stackPartitions: DEFAULT_PARAMS.stackPartitions,
                slicePartitions: DEFAULT_PARAMS.slicePartitions,
            }),
            modelMatrix: _applyAzimuth(modelMatrix, _azimuthDeg),
            attributes: {
                color: Cesium.ColorGeometryInstanceAttribute.fromColor(color),
            },
        });

        var primitive = _viewer.scene.primitives.add(new Cesium.Primitive({
            geometryInstances: instance,
            appearance: new Cesium.PerInstanceColorAppearance({
                closed: false,
                translucent: true,
                flat: true,
            }),
            asynchronous: false,
        }));

        primitiveList.push(primitive);
    }

    /**
     * 방위각 회전 적용한 modelMatrix 생성
     */
    function _applyAzimuth(baseMatrix, azDeg) {
        if (azDeg === 0) return baseMatrix;

        var rotation = Cesium.Matrix3.fromRotationZ(Cesium.Math.toRadians(azDeg));
        var rotMatrix = Cesium.Matrix4.fromRotationTranslation(rotation);
        var result = new Cesium.Matrix4();
        Cesium.Matrix4.multiply(baseMatrix, rotMatrix, result);
        return result;
    }

    /**
     * 센서 ID에서 유형 추정
     */
    function _inferSensorType(sensorId) {
        if (!sensorId) return "";
        if (sensorId.indexOf("EWR") >= 0) return "EWR";
        if (sensorId.indexOf("PAT_RADAR") >= 0) return "PAT_RADAR";
        if (sensorId.indexOf("MFR") >= 0) return "MFR";
        if (sensorId.indexOf("SH_RADAR") >= 0) return "SH_RADAR";
        return "";
    }

    /**
     * 방위각 업데이트 → 모든 볼륨 회전
     * @param {number} azimuthDeg — 방위각 (도)
     */
    function updateAzimuth(azimuthDeg) {
        _azimuthDeg = azimuthDeg;
        // 기존 볼륨 제거 후 재생성
        if (_viewer && _volumeData.length > 0) {
            _clearPrimitives();

            _volumeData.forEach(function(data) {
                _addVolume(data.detectionRange, data.modelMatrix, DETECTION_COLOR, _detectionPrimitives);
                if (data.engagementRange > 0) {
                    _addVolume(data.engagementRange, data.modelMatrix, ENGAGEMENT_COLOR, _engagementPrimitives);
                }
            });

            _applyVisibility();
        }
    }

    /**
     * 볼륨 표시/숨김 토글
     * @param {boolean} [show] — 지정 시 해당 값으로, 미지정 시 토글
     * @returns {boolean} — 현재 표시 상태
     */
    function toggle(show) {
        _visible = (show !== undefined) ? show : !_visible;
        _applyVisibility();
        return _visible;
    }

    function _applyVisibility() {
        _detectionPrimitives.forEach(function(p) { p.show = _visible; });
        _engagementPrimitives.forEach(function(p) { p.show = _visible; });
    }

    /**
     * 모든 볼륨 제거
     */
    function clear() {
        _clearPrimitives();
        _volumeData = [];
    }

    function _clearPrimitives() {
        if (!_viewer) return;
        _detectionPrimitives.forEach(function(p) {
            _viewer.scene.primitives.remove(p);
        });
        _engagementPrimitives.forEach(function(p) {
            _viewer.scene.primitives.remove(p);
        });
        _detectionPrimitives = [];
        _engagementPrimitives = [];
    }

    return {
        create: create,
        updateAzimuth: updateAzimuth,
        toggle: toggle,
        clear: clear,
    };
})();
