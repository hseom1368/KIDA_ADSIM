# KIDA_ADSIM — Claude Code 프로젝트 컨텍스트

## 프로젝트 개요
한국군 방공체계 C2 아키텍처(선형 C2 vs Kill Web) 비교 M&S.
Mesa(ABM) + SimPy(DES) + NetworkX 기반 에이전트 시뮬레이션.

## 디렉터리 구조
```
modules/
  config.py      — 모든 파라미터 + TOPOLOGY_RELATIONS + REALISTIC_DEPLOYMENT + ENGAGEMENT_LAYERS + THREAT_ID_CONFIG
  ontology.py    — Pydantic 도메인 온톨로지 (SensorType/C2Type/ShooterType/ThreatType + v0.7 신규 필드)
  registry.py    — 엔티티 레지스트리 (config→온톨로지 변환, Pk 기반 우선순위, 토폴로지 역조회, 고도 범위 쿼리)
  strategies.py  — 아키텍처 전략 패턴 (LinearC2Strategy/KillWebStrategy + 3축 분리/위협 식별/센서 큐잉/다축 킬체인)
  agents.py      — Mesa 에이전트 4종 + _slant_range() + identified_type 기반 Pk 조회
  model.py       — 통합 시뮬레이션 엔진 — 전략 위임 + 다층 핸드오프 + 다축 킬체인
  network.py     — NetworkX 토폴로지 빌더 (선형/킬웹 + 현실적 3축/IAOC)
  comms.py       — SimPy 통신 채널 + 킬체인 프로세스 + redundancy_factor 주입
  metrics.py     — 18개 성능 지표 수집기 (기존 12 + v0.7 신규 6)
  threats.py     — 위협 생성기 (7개 시나리오 + TOT 스케줄링 + THREAT_ORIGINS)
  exporters.py   — CZML 내보내기 + CesiumConfigExporter (Cesium 3D 시각화)
  viz.py         — 2D 전술 시각화 (matplotlib.animation 기반)
cesium-viewer/
  index.html     — CesiumJS 3D 통합 뷰어 (CDN 기반)
  js/app.js      — 메인 앱 (비교 모드, 시나리오 선택, 모듈 통합)
  js/czml-loader.js    — CZML 로더 + 시간 컨트롤
  js/radar-volumes.js  — 3D 레이더 볼륨 (Primitive API)
  js/engagement-viz.js — 교전 시각화 (요격 궤적 + 폭발 이펙트)
  js/topology-viz.js   — C2 토폴로지 시각화
  js/performance.js    — Primitive 컬렉션 (라벨/포인트)
  js/hud-panel.js      — Military HUD 패널
  css/hud.css          — HUD 스타일
run_cesium.py  — 시뮬레이션→CZML→뷰어 자동화 스크립트
notebook1~5    — Jupyter 노트북 (모델정의, 시나리오, 배치실험, 분석, 전술시각화)
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

## 핵심 아키텍처 비교 (v0.7 기준, REALISTIC_DEPLOYMENT S1 seed=42)
| 항목 | 선형 C2 (3축 분리) | Kill Web (IAOC 통합) |
|------|-------------------|----------------------|
| S2S 시간 | ~107s | ~12s (9배 빠름) |
| 누출률 | 26.7% | **8.9%** (3배 개선) |
| 교전 성공률 | 80.8% | **53.8%** |
| 다층 교전 기회 | 2.7회 | **2.1회** (적은 시도 → 높은 효율) |
| 중복교전율 | 7.7% | **0.0%** (COP 공유 방지) |
| 토폴로지 | 3축 분리 (MCRC/KAMD/육군) | 완전 메시 (IAOC 통합) |
| COP 품질 | 위협 항적만 (축 간 미공유) | **위협 + 아군 상태 + 교전 계획** |
| 센서 융합 | 단일 센서 (σ=0.5km) | **√N 오차 감소 (min 0.1km)** |
| 사수 선택 | 축별 통제 사수만 | **Any Sensor → Best Shooter** |
| 위협 식별 | 단일 센서 (MLRS 70% 오인식) | **다중 센서 융합 (100% 정확)** |
| 교전 정책 | 고정 다중 교전 | **적응형 (탄약 기반 자동 전환)** |
| 센서 큐잉 | C2→큐잉 3~10s + 추적 5~15s | **C2→큐잉 1~3s + 추적 2.5~7.5s** |

## 현재 버전: v0.7.3 (시뮬레이션 현실화)
**상태**: v0.6.5 + 시뮬레이션 현실화 보완 (무기체계 10종, 센서 7종, C2 6종, 3축 분리, 위협 식별, 다층 교전, 중복교전, 센서 큐잉) + 264개 테스트 (20개 파일)

## 소프트웨어 아키텍처 흐름 (v0.7)
```
config.py → ontology.py → registry.py → strategies.py → model.py → agents.py
(파라미터)   (Pydantic 타입)  (타입 레지스트리)  (전략 패턴)     (시뮬엔진)    (Mesa 에이전트)
                                            ↓                  ↓
                                    run_killchain()     다층 핸드오프
                                    run_killchain_for_axis()  다축 킬체인
                                    identify_threat_type()    위협 식별
                                    센서 큐잉 SimPy 지연      SENSOR_CUEING_DELAYS
```
- **초기화 순서**: Registry 로드 → Strategy 생성 → Agent 생성 → Topology 빌드 → Comm 채널
- **런타임 규칙**: Pydantic 빌드 타임 전용, step() 루프에서 Pydantic 호출 금지
- **배치 선택**: deployment 파라미터로 DEFAULT_DEPLOYMENT / REALISTIC_DEPLOYMENT 선택

## 모듈별 핵심 역할 (v0.7)
| 모듈 | 핵심 역할 | v0.7 변경 |
|------|-----------|-----------|
| `config.py` | 파라미터 집중 관리 | 무기 10종, 센서 7종, C2 6종, REALISTIC_DEPLOYMENT, ENGAGEMENT_LAYERS, THREAT_ID_CONFIG |
| `ontology.py` | Pydantic 빌드타임 검증 | min_altitude, intercept_method, radar_signature, cost_ratio 필드 |
| `registry.py` | config→온톨로지, Pk 우선순위, 역조회 | get_sensors_by_role, get_shooters_by_altitude_range |
| `strategies.py` | Linear 3축 분리 / KillWeb IAOC 통합 | 위협 식별, 센서 큐잉 SimPy 지연, run_killchain_for_axis (다축 킬체인) |
| `agents.py` | Mesa 에이전트 4종 | identified_type 기준 Pk 조회, detectable_types 필터, min_altitude 체크 |
| `model.py` | 시뮬엔진 — strategy 위임 | 다층 핸드오프, 다축 킬체인, 축별 교전 추적 |
| `network.py` | 토폴로지 빌더 | build_realistic_linear/killweb_topology |
| `threats.py` | 위협 생성기 | TOT 스케줄링, THREAT_ORIGINS 기반 생성 |
| `metrics.py` | 18개 성능 지표 | 중복교전율, 고가자산소모율, 위협식별정확도, 다층기회, C2간지연 |
| `comms.py` | SimPy 통신 | redundancy_factor, SENSOR_CUEING_DELAYS |

## v0.5에서 구현된 핵심 사항
1. **COP 품질 차별화** — Kill Web: 센서 융합 √N 오차, 아군 상태 공유, 교전 계획 공유
2. **적응형 교전 정책** — 탄약 30% 이하 단일교전, 10% 이하 고위협만 교전
3. **통신 네트워크 동적 열화** — 링크별 차등 재밍, Kill Web 메시 다중경로 완화
4. **2D 전술 시각화 모듈** — TacticalVisualizer (렌더/애니메이션/비교/타임라인)

## v0.7에서 구현된 핵심 사항 (시뮬레이션 현실화)
1. **무기체계 확장** — THAAD, L-SAM ABM/AAM, 천궁-I, 천마 + min_altitude 고도 필터
2. **센서 역할 분리** — GREEN_PINE(조기경보), FPS117(방공관제), TPS880K(국지방공) + detectable_types
3. **C2 3축 분리** — MCRC(항공기/CM), KAMD_OPS(탄도탄), ARMY_LOCAL_AD(저고도) 독립 라우팅
4. **Kill Web IAOC 통합** — Any Sensor → Best Shooter, 교전상태 COP 공유
5. **위협 식별 모델** — Linear 단일센서 오인식(70%), KillWeb 다중센서 정확식별(100%)
6. **KN-25 MLRS** — ballistic 시그니처, cost_ratio=0.01, 장사정포 포화 시나리오
7. **TOT 스케줄링** — 역산 발사시각으로 동시도착 복합공격
8. **다층 교전 핸드오프** — 교전 실패 시 다른 유형 사수가 재교전
9. **중복교전 모델링** — Linear 3축에서 다축 독립 킬체인 → 동일 표적 중복 교전
10. **센서 큐잉 SimPy 지연** — 큐잉→추적획득→화력통제 단계별 지연
11. **REALISTIC_DEPLOYMENT** — 한반도 5개 방어구역, THREAT_ORIGINS 기반 위협 생성
12. **메트릭 6개 추가** — 중복교전율, 고가자산소모율, 위협식별정확도, 다층기회, C2간지연

## 알려진 문제 (v0.7.3)
- 한글 폰트 미지원 — matplotlib 시각화에서 한글 글리프 경고
- 스냅샷 메모리 — record_snapshots=True 시 배치 실험에서 메모리 증가 가능
- 천궁-II 탄종 이원화 미구현 — 대탄도탄/대항공기 모드 분리 (v0.8)
- 비호 복합무장 미구현 — 기관포+신궁 (v0.8)
- LAMD 장사정포요격체계 미구현 — 미래전력 (v0.8 이후)
- Cesium Ion 토큰 하드코딩 — 환경변수 분리 권장

## 다음 작업: v0.8 (Monte Carlo 통계 분석)
- 상세 Spec: 추후 계획 수립

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

# 전체 테스트 (264개)
python -m pytest tests/ -v

# Cesium 3D 시각화 (시뮬→CZML→웹서버)
python run_cesium.py --serve                    # S1 기본
python run_cesium.py --all --serve              # 전 시나리오
python run_cesium.py -s scenario_2_complex      # 특정 시나리오
```

## 버전 완료 체크리스트
v0.x 단위 작업 완료 시 아래 파일을 반드시 갱신:
1. `CHANGELOG.md` — 변경사항(v0.x.x 세부 포함), 테스트 현황, 알려진 문제
2. `CLAUDE.md` — 현재 버전, 디렉터리 구조, 모듈 역할, 알려진 문제, 다음 작업
3. `README.md` — **v0.x 단위만** 기록. 기술 스택, 아키텍처 버전, 프로젝트 구조, 실행 방법, 로드맵
   - v0.x.x 하위 버전 세부사항은 README에 기록하지 않음 (CHANGELOG.md 전용)
   - 로드맵: 완료된 v0.x + 다음 예정 v0.x만 기록

## 이력 관리 파일
| 파일 | 갱신 단위 | 내용 범위 |
|------|-----------|-----------|
| `README.md` | v0.x | 프로젝트 개요, 기술 스택, 구조, 실행법, 로드맵 |
| `CHANGELOG.md` | v0.x.x | 상세 변경사항, 테스트 현황, 문제점, 개선 계획 |
| `CLAUDE.md` | v0.x.x | 에이전트 컨텍스트 (디렉터리, 모듈 역할, 코딩 규칙, 명령어) |
| `plan.md` | 작업 단위 | 현재 진행 중인 개선 작업의 상세 기술 계획 (v0.6 완료) |
| `cesium_integration_plan.md` | — | Cesium 3D 시각화 통합 상세 스펙 (Phase 1~5, 완료) |
| `dev_blueprint.md` | — | 초기 개발 청사진 (참조용, 동결) |
