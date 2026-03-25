/**
 * engagement-viz.js — 교전 시각화 모듈 (요격 궤적 + 폭발 이펙트)
 *
 * CZML engagement/effect 패킷을 기반으로:
 * 1. 요격 미사일 궤적 (사수→교점 곡선, 부스터 상승 포함)
 * 2. 폭발 이펙트 (ParticleSystem, hit=구체 확대→소멸)
 * 3. 교전 연결선 (사수→위협 점선, 교전 중에만 표시)
 *
 * SSOT: 모든 교전 판정은 백엔드에서 완료됨.
 * 이 모듈은 CZML 데이터를 시각적으로 강화(enhance)만 함.
 */

/* global Cesium */

const EngagementViz = (() => {
    "use strict";

    // ── 상수 ─────────────────────────────────────────
    const HIT_COLOR = Cesium.Color.ORANGE;
    const MISS_COLOR = Cesium.Color.GRAY;
    const EXPLOSION_LIFETIME = 2.0;      // 폭발 파티클 수명 (초)
    const MISSILE_FLIGHT_TIME = 5.0;     // 요격 미사일 비행 시간 (초)
    const BOOSTER_PHASE_SEC = 1.5;       // 부스터 수직 상승 시간 (초)
    const BOOSTER_ALT_M = 3000;          // 부스터 최대 고도 (m)
    const MISSILE_TRAIL_COLOR = new Cesium.Color(1.0, 0.8, 0.2, 0.7);

    // 기본 폭발 스프라이트 — 텍스처 파일 없이 단색 원형 이미지 생성
    let _explosionImage = null;

    // ── 상태 ─────────────────────────────────────────
    let _viewer = null;
    let _missileEntities = [];
    let _explosionPrimitives = [];

    /**
     * 초기화
     * @param {Cesium.Viewer} viewer
     */
    function init(viewer) {
        _viewer = viewer;
        _explosionImage = _createParticleImage();
    }

    /**
     * 캔버스로 파티클 이미지 생성 (외부 텍스처 파일 불필요)
     */
    function _createParticleImage() {
        var canvas = document.createElement("canvas");
        canvas.width = 16;
        canvas.height = 16;
        var ctx = canvas.getContext("2d");
        var gradient = ctx.createRadialGradient(8, 8, 0, 8, 8, 8);
        gradient.addColorStop(0, "rgba(255, 200, 50, 1.0)");
        gradient.addColorStop(0.4, "rgba(255, 100, 0, 0.8)");
        gradient.addColorStop(1, "rgba(255, 0, 0, 0.0)");
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 16, 16);
        return canvas.toDataURL();
    }

    /**
     * CZML DataSource에서 교전 이벤트를 추출하여 시각 효과 생성
     * @param {Cesium.CzmlDataSource} dataSource — 로드된 CZML DataSource
     */
    function enhance(dataSource) {
        if (!_viewer || !dataSource) return;

        clear();

        var entities = dataSource.entities.values;
        var engagements = [];
        var effects = [];

        for (var i = 0; i < entities.length; i++) {
            var entity = entities[i];
            var id = entity.id || "";

            if (id.indexOf("engagement_") === 0) {
                engagements.push(entity);
            } else if (id.indexOf("effect_") === 0) {
                effects.push(entity);
            }
        }

        // 교전별 요격 미사일 궤적 + 폭발 예약
        for (var j = 0; j < engagements.length; j++) {
            var eng = engagements[j];
            var props = eng.properties;
            if (!props) continue;

            var result = _getPropertyValue(props, "result");
            var isHit = (result === "hit");

            // engagement polyline에서 사수/위협 위치 추출
            var positions = _extractPolylinePositions(eng);
            if (!positions || positions.length < 2) continue;

            var shooterPos = positions[0];
            var threatPos = positions[1];

            // 교전 시간 추출 (availability에서)
            var engTime = _getAvailabilityMidpoint(eng);
            if (!engTime) continue;

            // 요격 미사일 궤적 생성
            _createMissileTrajectory(shooterPos, threatPos, engTime, isHit);

            // 폭발 이펙트 예약 (타격 시점에)
            if (isHit) {
                _scheduleExplosion(threatPos, engTime, false);
            }
        }
    }

    /**
     * 요격 미사일 궤적 엔티티 생성
     * 부스터 상승 → 곡선 유도 → 교점
     */
    function _createMissileTrajectory(shooterPos, threatPos, engTime, isHit) {
        var startTime = Cesium.JulianDate.addSeconds(engTime, -MISSILE_FLIGHT_TIME, new Cesium.JulianDate());
        var endTime = engTime;

        // 보간 포인트 생성 (부스터 상승 포함)
        var sampledPos = new Cesium.SampledPositionProperty();
        var numPoints = 10;

        for (var i = 0; i <= numPoints; i++) {
            var t = i / numPoints;
            var time = Cesium.JulianDate.addSeconds(startTime, t * MISSILE_FLIGHT_TIME, new Cesium.JulianDate());

            var pos;
            if (t < (BOOSTER_PHASE_SEC / MISSILE_FLIGHT_TIME)) {
                // 부스터 단계: 수직 상승
                var boosterT = t / (BOOSTER_PHASE_SEC / MISSILE_FLIGHT_TIME);
                var shooterCarto = Cesium.Cartographic.fromCartesian(shooterPos);
                var altBoost = shooterCarto.height + BOOSTER_ALT_M * boosterT;
                pos = Cesium.Cartesian3.fromRadians(
                    shooterCarto.longitude, shooterCarto.latitude, altBoost
                );
            } else {
                // 유도 단계: 사수→위협 보간 (곡선)
                var guideT = (t - BOOSTER_PHASE_SEC / MISSILE_FLIGHT_TIME) /
                             (1 - BOOSTER_PHASE_SEC / MISSILE_FLIGHT_TIME);

                // 약간의 곡선을 위해 고도 bump 추가
                var midAltBump = BOOSTER_ALT_M * (1 - guideT) * 0.5;
                var lerped = Cesium.Cartesian3.lerp(shooterPos, threatPos, guideT, new Cesium.Cartesian3());
                var lerpedCarto = Cesium.Cartographic.fromCartesian(lerped);
                pos = Cesium.Cartesian3.fromRadians(
                    lerpedCarto.longitude, lerpedCarto.latitude,
                    lerpedCarto.height + midAltBump
                );
            }

            sampledPos.addSample(time, pos);
        }

        sampledPos.setInterpolationOptions({
            interpolationDegree: 3,
            interpolationAlgorithm: Cesium.LagrangePolynomialApproximation,
        });

        var missileEntity = _viewer.entities.add({
            availability: new Cesium.TimeIntervalCollection([
                new Cesium.TimeInterval({ start: startTime, stop: endTime }),
            ]),
            position: sampledPos,
            point: {
                pixelSize: 5,
                color: isHit ? HIT_COLOR : MISS_COLOR,
            },
            path: {
                material: new Cesium.ColorMaterialProperty(MISSILE_TRAIL_COLOR),
                width: 1.5,
                leadTime: 0,
                trailTime: MISSILE_FLIGHT_TIME,
            },
        });

        _missileEntities.push(missileEntity);
    }

    /**
     * ParticleSystem 폭발 이펙트 예약
     * @param {Cesium.Cartesian3} position — 폭발 위치
     * @param {Cesium.JulianDate} time — 폭발 시점
     * @param {boolean} isLarge — 대형 폭발 여부
     */
    function _scheduleExplosion(position, time, isLarge) {
        // 클럭 tick 이벤트로 시점 감시
        var handler = _viewer.clock.onTick.addEventListener(function(clock) {
            var diff = Cesium.JulianDate.secondsDifference(clock.currentTime, time);
            if (diff >= 0 && diff < 1.0) {
                handler();  // 리스너 제거
                _createExplosion(position, isLarge);
            }
        });
    }

    /**
     * 즉시 폭발 이펙트 생성
     */
    function _createExplosion(position, isLarge) {
        if (!_viewer || !_explosionImage) return;

        var modelMatrix = Cesium.Transforms.eastNorthUpToFixedFrame(position);

        var particleSystem = _viewer.scene.primitives.add(new Cesium.ParticleSystem({
            image: _explosionImage,
            emitter: new Cesium.SphereEmitter(isLarge ? 4.0 : 2.0),
            emissionRate: 0,
            bursts: [
                new Cesium.ParticleBurst({ time: 0.0, minimum: 150, maximum: 300 }),
            ],
            startColor: Cesium.Color.YELLOW.withAlpha(1.0),
            endColor: Cesium.Color.RED.withAlpha(0.0),
            startScale: isLarge ? 3.0 : 1.5,
            endScale: isLarge ? 15.0 : 8.0,
            minimumSpeed: isLarge ? 30.0 : 15.0,
            maximumSpeed: isLarge ? 60.0 : 35.0,
            minimumParticleLife: 0.4,
            maximumParticleLife: 1.2,
            lifetime: EXPLOSION_LIFETIME,
            loop: false,
            sizeInMeters: true,
            modelMatrix: modelMatrix,
        }));

        _explosionPrimitives.push(particleSystem);

        // 자동 제거 (메모리 관리)
        setTimeout(function() {
            if (_viewer && !_viewer.isDestroyed()) {
                _viewer.scene.primitives.remove(particleSystem);
                var idx = _explosionPrimitives.indexOf(particleSystem);
                if (idx >= 0) _explosionPrimitives.splice(idx, 1);
            }
        }, (EXPLOSION_LIFETIME + 1) * 1000);
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

    function _extractPolylinePositions(entity) {
        if (!entity.polyline || !entity.polyline.positions) return null;
        try {
            return entity.polyline.positions.getValue(Cesium.JulianDate.now());
        } catch (_) {
            return null;
        }
    }

    function _getAvailabilityMidpoint(entity) {
        if (!entity.availability || entity.availability.length === 0) return null;
        var interval = entity.availability.get(0);
        var start = interval.start;
        var stop = interval.stop;
        var midSec = Cesium.JulianDate.secondsDifference(stop, start) / 2;
        return Cesium.JulianDate.addSeconds(start, midSec, new Cesium.JulianDate());
    }

    /**
     * 모든 교전 시각화 요소 제거
     */
    function clear() {
        if (!_viewer) return;

        _missileEntities.forEach(function(e) {
            _viewer.entities.remove(e);
        });
        _missileEntities = [];

        _explosionPrimitives.forEach(function(p) {
            if (_viewer.scene && !_viewer.isDestroyed()) {
                _viewer.scene.primitives.remove(p);
            }
        });
        _explosionPrimitives = [];
    }

    return {
        init: init,
        enhance: enhance,
        clear: clear,
    };
})();
