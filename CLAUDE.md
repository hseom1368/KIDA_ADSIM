# KIDA_ADSIM — Claude Code 프로젝트 컨텍스트

## 프로젝트 개요
한국군 방공체계 C2 아키텍처(선형 C2 vs Kill Web) 비교 M&S.
Mesa(ABM) + SimPy(DES) + NetworkX 기반 에이전트 시뮬레이션.

## 디렉터리 구조
```
modules/
  config.py      — 모든 파라미터 + TOPOLOGY_RELATIONS (토폴로지 관계 매핑)
  ontology.py    — Pydantic 도메인 온톨로지 (SensorType/C2Type/ShooterType/ThreatType)
  registry.py    — 엔티티 레지스트리 (config→온톨로지 변환, Pk 기반 우선순위, 토폴로지 역조회)
  strategies.py  — 아키텍처 전략 패턴 (LinearC2Strategy/KillWebStrategy)
  agents.py      — Mesa 에이전트 4종 (Sensor, C2Node, Shooter, Threat) + _slant_range()
  model.py       — 통합 시뮬레이션 엔진 (AirDefenseModel) — 전략 위임 패턴
  network.py     — NetworkX 토폴로지 빌더 (선형/킬웹)
  comms.py       — SimPy 통신 채널 + 킬체인 프로세스 + redundancy_factor 주입
  metrics.py     — 12개 성능 지표 수집기
  threats.py     — 위협 생성기 (5개 시나리오)
  exporters.py   — CZML 내보내기 (Cesium 3D 시각화)
  viz.py         — 2D 전술 시각화 (matplotlib.animation 기반)
notebook1~5      — Jupyter 노트북 (모델정의, 시나리오, 배치실험, 분석, 전술시각화)
```

## 기술 스택
- Python 3.10+, SimPy 4.1, Mesa 3.0, NetworkX 3.0
- numpy, pandas, scipy, matplotlib, seaborn
- pydantic 2.x (도메인 온톨로지 타입 검증)

## 코딩 규칙
- 주석·변수명: 한국어 주석 허용, 변수·함수명은 영문 snake_case
- config.py에 모든 상수 집중 관리 — 매직 넘버 금지
- 에이전트 간 통신은 반드시 SimPy yield를 통한 지연 모델링
- 거리 계산: 고도 반영 시 `_slant_range()` 사용 (구현 완료)
- 교전 시점 판단: `_should_engage_now()` → ENGAGEMENT_POLICY 참조
- 아키텍처 분기: `model.py`에서 `self.strategy.method()` 위임 — if/else 아키텍처 분기 금지
- Pydantic 모델: 빌드 타임(초기화) 검증 전용 — 시뮬레이션 step() 루프에서 Pydantic 호출 금지
- 테스트: 변경 후 반드시 `python -m pytest tests/` 및 시나리오 1 스모크 테스트 실행

## 핵심 아키텍처 비교 (v0.5 기준, 시나리오 1 seed=42)
| 항목 | 선형 C2 | Kill Web |
|------|---------|----------|
| S2S 시간 | ~344s | ~5s (69배 빠름) |
| 누출률 | 35.6% | **22.2%** |
| 교전 성공률 | 37.1% | **37.5%** |
| 다중교전율 | 14.3% | **16.7%** |
| 토폴로지 | 계층 체인 (MCRC SPOF) | 완전 메시 (분산) |
| COP 품질 | 위협 항적만 | **위협 + 아군 상태 + 교전 계획** |
| 센서 융합 | 단일 센서 (σ=0.5km) | **√N 오차 감소 (min 0.1km)** |
| 사수 선택 | 유형 우선 고정 | **COP 기반 최적 점수 (아군 상태 반영)** |
| 교전 정책 | 고정 다중 교전 | **적응형 (탄약 기반 자동 전환)** |
| 통신 열화 | 전역 균일 | **링크별 차등 + 메시 다중경로 완화** |

## 현재 버전: v0.5.1 (온톨로지 리팩토링)
**상태**: Pydantic 도메인 온톨로지 + Strategy 패턴 + Registry + CZML 내보내기 + 146개 테스트 (13개 파일)

## 소프트웨어 아키텍처 흐름 (v0.5.1)
```
config.py → ontology.py → registry.py → strategies.py → model.py → agents.py
(파라미터)   (Pydantic 타입)  (타입 레지스트리)  (전략 패턴)     (시뮬엔진)    (Mesa 에이전트)
```
- **초기화 순서**: Registry 로드 → Strategy 생성 → Agent 생성 → Topology 빌드 → Comm 채널
- **런타임 규칙**: Pydantic 빌드 타임 전용, step() 루프에서 Pydantic 호출 금지

## 모듈별 핵심 역할 (v0.5.1)
| 모듈 | 핵심 역할 | 비고 |
|------|-----------|------|
| `ontology.py` | SensorType/C2Type/ShooterType/ThreatType + 능력 모델 | 토폴로지 관계 필드 내장 |
| `registry.py` | config→온톨로지 변환, Pk 사수 우선순위, 토폴로지 역조회 | TOPOLOGY_RELATIONS 참조 |
| `strategies.py` | LinearC2Strategy/KillWebStrategy (9개 추상 메서드) | 11개 if/else 분기 대체 |
| `exporters.py` | 스냅샷→CZML 변환 (Cesium 3D 시각화) | 한반도 좌표 기준 |
| `model.py` | 시뮬엔진 — `self.strategy.method()` 위임 | 아키텍처 분기 코드 없음 |
| `comms.py` | SimPy 통신 — redundancy_factor 주입 | architecture 문자열 의존 제거 |

## v0.5에서 구현된 핵심 사항
1. **COP 품질 차별화** — Kill Web: 센서 융합 √N 오차, 아군 상태 공유, 교전 계획 공유
2. **적응형 교전 정책** — 탄약 30% 이하 단일교전, 10% 이하 고위협만 교전
3. **통신 네트워크 동적 열화** — 링크별 차등 재밍, Kill Web 메시 다중경로 완화
4. **2D 전술 시각화 모듈** — TacticalVisualizer (렌더/애니메이션/비교/타임라인)

## 알려진 문제 (v0.5.1)
- 한글 폰트 미지원 — matplotlib 시각화에서 한글 글리프 경고
- 스냅샷 메모리 — record_snapshots=True 시 배치 실험에서 메모리 증가 가능
- agents.py 온톨로지 DI 미완료 — 현재 config.py 딕셔너리 직접 참조 유지 (향후 Phase 5 완성)

## 다음 작업: v0.6.x (Cesium 3D 시각화 통합)
- **v0.6.1** — CZML Exporter 고도화 (궤적 보간, 교전 이벤트, 토폴로지, viewer_config.json)
- **v0.6.2** — CesiumJS 통합 뷰어 기반 (`cesium-viewer/`, CZML 로더, 비교 모드)
- **v0.6.3** — 3D 센서 볼륨 & 교전 시각화 (레이더 볼륨, 요격 궤적, 폭발 이펙트)
- **v0.6.4** — 성능 최적화 & Military HUD (Primitive API, HUD 패널)
- **v0.6.5** — 통합 검증 & 문서화 (E2E 테스트, run_cesium.py, 문서 갱신)
- **v0.7** — Monte Carlo 통계 분석 (기존 v0.6 계획 이동)
- 상세 Spec: `cesium_integration_plan.md` 참조

## 자주 쓰는 명령어
```bash
# 스모크 테스트 (시나리오 1, 두 아키텍처)
python -c "
from modules.model import AirDefenseModel
for arch in ['linear', 'killweb']:
    m = AirDefenseModel(architecture=arch, scenario='scenario_1_saturation', seed=42)
    r = m.run_full()
    s2s = r['metrics']['sensor_to_shooter_time']['mean']
    leaker = r['metrics']['leaker_rate']
    success = r['metrics']['engagement_success_rate']
    print(f'{arch}: leaker={leaker:.1f}%, s2s={s2s:.1f}s, success={success:.1f}%')
"

# 전체 테스트
python -m pytest tests/ -v
```

## 이력 관리 파일
- `README.md` — 프로젝트 목표, 개념, 아키텍처 청사진
- `CHANGELOG.md` — 버전별 업데이트 이력 + 발견된 문제 + 개선 계획
- `plan.md` — 현재 진행 중인 개선 작업의 상세 기술 계획 (현재: v0.6 계획 수립)
- `dev_blueprint.md` — 초기 개발 청사진 (참조용, 동결)
- `ontology_refactoring_plan.md` — 온톨로지 리팩토링 분석 (참조용)
- `ontology_refactoring_plan_refined.md` — 온톨로지 리팩토링 상세 권장안 (참조용)
