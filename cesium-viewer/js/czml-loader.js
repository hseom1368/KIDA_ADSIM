/**
 * czml-loader.js — CZML 파일 로드 및 시간 컨트롤 모듈
 *
 * SSOT: 이 모듈은 시뮬레이션 로직을 수행하지 않음.
 * 백엔드가 생성한 CZML을 Cesium 뷰어에 로드하고
 * 시간 제어(재생/일시정지/속도/스크러빙)만 담당.
 */

/* global Cesium */

const CZMLLoader = (() => {
    "use strict";

    // 활성 DataSource 참조
    let _activeDataSource = null;
    let _viewer = null;

    /**
     * 뷰어 참조 설정
     * @param {Cesium.Viewer} viewer
     */
    function init(viewer) {
        _viewer = viewer;
    }

    /**
     * CZML 파일을 뷰어에 로드
     * @param {string} url — CZML 파일 경로
     * @returns {Promise<Cesium.CzmlDataSource>}
     */
    async function loadCZML(url) {
        if (!_viewer) {
            throw new Error("CZMLLoader not initialized. Call init(viewer) first.");
        }

        // 기존 DataSource 제거
        if (_activeDataSource) {
            _viewer.dataSources.remove(_activeDataSource, true);
            _activeDataSource = null;
        }

        const dataSource = await Cesium.CzmlDataSource.load(url);
        _viewer.dataSources.add(dataSource);
        _activeDataSource = dataSource;

        // 시뮬레이션 클럭 동기화
        _syncClock(dataSource);

        return dataSource;
    }

    /**
     * DataSource의 clock을 뷰어에 동기화
     */
    function _syncClock(dataSource) {
        const dsClock = dataSource.clock;
        if (!dsClock) return;

        const clock = _viewer.clock;
        clock.startTime = dsClock.startTime;
        clock.stopTime = dsClock.stopTime;
        clock.currentTime = dsClock.startTime.clone();
        clock.clockRange = Cesium.ClockRange.LOOP_STOP;
        clock.shouldAnimate = false;

        // 타임라인 동기화
        if (_viewer.timeline) {
            _viewer.timeline.zoomTo(dsClock.startTime, dsClock.stopTime);
        }
    }

    /**
     * 재생/일시정지 토글
     * @returns {boolean} — 현재 재생 상태
     */
    function togglePlayPause() {
        if (!_viewer) return false;
        _viewer.clock.shouldAnimate = !_viewer.clock.shouldAnimate;
        return _viewer.clock.shouldAnimate;
    }

    /**
     * 재생 속도 설정
     * @param {number} multiplier — 배속 (1, 2, 5, 10, 20)
     */
    function setPlaybackSpeed(multiplier) {
        if (!_viewer) return;
        _viewer.clock.multiplier = multiplier;
    }

    /**
     * 특정 시뮬레이션 시간(초)으로 이동
     * @param {number} simTimeSec — 시뮬레이션 시간(초)
     */
    function seekToSimTime(simTimeSec) {
        if (!_viewer) return;
        const epoch = Cesium.JulianDate.fromIso8601("2024-01-01T00:00:00Z");
        const target = Cesium.JulianDate.addSeconds(epoch, simTimeSec, new Cesium.JulianDate());
        _viewer.clock.currentTime = target;
    }

    /**
     * 현재 활성 DataSource 반환
     * @returns {Cesium.CzmlDataSource|null}
     */
    function getActiveDataSource() {
        return _activeDataSource;
    }

    /**
     * 모든 DataSource 제거
     */
    function clearAll() {
        if (_viewer) {
            _viewer.dataSources.removeAll(true);
        }
        _activeDataSource = null;
    }

    /**
     * 엔티티 정보를 HTML로 포맷팅
     * @param {Cesium.Entity} entity
     * @returns {string} HTML 문자열
     */
    function formatEntityInfo(entity) {
        const props = entity.properties;
        let html = "";

        html += _propRow("Name", entity.name || entity.id);

        if (props) {
            const names = props.propertyNames;
            for (let i = 0; i < names.length; i++) {
                const key = names[i];
                const val = props[key] ? props[key].getValue(
                    _viewer.clock.currentTime
                ) : "N/A";
                html += _propRow(key, val);
            }
        }

        // 위치 정보
        if (entity.position) {
            const pos = entity.position.getValue(_viewer.clock.currentTime);
            if (pos) {
                const carto = Cesium.Cartographic.fromCartesian(pos);
                html += _propRow("Lon", Cesium.Math.toDegrees(carto.longitude).toFixed(3) + "\u00b0");
                html += _propRow("Lat", Cesium.Math.toDegrees(carto.latitude).toFixed(3) + "\u00b0");
                html += _propRow("Alt", (carto.height / 1000).toFixed(1) + " km");
            }
        }

        return html;
    }

    function _propRow(label, value) {
        return '<div class="prop-row">' +
               '<span class="prop-label">' + label + '</span>' +
               '<span class="prop-value">' + value + '</span>' +
               '</div>';
    }

    return {
        init,
        loadCZML,
        togglePlayPause,
        setPlaybackSpeed,
        seekToSimTime,
        getActiveDataSource,
        clearAll,
        formatEntityInfo,
    };
})();
