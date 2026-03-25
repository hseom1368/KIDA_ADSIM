/**
 * performance.js — Primitive API 기반 성능 최적화 모듈
 *
 * CZML DataSource의 Entity API 엔티티를 보완하여
 * 정적 라벨/아이콘을 Primitive 컬렉션으로 렌더링.
 *
 * 대상:
 * - 센서/사수/C2 노드 라벨 → LabelCollection
 * - 방어 대상 마커 → BillboardCollection
 *
 * CZML 동적 엔티티(위협 궤적 등)는 Cesium 내부 최적화에 위임.
 */

/* global Cesium */

const Performance = (() => {
    "use strict";

    let _viewer = null;
    let _labelCollection = null;
    let _pointCollection = null;

    /**
     * 초기화 + Primitive 컬렉션 생성
     * @param {Cesium.Viewer} viewer
     */
    function init(viewer) {
        _viewer = viewer;
        clear();
    }

    /**
     * viewer_config.json 기반으로 정적 라벨 생성
     * @param {Object} viewerConfig
     */
    function createLabels(viewerConfig) {
        if (!_viewer || !viewerConfig) return;

        clear();

        _labelCollection = _viewer.scene.primitives.add(
            new Cesium.LabelCollection({ scene: _viewer.scene })
        );
        _pointCollection = _viewer.scene.primitives.add(
            new Cesium.PointPrimitiveCollection()
        );

        // 센서 라벨
        var sensors = viewerConfig.radar_volumes || [];
        for (var i = 0; i < sensors.length; i++) {
            var s = sensors[i];
            var pos = Cesium.Cartesian3.fromDegrees(s.position.lon, s.position.lat, 200);
            _labelCollection.add({
                position: pos,
                text: s.sensor_id,
                font: "11px monospace",
                fillColor: Cesium.Color.DEEPSKYBLUE,
                outlineColor: Cesium.Color.BLACK,
                outlineWidth: 2,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                pixelOffset: new Cesium.Cartesian2(0, -18),
                disableDepthTestDistance: Number.POSITIVE_INFINITY,
                scale: 1.0,
            });
        }

        // 사수 라벨
        var batteries = viewerConfig.batteries || [];
        for (var j = 0; j < batteries.length; j++) {
            var b = batteries[j];
            var bpos = Cesium.Cartesian3.fromDegrees(b.position.lon, b.position.lat, 200);
            _labelCollection.add({
                position: bpos,
                text: b.battery_id,
                font: "11px monospace",
                fillColor: Cesium.Color.LIME,
                outlineColor: Cesium.Color.BLACK,
                outlineWidth: 2,
                style: Cesium.LabelStyle.FILL_AND_OUTLINE,
                pixelOffset: new Cesium.Cartesian2(0, -18),
                disableDepthTestDistance: Number.POSITIVE_INFINITY,
                scale: 1.0,
            });

            // 탄약량 포인트 (초기 상태)
            _pointCollection.add({
                position: bpos,
                pixelSize: 6,
                color: Cesium.Color.LIME.withAlpha(0.8),
                outlineColor: Cesium.Color.BLACK,
                outlineWidth: 1,
                disableDepthTestDistance: Number.POSITIVE_INFINITY,
            });
        }
    }

    /**
     * 모든 Primitive 컬렉션 제거
     */
    function clear() {
        if (!_viewer) return;

        if (_labelCollection) {
            _viewer.scene.primitives.remove(_labelCollection);
            _labelCollection = null;
        }
        if (_pointCollection) {
            _viewer.scene.primitives.remove(_pointCollection);
            _pointCollection = null;
        }
    }

    return {
        init: init,
        createLabels: createLabels,
        clear: clear,
    };
})();
