/**
 * app.js — KIDA ADSIM 3D Viewer 메인 앱
 *
 * SSOT: 프론트엔드는 백엔드가 생성한 CZML/JSON만 렌더링.
 * 시뮬레이션 로직(교전 판정, 이동 계산 등) 절대 수행하지 않음.
 */

/* global Cesium, CZMLLoader, RadarVolumes, EngagementViz, TopologyViz */

const App = (() => {
    "use strict";

    // ── 설정 ─────────────────────────────────────────
    const CONFIG = {
        CESIUM_ION_TOKEN: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiI1MTMyYzU3Yi0zZDE1LTQzNTYtODhlNi0yMDdkM2UzMjQwMTIiLCJpZCI6Mzk3OTczLCJpYXQiOjE3NzI2MzQyOTB9.D2d_S6YUnRW6ppk8PYYKQs2J-aYT4DzOF3ipDMHsqnI",
        DEFAULT_CENTER: { lon: 127.0, lat: 37.0, alt: 300000 },
        CZML_BASE_PATH: "../output/",
        DEFAULT_SCENARIO: "scenario_1_saturation",
        DEFAULT_ARCH: "killweb",
        DEFAULT_SPEED: 5,
    };

    // 카메라 프리셋 (viewer_config.json에서 로드 가능, 기본값은 하드코딩)
    const CAMERA_PRESETS = {
        overview: { lon: 127.0, lat: 37.0, alt: 300000, heading: 0, pitch: -55 },
        tactical: { lon: 127.03, lat: 36.8, alt: 130000, heading: 0, pitch: -30 },
        horizontal: { lon: 126.65, lat: 37.82, alt: 60000, heading: 90, pitch: -4 },
        battery: { lon: 127.03, lat: 37.77, alt: 20000, heading: 0, pitch: -38 },
    };

    // ── 상태 ─────────────────────────────────────────
    let _viewer = null;
    let _viewerLeft = null;
    let _viewerRight = null;
    let _currentScenario = CONFIG.DEFAULT_SCENARIO;
    let _currentArch = CONFIG.DEFAULT_ARCH;
    let _compareMode = false;
    let _viewerConfig = null;

    // ── 초기화 ───────────────────────────────────────

    function start() {
        Cesium.Ion.defaultAccessToken = CONFIG.CESIUM_ION_TOKEN;

        // 메인 뷰어 생성
        _viewer = new Cesium.Viewer("cesiumContainer", {
            terrain: Cesium.Terrain.fromWorldTerrain(),
            baseLayerPicker: false,
            geocoder: false,
            homeButton: true,
            sceneModePicker: false,
            navigationHelpButton: false,
            animation: false,
            timeline: true,
            fullscreenButton: false,
            infoBox: false,
            selectionIndicator: true,
        });

        // 카메라 → 한반도 중심
        _flyToPreset("overview");

        // 모듈 초기화
        CZMLLoader.init(_viewer);
        EngagementViz.init(_viewer);
        TopologyViz.init(_viewer);

        // UI 이벤트 바인딩
        _bindEvents();

        // 기본 CZML 로드
        _loadScenario(_currentScenario, _currentArch);
    }

    // ── CZML 로드 ────────────────────────────────────

    async function _loadScenario(scenario, arch) {
        _showLoading(true);

        try {
            const czmlUrl = CONFIG.CZML_BASE_PATH + scenario + "_" + arch + ".czml";
            const configUrl = CONFIG.CZML_BASE_PATH + "viewer_config_" + arch + ".json";

            const dataSource = await CZMLLoader.loadCZML(czmlUrl);

            // viewer_config.json 로드 (에러 시 무시)
            try {
                const resp = await fetch(configUrl);
                if (resp.ok) {
                    _viewerConfig = await resp.json();
                }
            } catch (_) {
                // viewer_config 없어도 동작
            }

            // v0.6.3: 3D 시각화 모듈 적용
            _applyEnhancements(dataSource);

            // 재생 속도 설정
            CZMLLoader.setPlaybackSpeed(CONFIG.DEFAULT_SPEED);
        } catch (err) {
            console.warn("CZML load failed:", err.message);
        }

        _showLoading(false);
    }

    // ── 비교 모드 ────────────────────────────────────

    async function _enterCompareMode() {
        _compareMode = true;
        document.getElementById("viewer-container").classList.add("hidden");
        document.getElementById("compare-container").classList.remove("hidden");
        document.getElementById("btn-compare").classList.add("active");
        document.getElementById("btn-compare").textContent = "Exit Compare";

        // 기존 뷰어 파괴
        if (_viewer) {
            _viewer.destroy();
            _viewer = null;
        }

        // 좌: Linear, 우: Kill Web
        const viewerOpts = {
            terrain: Cesium.Terrain.fromWorldTerrain(),
            baseLayerPicker: false,
            geocoder: false,
            homeButton: false,
            sceneModePicker: false,
            navigationHelpButton: false,
            animation: false,
            timeline: false,
            fullscreenButton: false,
            infoBox: false,
            selectionIndicator: false,
        };

        _viewerLeft = new Cesium.Viewer("cesiumLeft", viewerOpts);
        _viewerRight = new Cesium.Viewer("cesiumRight", viewerOpts);

        // 양쪽 카메라 초기 위치
        _flyToPresetOn(_viewerLeft, "overview");
        _flyToPresetOn(_viewerRight, "overview");

        // CZML 로드
        _showLoading(true);
        const czmlLinear = CONFIG.CZML_BASE_PATH + _currentScenario + "_linear.czml";
        const czmlKillweb = CONFIG.CZML_BASE_PATH + _currentScenario + "_killweb.czml";

        try {
            const [dsLeft, dsRight] = await Promise.all([
                Cesium.CzmlDataSource.load(czmlLinear),
                Cesium.CzmlDataSource.load(czmlKillweb),
            ]);
            _viewerLeft.dataSources.add(dsLeft);
            _viewerRight.dataSources.add(dsRight);

            // 클럭 동기화 (좌측 기준)
            _syncCompareClocks(dsLeft);
        } catch (err) {
            console.warn("Compare mode CZML load failed:", err.message);
        }
        _showLoading(false);

        // 카메라 동기화 시작
        _startCameraSync();
    }

    function _exitCompareMode() {
        _compareMode = false;
        document.getElementById("compare-container").classList.add("hidden");
        document.getElementById("viewer-container").classList.remove("hidden");
        document.getElementById("btn-compare").classList.remove("active");
        document.getElementById("btn-compare").textContent = "Compare Mode";

        // 비교 뷰어 파괴
        if (_viewerLeft) { _viewerLeft.destroy(); _viewerLeft = null; }
        if (_viewerRight) { _viewerRight.destroy(); _viewerRight = null; }

        // 메인 뷰어 재생성
        _viewer = new Cesium.Viewer("cesiumContainer", {
            terrain: Cesium.Terrain.fromWorldTerrain(),
            baseLayerPicker: false,
            geocoder: false,
            homeButton: true,
            sceneModePicker: false,
            navigationHelpButton: false,
            animation: false,
            timeline: true,
            fullscreenButton: false,
            infoBox: false,
            selectionIndicator: true,
        });

        CZMLLoader.init(_viewer);
        EngagementViz.init(_viewer);
        TopologyViz.init(_viewer);
        _flyToPreset("overview");
        _loadScenario(_currentScenario, _currentArch);
    }

    function _syncCompareClocks(dataSource) {
        const dsClock = dataSource.clock;
        if (!dsClock) return;

        [_viewerLeft, _viewerRight].forEach(function(v) {
            v.clock.startTime = dsClock.startTime;
            v.clock.stopTime = dsClock.stopTime;
            v.clock.currentTime = dsClock.startTime.clone();
            v.clock.clockRange = Cesium.ClockRange.LOOP_STOP;
            v.clock.multiplier = CONFIG.DEFAULT_SPEED;
            v.clock.shouldAnimate = false;
        });
    }

    let _cameraSyncHandler = null;

    function _startCameraSync() {
        if (_cameraSyncHandler) return;

        let _syncing = false;

        function syncFrom(source, target) {
            if (_syncing) return;
            _syncing = true;

            const cam = source.camera;
            target.camera.setView({
                destination: cam.positionWC.clone(),
                orientation: {
                    heading: cam.heading,
                    pitch: cam.pitch,
                    roll: cam.roll,
                },
            });

            // 시간 동기화
            target.clock.currentTime = source.clock.currentTime.clone();
            target.clock.shouldAnimate = source.clock.shouldAnimate;
            target.clock.multiplier = source.clock.multiplier;

            _syncing = false;
        }

        // 좌측 변경 → 우측 동기
        _viewerLeft.camera.changed.addEventListener(function() {
            if (_viewerRight) syncFrom(_viewerLeft, _viewerRight);
        });
        _viewerLeft.camera.moveEnd.addEventListener(function() {
            if (_viewerRight) syncFrom(_viewerLeft, _viewerRight);
        });

        // 클럭 동기화 (매 tick)
        _cameraSyncHandler = _viewerLeft.clock.onTick.addEventListener(function() {
            if (_viewerRight && _viewerLeft.clock.shouldAnimate) {
                _viewerRight.clock.currentTime = _viewerLeft.clock.currentTime.clone();
            }
        });
    }

    // ── 카메라 프리셋 ────────────────────────────────

    function _flyToPreset(presetName) {
        if (!_viewer) return;
        _flyToPresetOn(_viewer, presetName);
    }

    function _flyToPresetOn(viewer, presetName) {
        const p = (_viewerConfig && _viewerConfig.camera_presets && _viewerConfig.camera_presets[presetName])
            ? _viewerConfig.camera_presets[presetName]
            : CAMERA_PRESETS[presetName];

        if (!p) return;

        viewer.camera.flyTo({
            destination: Cesium.Cartesian3.fromDegrees(p.lon, p.lat, p.alt),
            orientation: {
                heading: Cesium.Math.toRadians(p.heading || 0),
                pitch: Cesium.Math.toRadians(p.pitch || -90),
                roll: 0,
            },
            duration: 1.5,
        });
    }

    // ── 엔티티 선택 ──────────────────────────────────

    function _setupEntitySelection(viewer) {
        const handler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);

        handler.setInputAction(function(click) {
            const picked = viewer.scene.pick(click.position);
            if (Cesium.defined(picked) && Cesium.defined(picked.id)) {
                const entity = picked.id;
                _showEntityInfo(entity);
            } else {
                _hideEntityInfo();
            }
        }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
    }

    function _showEntityInfo(entity) {
        const panel = document.getElementById("info-panel");
        const title = document.getElementById("info-panel-title");
        const content = document.getElementById("info-panel-content");

        title.textContent = entity.name || entity.id;
        content.innerHTML = CZMLLoader.formatEntityInfo(entity);
        panel.classList.remove("hidden");
    }

    function _hideEntityInfo() {
        document.getElementById("info-panel").classList.add("hidden");
    }

    // ── UI 이벤트 ────────────────────────────────────

    function _bindEvents() {
        // 시나리오 선택
        document.getElementById("scenario-select").addEventListener("change", function(e) {
            _currentScenario = e.target.value;
            if (_compareMode) {
                _exitCompareMode();
                _enterCompareMode();
            } else {
                _loadScenario(_currentScenario, _currentArch);
            }
        });

        // 아키텍처 토글
        document.getElementById("btn-linear").addEventListener("click", function() {
            _setArchitecture("linear");
        });
        document.getElementById("btn-killweb").addEventListener("click", function() {
            _setArchitecture("killweb");
        });

        // 비교 모드
        document.getElementById("btn-compare").addEventListener("click", function() {
            if (_compareMode) {
                _exitCompareMode();
            } else {
                _enterCompareMode();
            }
        });

        // 재생/일시정지
        document.getElementById("btn-play-pause").addEventListener("click", function() {
            if (_compareMode) {
                // 비교 모드: 양쪽 동시
                if (_viewerLeft) {
                    const playing = !_viewerLeft.clock.shouldAnimate;
                    _viewerLeft.clock.shouldAnimate = playing;
                    if (_viewerRight) _viewerRight.clock.shouldAnimate = playing;
                    this.innerHTML = playing ? "&#9646;&#9646;" : "&#9654;";
                }
            } else {
                const playing = CZMLLoader.togglePlayPause();
                this.innerHTML = playing ? "&#9646;&#9646;" : "&#9654;";
            }
        });

        // 속도 조절
        document.getElementById("speed-select").addEventListener("change", function(e) {
            const speed = parseInt(e.target.value, 10);
            if (_compareMode) {
                if (_viewerLeft) _viewerLeft.clock.multiplier = speed;
                if (_viewerRight) _viewerRight.clock.multiplier = speed;
            } else {
                CZMLLoader.setPlaybackSpeed(speed);
            }
        });

        // 카메라 프리셋
        document.querySelectorAll(".preset-btn").forEach(function(btn) {
            btn.addEventListener("click", function() {
                const preset = this.getAttribute("data-preset");
                if (_compareMode) {
                    if (_viewerLeft) _flyToPresetOn(_viewerLeft, preset);
                    if (_viewerRight) _flyToPresetOn(_viewerRight, preset);
                } else {
                    _flyToPreset(preset);
                }
            });
        });

        // 오버레이 토글
        document.getElementById("btn-toggle-radar").addEventListener("click", function() {
            var show = RadarVolumes.toggle();
            this.classList.toggle("active", show);
        });
        document.getElementById("btn-toggle-topo").addEventListener("click", function() {
            var show = TopologyViz.toggle();
            this.classList.toggle("active", show);
        });

        // 레이더 방위각 슬라이더
        document.getElementById("radar-azimuth").addEventListener("input", function() {
            var az = parseInt(this.value, 10);
            document.getElementById("radar-azimuth-val").innerHTML = az + "&deg;";
            RadarVolumes.updateAzimuth(az);
        });

        // 정보 패널 닫기
        document.getElementById("info-panel-close").addEventListener("click", _hideEntityInfo);

        // 엔티티 선택 핸들러
        _setupEntitySelection(_viewer);
    }

    function _setArchitecture(arch) {
        _currentArch = arch;

        // UI 업데이트
        document.getElementById("btn-linear").classList.toggle("active", arch === "linear");
        document.getElementById("btn-killweb").classList.toggle("active", arch === "killweb");

        if (!_compareMode) {
            _loadScenario(_currentScenario, _currentArch);
        }
    }

    // ── v0.6.3 시각화 모듈 통합 ────────────────────

    function _applyEnhancements(dataSource) {
        if (!_viewer || !dataSource) return;

        // 레이더 볼륨 (viewer_config 필요)
        RadarVolumes.clear();
        if (_viewerConfig) {
            RadarVolumes.create(_viewer, _viewerConfig);
        }

        // 교전 시각화 (요격 궤적 + 폭발)
        EngagementViz.init(_viewer);
        EngagementViz.enhance(dataSource);

        // 토폴로지 스타일 강화
        TopologyViz.init(_viewer);
        TopologyViz.enhance(dataSource);
    }

    function _showLoading(show) {
        const el = document.getElementById("loading-indicator");
        el.classList.toggle("hidden", !show);
    }

    // ── 공개 인터페이스 ──────────────────────────────

    return { start };
})();

// 페이지 로드 시 앱 시작
document.addEventListener("DOMContentLoaded", App.start);
