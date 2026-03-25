/**
 * hud-panel.js — Military HUD 패널
 *
 * CZML 재생 중 실시간 교전 현황 표시:
 * - 방어 상태 (아키텍처, 시나리오, 시뮬시간)
 * - 교전 카운터 (탐지, 교전, 격추, 누출)
 * - 교전 로그 (시간순 이벤트 스크롤)
 *
 * 데이터 소스: CZML 엔티티의 properties + Clock 시간
 * SSOT: 렌더링만 수행. 판정/계산 없음.
 */

/* global Cesium */

const HUDPanel = (() => {
    "use strict";

    // ── 상수 ─────────────────────────────────────────
    const MAX_LOG_ENTRIES = 14;

    // ── 상태 ─────────────────────────────────────────
    let _viewer = null;
    let _panelEl = null;
    let _tickHandler = null;
    let _metadata = {};
    let _engagementEntities = [];
    let _effectEntities = [];
    let _threatEntities = [];
    let _logEntries = [];

    /**
     * HUD 패널 생성 및 DOM 삽입
     * @param {Cesium.Viewer} viewer
     * @param {Object} viewerConfig — viewer_config.json 파싱 결과
     */
    function create(viewer, viewerConfig) {
        _viewer = viewer;
        destroy();

        _metadata = (viewerConfig && viewerConfig.metadata) || {};

        // DOM 생성
        _panelEl = document.createElement("div");
        _panelEl.id = "hud-panel";
        _panelEl.innerHTML = _buildHTML();
        document.body.appendChild(_panelEl);

        // 엔티티 참조 수집
        _collectEntities();

        // 클럭 tick 이벤트로 실시간 갱신
        _tickHandler = _viewer.clock.onTick.addEventListener(_onTick);
    }

    /**
     * HUD HTML 구조
     */
    function _buildHTML() {
        return '' +
        '<div class="hud-section">' +
        '  <div class="hud-title">DEFENSE STATUS</div>' +
        '  <div class="hud-row"><span class="hud-label">ARCH</span><span id="hud-arch" class="hud-value">' +
             (_metadata.architecture || "N/A").toUpperCase() + '</span></div>' +
        '  <div class="hud-row"><span class="hud-label">SCENARIO</span><span id="hud-scenario" class="hud-value">' +
             _formatScenario(_metadata.scenario) + '</span></div>' +
        '  <div class="hud-row"><span class="hud-label">SIM TIME</span><span id="hud-time" class="hud-value">T = 0.0s</span></div>' +
        '  <div class="hud-row"><span class="hud-label">THREATS</span><span id="hud-threats" class="hud-value">' +
             (_metadata.total_threats || 0) + '</span></div>' +
        '</div>' +
        '<div class="hud-section">' +
        '  <div class="hud-title">ENGAGEMENT</div>' +
        '  <div class="hud-row"><span class="hud-label">DETECTED</span><span id="hud-detected" class="hud-value">0</span></div>' +
        '  <div class="hud-row"><span class="hud-label">ENGAGED</span><span id="hud-engaged" class="hud-value">0</span></div>' +
        '  <div class="hud-row"><span class="hud-label">KILLED</span><span id="hud-killed" class="hud-value hud-green">0</span></div>' +
        '  <div class="hud-row"><span class="hud-label">LEAKED</span><span id="hud-leaked" class="hud-value hud-red">0</span></div>' +
        '  <div class="hud-row"><span class="hud-label">LEAK RATE</span><span id="hud-leak-rate" class="hud-value">0.0%</span></div>' +
        '</div>' +
        '<div class="hud-section">' +
        '  <div class="hud-title">ENGAGEMENT LOG</div>' +
        '  <div id="hud-log" class="hud-log"></div>' +
        '</div>';
    }

    /**
     * DataSource에서 엔티티 참조 수집
     */
    function _collectEntities() {
        _engagementEntities = [];
        _effectEntities = [];
        _threatEntities = [];

        if (!_viewer || _viewer.dataSources.length === 0) return;

        for (var d = 0; d < _viewer.dataSources.length; d++) {
            var entities = _viewer.dataSources.get(d).entities.values;
            for (var i = 0; i < entities.length; i++) {
                var id = entities[i].id || "";
                if (id.indexOf("engagement_") === 0) _engagementEntities.push(entities[i]);
                else if (id.indexOf("effect_") === 0) _effectEntities.push(entities[i]);
                else if (id.indexOf("threat_") === 0) _threatEntities.push(entities[i]);
            }
        }
    }

    /**
     * 매 클럭 tick마다 HUD 갱신
     */
    function _onTick(clock) {
        if (!_panelEl) return;

        var currentTime = clock.currentTime;
        var epoch = Cesium.JulianDate.fromIso8601("2024-01-01T00:00:00Z");
        var simTime = Cesium.JulianDate.secondsDifference(currentTime, epoch);

        // 시뮬 시간
        var timeEl = document.getElementById("hud-time");
        if (timeEl) timeEl.textContent = "T = " + simTime.toFixed(1) + "s";

        // 위협 상태 카운트 (시간 기반 availability 체크)
        var detected = 0;
        for (var t = 0; t < _threatEntities.length; t++) {
            var threat = _threatEntities[t];
            if (threat.isAvailable(currentTime)) {
                detected++;
            }
        }

        // 교전/격추 카운트 (현재 시간까지 available한 engagement/effect)
        var engaged = 0;
        var killed = 0;
        for (var e = 0; e < _engagementEntities.length; e++) {
            var eng = _engagementEntities[e];
            if (!eng.availability || eng.availability.length === 0) continue;
            var engStart = eng.availability.get(0).start;
            if (Cesium.JulianDate.lessThanOrEquals(engStart, currentTime)) {
                engaged++;
                // result 확인
                var result = _getPropertyValue(eng.properties, "result");
                if (result === "hit") killed++;
            }
        }

        // 누출 = 위협 총수 - 격추 - 현재 활성 위협 (대략적 추정)
        var totalThreats = _metadata.total_threats || _threatEntities.length;
        var leaked = Math.max(0, totalThreats - detected - killed);
        var leakRate = totalThreats > 0 ? (leaked / totalThreats * 100) : 0;

        _updateEl("hud-detected", detected);
        _updateEl("hud-engaged", engaged);
        _updateEl("hud-killed", killed);
        _updateEl("hud-leaked", leaked);
        _updateEl("hud-leak-rate", leakRate.toFixed(1) + "%");

        // 교전 로그 갱신
        _updateLog(currentTime);
    }

    /**
     * 교전 로그 갱신
     */
    function _updateLog(currentTime) {
        var logEl = document.getElementById("hud-log");
        if (!logEl) return;

        var epoch = Cesium.JulianDate.fromIso8601("2024-01-01T00:00:00Z");
        var newEntries = [];

        for (var i = 0; i < _engagementEntities.length; i++) {
            var eng = _engagementEntities[i];
            if (!eng.availability || eng.availability.length === 0) continue;

            var engStart = eng.availability.get(0).start;
            if (!Cesium.JulianDate.lessThanOrEquals(engStart, currentTime)) continue;

            var timeSec = Cesium.JulianDate.secondsDifference(engStart, epoch);
            var result = _getPropertyValue(eng.properties, "result");
            var shooterId = _getPropertyValue(eng.properties, "shooter_id") || "?";
            var threatId = _getPropertyValue(eng.properties, "threat_id") || "?";
            var timeStr = _formatTime(timeSec);
            var icon = (result === "hit") ? "\u2713" : "\u2717";

            newEntries.push({
                time: timeSec,
                text: "[" + timeStr + "] " + icon + " " + shooterId + " \u2192 " + threatId,
                isHit: result === "hit",
            });
        }

        // 시간순 정렬
        newEntries.sort(function(a, b) { return a.time - b.time; });

        // 마지막 N개만 표시
        var display = newEntries.slice(-MAX_LOG_ENTRIES);

        if (display.length !== _logEntries.length) {
            _logEntries = display;
            var html = "";
            for (var j = 0; j < display.length; j++) {
                var cls = display[j].isHit ? "log-hit" : "log-miss";
                html += '<div class="log-entry ' + cls + '">' + display[j].text + '</div>';
            }
            logEl.innerHTML = html;
            logEl.scrollTop = logEl.scrollHeight;
        }
    }

    // ── 유틸리티 ─────────────────────────────────────

    function _updateEl(id, value) {
        var el = document.getElementById(id);
        if (el) el.textContent = value;
    }

    function _formatTime(sec) {
        var m = Math.floor(sec / 60);
        var s = Math.floor(sec % 60);
        return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
    }

    function _formatScenario(s) {
        if (!s) return "N/A";
        return s.replace("scenario_", "S").replace("_saturation", ": SAT")
               .replace("_complex", ": CPLX").replace("_ew_", ": EW-")
               .replace("_sequential", ": SEQ").replace("_node_destruction", ": NODE")
               .toUpperCase();
    }

    function _getPropertyValue(props, name) {
        if (!props || !props[name]) return null;
        try {
            return props[name].getValue(Cesium.JulianDate.now());
        } catch (_) {
            return null;
        }
    }

    /**
     * HUD 패널 제거
     */
    function destroy() {
        if (_tickHandler) {
            _tickHandler();
            _tickHandler = null;
        }
        if (_panelEl && _panelEl.parentNode) {
            _panelEl.parentNode.removeChild(_panelEl);
        }
        _panelEl = null;
        _logEntries = [];
    }

    return {
        create: create,
        destroy: destroy,
    };
})();
