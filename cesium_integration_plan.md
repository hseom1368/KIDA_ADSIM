# KIDA_ADSIM × CesiumJS 3D 시각화 통합 작업 계획

> **문서 유형**: Agentic Coding 기반 Spec-driven Development 작업 계획서
> **작성일**: 2026-03-24
> **기반 버전**: KIDA_ADSIM v0.5.1 + CesiumJS Capabilities 분석 보고서
> **목표**: Python 방공 시뮬레이션 백엔드와 CesiumJS 3D 프론트엔드의 통합

---

## 1. 문서 목적 및 Agentic Coding 설계 원칙

### 1.1 이 문서가 존재하는 이유

이 문서는 **AI 코딩 에이전트(Claude Code 등)가 각 작업을 자율적으로 수행**할 수 있도록 설계된 Spec-driven 작업 계획이다. 일반적인 개발 계획서와 다른 점은:

1. **각 Task가 독립적으로 실행 가능** — 에이전트가 선행 작업의 맥락 없이도 해당 Task만 읽고 구현 가능
2. **입력/출력이 명시적** — "무엇을 받아서 무엇을 만드는가"가 코드 수준으로 정의됨
3. **검증 기준이 자동화 가능** — 모든 Acceptance Criteria가 `pytest` 또는 CLI 명령으로 검증 가능
4. **의존성 그래프가 명확** — 어떤 Task가 어떤 Task를 선행 조건으로 요구하는지 DAG로 표현

### 1.2 Spec-driven Development 원칙

```
[Spec 문서] → [테스트 먼저 작성] → [구현] → [검증] → [Spec 갱신]
```

| 원칙 | 적용 방법 |
|------|----------|
| **Contract First** | 각 모듈의 public interface를 Spec에 먼저 정의 → 구현은 해당 계약을 충족 |
| **Test Before Code** | Acceptance Criteria → pytest 테스트 → 구현 코드 순서 |
| **Incremental Verification** | 각 Task 완료 시 기존 146개 테스트 + 신규 테스트 전부 PASS |
| **Immutable Baseline** | seed=42 시나리오 1 성능 기준선 변경 불가 (시뮬레이션 로직 변경 금지) |
| **Single Responsibility per Task** | 하나의 Task는 하나의 모듈 또는 하나의 관심사만 변경 |

### 1.3 Single Source of Truth (SSOT) 아키텍처 원칙

이 프로젝트의 **가장 중요한 아키텍처 불변 조건(Architectural Invariant)**:

```
┌─────────────────────────────────────────────────────────────┐
│  모든 교전 판정, 이동 좌표 계산, 탄약 관리, 킬체인 지연 시간은  │
│  오직 Python 백엔드(KIDA_ADSIM)에서만 수행한다.               │
│                                                             │
│  프론트엔드(CesiumJS)는 자체 연산(Math.random(), 충돌 판정,    │
│  난수 기반 판정 등)을 절대 수행하지 않으며, 백엔드가 생성한     │
│  CZML/JSON 데이터를 시간에 맞춰 렌더링(보간 + 이펙트)만 한다. │
└─────────────────────────────────────────────────────────────┘
```

**이 원칙이 보장하는 것**:
- 시뮬레이션 재현성: 동일 seed → 동일 CZML → 동일 시각화 (프론트엔드 난수 없음)
- 검증 용이성: 시뮬레이션 로직은 pytest로만 검증, 프론트엔드는 시각적 확인만
- 분리 개발: Python 개발자와 JS 개발자가 스키마 계약(Contract)만 공유하면 독립 작업 가능

**위반 감지 방법**: 프론트엔드 JS 코드에 아래가 존재하면 SSOT 위반:
```
금지 패턴: Math.random(), new Date().getTime() (시드 없는 난수/시간)
금지 패턴: if (distance < killRadius) (충돌 판정)
금지 패턴: pk * rangeFactor * maneuverPenalty (Pk 계산)
허용 패턴: Cesium.Math.lerp() (보간), Cesium.Color.fromAlpha() (렌더링)
```

### 1.4 Agentic Coding 컨벤션

에이전트가 이 문서를 읽고 작업할 때 따라야 할 규칙:

**작업 흐름 규칙**:
```
1. Task를 시작하기 전에 [선행 조건]의 파일이 존재하는지 확인
2. [Acceptance Criteria]를 pytest 테스트로 먼저 작성 (TDD)
3. 구현 후 `python -m pytest tests/ -v` 전체 통과 확인
4. 변경된 파일 목록과 테스트 결과를 Task 완료 기록에 남김
5. CHANGELOG.md, CLAUDE.md 갱신은 Phase 완료 시 일괄 수행
```

**코드 품질 규칙 (에이전트 System Prompt로 주입)**:
```
RULE-1 [No Magic Numbers]: 코드 내 매직 넘버 금지. 
       상수는 config.py 또는 모듈 상단 상수로 분리할 것.
RULE-2 [Context Isolation]: 프론트엔드(HTML/JS) 수정 시 
       백엔드 Python 코드의 로직을 절대 건드리지 말 것.
RULE-3 [Type Hinting]: Python 코드에 엄격한 타입 힌팅(typing) 사용.
       반환값 타입, 파라미터 타입, 딕셔너리 키 구조를 명시할 것.
RULE-4 [Schema Compliance]: CZML/JSON 출력은 반드시 
       섹션 3.3의 정규 스키마와 100% 일치해야 함.
RULE-5 [SSOT Compliance]: 프론트엔드에 Math.random(), 
       충돌 판정, Pk 계산 등 시뮬레이션 로직을 절대 작성하지 말 것.
RULE-6 [Pydantic Runtime Ban]: 시뮬레이션 step() 루프 내에서 
       Pydantic 객체 생성/검증 호출 금지 (CLAUDE.md 참조).
```

---

## 2. 현재 상태 분석 (As-Is)

### 2.1 KIDA_ADSIM v0.5.1 아키텍처

```
config.py → ontology.py → registry.py → strategies.py → model.py → agents.py
(파라미터)   (Pydantic 타입)  (타입 레지스트리)  (전략 패턴)     (시뮬엔진)    (Mesa 에이전트)
```

**시뮬레이션 좌표계**: 200×200km 평면 직교 좌표 (km 단위)
**시간 해상도**: 5초 스텝
**출력 형식**: Python dict (`run_full()` 반환값) + CSV (Monte Carlo 배치)

### 2.2 기존 Cesium 연동 자산

| 자산 | 위치 | 상태 | 비고 |
|------|------|------|------|
| `exporters.py` (CZMLExporter) | `modules/exporters.py` | v0.5.1 구현 완료 | 기본 CZML 패킷 생성, 테스트 8개 |
| `patriot-sim.html` | 별도 파일 | 독립 동작 | CesiumJS 1.111, PNG 유도, 3D 구면 부채꼴 |
| Cesium Ion 토큰 | patriot-sim.html 내 | 유효 | 공개 가능 토큰 |

### 2.3 Gap 분석

| 영역 | 현재 (As-Is) | 목표 (To-Be) | Gap |
|------|-------------|-------------|-----|
| **좌표계** | km 평면 직교 | WGS84 경위도+고도 | `_sim_to_geo()` 존재하나 검증 미완 |
| **CZML 궤적** | `cartographicDegrees` 시계열 | Lagrange 보간 + `path` + `model` | 보간 알고리즘 미설정, glTF 미사용 |
| **센서 볼륨** | 2D `ellipse` (CZML) | 3D `EllipsoidGeometry` 구면 부채꼴 | patriot-sim.html에 구현됨, CZML에 미반영 |
| **요격 시각화** | 미구현 | PNG 유도 궤적 + 폭발 ParticleSystem | patriot-sim.html에 부분 구현 |
| **렌더링 성능** | Entity API | Primitive API (PointPrimitive/Polyline Collection) | 미착수 |
| **실시간 데이터** | 미구현 | WebSocket + ADS-B (선택) | 아키텍처 설계 필요 |
| **통합 뷰어** | patriot-sim.html (독립) | KIDA_ADSIM 결과를 로드하는 통합 뷰어 | 프레임워크 구축 필요 |

---

## 3. 목표 아키텍처 (To-Be)

### 3.1 전체 시스템 구조

```
[Python Backend]                          [CesiumJS Frontend]
                                          
KIDA_ADSIM v0.5.1                         cesium-viewer/
├── model.py (시뮬엔진)                      ├── index.html (통합 뷰어)
│   └── run_full(record_snapshots=True)     ├── js/
│       → result dict                       │   ├── app.js (메인 앱)
├── exporters.py (v2)                       │   ├── czml-loader.js (CZML 로더)
│   ├── CZMLExporter (Enhanced)             │   ├── radar-volumes.js (3D 센서 볼륨)
│   │   ├── 궤적 (Lagrange 보간)              │   ├── engagement-viz.js (교전 시각화)
│   │   ├── 센서 볼륨 (구면 부채꼴 메타데이터)    │   ├── hud-panel.js (Military HUD)
│   │   ├── 교전 이벤트 (요격 궤적)             │   └── performance.js (Primitive 최적화)
│   │   └── C2 네트워크 (토폴로지 연결선)        └── assets/
│   └── CesiumConfigExporter (신규)               ├── models/ (glTF 미사일/레이더)
│       └── 뷰어 설정 JSON 내보내기                └── textures/ (폭발 스프라이트)
│                                           
└── output/                                로드 경로:
    ├── sim_result.czml                    index.html → fetch("output/sim_result.czml")
    └── viewer_config.json                            → CzmlDataSource.load()
```

### 3.2 데이터 흐름

```
1. Python: model.run_full(record_snapshots=True) → result dict
2. Python: CZMLExporter(result).export("output/sim_result.czml")
3. Python: CesiumConfigExporter(result).export("output/viewer_config.json")
4. Browser: index.html → fetch CZML → CzmlDataSource.load()
5. Browser: viewer_config.json → 센서 볼륨/HUD 파라미터 적용
6. Browser: 사용자 인터랙션 (재생/일시정지, 시점 전환, 위협 선택)
```

### 3.3 정규 데이터 스키마 레퍼런스 (Canonical Schema)

**에이전트는 CZML/JSON 출력 시 반드시 이 섹션의 스키마를 준수해야 한다.**
각 Task의 Spec은 이 섹션을 참조하며, 스키마 불일치는 Acceptance Criteria 실패로 간주한다.

#### 3.3.1 CZML Document 패킷 (필수, 파일 최상단)
```json
{
    "id": "document",
    "name": "KIDA_ADSIM",
    "version": "1.0",
    "clock": {
        "interval": "2024-01-01T00:00:00Z/2024-01-01T00:30:00Z",
        "currentTime": "2024-01-01T00:00:00Z",
        "multiplier": 10
    }
}
```

#### 3.3.2 위협 궤적 (Threat Trajectory) 패킷
```json
{
    "id": "threat_{unique_id}",
    "name": "{threat_type}_{unique_id}",
    "availability": "{start_iso}/{end_iso}",
    "position": {
        "epoch": "2024-01-01T00:00:00Z",
        "cartographicDegrees": [
            0,   127.55, 37.90, 35000,
            30,  127.40, 37.70, 28000,
            60,  127.30, 37.55, 15000
        ],
        "interpolationAlgorithm": "LAGRANGE",
        "interpolationDegree": 5
    },
    "point": {
        "color": { "rgba": [255, 0, 0, 255] },
        "pixelSize": 8
    },
    "path": {
        "material": { "solidColor": { "color": { "rgba": [255, 0, 0, 200] } } },
        "width": 2,
        "leadTime": 0,
        "trailTime": 300
    },
    "properties": {
        "type": { "string": "SRBM" },
        "status": { "string": "flying" }
    }
}
```

**위협 유형별 보간 설정**:
| 위협 유형 | interpolationAlgorithm | interpolationDegree | 색상 RGBA |
|-----------|----------------------|---------------------|-----------|
| SRBM | LAGRANGE | 5 | [255, 0, 0, 255] 빨강 |
| CRUISE_MISSILE | LINEAR | 1 | [255, 165, 0, 255] 주황 |
| AIRCRAFT | LAGRANGE | 3 | [255, 255, 0, 255] 노랑 |
| UAS | LINEAR | 1 | [128, 0, 128, 255] 보라 |

#### 3.3.3 교전 이벤트 (Engagement Event) 패킷
```json
{
    "id": "engagement_{threat_id}_{shooter_id}",
    "name": "요격: {shooter_id} → {threat_id}",
    "availability": "{engagement_start_iso}/{engagement_end_iso}",
    "polyline": {
        "positions": {
            "cartographicDegrees": [
                127.03, 37.82, 150,
                127.30, 37.55, 15000
            ]
        },
        "width": 2,
        "material": { "solidColor": { "color": { "rgba": [0, 255, 136, 200] } } }
    },
    "properties": {
        "type": { "string": "ENGAGEMENT" },
        "result": { "string": "HIT" },
        "shooter_id": { "string": "PAT_1" },
        "threat_id": { "string": "threat_1001" },
        "pk_actual": { "number": 0.72 }
    }
}
```

**교전 결과별 이펙트 마커 패킷** (교전 패킷과 별도):
```json
{
    "id": "effect_{engagement_id}",
    "availability": "{impact_time_iso}/{impact_time_plus_3s_iso}",
    "position": { "cartographicDegrees": [127.30, 37.55, 15000] },
    "point": {
        "color": { "rgba": [255, 200, 0, 255] },
        "pixelSize": 20,
        "outlineColor": { "rgba": [255, 100, 0, 255] },
        "outlineWidth": 3
    },
    "properties": {
        "type": { "string": "INTERCEPT_SUCCESS" }
    }
}
```

| 이벤트 유형 | properties.type | 마커 색상 | pixelSize |
|------------|----------------|----------|-----------|
| 요격 성공 | INTERCEPT_SUCCESS | [255, 200, 0] 주황 | 20 |
| 요격 실패 | INTERCEPT_FAIL | [128, 128, 128] 회색 | 12 |
| 지면 타격 | GROUND_IMPACT | [255, 0, 0] 빨강 | 25 |

#### 3.3.4 센서/사수/C2 고정 엔티티 패킷
```json
{
    "id": "sensor_{agent_id}",
    "name": "{agent_id}",
    "position": { "cartographicDegrees": [127.88, 38.43, 0] },
    "point": {
        "color": { "rgba": [0, 128, 255, 180] },
        "pixelSize": 10
    },
    "ellipse": {
        "semiMajorAxis": 170000,
        "semiMinorAxis": 170000,
        "material": { "solidColor": { "color": { "rgba": [0, 128, 255, 30] } } }
    },
    "properties": {
        "category": { "string": "sensor" },
        "sensor_type": { "string": "PATRIOT_RADAR" },
        "detection_range_km": { "number": 170 },
        "tracking_capacity": { "number": 100 }
    }
}
```

#### 3.3.5 C2 토폴로지 연결선 패킷
```json
{
    "id": "link_{source_id}_{target_id}",
    "name": "{source_id} → {target_id}",
    "availability": "{active_start_iso}/{active_end_iso}",
    "polyline": {
        "positions": {
            "cartographicDegrees": [
                127.10, 38.40, 500,
                127.00, 38.26, 500
            ]
        },
        "width": 1.5,
        "material": {
            "polylineDash": {
                "color": { "rgba": [255, 255, 255, 150] },
                "dashLength": 16
            }
        }
    },
    "properties": {
        "link_type": { "string": "sensor_to_c2" },
        "architecture": { "string": "linear" }
    }
}
```

#### 3.3.6 viewer_config.json 전체 스키마
```json
{
    "metadata": {
        "architecture": "killweb",
        "scenario": "scenario_1_saturation",
        "sim_time_total": 450.0,
        "total_threats": 45,
        "version": "0.7",
        "generated_at": "2026-03-24T12:00:00Z"
    },
    "camera_presets": {
        "overview": {
            "lon": 127.0, "lat": 37.0, "alt": 300000,
            "heading": 0, "pitch": -55, "roll": 0
        },
        "tactical": {
            "lon": 127.03, "lat": 36.8, "alt": 130000,
            "heading": 0, "pitch": -30, "roll": 0
        },
        "horizontal": {
            "lon": 126.65, "lat": 37.82, "alt": 60000,
            "heading": 90, "pitch": -4, "roll": 0
        },
        "battery": {
            "lon": 127.03, "lat": 37.77, "alt": 20000,
            "heading": 0, "pitch": -38, "roll": 0
        }
    },
    "radar_volumes": [
        {
            "sensor_id": "PAT_RADAR_1",
            "position": { "lon": 127.88, "lat": 38.17, "alt": 0 },
            "detection_range_m": 170000,
            "engagement_range_m": 40000,
            "azimuth_center_deg": 0,
            "azimuth_half_deg": 60,
            "elevation_max_deg": 90,
            "color_detect": [0, 136, 255, 64],
            "color_engage": [0, 255, 136, 115]
        }
    ],
    "batteries": [
        {
            "battery_id": "PAT_BATTERY_ALPHA",
            "radar_id": "PAT_RADAR_1",
            "ecs_id": "TOC_PAT",
            "launchers": [
                {
                    "id": "PAT_1",
                    "position": { "lon": 127.77, "lat": 37.99, "alt": 0 },
                    "initial_ammo": 16,
                    "weapon_type": "PATRIOT_PAC3"
                }
            ]
        }
    ],
    "engagement_policy": {
        "optimal_pk_threshold": 0.30,
        "emergency_pk_threshold": 0.10,
        "must_engage_distance_km": 30.0,
        "max_simultaneous_shooters": {
            "SRBM": 3, "CRUISE_MISSILE": 2, "AIRCRAFT": 1, "UAS": 1
        }
    },
    "hud_config": {
        "show_radar_fov": true,
        "show_engagement_range": true,
        "show_ammo_bars": true,
        "show_engagement_log": true,
        "show_topology_links": true,
        "log_max_entries": 14
    },
    "coordinate_reference": {
        "base_lon": 127.0,
        "base_lat": 37.0,
        "km_to_lat": 0.009,
        "km_to_lon": 0.011,
        "note": "시뮬레이션 (x,y) km → WGS84 변환 기준점"
    }
}
```

**스키마 검증 방법 (에이전트용)**:
```python
# tests/test_schema_compliance.py에서 사용
import json
REQUIRED_CZML_THREAT_KEYS = {"id", "position", "point", "path", "properties"}
REQUIRED_CONFIG_TOP_KEYS = {"metadata", "camera_presets", "radar_volumes", 
                            "batteries", "engagement_policy", "hud_config",
                            "coordinate_reference"}

def validate_threat_packet(packet: dict) -> bool:
    return REQUIRED_CZML_THREAT_KEYS.issubset(packet.keys())

def validate_viewer_config(config: dict) -> bool:
    return REQUIRED_CONFIG_TOP_KEYS.issubset(config.keys())
```

---

## 4. Phase 구조 및 의존성 DAG

### 4.1 Phase 개요

| Phase | 이름 | 핵심 산출물 | Task 수 | 예상 시간 |
|-------|------|-----------|---------|----------|
| **P1** | CZML Exporter 고도화 | `exporters.py` v2 + 스키마 검증 | 6 | 중간 |
| **P2** | CesiumJS 통합 뷰어 기반 | `cesium-viewer/` 프레임워크 | 4 | 높음 |
| **P3** | 3D 센서 볼륨 및 교전 시각화 | 레이더 구면 부채꼴, 요격 궤적 | 4 | 높음 |
| **P4** | 성능 최적화 및 HUD | Primitive 마이그레이션, Military HUD | 3 | 중간 |
| **P5** | 통합 검증 및 문서화 | E2E 테스트, 사용 가이드 | 3 | 낮음 |

### 4.2 의존성 DAG

```
P1-T0 ─→ P1-T1 ─→ P1-T2 ─→ P1-T3 ─→ P1-T4 ─→ P1-T5
                                                   │
P2-T1 ─→ P2-T2 ─→ P2-T3 ─→ P2-T4 ────────────────┤
                     │                              │
                     ├──→ P3-T1 ─→ P3-T2            │
                     │           ↘                  │
                     └──→ P3-T3 ─→ P3-T4 ───────────┤
                                                    │
                                P4-T1 ──────────────┤
                                P4-T2 ──────────────┤
                                P4-T3 ──────────────┤
                                                    │
                                              P5-T1 ─→ P5-T2 ─→ P5-T3
```

**P1-T0의 역할**: 스키마 검증 테스트를 먼저 작성하여 이후 P1-T1~T5가 
각각 해당 테스트를 PASS시키는 TDD 진입점 역할.

**병렬 가능 경로**:
- P1 (Python 백엔드)과 P2-T1~T2 (프론트엔드 기반)는 병렬 수행 가능
- P3 (3D 시각화)는 P2-T2 완료 후 시작
- P4 (최적화)는 P3 완료 후 시작하되, P4-T1~T3은 병렬 가능
- P1 (Python 백엔드)과 P2-T1~T2 (프론트엔드 기반)는 병렬 수행 가능
- P3 (3D 시각화)는 P2-T2 완료 후 시작
- P4 (최적화)는 P3 완료 후 시작하되, P4-T1~T3은 병렬 가능

---

## 5. Phase 1: CZML Exporter 고도화 (Python Backend)

### P1-T0: 스키마 준수 검증 테스트 프레임워크 (TDD 진입점)

**목적**: 섹션 3.3 정규 스키마를 pytest로 자동 검증하는 테스트 프레임워크 선행 구축. 이후 모든 Exporter Task는 이 테스트를 통과해야 한다.

**선행 조건**: 섹션 3.3 정규 데이터 스키마 레퍼런스 확정

**생성 파일**: `tests/test_schema_compliance.py`

**Spec**:
```python
"""tests/test_schema_compliance.py
섹션 3.3 정규 스키마 준수 자동 검증.
모든 P1 Task는 이 테스트를 PASS해야 한다.
"""

import json
import pytest
from modules.model import AirDefenseModel
from modules.exporters import CZMLExporter

# ── 스키마 상수 (섹션 3.3에서 추출) ──
REQUIRED_THREAT_KEYS = {"id", "position", "point", "path", "properties"}
REQUIRED_THREAT_POSITION_KEYS = {"epoch", "cartographicDegrees"}
REQUIRED_THREAT_PROPERTIES = {"type", "status"}
INTERPOLATION_CONFIG = {
    "SRBM": {"algorithm": "LAGRANGE", "degree": 5},
    "CRUISE_MISSILE": {"algorithm": "LINEAR", "degree": 1},
    "AIRCRAFT": {"algorithm": "LAGRANGE", "degree": 3},
    "UAS": {"algorithm": "LINEAR", "degree": 1},
}
REQUIRED_ENGAGEMENT_PROPERTIES = {"type", "result", "shooter_id", "threat_id"}
REQUIRED_CONFIG_TOP_KEYS = {"metadata", "camera_presets", "radar_volumes",
                            "batteries", "engagement_policy", "hud_config",
                            "coordinate_reference"}

@pytest.fixture
def czml_packets():
    m = AirDefenseModel(architecture="killweb", 
                        scenario="scenario_1_saturation",
                        seed=42, record_snapshots=True)
    result = m.run_full()
    exporter = CZMLExporter(result["snapshots"], result["config"])
    return exporter.build_czml()

class TestCZMLDocumentPacket:
    def test_first_packet_is_document(self, czml_packets):
        assert czml_packets[0]["id"] == "document"
        assert "clock" in czml_packets[0]

class TestThreatPacketSchema:
    def test_threat_packets_have_required_keys(self, czml_packets):
        threats = [p for p in czml_packets if p["id"].startswith("threat_")]
        assert len(threats) > 0
        for t in threats:
            assert REQUIRED_THREAT_KEYS.issubset(t.keys()), \
                f"Missing keys in {t['id']}: {REQUIRED_THREAT_KEYS - t.keys()}"

    def test_threat_position_has_interpolation(self, czml_packets):
        """P1-T1 완료 후 PASS 예상"""
        threats = [p for p in czml_packets if p["id"].startswith("threat_")]
        for t in threats:
            pos = t["position"]
            assert "interpolationAlgorithm" in pos, \
                f"{t['id']} missing interpolationAlgorithm"

    def test_threat_has_properties(self, czml_packets):
        threats = [p for p in czml_packets if p["id"].startswith("threat_")]
        for t in threats:
            props = t.get("properties", {})
            for key in REQUIRED_THREAT_PROPERTIES:
                assert key in props, f"{t['id']} missing property: {key}"

class TestEngagementPacketSchema:
    def test_engagement_packets_exist(self, czml_packets):
        """P1-T2 완료 후 PASS 예상"""
        engagements = [p for p in czml_packets 
                       if p["id"].startswith("engagement_")]
        # 교전이 발생했으면 패킷이 있어야 함
        assert len(engagements) >= 0  # 초기에는 0 허용
```

**Acceptance Criteria**:
```
AC-1: tests/test_schema_compliance.py 파일 생성 및 pytest 정상 수집
AC-2: P1-T0 시점에서 일부 테스트는 xfail/skip 가능 (향후 Task에서 구현)
AC-3: 기존 146개 테스트 영향 없음
```

**에이전트 지시**: 이 Task는 테스트만 작성한다. 구현 코드는 변경하지 않는다. 
`@pytest.mark.xfail`로 아직 미구현된 스키마 항목을 표시한다.

---

### P1-T1: CZML 궤적 보간 알고리즘 적용

**목적**: 위협 궤적에 Lagrange 보간을 적용하여 부드러운 3D 궤적 표현

**선행 조건**: `modules/exporters.py` (현재 v0.5.1 버전)

**변경 파일**: `modules/exporters.py`

**Spec**:
```python
# CZMLExporter._build_threat_packets() 변경사항

# AS-IS: 단순 시계열 cartographicDegrees
"position": {
    "epoch": "2024-01-01T00:00:00Z",
    "cartographicDegrees": [t, lon, lat, alt, ...]
}

# TO-BE: 보간 알고리즘 명시 + 최적 보간 차수
"position": {
    "epoch": "2024-01-01T00:00:00Z",
    "cartographicDegrees": [t, lon, lat, alt, ...],
    "interpolationAlgorithm": "LAGRANGE",  # 탄도 궤적에 최적
    "interpolationDegree": 5,              # 5차 다항식
}

# 위협 유형별 보간 전략:
# - SRBM: LAGRANGE degree=5 (포물선 궤적에 최적)
# - CRUISE_MISSILE: LINEAR (일정 고도 순항)
# - AIRCRAFT: LAGRANGE degree=3 (완만한 기동)
# - UAS: LINEAR (저속 직선)
```

**Acceptance Criteria (→ pytest)**:
```
AC-1: SRBM 궤적 CZML에 "interpolationAlgorithm": "LAGRANGE" 포함
AC-2: CRUISE_MISSILE 궤적에 "interpolationAlgorithm": "LINEAR" 포함
AC-3: 모든 위협 궤적에 "interpolationDegree" 필드 존재
AC-4: 기존 test_exporters.py 8개 테스트 전부 PASS
AC-5: Cesium Sandcastle에서 CZML 로드 시 궤적 시각적 확인 (수동)
```

**구현 가이드**:
```python
INTERPOLATION_CONFIG = {
    "SRBM": {"algorithm": "LAGRANGE", "degree": 5},
    "CRUISE_MISSILE": {"algorithm": "LINEAR", "degree": 1},
    "AIRCRAFT": {"algorithm": "LAGRANGE", "degree": 3},
    "UAS": {"algorithm": "LINEAR", "degree": 1},
}
```

---

### P1-T2: 교전 이벤트 CZML 패킷 추가

**목적**: 요격 미사일 궤적, 명중/실패 이벤트를 CZML로 내보내기

**선행 조건**: P1-T1 완료, `model.py`의 `killchain.event_log` 구조 이해

**변경 파일**: `modules/exporters.py`

**Spec**:
```python
class CZMLExporter:
    def _build_engagement_packets(self) -> list:
        """교전 이벤트 CZML 패킷 생성
        
        event_log에서 'engagement' 이벤트를 추출하여:
        1. 사수→위협 연결선 (교전 시각에 순간 표시)
        2. 명중 시 폭발 마커 (위협 마지막 위치에 PointGraphics 적색 확대)
        3. 실패 시 회색 X 마커
        
        Returns:
            list: CZML 패킷 리스트
        """
```

**출력 패킷 구조**:
```json
{
    "id": "engagement_BM-1001_PAT_1",
    "name": "요격: PAT_1 → BM-1001",
    "availability": "2024-01-01T00:01:30Z/2024-01-01T00:01:35Z",
    "polyline": {
        "positions": {
            "cartographicDegrees": [shooter_lon, shooter_lat, 0, threat_lon, threat_lat, threat_alt]
        },
        "width": 2,
        "material": {
            "solidColor": {
                "color": {"rgba": [0, 255, 136, 200]}
            }
        }
    }
}
```

**Acceptance Criteria**:
```
AC-1: 시뮬레이션 결과에 engagement 이벤트가 있으면 engagement 패킷 1개 이상 생성
AC-2: 패킷에 shooter_id와 threat_id가 포함된 id 필드
AC-3: 명중 이벤트에 hit=True 표시 (폭발 point 패킷)
AC-4: availability가 교전 시간 ±5초 범위
```

---

### P1-T3: C2 네트워크 토폴로지 CZML 내보내기

**목적**: 선형 C2 / Kill Web 네트워크 연결 구조를 CZML polyline으로 시각화

**선행 조건**: P1-T1, `network.py`의 토폴로지 그래프 구조

**변경 파일**: `modules/exporters.py`

**Spec**:
```python
def _build_topology_packets(self) -> list:
    """C2 네트워크 연결선 CZML 패킷
    
    NetworkX topology의 edge를 polyline으로 변환:
    - 선형 C2: 계층적 단방향 연결선 (흰색 실선)
    - Kill Web: 메시 양방향 연결선 (청색 점선)
    - 파괴된 노드의 연결선: 회색 + 투명도 증가
    
    스냅샷 시계열로 노드 파괴 시 연결선 사라짐 표현:
    - availability 속성으로 시간대별 가시성 제어
    """
```

**Acceptance Criteria**:
```
AC-1: 토폴로지 edge 수만큼 polyline 패킷 생성
AC-2: 시나리오 5(노드파괴) 실행 시 파괴 시점 이후 해당 노드 연결선 비활성
AC-3: 선형 C2와 Kill Web의 연결선 시각적 구분 (색상/스타일)
```

---

### P1-T4: 뷰어 설정 JSON Exporter 신규 생성

**목적**: CZML로 표현할 수 없는 3D 렌더링 파라미터를 별도 JSON으로 내보내기

**선행 조건**: P1-T1~T3, `config.py` 파라미터 구조

**변경 파일**: `modules/exporters.py` (CesiumConfigExporter 클래스 추가)

**Spec**:
```python
class CesiumConfigExporter:
    """CesiumJS 뷰어 설정 JSON 내보내기
    
    CZML이 지원하지 않는 커스텀 렌더링 파라미터를 JSON으로 제공:
    - 센서 3D 볼륨 파라미터 (방위각, 고각, 반경)
    - 교전 정책 파라미터 (Pk 임계값, 킬 반경)
    - HUD 표시 정보 (포대 편성, 발사대 상태)
    - 카메라 프리셋 (전체뷰, 45도, 수평뷰, 포대근접)
    """
    
    def export(self, filepath: str) -> None:
        """
        출력 JSON 구조:
        {
            "metadata": { "architecture", "scenario", "sim_time", "version" },
            "camera_presets": { "overview", "tactical", "horizontal", "battery" },
            "radar_volumes": [
                {
                    "sensor_id": "PAT_RADAR_1",
                    "position": [lon, lat, alt],
                    "detection_range_m": 170000,
                    "engagement_range_m": 40000,
                    "azimuth_center_deg": 0,
                    "azimuth_half_deg": 60,
                    "elevation_max_deg": 90,
                }
            ],
            "batteries": [
                {
                    "battery_id": "PAT_BATTERY_ALPHA",
                    "radar": { ... },
                    "launchers": [ { "id", "position", "ammo_timeline": [...] } ],
                    "ecs": { ... },
                }
            ],
            "engagement_policy": {
                "pk_threshold": 0.30,
                "kill_radius_m": 500,
                "max_simultaneous": { "SRBM": 3, "CRUISE_MISSILE": 2 },
            },
            "hud_config": {
                "show_radar_fov": true,
                "show_engagement_range": true,
                "show_ammo_bars": true,
                "show_engagement_log": true,
            }
        }
        """
```

**Acceptance Criteria**:
```
AC-1: JSON 파일이 유효한 JSON으로 파싱 가능
AC-2: radar_volumes 배열에 시뮬레이션 센서 수만큼 항목 존재
AC-3: batteries 배열에 사수 배치 정보 포함
AC-4: 좌표가 WGS84 경위도로 변환됨 (BASE_LON/LAT 기준)
AC-5: engagement_policy가 config.py ENGAGEMENT_POLICY와 일치
```

---

### P1-T5: CZMLExporter 통합 테스트 및 Cesium Sandcastle 검증

**목적**: P1-T1~T4 통합 결과를 Cesium Sandcastle에서 시각적으로 검증

**선행 조건**: P1-T1~T4 전부 완료

**변경 파일**: `tests/test_exporters.py` (확장), `output/` (검증 결과 파일)

**Spec**:
```python
# tests/test_exporters.py 추가 테스트

class TestCZMLv2Integration:
    def test_full_export_all_scenarios(self):
        """7개 시나리오 × 2 아키텍처 CZML 내보내기 에러 없음"""
    
    def test_czml_valid_json(self):
        """내보낸 CZML이 유효한 JSON이며 document 패킷 포함"""
    
    def test_viewer_config_matches_simulation(self):
        """viewer_config.json의 센서 수 = 시뮬레이션 센서 수"""
    
    def test_engagement_packets_count(self):
        """교전 패킷 수 ≤ metrics.total_shots"""
    
    def test_topology_packets_edge_count(self):
        """토폴로지 패킷 수 = topology.number_of_edges()"""

class TestCesiumConfigExporter:
    def test_export_creates_file(self):
    def test_radar_volumes_structure(self):
    def test_coordinate_conversion_consistency(self):
```

**Acceptance Criteria**:
```
AC-1: 전체 테스트 스위트 PASS (기존 146개 + 신규 ~10개)
AC-2: output/scenario_1_linear.czml, output/scenario_1_killweb.czml 파일 생성
AC-3: output/viewer_config_linear.json, output/viewer_config_killweb.json 생성
AC-4: (수동) Cesium Sandcastle에서 CZML 로드 → 위협 궤적 표시 확인
```

---

## 6. Phase 2: CesiumJS 통합 뷰어 기반 구축

### P2-T1: 프로젝트 구조 및 기본 뷰어 세팅

**목적**: CesiumJS 기반 통합 뷰어 HTML/JS 프레임워크 구축

**선행 조건**: Cesium Ion 토큰 (patriot-sim.html에서 확보)

**생성 파일**:
```
cesium-viewer/
├── index.html           # 메인 뷰어 (CDN 기반 CesiumJS)
├── js/
│   └── app.js           # 메인 앱 초기화
├── css/
│   └── hud.css          # Military HUD 스타일
└── README.md            # 로컬 실행 가이드
```

**Spec (index.html)**:
```html
<!-- 
  핵심 요구사항:
  1. CesiumJS 1.130+ CDN 로드 (MSAA, 이미지 드레이핑 지원)
  2. Cesium Ion 토큰 설정
  3. globe: false (Google 3D Tiles 대비) 또는 Cesium World Terrain
  4. 한반도 중심 초기 카메라 (127.0°E, 37.0°N, 고도 300km)
  5. 기본 네비게이션 컨트롤 활성화
  6. Python 로컬 웹서버에서 실행 가능 (file:// 아님)
-->
```

**Spec (app.js)**:
```javascript
// 초기화 흐름:
// 1. Cesium.Viewer 생성 (옵션: terrain, lighting, navigation)
// 2. 카메라 한반도 중심 flyTo
// 3. CZML 로드 대기 (로드 버튼 또는 자동 fetch)
// 4. viewer_config.json 로드 → 센서 볼륨/HUD 설정

const CONFIG = {
    CESIUM_ION_TOKEN: "...",  // from patriot-sim.html
    DEFAULT_CENTER: { lon: 127.0, lat: 37.0, alt: 300000 },
    CZML_PATH: "../output/sim_result.czml",
    CONFIG_PATH: "../output/viewer_config.json",
};
```

**Acceptance Criteria**:
```
AC-1: python -m http.server 8000 → localhost:8000/cesium-viewer/ 접속 시 지구본 표시
AC-2: 한반도 중심으로 카메라 이동
AC-3: Cesium Ion 지형 로딩 (Cesium World Terrain)
AC-4: 나침반, 줌, 홈버튼 등 기본 네비게이션 동작
```

---

### P2-T2: CZML 로더 및 시간 컨트롤

**목적**: Python에서 내보낸 CZML을 로드하고 시뮬레이션 시간을 제어

**선행 조건**: P2-T1, P1-T5

**생성/변경 파일**: `cesium-viewer/js/czml-loader.js`, `cesium-viewer/js/app.js`

**Spec (czml-loader.js)**:
```javascript
/**
 * CZML 파일을 Cesium 뷰어에 로드하는 모듈
 * 
 * 기능:
 * 1. fetch → CzmlDataSource.load()
 * 2. 시뮬레이션 Clock 동기화 (epoch, multiplier)
 * 3. 재생/일시정지/속도 조절 UI
 * 4. 시간 슬라이더 (타임라인 스크러빙)
 * 5. 엔티티 클릭 시 정보 패널 표시
 * 
 * 인터페이스:
 *   loadCZML(url) → Promise<CzmlDataSource>
 *   setPlaybackSpeed(multiplier)   // 1x, 2x, 5x, 10x
 *   seekToTime(julianDate)
 *   togglePlayPause()
 */
```

**Acceptance Criteria**:
```
AC-1: CZML 로드 후 위협 궤적이 지구본 위에 표시
AC-2: 재생 버튼 클릭 시 위협이 시간에 따라 이동
AC-3: 속도 조절 (1x, 5x, 10x) 정상 동작
AC-4: 타임라인 스크러빙으로 특정 시점 이동 가능
AC-5: 엔티티 클릭 시 이름/유형/고도 표시
```

---

### P2-T3: 아키텍처 비교 모드 (Linear vs Kill Web)

**목적**: 두 아키텍처 결과를 동시에 로드하여 나란히 비교

**선행 조건**: P2-T2

**변경 파일**: `cesium-viewer/js/app.js`, `cesium-viewer/index.html`

**Spec**:
```javascript
/**
 * 비교 모드 구현 방안:
 * 
 * 옵션 A: 단일 뷰어 + 토글 버튼
 *   - "Linear" / "Kill Web" 버튼으로 DataSource 교체
 *   - 교전 이벤트 / 토폴로지만 전환, 위협은 동일
 * 
 * 옵션 B: Split Screen (권장)
 *   - 좌: Linear C2, 우: Kill Web
 *   - 카메라 동기화 (한쪽 이동 → 다른 쪽도 이동)
 *   - 시간 동기화 (단일 타임라인 컨트롤)
 * 
 * 비교 지표 오버레이:
 *   - 실시간 누출률 카운터
 *   - S2S 시간 비교 바
 *   - 교전 성공/실패 카운터
 */
```

**Acceptance Criteria**:
```
AC-1: 두 아키텍처 CZML 동시 로드 가능
AC-2: 시간 동기화 (재생 시 양쪽 동시 진행)
AC-3: 카메라 동기화 (한쪽 회전 → 다른 쪽 동기)
AC-4: 비교 지표 오버레이 실시간 갱신
```

---

### P2-T4: 시나리오 선택 UI

**목적**: 7개 시나리오 중 선택하여 해당 CZML/config 자동 로드

**선행 조건**: P2-T2

**변경 파일**: `cesium-viewer/index.html`, `cesium-viewer/js/app.js`

**Spec**:
```javascript
// 시나리오 선택 드롭다운
const SCENARIOS = [
    { id: "scenario_1_saturation", label: "S1: 포화공격", icon: "⚠" },
    { id: "scenario_2_complex", label: "S2: 복합위협", icon: "◈" },
    { id: "scenario_3_ew_light", label: "S3: 전자전 (Light)", icon: "📡" },
    { id: "scenario_3_ew_moderate", label: "S3: 전자전 (Moderate)", icon: "📡" },
    { id: "scenario_3_ew_heavy", label: "S3: 전자전 (Heavy)", icon: "📡" },
    { id: "scenario_4_sequential", label: "S4: 순차교전", icon: "⏱" },
    { id: "scenario_5_node_destruction", label: "S5: 노드파괴", icon: "💥" },
];

// 선택 시: 
// 1. 기존 DataSource 제거
// 2. output/{scenario}_{architecture}.czml 로드
// 3. output/viewer_config_{architecture}.json 로드
// 4. 카메라 리셋
```

**Acceptance Criteria**:
```
AC-1: 드롭다운에서 시나리오 변경 시 이전 CZML 제거 + 새 CZML 로드
AC-2: 아키텍처 토글 버튼으로 Linear/Kill Web 전환
AC-3: 로딩 인디케이터 표시
```

---

## 7. Phase 3: 3D 센서 볼륨 및 교전 시각화

### P3-T1: 3D 구면 부채꼴 레이더 볼륨

**목적**: viewer_config.json의 센서 파라미터를 기반으로 3D EllipsoidGeometry 구면 부채꼴 렌더링

**선행 조건**: P2-T2, P1-T4

**생성 파일**: `cesium-viewer/js/radar-volumes.js`

**Spec**:
```javascript
/**
 * 레이더 탐지/교전 범위를 3D 구면 부채꼴로 렌더링
 * 
 * patriot-sim.html의 buildRadar() 로직을 모듈화하되,
 * viewer_config.json에서 파라미터를 동적으로 로드
 * 
 * 렌더링 방식: EllipsoidGeometry + PerInstanceColorAppearance
 *   (Entity API의 ellipsoid가 아닌 Primitive API 사용 — 성능)
 * 
 * 구현 항목:
 * 1. 탐지 범위 볼륨 (파란색 반투명, viewer_config.radar_volumes[].detection_range_m)
 * 2. 교전 범위 볼륨 (녹색 반투명, viewer_config.radar_volumes[].engagement_range_m)
 * 3. 방위각/고각 제한 (minimumClock/maximumClock, minimumCone/maximumCone)
 * 4. 레이더 방향 슬라이더 연동 (UI에서 방위각 조정 → 볼륨 회전)
 * 
 * 인터페이스:
 *   createRadarVolumes(viewer, config) → { detection: Primitive, engagement: Primitive }
 *   updateRadarAzimuth(azimuthDeg)     → 볼륨 modelMatrix 회전
 *   toggleVolumes(show)                → show/hide
 */
```

**핵심 코드 패턴 (from CesiumJS 분석 보고서)**:
```javascript
const instance = new Cesium.GeometryInstance({
    geometry: new Cesium.EllipsoidGeometry({
        radii: new Cesium.Cartesian3(100000, 100000, 100000),
        innerRadii: new Cesium.Cartesian3(1000, 1000, 1000),
        minimumClock: Cesium.Math.toRadians(-60),
        maximumClock: Cesium.Math.toRadians(60),
        minimumCone: Cesium.Math.toRadians(10),
        maximumCone: Cesium.Math.toRadians(80),
        stackPartitions: 32,
        slicePartitions: 32,
    }),
    modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(radarPosition),
    attributes: {
        color: Cesium.ColorGeometryInstanceAttribute.fromColor(
            Cesium.Color.GREEN.withAlpha(0.15)
        )
    }
});
```

**Acceptance Criteria**:
```
AC-1: viewer_config.json 로드 시 센서 수만큼 3D 볼륨 생성
AC-2: 탐지 범위(파랑)와 교전 범위(초록) 색상 구분
AC-3: 방위각 슬라이더 조작 시 볼륨 실시간 회전
AC-4: 토글 버튼으로 볼륨 표시/숨김
```

---

### P3-T2: 요격 미사일 궤적 시각화

**목적**: 교전 이벤트의 사수→위협 요격 궤적을 3D 곡선으로 표현

**선행 조건**: P2-T2, P1-T2

**생성 파일**: `cesium-viewer/js/engagement-viz.js`

**Spec**:
```javascript
/**
 * 교전 시각화 모듈
 * 
 * CZML의 engagement 패킷 + viewer_config의 교전 정책을 조합하여:
 * 1. 요격 미사일 궤적: 사수 위치 → 교점까지 곡선 (PNG 유도 모사)
 *    - 발사 직후 수직 상승 2초 (부스터)
 *    - 이후 교점 방향으로 곡선 유도
 * 2. 교전 결과 이펙트:
 *    - 성공 (hit=true): 주황색 구체 확대→소멸 (폭발)
 *    - 실패 (hit=false): 회색 X 마커
 * 3. 교전 연결선: 사수→위협 점선 (교전 중에만 표시)
 * 
 * 참고: patriot-sim.html의 pngGuide() 함수 로직 재활용
 * 단, 여기서는 사전 계산된 궤적을 SampledPositionProperty로 표현
 * (실시간 물리 시뮬레이션이 아닌 리플레이)
 */
```

**Acceptance Criteria**:
```
AC-1: 교전 이벤트 시 사수 위치에서 요격 미사일 궤적 표시
AC-2: 명중 시 폭발 이펙트 (확대→소멸 구체)
AC-3: 실패 시 위협이 계속 비행하는 것 시각적 확인
AC-4: 교전 연결선이 교전 시간 동안만 표시
```

---

### P3-T3: ParticleSystem 폭발 이펙트

**목적**: 요격 성공/지면 타격 시 Cesium ParticleSystem 기반 사실적 폭발 효과

**선행 조건**: P3-T2

**변경 파일**: `cesium-viewer/js/engagement-viz.js`

**Spec (from CesiumJS 분석 보고서)**:
```javascript
function createExplosion(position, isLargeExplosion) {
    return viewer.scene.primitives.add(new Cesium.ParticleSystem({
        image: "assets/textures/fire.png",   // 4x4 또는 8x8 스프라이트
        emitter: new Cesium.SphereEmitter(2.0),
        emissionRate: 0,
        bursts: [new Cesium.ParticleBurst({ time: 0.0, minimum: 200, maximum: 400 })],
        startColor: Cesium.Color.YELLOW.withAlpha(1.0),
        endColor: Cesium.Color.RED.withAlpha(0.0),
        startScale: isLargeExplosion ? 2.0 : 1.0,
        endScale: isLargeExplosion ? 12.0 : 6.0,
        minimumSpeed: 20.0,
        maximumSpeed: 50.0,
        minimumParticleLife: 0.5,
        maximumParticleLife: 1.5,
        lifetime: 2.0,
        loop: false,
        sizeInMeters: true,
        modelMatrix: Cesium.Transforms.eastNorthUpToFixedFrame(position),
    }));
}
```

**Acceptance Criteria**:
```
AC-1: 요격 성공 시 공중 폭발 파티클 이펙트 표시
AC-2: 지면 타격 시 대형 폭발 이펙트 표시 (isLargeExplosion=true)
AC-3: 폭발 후 2초 이내 파티클 시스템 자동 제거 (메모리 관리)
AC-4: 동시 4~8개 폭발에서 60fps 유지
```

---

### P3-T4: C2 토폴로지 네트워크 3D 렌더링

**목적**: C2 네트워크 연결 구조를 3D 공간에서 연결선으로 표현

**선행 조건**: P2-T2, P1-T3

**생성 파일**: `cesium-viewer/js/topology-viz.js`

**Spec**:
```javascript
/**
 * C2 토폴로지 시각화
 * 
 * CZML의 topology 패킷을 기반으로:
 * 1. 센서→C2 연결선 (파란 실선)
 * 2. C2→C2 연결선 (주황 점선)
 * 3. C2→사수 연결선 (빨간 실선)
 * 4. 노드 파괴 시 연결선 단절 애니메이션 (색상 변화→소멸)
 * 5. Kill Web의 메시 구조 vs Linear의 계층 구조 시각적 대비
 * 
 * 데이터 흐름 표현 (선택):
 * - 킬체인 이벤트 시 연결선을 따라 "데이터 패킷" 애니메이션
 * - 선형: 느린 패킷 (지연 반영), Kill Web: 빠른 패킷
 */
```

**Acceptance Criteria**:
```
AC-1: 모든 토폴로지 edge가 3D 연결선으로 표시
AC-2: 에이전트 유형별 연결선 색상 구분
AC-3: 시나리오 5 재생 시 노드 파괴 시점에 연결선 사라짐
AC-4: 토폴로지 토글 버튼으로 연결선 표시/숨김
```

---

## 8. Phase 4: 성능 최적화 및 HUD

### P4-T1: Primitive API 마이그레이션

**목적**: 동적 엔티티(위협, 교전 궤적, 항적)를 Entity API에서 Primitive API로 전환

**선행 조건**: P3 전체 완료

**변경 파일**: `cesium-viewer/js/performance.js`, 관련 JS 모듈

**Spec**:
```javascript
/**
 * Primitive API 최적화 모듈
 * 
 * CesiumJS 분석 보고서 핵심:
 * - Entity API: 15,000개에서 BillboardVisualizer가 CPU 50% 소비
 * - Primitive API: 동일 수량에서 ~5% 소비 (10배 절감)
 * 
 * 마이그레이션 대상:
 * 1. 위협 위치 마커 → PointPrimitiveCollection
 * 2. 항적 (trail) → PolylineCollection
 * 3. 교전 연결선 → PolylineCollection
 * 4. 센서/사수 라벨 → LabelCollection
 * 5. 정적 아이콘 → BillboardCollection
 * 
 * 유지 (Entity API):
 * - CZML DataSource 엔티티 (Cesium 내부 최적화)
 * - 클릭 가능 인터랙티브 엔티티
 */
```

**Acceptance Criteria**:
```
AC-1: 동시 50개 이상 위협 + 항적에서 60fps 유지 (Chrome DevTools)
AC-2: CallbackProperty 사용 0건 (코드 검색으로 확인)
AC-3: 기능 동일성 (마이그레이션 전후 시각적 차이 없음)
```

---

### P4-T2: Military HUD 패널

**목적**: patriot-sim.html의 Military HUD를 통합 뷰어로 이식 및 확장

**선행 조건**: P2-T2, P1-T4

**생성 파일**: `cesium-viewer/js/hud-panel.js`, `cesium-viewer/css/hud.css`

**Spec**:
```javascript
/**
 * Military HUD 패널
 * 
 * patriot-sim.html의 HUD 디자인을 기반으로:
 * 
 * [좌측 패널]
 * ▸ DEFENSE STATUS
 *   아키텍처: LINEAR / KILL WEB
 *   시나리오: S1 포화공격
 *   시뮬시간: T = 120.0s
 *   위협총수: 45기
 *   
 * ▸ 교전 현황
 *   탐지: 38기
 *   교전: 25건
 *   격추: 18기  
 *   누출: 8기
 *   누출률: 17.8%
 *   
 * ▸ 교전 로그
 *   [00:01:30] 탐지: BM-1001
 *   [00:01:35] 요격 발사 ← PAT_1
 *   [00:01:42] ✓ 요격 성공: BM-1001
 *   
 * [우측 패널]
 * ▸ 레이더 제어 (P3-T1 연동)
 *   방위각 슬라이더
 *   고각 슬라이더
 *   
 * ▸ 카메라 프리셋
 *   🌏 전체 / 📐 45° / ✈ 수평 / 🎯 포대
 *   
 * ▸ 재생 제어
 *   ▶ 재생 / ⏸ 일시정지 / 속도 1x~10x
 * 
 * 데이터 소스:
 * - 정적 데이터: viewer_config.json
 * - 동적 데이터: CZML Clock 시간에 따라 스냅샷에서 추출
 */
```

**Acceptance Criteria**:
```
AC-1: HUD 패널이 뷰어 위에 반투명 오버레이로 표시
AC-2: 시뮬레이션 재생 중 교전 현황 실시간 갱신
AC-3: 교전 로그가 시간순으로 자동 스크롤
AC-4: 카메라 프리셋 버튼 4종 정상 동작
AC-5: 폰트: Share Tech Mono + Orbitron (군사 HUD 스타일)
```

---

### P4-T3: requestRenderMode 기반 성능 제어

**목적**: 시뮬레이션 일시정지 시 CPU 사용량 최소화

**선행 조건**: P4-T1

**변경 파일**: `cesium-viewer/js/app.js`

**Spec**:
```javascript
// 시뮬레이션 재생 중: 연속 렌더링
viewer.scene.requestRenderMode = false;

// 시뮬레이션 일시정지: 요청 시에만 렌더링
viewer.scene.requestRenderMode = true;
viewer.scene.maximumRenderTimeChange = Infinity;

// 사용자 인터랙션(마우스 이동 등) 시 자동 렌더
// → Cesium 기본 동작으로 처리됨

// 상태 전환:
//   재생 → requestRenderMode = false
//   일시정지 → requestRenderMode = true + scene.requestRender()
```

**Acceptance Criteria**:
```
AC-1: 일시정지 시 CPU 사용량 25% → 5% 이하 감소
AC-2: 일시정지 중 마우스 조작(회전/줌) 정상 응답
AC-3: 재생 재개 시 즉시 연속 렌더링 복원
```

---

## 9. Phase 5: 통합 검증 및 문서화

### P5-T1: End-to-End 통합 테스트

**목적**: Python 시뮬레이션 → CZML 내보내기 → Cesium 뷰어 로드 전체 파이프라인 검증

**Spec**:
```python
# tests/test_e2e_cesium.py

class TestE2ECesiumIntegration:
    def test_full_pipeline_scenario_1(self):
        """S1: 시뮬레이션 → CZML → JSON 파싱 검증"""
        m = AirDefenseModel(
            architecture="killweb", scenario="scenario_1_saturation",
            seed=42, record_snapshots=True
        )
        result = m.run_full()
        
        czml_exporter = CZMLExporter(result["snapshots"], result["config"])
        czml = czml_exporter.build_czml()
        
        config_exporter = CesiumConfigExporter(result)
        config = config_exporter.build_config()
        
        # 검증
        assert len(czml) > 10  # document + threats + sensors + shooters + ...
        assert "radar_volumes" in config
        assert len(config["radar_volumes"]) == len(result["snapshots"][0]["sensors"])
        
    def test_all_scenarios_export(self):
        """7 시나리오 × 2 아키텍처 = 14개 CZML 내보내기"""
        
    def test_czml_entity_count_matches_simulation(self):
        """CZML 엔티티 수 = 시뮬레이션 에이전트 수"""
```

**Acceptance Criteria**:
```
AC-1: 14개 시나리오×아키텍처 조합 CZML 내보내기 에러 없음
AC-2: 전체 테스트 스위트 PASS (기존 146 + Phase 1~4 신규 + E2E)
AC-3: seed=42 시나리오 1 성능 기준선 불변 확인
```

---

### P5-T2: 실행 자동화 스크립트

**목적**: 시뮬레이션 → 내보내기 → 뷰어 실행을 단일 명령으로 자동화

**생성 파일**: `run_cesium.py`, `run_cesium.bat` (Windows)

**Spec**:
```python
#!/usr/bin/env python3
"""KIDA_ADSIM → Cesium 3D 시각화 자동 실행 스크립트

Usage:
    python run_cesium.py                          # 기본: S1 Kill Web
    python run_cesium.py --scenario scenario_2    # 시나리오 지정
    python run_cesium.py --all                    # 전 시나리오 내보내기
    python run_cesium.py --serve                  # 웹서버 자동 시작
"""

# 1. 시뮬레이션 실행 (record_snapshots=True)
# 2. CZML 내보내기 → output/
# 3. viewer_config.json 내보내기 → output/
# 4. (--serve) python -m http.server 8000 & open browser
```

**Acceptance Criteria**:
```
AC-1: python run_cesium.py 실행 시 output/ 디렉토리에 CZML + JSON 생성
AC-2: python run_cesium.py --serve 실행 시 브라우저 자동 열림
AC-3: python run_cesium.py --all 실행 시 14개 파일 생성
```

---

### P5-T3: 문서 갱신

**목적**: CHANGELOG.md, CLAUDE.md, README.md에 Cesium 통합 내용 반영

**변경 파일**: `CHANGELOG.md`, `CLAUDE.md`, `README.md`, `plan.md`

**Spec**:
```markdown
# CHANGELOG.md 추가 내용
## [v0.7] — Cesium 3D 시각화 통합
### 변경사항
- CZMLExporter v2: 궤적 보간, 교전 이벤트, 토폴로지 패킷
- CesiumConfigExporter: 센서 볼륨, 교전 정책, HUD 설정 JSON
- cesium-viewer/: CesiumJS 통합 3D 뷰어
  - 3D 구면 부채꼴 레이더 볼륨 (EllipsoidGeometry)
  - 요격 미사일 궤적 + ParticleSystem 폭발
  - Military HUD 패널
  - 아키텍처 비교 모드
  - Primitive API 성능 최적화
```

**Acceptance Criteria**:
```
AC-1: CHANGELOG.md에 v0.7 섹션 추가
AC-2: CLAUDE.md 디렉토리 구조에 cesium-viewer/ 반영
AC-3: README.md에 Cesium 실행 방법 섹션 추가
```

---

## 10. 리스크 매트릭스

| 리스크 | 확률 | 영향 | 완화 방안 |
|--------|------|------|----------|
| CesiumJS Worker 오류 (file:// 실행) | 높음 | 중간 | 반드시 localhost 웹서버로 실행. run_cesium.py --serve 자동화 |
| Cesium Ion 토큰 만료/할당량 초과 | 낮음 | 높음 | 토큰 재발급 가이드 문서화, ArcGIS 위성 이미지 fallback |
| CZML 파일 크기 (300회 Monte Carlo) | 중간 | 중간 | record_snapshots는 단일 시드만, 배치는 CSV 유지 |
| 좌표 변환 오차 누적 | 중간 | 낮음 | 한반도 중심 127°E/37°N 기준, km→degree 변환 검증 테스트 |
| Google 3D Tiles 비용 | 낮음 | 낮음 | 기본은 Cesium World Terrain 무료, 3D Tiles는 선택 |
| 시뮬레이션 로직 변경에 의한 기준선 이탈 | 높음 | 높음 | **P1~P5 전 구간 시뮬레이션 코드 변경 금지** (exporters/viewer만 수정) |

---

## 11. 성공 기준 (Definition of Done)

### Phase별 완료 기준

| Phase | 완료 기준 |
|-------|----------|
| P1 | 7×2=14개 CZML+JSON 내보내기 성공, 테스트 ~156개 PASS |
| P2 | localhost에서 뷰어 로드 → 위협 궤적 3D 표시 + 시간 제어 |
| P3 | 3D 레이더 볼륨 + 요격 궤적 + 폭발 이펙트 동작 |
| P4 | 50+ 동시 위협에서 60fps, HUD 실시간 갱신 |
| P5 | python run_cesium.py --serve 단일 명령으로 전체 파이프라인 동작 |

### 최종 완료 기준 (v0.7 릴리즈)

```
1. seed=42 시나리오 1 성능 기준선 불변 (leaker_rate, s2s_time, success_rate)
2. 기존 146개 + 신규 ~35개 = 총 ~181개 테스트 PASS (P1-T0 스키마 검증 포함)
3. 7개 시나리오 × 2 아키텍처 모두 Cesium 3D 시각화 가능
4. 선형 C2 vs Kill Web 비교 모드에서 차이 시각적으로 확인 가능
5. SSOT 준수: cesium-viewer/js/ 내 Math.random() / 충돌 판정 코드 0건
6. 팀원에게 시연 가능한 수준의 완성도
```

---

## 12. 작업 우선순위 및 권장 실행 순서

### 최소 기능 제품 (MVP) — 팀 시연용

시간 제약이 있는 경우 아래 Task만 수행:

```
P1-T0 → P1-T1 → P1-T2 → P1-T5 → P2-T1 → P2-T2 → P4-T2
```

이 경로로 **"시뮬레이션 결과를 3D 지구본 위에서 재생하며 HUD로 모니터링"**하는 MVP 달성 가능.
P1-T0의 스키마 검증 테스트가 이후 Task의 품질 게이트 역할을 한다.

### 전체 구현 권장 순서

```
Week 1: P1-T1, P1-T2, P1-T3, P1-T4, P1-T5   (Python 백엔드 완성)
Week 2: P2-T1, P2-T2, P2-T3, P2-T4           (프론트엔드 기반)
Week 3: P3-T1, P3-T2, P3-T3, P3-T4           (3D 시각화)
Week 4: P4-T1, P4-T2, P4-T3                   (최적화)
Week 5: P5-T1, P5-T2, P5-T3                   (통합 검증)
```

---

## 부록 A: patriot-sim.html 재활용 가능 코드

| patriot-sim.html 함수 | 통합 뷰어 대응 모듈 | 재활용 수준 |
|----------------------|-------------------|-----------|
| `buildRadar()` (구면 부채꼴) | `radar-volumes.js` | **코어 로직 재활용** (EllipsoidGeometry로 교체) |
| `inDetectSector()` (3D 판정) | Python에서 사전 계산 | 참조만 (JS에서 재구현 불필요) |
| `pngGuide()` (PNG 유도) | `engagement-viz.js` | **궤적 사전 계산에 참조** |
| `explode()` (폭발 이펙트) | `engagement-viz.js` | **ParticleSystem으로 업그레이드** |
| HUD CSS/HTML | `hud-panel.js` + `hud.css` | **직접 이식 가능** |
| `spawnThreat()` / `fireInterceptor()` | Python에서 사전 계산 | 불필요 (리플레이 모드) |

## 부록 B: CesiumJS 버전 업그레이드 체크리스트

현재 patriot-sim.html은 CesiumJS **1.111**을 사용 중. 통합 뷰어는 **1.130+** 권장.

| 기능 | 도입 버전 | 적용 대상 |
|------|----------|----------|
| MSAA 기본 활성화 | 1.121 | 뷰어 전체 품질 향상 |
| Camera collision with 3D Tiles | 1.114 | Google 3D Tiles 사용 시 |
| ClippingPolygon | 1.117 | 특정 지역 마스킹 |
| Imagery draping on 3D Tiles | 1.130 | 전술 이미지 오버레이 |
| HeightReference.CLAMP_TO_3D_TILE | 1.114 | 지상 장비 배치 (성능 주의) |
| Asynchronous scene picking | 1.136 | 엔티티 클릭 성능 개선 |

## 부록 C: 에이전트에게 전달할 컨텍스트 템플릿

각 Task를 에이전트에게 할당할 때 아래 형식으로 컨텍스트를 제공:

```markdown
## Task: [P{phase}-T{task}] {제목}

### 컨텍스트 파일 (반드시 읽을 것)
- `modules/exporters.py` — 현재 CZMLExporter 구현
- `patriot-sim.html` — 참조 코드 (해당 함수만)
- `modules/config.py` — 파라미터 구조

### 스키마 레퍼런스 (반드시 준수할 것)
- 이 문서의 섹션 3.3 "정규 데이터 스키마 레퍼런스" 해당 항목

### 작업 지시
{이 문서의 해당 Task Spec 전문 복사}

### 테스트 먼저 작성
{Acceptance Criteria를 pytest 코드로 변환}

### 완료 조건
1. 신규 테스트 전부 PASS
2. `python -m pytest tests/ -v` 전체 PASS
3. 변경 파일 목록 출력
4. SSOT 위반 검사: JS 코드에 Math.random() / 충돌 판정 로직 없음 확인
```

---

## 부록 D: Gemini 3.1 제안의견 검토 결과

> Gemini 3.1에게 별도로 Agentic Coding 관점에서 이 계획의 부족한 점을 질의했다.
> 아래는 제안의견 4개 항목 + 4개 Task에 대한 수용/기각 판정이다.

### D.1 제안의견 항목별 판정

| # | Gemini 제안 | 판정 | 근거 |
|---|------------|------|------|
| 1 | **구체적인 데이터 스키마 부재** — AI가 어떤 속성 키값을 써야 할지 방황한다. JSON/CZML 스키마 예시를 하드코딩해서 프롬프트에 제공해야 한다. | **수용** (보강) | 기존 계획에 Task별 스키마 예시는 있었으나 분산 배치. **섹션 3.3으로 정규 스키마 레퍼런스 통합** 신설하여 에이전트가 단일 참조점을 갖도록 개선. |
| 2 | **원자적 태스크 분할 부족** — AI에게 "프론트엔드와 백엔드를 연동해"라고 하면 컨텍스트를 잃는다. 매우 잘게 쪼개야 한다. | **기각** (이미 충족) | 기존 계획은 5개 Phase × 19개 Task로 분할, 각 Task에 변경 파일/Spec/AC 명시. Gemini 자체 제안(4개 Task)보다 오히려 더 세분화되어 있음. |
| 3 | **작업 대상 파일 명시** — AI가 탐색 범위를 줄일 수 있도록 타겟 파일명을 정확히 짚어야 한다. | **기각** (이미 충족) | 모든 19개 Task에 "변경 파일" 또는 "생성 파일" 필드가 명시되어 있음. |
| 4 | **검증 기준(DoD)** — AI가 스스로 '이 작업이 끝났는지' 판단할 수 있는 기준이 필요하다. | **기각** (이미 충족) | 모든 Task에 AC-1~AC-N 형태의 Acceptance Criteria가 pytest 기반으로 정의되어 있음. 총 73개 AC 존재. |

### D.2 Gemini Task별 판정

| Gemini Task | 판정 | 근거 |
|------------|------|------|
| **Task 1: 3D 좌표계 확장** — `threats.py`, `agents.py`에 lon/lat/alt 확장 | **기각** (이미 구현 완료) | KIDA_ADSIM v0.2에서 `_slant_range(pos1, alt1, pos2, alt2)` 3D 경사거리 함수, `ThreatAgent.altitude` 동적 비행 프로파일, `_compute_phase_state()` 고도/속도 계산이 이미 구현됨. `exporters.py`의 `_sim_to_geo(pos, altitude_km)` 도 고도 포함 변환 구현 완료. **Gemini가 코드베이스를 정확히 파악하지 못한 것으로 판단.** |
| **Task 2: Exporter CZML 3D 스펙 적용** | **수용** (기존 P1-T1~T5와 대응) | 방향성은 동일. 다만 Gemini는 TDD 접근(테스트 먼저)을 명시했는데, 이는 기존 계획의 "Test Before Code" 원칙에 이미 반영됨. |
| **Task 3: 프론트엔드 연산 로직 제거** | **부분 수용** (SSOT 원칙으로 흡수) | 핵심 개념(프론트엔드에서 자체 연산 제거)은 **섹션 1.3 SSOT 원칙**으로 반영. 단, patriot-sim.html을 직접 수정하는 것이 아니라 **새 통합 뷰어(cesium-viewer/)를 SSOT 준수로 신규 구축**하는 접근을 유지. patriot-sim.html은 참조 코드(reference implementation)로만 활용. |
| **Task 4: CZML 기반 렌더링 및 이펙트 연동** | **수용** (기존 P3-T1~T4와 대응) | 방향성 동일. 기존 계획이 더 세분화(레이더 볼륨, 요격 궤적, ParticleSystem, 토폴로지 각각 별도 Task). |

### D.3 SSOT 원칙 반영에 대한 주요 유의사항

Gemini의 Task 3 ("프론트엔드 연산 로직 제거")에서 제안한 핵심 가치는 올바르다:

> *"기존 파일 내에 있는 `spawnThreat()`, `fireInterceptor()`, `inDetectSector()` 등
> 자체적으로 난수를 발생시키거나 충돌을 판정하는 로직을 모두 삭제하라."*

단, 우리 접근은 **기존 patriot-sim.html을 수정하는 것이 아니라**, 처음부터 SSOT를 준수하는
`cesium-viewer/`를 신규 구축하는 것이다. patriot-sim.html은 **독립 데모/프로토타입**으로 보존하되,
통합 뷰어에서는 다음이 보장된다:

```
cesium-viewer/js/ 내 모든 파일:
  ✅ CzmlDataSource.load()로 CZML 로드 → 렌더링
  ✅ viewer_config.json에서 파라미터 읽기 → 3D 볼륨 생성
  ✅ Cesium Clock 기반 시간 보간 → 애니메이션
  ✅ 이벤트 properties.type 체크 → 이펙트 트리거
  ❌ Math.random() (금지)
  ❌ 자체 Pk 계산 (금지)
  ❌ 충돌 판정 (금지)
  ❌ 위협 생성 (금지)
```

### D.4 종합 평가

Gemini 제안의견은 Agentic Coding의 일반론으로는 타당하나, **KIDA_ADSIM 코드베이스의 현재 상태
(v0.5.1, 이미 3D 좌표/비행 프로파일/CZML 내보내기 구현 완료)를 정확히 반영하지 못했다.**
4개 Task 중 Task 1은 이미 완료된 작업이고, Task 2/4는 기존 계획과 방향 동일하며,
Task 3의 SSOT 원칙만이 실질적으로 새로운 기여였다.

**반영 결과 요약**:
- [신규] 섹션 1.3: Single Source of Truth (SSOT) 아키텍처 원칙 + 위반 감지 패턴
- [신규] 섹션 3.3: 정규 데이터 스키마 레퍼런스 (6개 패킷 유형 전체 JSON 예시)
- [보강] 섹션 1.4: 에이전트 System Prompt 규칙 6개 (RULE-1~6)
- [보강] 부록 C: 컨텍스트 템플릿에 스키마 레퍼런스 + SSOT 검사 항목 추가
