/**
 * topology-viz.js — C2 토폴로지 네트워크 3D 시각화
 *
 * CZML의 topo_ 패킷을 기반으로 연결선 스타일 강화:
 * 1. link_type별 색상 구분 (센서→C2=파랑, C2→C2=주황, C2→사수=초록)
 * 2. 노드 파괴 시 연결선 단절 시각화 (색상 변화→소멸)
 * 3. 토폴로지 토글 (표시/숨김)
 *
 * SSOT: CZML 데이터만 시각적으로 강화. 토폴로지 계산 없음.
 */

/* global Cesium */

const TopologyViz = (() => {
    "use strict";

    // ── 상수 ─────────────────────────────────────────
    // link_type 기반 색상 분류
    const LINK_COLORS = {
        sensor_to_c2: Cesium.Color.DEEPSKYBLUE.withAlpha(0.6),
        c2_to_c2: Cesium.Color.ORANGE.withAlpha(0.6),
        c2_to_shooter: Cesium.Color.LIME.withAlpha(0.6),
        default: Cesium.Color.WHITE.withAlpha(0.4),
    };

    const LINK_WIDTHS = {
        sensor_to_c2: 1.5,
        c2_to_c2: 2.0,
        c2_to_shooter: 1.5,
        default: 1.0,
    };

    // ── 상태 ─────────────────────────────────────────
    let _viewer = null;
    let _topoEntities = [];
    let _visible = true;

    /**
     * 초기화
     * @param {Cesium.Viewer} viewer
     */
    function init(viewer) {
        _viewer = viewer;
    }

    /**
     * CZML DataSource에서 토폴로지 엔티티를 추출하여 스타일 강화
     * @param {Cesium.CzmlDataSource} dataSource
     */
    function enhance(dataSource) {
        if (!_viewer || !dataSource) return;

        clear();

        var entities = dataSource.entities.values;

        for (var i = 0; i < entities.length; i++) {
            var entity = entities[i];
            var id = entity.id || "";

            if (id.indexOf("topo_") !== 0) continue;

            _topoEntities.push(entity);

            // link_type에 따라 스타일 적용
            var linkType = _getPropertyValue(entity.properties, "link_type");
            var colorKey = _classifyLink(linkType);

            if (entity.polyline) {
                entity.polyline.material = new Cesium.ColorMaterialProperty(
                    LINK_COLORS[colorKey] || LINK_COLORS.default
                );
                entity.polyline.width = LINK_WIDTHS[colorKey] || LINK_WIDTHS.default;
            }
        }
    }

    /**
     * link_type 문자열을 색상 키로 분류
     */
    function _classifyLink(linkType) {
        if (!linkType) return "default";

        var lt = linkType.toLowerCase();
        if (lt.indexOf("sensor") >= 0) return "sensor_to_c2";
        if (lt.indexOf("c2_to_c2") >= 0 || lt.indexOf("peer") >= 0) return "c2_to_c2";
        if (lt.indexOf("shooter") >= 0 || lt.indexOf("fire") >= 0) return "c2_to_shooter";

        // 소스/타겟 ID 기반 추정
        return "default";
    }

    /**
     * 토폴로지 표시/숨김 토글
     * @param {boolean} [show]
     * @returns {boolean} — 현재 표시 상태
     */
    function toggle(show) {
        _visible = (show !== undefined) ? show : !_visible;
        _topoEntities.forEach(function(e) {
            e.show = _visible;
        });
        return _visible;
    }

    /**
     * 모든 토폴로지 시각화 제거
     */
    function clear() {
        _topoEntities = [];
        _visible = true;
    }

    // ── 유틸리티 ─────────────────────────────────────

    function _getPropertyValue(props, name) {
        if (!props || !props[name]) return null;
        try {
            return props[name].getValue(Cesium.JulianDate.now());
        } catch (_) {
            return null;
        }
    }

    return {
        init: init,
        enhance: enhance,
        toggle: toggle,
        clear: clear,
    };
})();
