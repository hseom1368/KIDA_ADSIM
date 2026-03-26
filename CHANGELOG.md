# CHANGELOG — KIDA_ADSIM 버전 이력

> 각 버전에 [변경사항], [발견된 문제], [개선 계획]을 통합 기록하여
> 새 세션에서 맥락을 빠르게 파악할 수 있도록 함.

---

## [v0.7.3] — 2026-03-26

### 변경사항

#### 고가자산 소모율 + 중복교전 해결
- `modules/agents.py`: `can_engage()`/`compute_pk()`에서 Pk 조회를 `threat.identified_type` 기준으로 변경 — 오인식 시 해당 유형의 Pk로 교전 (getattr fallback으로 하위 호환)
- `modules/config.py`: PAC-3/CHEONGUNG2/THAAD/LSAM_ABM pk_table에 `MLRS_GUIDED` Pk 추가
- `modules/model.py`: `_threat_detected_axes`, `_threat_killchain_axes` 추적, `_record_sensor_axis()` 센서별 C2 축 매핑, 다축 킬체인 추가 실행
- `modules/strategies.py`: `run_killchain_for_axis()` ABC 기본 구현 + LinearC2Strategy 축별 독립 킬체인 + 중복교전 기록
- `tests/test_v073_fixes.py` 신규 (7개 테스트)

#### 검증 결과
- **고가자산 소모**: KillWeb S7에서 waste=79.4% (PAC-3→MLRS 15회, CHEONGUNG2→MLRS 12회)
- **중복교전**: Linear S6에서 dup=44.2% (23건, KAMD↔MCRC↔ARMY 축 간). KillWeb 0%
- **DEFAULT_DEPLOYMENT**: waste=0%, dup=0% (하위 호환 완전 유지)

---

## [v0.7.2] — 2026-03-26

### 변경사항

#### REALISTIC_DEPLOYMENT 전면 재배치 (§8.3 좌표계 준수)
- 천마/비호: Zone A(전방 y=15~20) + Zone B(수도권 y=40) 배치
- TPS880K: Zone A + 수도권 전방(y=45) 배치 (UAS 탐지 보강)
- SHORAD_RADAR 추가 배치 (y=20, y=35)
- 천마(수도권 보강) 2기 추가 (§8.3 ZONE_B 반영)

#### THREAT_ORIGINS 기반 위협 생성
- S6/S7 시나리오에서 `use_threat_origins=True`
- SRBM: 평양(y=-180)에서 발사, UAS/CM/MLRS: DMZ(y=-10)에서 발사
- `_origin_based_position()` 함수 추가

#### 다층 교전 핸드오프
- `_threats_engaged_layers`: 교전 시도한 사수 유형 추적
- 동일 유형 재교전 방지, 다른 유형 사수가 재교전 시도
- `metrics.record_layer_attempt()` 호출

#### 센서 큐잉 SimPy 지연 (SENSOR_CUEING_DELAYS 적용)
- Linear: C2→큐잉(3~10s) + 추적획득(5~15s) + 화력통제(2~5s)
- KillWeb: C2→큐잉(1~3s) + 추적획득(2.5~7.5s, 자동큐잉)

#### 검증 결과
- UAS 15/15 탐지+격추, 천마 6~7shots, 비호 2shots
- 다층 교전: 위협당 평균 2.2~2.7회 교전 시도
- Linear S2S: 89~107초, KillWeb S2S: 11~12초

---

## [v0.7.1] — 2026-03-26

### 변경사항

#### C2 3축 분리 (LinearC2Strategy)
- `_get_axis_c2()`: 위협 유형별 C2 축 라우팅 (KAMD_OPS/MCRC/ARMY_LOCAL_AD)
- `select_shooter()`: 3축 분리 시 축별 통제 사수 필터
- `_has_3axis_c2()`: DEFAULT_DEPLOYMENT에서 기존 동작 유지 게이트
- `C2_AXIS_CONTROL`, `THREAT_C2_AXIS` 매핑 추가

#### 위협 식별 모델
- `identify_threat_type()`: Linear 단일센서 오인식(70%), KillWeb 다중센서 정확식별
- `THREAT_ID_CONFIG`: misid_prob, min_sensors_for_id 파라미터
- `ThreatAgent`: `radar_signature`, `actual_type`, `identified_type`, `cost_ratio` 속성
- `metrics.record_threat_identification()` 호출

#### KN-25 MLRS 위협 + 신규 시나리오
- `MLRS_GUIDED` 위협 유형 (ballistic 시그니처, cost_ratio=0.01)
- `scenario_6_tot_mixed`: TOT 섞어쏘기 (SRBM+CM+UAS 동시도착)
- `scenario_7_mlrs_saturation`: 장사정포 포화 (KN-25 30+20기 + SRBM 5기)
- TOT 역산 발사시각 스케줄링 (`_generate_tot_threats`)

#### 신규 메트릭 6개
- duplicate_engagement_rate, expensive_asset_waste_rate, threat_id_accuracy
- multi_layer_intercept_opportunities, engagement_allocation_efficiency, inter_c2_info_delay

---

## [v0.7.0] — 2026-03-26

### 변경사항

#### 무기체계 5종 신규 추가
- THAAD (200km, 40~150km 고도, SRBM 전용, hit_to_kill)
- LSAM_ABM (150km, 40~60km 고도, 탄도탄 전용)
- LSAM_AAM (200km, ~20km 고도, 항공기/CM)
- CHEONGUNG1 (40km, ~15km 고도, 항공기/CM 전용)
- CHUNMA (9km, ~5km 고도, 저고도 방어)

#### 기존 무기체계 스펙 수정
- PAC-3 MSE: max_altitude 30→40km, max_range 120→90km
- 전 사수에 `min_altitude` 필드 추가 (기본 0)
- 전 사수에 `intercept_method` 필드 추가

#### 센서 3종 신규 + 역할 분리
- GREEN_PINE (800km, 탄도탄 조기경보, detectable_types=["SRBM"])
- FPS117 (470km, 방공관제, min_detection_altitude=1.0km)
- TPS880K (40km, 국지방공, min_detection_altitude=0.05km)
- 기존 센서에 role="weapon_fc" 기본값 (하위 호환)

#### C2 노드 3종 신규
- KAMD_OPS (탄도탄 전담), ARMY_LOCAL_AD (육군 국지방공), IAOC (Kill Web 통합)

#### REALISTIC_DEPLOYMENT (한반도 5개 방어구역)
- Zone A (전방): 천마, 비호, TPS880K
- Zone B (수도권): PAC-3, 천궁-I/II, 천마(보강)
- Zone C (중부): 그린파인, FPS117
- Zone D (남부): THAAD, L-SAM, 그린파인

#### 네트워크 토폴로지 확장
- `build_realistic_linear_topology()`: 3축 분리 (MCRC↔KAMD 부분연결, 육군 독립)
- `build_realistic_killweb_topology()`: IAOC 중심 완전 메시

### 테스트 현황
- v0.7.0: 244개 → v0.7.1: 257개 → v0.7.2: 257개 → v0.7.3: 264개 PASS
- DEFAULT_DEPLOYMENT 하위 호환 100%

### 알려진 문제
- 한글 폰트 미지원 (matplotlib 시각화에서 글리프 경고)
- 천궁-II 탄종 이원화 미구현 (대탄도탄/대항공기 모드 분리 → v0.8)
- 비호 복합무장 미구현 (기관포+신궁 → v0.8)
- LAMD 장사정포요격체계 미구현 (미래전력 → v0.8 이후)

---

## [v0.6.5] — 2026-03-25

### 변경사항

#### v0.6.1 — CZML Exporter 고도화 (Python Backend)
- `modules/exporters.py` 확장 (+381줄)
  - 위협 궤적 보간 (LAGRANGE/LINEAR, 유형별 자동 적용)
  - 교전 이벤트 CZML 패킷 (사수→위협 polyline + 명중/실패 효과 마커)
  - C2 토폴로지 연결선 패킷 (선형=흰색 실선, 킬웹=파랑 점선)
  - `CesiumConfigExporter` 클래스 (viewer_config.json 7개 섹션)
  - `topology_edges`/`architecture` optional 파라미터 (하위 호환)
- `tests/test_schema_compliance.py` 신규 (19개 테스트)
- `tests/test_exporters.py` 확장 (+10개 통합 테스트)

#### v0.6.2 — CesiumJS 통합 뷰어 기반
- `cesium-viewer/` 디렉토리 신규 생성
  - `index.html` — CesiumJS 1.130 CDN + Military HUD 레이아웃
  - `js/czml-loader.js` — CZML 로더 + 시간 컨트롤 (재생/속도/스크러빙)
  - `js/app.js` — 메인 앱 (비교 모드, 시나리오 선택, 카메라 프리셋)
  - `css/hud.css` — Military HUD 스타일 (녹색 콘솔 테마)

#### v0.6.3 — 3D 센서 볼륨 & 교전 시각화
- `js/radar-volumes.js` — EllipsoidGeometry Primitive API 레이더 볼륨 (방위각 슬라이더)
- `js/engagement-viz.js` — 요격 미사일 궤적 (부스터+곡선유도) + ParticleSystem 폭발 이펙트
- `js/topology-viz.js` — link_type별 색상 구분 토폴로지 시각화

#### v0.6.4 — 성능 최적화 & HUD
- `js/performance.js` — LabelCollection/PointPrimitiveCollection 정적 라벨
- `js/hud-panel.js` — 실시간 방어 현황 + 교전 카운터 + 스크롤 로그
- requestRenderMode — 일시정지 시 CPU 절약

#### v0.6.5 — 통합 검증 & 문서화
- `tests/test_e2e_cesium.py` — E2E 통합 테스트 7개 (전 파이프라인 검증)
- `run_cesium.py` — 시뮬레이션→내보내기→웹서버 자동화 스크립트
- CHANGELOG.md, CLAUDE.md 갱신

### 테스트 현황
- 전체: 182개 PASS (기존 146 + v0.6 신규 36)
- 시뮬레이션 기준선 불변: linear=35.6%, killweb=22.2%
- SSOT 준수: 프론트엔드 JS에 Math.random()/충돌 판정 코드 0건

### 알려진 문제
- Cesium Ion 토큰 하드코딩 (환경변수 분리 권장)
- 한글 폰트 미지원 (matplotlib + Cesium 양쪽)
- ParticleSystem fire.png 미사용 (캔버스 생성 스프라이트로 대체)

---

## [v0.5.1] — 2026-03-23

### 변경사항

#### Pydantic 도메인 온톨로지 (신규 모듈)
- `modules/ontology.py` 신규 (157행)
  - `SensorType`, `C2Type`, `ShooterType`, `ThreatType` — 4개 엔티티 타입 모델
  - `DetectionCapability`, `C2Capability`, `EngagementCapability`, `ThreatCapability` — 능력 모델
  - `FlightPhase`, `FlightProfile` — 비행 프로파일 스키마
  - `WaveSpec`, `ScenarioSchema` — 시나리오 구조 검증
  - 토폴로지 관계 필드 내장 (`reporting_c2_type`, `parent_c2_type`, `controlling_c2_type`)

#### 엔티티 레지스트리 (신규 모듈)
- `modules/registry.py` 신규 (182행)
  - `load_from_config()`: config.py 딕셔너리 → Pydantic 온톨로지 자동 변환
  - `get_prioritized_shooters(threat_type_id)`: Pk 기반 사수 우선순위 정렬
  - `get_sensors_for_c2()`, `get_shooters_for_c2()`, `get_child_c2_types()`: 토폴로지 역조회
  - `TOPOLOGY_RELATIONS` (config.py 추가): sensor_to_c2, c2_hierarchy, shooter_to_c2 매핑

#### Strategy 패턴 (신규 모듈)
- `modules/strategies.py` 신규 (420행)
  - `ArchitectureStrategy` ABC — 9개 추상 메서드 정의
  - `LinearC2Strategy` — 계층형 킬체인, Pk 우선 사수 선택, 고정 교전 정책
  - `KillWebStrategy` — COP 융합 킬체인, 가중 점수 사수 선택, 적응형 교전
  - model.py의 **11개 인라인 if/else 아키텍처 분기를 전략 위임으로 교체**

#### CZML 내보내기 (신규 모듈)
- `modules/exporters.py` 신규 (270행)
  - `CZMLExporter` 클래스 — 시뮬레이션 스냅샷 → CZML 형식 변환
  - 한반도 중심 좌표 기준 (127.0°E, 37.0°N) 변환
  - 위협 궤적, 센서/사수 커버리지, C2 노드, 방어 목표 패킷 생성
  - Cesium.js 3D 시각화 연동 가능

#### model.py 리팩토링
- Registry → Strategy → Agent → Topology → Comm 초기화 순서 확립
- `self.strategy.method()` 위임으로 아키텍처 분기 코드 제거
- 시뮬레이션 로직 변경 없이 구조적 개선 달성

#### comms.py 개선
- `architecture` 문자열 직접 의존 제거
- `redundancy_factor` 수치 파라미터 주입 방식으로 전환

#### config.py 확장
- `TOPOLOGY_RELATIONS` 딕셔너리 추가
  - `sensor_to_c2`: EWR→MCRC, PATRIOT_RADAR→TOC_PAT 등
  - `c2_hierarchy`: TOC_PAT→MCRC, TOC_MSAM→MCRC 등
  - `shooter_to_c2`: PATRIOT_PAC3→TOC_PAT 등

#### 테스트 확장 (60개 신규)
- `test_ontology.py` 신규 (20+개) — 4개 엔티티 타입 검증, 필드 제약, 능력 모델
- `test_registry.py` 신규 — config 로드, Pk 우선순위, 토폴로지 역조회
- `test_strategies.py` 신규 — 선형/킬웹 전략 동작, 모델 통합
- `test_exporters.py` 신규 — CZML 패킷 생성, 궤적 변환, 센서/사수 렌더링
- 총 **146개 테스트** 전부 PASS (기존 86개 + 신규 60개, 13개 파일)

### 성능 검증 (v0.5.1 = v0.5 동일)
- 시나리오 1 seed=42 기준선 완전 일치 확인
- 리팩토링으로 인한 성능 변화 **0%** (순수 구조 개선)

### 발견된 문제
1. **한글 폰트 미지원** — matplotlib 시각화에서 한글 글리프 경고 (기존 이슈 유지)
2. **스냅샷 메모리** — record_snapshots=True 시 배치 실험 메모리 증가 가능 (기존 이슈 유지)
3. **agents.py 온톨로지 DI 미완료** — 현재 config.py 딕셔너리 직접 참조 유지
   - 향후 Phase 5에서 에이전트 생성자에 온톨로지 타입 주입 예정

### 개선 계획 (v0.6)
- v0.5 동일 — Monte Carlo 통계 분석 프레임워크

---

## [v0.5] — 2026-03-12

### 변경사항

#### COP 품질 차별화 (v0.5 핵심 기능)
- `config.py`: `COP_CONFIG` 파라미터 추가
  - `fusion_error_reduction=True`: Kill Web 센서 융합 √N 오차 감소
  - `min_fused_error=0.1km`: 융합 오차 하한선
  - `friendly_status_bonus=0.15`: 아군 상태 공유 시 사수 점수 보너스
  - `fusion_pk_bonus_max=0.10`: 센서 융합 Pk 보너스 상한
- `agents.py`: `C2NodeAgent`에 `friendly_status`, `engagement_plan` 필드 추가
  - `update_friendly_status()`: Kill Web 전용 아군 사수 상태 갱신
  - `update_engagement_plan()`: Kill Web 전용 교전 계획 공유
  - `ShooterAgent.engage()`: `pk_bonus` 파라미터 추가 (센서 융합 보너스)
- `model.py`: Kill Web COP 차별화 로직 구현
  - `_fuse_tracks()`: 복수 센서 추적 시 √N 오차 감소
  - `_update_friendly_status()`: 매 스텝 아군 상태 공유
  - `_update_engagement_plan()`: 교전 계획 C2 노드 공유
  - `_find_best_shooter()`: COP 아군 상태 기반 사수 선정 최적화

#### 적응형 교전 정책
- `config.py`: `ADAPTIVE_ENGAGEMENT` 파라미터 추가
  - `ammo_threshold_ratio=0.3`: 탄약 30% 이하 시 단일 교전 전환
  - `critical_ammo_ratio=0.1`: 탄약 10% 이하 시 고위협만 교전
  - `critical_threat_types`: SRBM, CRUISE_MISSILE
- `model.py`: `_get_adaptive_max_shooters()` — Kill Web 전용 적응형 교전 규모 결정

#### 통신 네트워크 동적 열화
- `config.py`: `COMM_DEGRADATION` 파라미터 추가
  - `link_failure_threshold=0.8`: 재밍 0.8 이상 링크 두절
  - `killweb_redundancy_factor=0.5`: Kill Web 메시 구조 열화 완화
- `comms.py`: `CommChannel` 확장
  - `get_link_latency()`: 링크별 차등 지연 계산
  - `link_degradation`: 링크별 열화 상태 관리
  - `is_message_delivered()`: 링크별 열화 반영 가능

#### 2D 전술 시각화 모듈 (신규)
- `modules/viz.py`: `TacticalVisualizer` 클래스
  - `render_frame()`: 특정 시점 전술 상황도 렌더링
  - `animate()`: 전체 시뮬레이션 리플레이 (GIF 저장 가능)
  - `snapshot_comparison()`: 복수 아키텍처 나란히 비교
  - `event_timeline()`: 킬체인 이벤트 타임라인 바 차트
- `model.py`: `record_snapshots` 파라미터 + `_record_snapshot()` 메서드
  - 매 스텝 에이전트 상태 기록 (시각화 모드 전용)

#### 시각화 노트북
- `notebook5_tactical_viz.ipynb` 신규
  - 정적 스냅샷 4패널, 아키텍처 비교, 이벤트 타임라인, 전체 애니메이션, COP 분석

#### 테스트 확장
- `test_cop_differentiation.py` 신규 (11개 테스트)
  - COP 설정 검증, 센서 융합, 아군 상태 공유
- `test_adaptive_engagement.py` 신규 (13개 테스트)
  - 적응형 교전, 통신 열화, 스냅샷 기능
- `test_viz.py` 신규 (5개 테스트)
  - 시각화 모듈 기본 동작 검증
- 총 86개 테스트 전부 PASS (기존 57개 + 신규 29개)

### 전 시나리오 성능 비교표 (v0.5, seed=42)

| 시나리오 | 아키텍처 | 누출률% | 성공률% | S2S(s) | 다중교전% |
|----------|----------|---------|---------|--------|-----------|
| S1 포화공격 | Linear | 35.6 | 37.1 | 343.9 | 14.3 |
| S1 포화공격 | **KillWeb** | **22.2** | **37.5** | **5.0** | **16.7** |
| S2 복합위협 | Linear | 26.3 | 30.3 | 288.0 | 12.1 |
| S2 복합위협 | **KillWeb** | **13.2** | **40.5** | **5.0** | 9.5 |
| S3 EW Light | Linear | 26.3 | 42.4 | 336.9 | 18.2 |
| S3 EW Light | **KillWeb** | **15.8** | 41.9 | **7.5** | 14.0 |
| S3 EW Moderate | Linear | 34.2 | 40.7 | 512.8 | 18.5 |
| S3 EW Moderate | **KillWeb** | **15.8** | **41.5** | **14.8** | 12.2 |
| S3 EW Heavy | Linear | 39.5 | 21.7 | 588.5 | 4.3 |
| S3 EW Heavy | **KillWeb** | **21.1** | **43.3** | **24.9** | 6.7 |
| S4 순차교전 | Linear | 35.8 | 43.8 | 148.6 | 6.2 |
| S4 순차교전 | **KillWeb** | **31.3** | 43.1 | **5.1** | **15.5** |
| S5 노드파괴 | Linear | 22.2 | 42.9 | 113.5 | 16.7 |
| S5 노드파괴 | **KillWeb** | 22.2 | 37.5 | **5.0** | 16.7 |

**핵심 분석 (v0.4 → v0.5 변화)**:
- Kill Web **전 시나리오 누출률 우위** 유지 (평균 20.2% vs 32.3%)
- COP 차별화로 Kill Web S2 성공률 40.5% (v0.4: 41.9%) — 아군 상태 기반 사수 재할당
- S3 EW Moderate: Kill Web 누출률 15.8% (v0.4: 15.8%) — 메시 다중경로 통신 내성 유지
- 적응형 교전: S4 Kill Web 누출률 31.3% (v0.4: 32.8%) — 탄약 절약 효과
- S5 노드파괴: 양쪽 동일 누출률 22.2% — v0.4와 동일 패턴 유지

### 발견된 문제
1. **한글 폰트 미지원** — matplotlib 시각화에서 한글 글리프 경고 (DejaVu Sans)
   - 대안: 영문 라벨 사용 또는 한글 폰트 설치
2. **스냅샷 메모리** — record_snapshots=True 시 300회 Monte Carlo 배치에서 메모리 증가 예상
   - 시각화 전용 옵션이므로 배치 실험에서는 사용하지 않을 것

### 개선 계획 (v0.6)
1. **Monte Carlo 300회 배치 실험 프레임워크**
   - 전 시나리오(7개) × 2 아키텍처 × 300 시드 = 4,200회 시뮬레이션
   - 수렴 분석 (누적 평균 안정성으로 300회 충분성 검증)
   - 결과 CSV/Parquet 저장, multiprocessing 병렬화
2. **통계 분석 모듈** (`modules/stats.py` 신규)
   - Shapiro-Wilk 정규성 검정 → Welch's t-test / Mann-Whitney U 선택
   - Cohen's d 효과 크기, 95% 신뢰 구간
   - Bonferroni 다중 비교 보정
3. **최종 분석 보고서** — 시나리오별 성능 비교, 정책 제언 포함 종합 보고
   - 박스플롯, 바이올린 플롯, 히트맵, 레이더 차트, 포레스트 플롯
4. **인터랙티브 시각화 (선택)** — plotly/dash 기반 웹 대시보드

---

## [v0.4] — 2026-03-11

### 변경사항

#### v0.3 알려진 이슈 전량 해소
- `model.py`: **jamming_level 오버라이드 정리** — `jamming_level=None` 기본값 도입
  - 명시적 파라미터 > 시나리오 config > 기본값 0.0 우선순위 확립
  - `AirDefenseModel(jamming_level=0.5)` 호출 시 시나리오 값과 무관하게 0.5 적용
- `comms.py`: **죽은 코드 삭제** — `linear_killchain()`, `killweb_killchain()` 제거 (118행)
  - 실제 킬체인 로직은 `model.py._killchain_process()`에 완전 구현
  - `KillChainProcess` 클래스는 `log_event()` 이벤트 기록 역할로 유지
- `config.py`: **죽은 설정 삭제** — 원본 `scenario_3_ew` 제거 (17행)
  - 3개 하위 시나리오(`_light`/`_moderate`/`_heavy`)가 완전 대체

#### 다중 교전 모델링 (v0.4 핵심 기능)
- `config.py`: `ENGAGEMENT_POLICY`에 다중 교전 파라미터 추가
  - `max_simultaneous_shooters`: SRBM=3, CRUISE_MISSILE=2, AIRCRAFT=1, UAS=1
  - `default_max_simultaneous`: 1 (미정의 위협 기본값)
- `model.py`: `_execute_engagements()` 리팩토링
  - 위협 우선도 기반 복수 사수 동시 교전 지원
  - `_execute_multi_engagement()` 신규 메서드 — 독립 Bernoulli 교전, 하나라도 명중 시 격추
- `metrics.py`: 12개 메트릭으로 확장 (기존 10개 + 2개 신규)
  - `multi_engagement_rate`: 다중 교전 비율 (%)
  - `avg_shooters_per_multi_engagement`: 다중 교전 시 평균 동시 사수 수

#### 테스트 확장
- `test_multi_engagement.py` 신규 (12개 테스트)
  - 설정 검증, 실행 검증, 회귀 호환성, jamming_level 오버라이드 검증
- 총 57개 테스트 전부 PASS

#### 노트북 업데이트
- `notebook3`: v0.4 다중 교전 메트릭 수집 반영
- `notebook4`: Cohen's d 효과 크기, 다중 교전 분석 섹션 추가

### 전 시나리오 성능 비교표 (v0.4, seed=42)

| 시나리오 | 아키텍처 | 누출률% | 성공률% | S2S(s) | 격추 | 총교전 | 다중교전% |
|----------|----------|---------|---------|--------|------|--------|-----------|
| S1 포화공격 | Linear | 35.6 | 37.1 | 343.9 | 13 | 35 | 14.3 |
| S1 포화공격 | **KillWeb** | **22.2** | 36.7 | **5.0** | **18** | 49 | 16.3 |
| S2 복합위협 | Linear | 26.3 | 30.3 | 288.0 | 10 | 33 | 12.1 |
| S2 복합위협 | **KillWeb** | **13.2** | **41.9** | **5.1** | **18** | 43 | 9.3 |
| S3 EW Light | Linear | 26.3 | 42.4 | 336.9 | 14 | 33 | 18.2 |
| S3 EW Light | **KillWeb** | **18.4** | 38.5 | **7.5** | 15 | 39 | 15.4 |
| S3 EW Moderate | Linear | 34.2 | 40.7 | 512.8 | 11 | 27 | 18.5 |
| S3 EW Moderate | **KillWeb** | **15.8** | 39.5 | **14.8** | **17** | 43 | 11.6 |
| S3 EW Heavy | Linear | 39.5 | 21.7 | 588.5 | 5 | 23 | 4.3 |
| S3 EW Heavy | **KillWeb** | **21.1** | **43.3** | **24.9** | **13** | 30 | 6.7 |
| S4 순차교전 | Linear | 35.8 | 43.8 | 148.6 | 21 | 48 | 6.2 |
| S4 순차교전 | **KillWeb** | **32.8** | 39.1 | **5.1** | **25** | 64 | 14.1 |
| S5 노드파괴 | Linear | 22.2 | 42.9 | 113.5 | 18 | 42 | 16.7 |
| S5 노드파괴 | **KillWeb** | 22.2 | 36.7 | **5.0** | 18 | 49 | 16.3 |

**핵심 분석 (v0.3 → v0.4 변화)**:
- 다중 교전으로 **총 교전 수 증가** (사수 집중 투입) → 탄약 소비 증가
- Kill Web이 **전 시나리오에서 누출률 우위** 유지 (평균 20.8% vs 32.2%)
- v0.3 대비 Kill Web 누출률 소폭 상승 (11.1%→22.2%, S1) — 다중 교전이 사수 가용성을 일시 감소
- S5 노드파괴: 양쪽 동일 누출률(22.2%) — 다중 교전 효과가 노드 손실과 상쇄
- S3 EW Heavy: Kill Web 성공률 43.3% vs Linear 21.7% — 재밍 환경에서 다중교전 효과 극대화

### 발견된 문제
1. **다중 교전의 탄약 고갈 가속** — SRBM에 3기 사수 투입 시 탄약 소모 빠름
   - v0.5에서 잔여 탄약 기반 적응형 교전 정책 도입 예정
2. **S5 Kill Web 누출률 미개선** — 노드 파괴 시 가용 사수 부족으로 다중교전 효과 제한

### 개선 계획 (v0.5)
1. **COP 품질 차별화** — Linear: 위협 항적만 공유 / Kill Web: 위협 + 아군 자산 상태 + 대응 계획 공유
   - 센서 융합 √N 오차 감소 (복수 센서 추적 시)
   - 아군 상태 공유로 사수 재할당 최적화 (재장전 회피, 탄약 부족 교체)
2. **적응형 교전 정책** — 잔여 탄약 30% 이하 시 다중→단일 교전 전환, 10% 이하 시 고위협 선별 교전
3. **통신 네트워크 동적 열화** — 재밍 링크별 차등 열화 (SNR 기반), 임계값 이상 링크 두절
4. **2D 전술 시각화 모듈** — matplotlib.animation 기반 전투공간 리플레이
   - 에이전트 배치/이동 궤적, 센서·사수 커버리지, 교전 이벤트, 킬체인 연결선
5. **시각화 노트북** — notebook5 신규: 시나리오별 전술 애니메이션 + 아키텍처 비교 스냅샷

---

## [v0.3] — 2026-03-09

### 변경사항

#### v0.2 미해결 이슈 전량 해소
- `metrics.py`: `MetricsCollector.shooters` 필드 추가 → `defense_coverage` 정상 작동
- `config.py`: 시나리오 3을 3개 하위 시나리오로 분할 (light/moderate/heavy)
  - 각각 `detection_factor`, `latency_factor` 개별 설정
- `model.py`: `detection_factor`/`latency_factor` 시나리오 파라미터 반영
  - 센서 탐지 확률: `SensorAgent.detect()` → `detection_factor` 적용
  - C2 통신 지연: `CommChannel.latency_factor` 직접 설정
- `model.py`: 시나리오 4 `duration > max_sim_time` 동적 조정
- `config.py`: `EXPERIMENT_CONFIG`에 시나리오 2~4 추가 (7개 시나리오 완비)
- `tests/`: 단위 테스트 프레임워크 구축 (4개 파일, 33개 테스트)

#### v0.3 검증 심화 및 코드 품질 리뷰
- **버그 수정**: `shooter_score()`가 2D `math.dist()` → 3D `_slant_range()` 사용하도록 수정
- **매직 넘버 제거**: 6개 하드코딩 상수를 `ENGAGEMENT_POLICY`로 이동
  - `effective_range_ratio=0.95`, `jamming_pk_penalty=0.3`
  - `tracking_position_error_std=0.5`, `coverage_overlap_factor=0.7`
  - `target_arrival_distance=1.0`
- **엣지 케이스 테스트 12개 추가** (총 45개 테스트)
  - 탄약 소진, 극한 재밍, 노드 파괴 회복탄력성, 시나리오 4 재현성
  - `shooter_score()` 3D 거리 검증, config 상수 검증

### 전 시나리오 성능 비교표 (seed=42)

| 시나리오 | 아키텍처 | 누출률% | 성공률% | S2S(s) | 격추 | 총교전 |
|----------|----------|---------|---------|--------|------|--------|
| S1 포화공격 | Linear | 35.6 | 37.5 | 354.4 | 12 | 32 |
| S1 포화공격 | **KillWeb** | **11.1** | **44.4** | **4.9** | **20** | 45 |
| S2 복합위협 | Linear | 26.3 | 29.4 | 286.5 | 10 | 34 |
| S2 복합위협 | **KillWeb** | **10.5** | **39.0** | **5.1** | **16** | 41 |
| S3 EW Light | Linear | 26.3 | 31.2 | 344.5 | 10 | 32 |
| S3 EW Light | **KillWeb** | **10.5** | **57.6** | **7.3** | **19** | 33 |
| S3 EW Moderate | Linear | 39.5 | 30.0 | 543.1 | 6 | 20 |
| S3 EW Moderate | **KillWeb** | **21.1** | 20.8 | **14.6** | **10** | 48 |
| S3 EW Heavy | Linear | 39.5 | 14.8 | 558.1 | 4 | 27 |
| S3 EW Heavy | **KillWeb** | **23.7** | **30.6** | **24.5** | **11** | 36 |
| S4 순차교전 | Linear | 37.3 | 38.5 | 150.5 | 20 | 52 |
| S4 순차교전 | **KillWeb** | **25.4** | **47.5** | **5.0** | **28** | 59 |
| S5 노드파괴 | Linear | 24.4 | 42.5 | 106.9 | 17 | 40 |
| S5 노드파괴 | **KillWeb** | **11.1** | **44.4** | **4.9** | **20** | 45 |

**핵심 분석**:
- Kill Web이 **전 시나리오에서 누출률 우위** (평균 16.2% vs 32.7%)
- EW Heavy에서도 Kill Web 누출률 23.7% vs Linear 39.5% — 재밍 내성 우수
- EW Moderate에서 Kill Web 성공률 20.8% < Linear 30.0% — 높은 교전 빈도(48발) 대비 Pk 저하
- S4 순차교전: Kill Web이 60분 지속 작전에서도 안정적 (누출 25.4% vs 37.3%)

### 발견된 문제
1. **생성자 `jamming_level` 파라미터 무시** — `model.py:65`에서 시나리오 config가 덮어씀
   - 시나리오에 `jamming_level`이 정의되면 생성자 값이 무시됨
2. **죽은 코드**: `comms.py` `linear_killchain()`/`killweb_killchain()` 미사용
   - `model.py._killchain_process()`에 동일 로직이 중복 구현됨
3. **죽은 설정**: `config.py` `scenario_3_ew` 원본 — 하위 시나리오로 대체됨

### 개선 계획 (v0.4)
- 생성자 `jamming_level` 오버라이드 로직 정리
- `comms.py` 죽은 코드 정리 또는 `model.py`에서 위임하도록 리팩토링
- 다중 교전 모델링 (동일 위협에 복수 사수 동시 교전)
- 센서 융합 로직 고도화 (Kill Web COP 품질 차별화)
- Monte Carlo 300회 배치 실험 실행 및 통계 분석

---

## [v0.2] — 2026-03-09

### 변경사항

#### 위협 비행 프로파일 현실화
- `config.py`: 4종 위협 모두에 `flight_profile` 파라미터 추가
  - SRBM: 부스트(0→50km) → 중간(50→30km) → 종말(30→0km, 풀업기동)
  - 순항미사일: 부스트(0→0.5km) → 해면밀착(30m) → 종말 기동
  - 항공기: 고고도(10km) → 저고도 침투(1km) → 공격 진입
  - UAS: 접근(300m) → 종말 강하(50m)
- `agents.py`: ThreatAgent 비행 프로파일 엔진 구현
  - `__init__`: `phase_timeline` 사전 계산 (가중평균 속도 기반 비행시간 추정)
  - `_compute_phase_state()`: 경과시간 → 고도/속도/기동여부 선형 보간
  - `move()`: 매 스텝 동적 고도·속도·기동 상태 갱신
  - 하위 호환: `flight_profile` 미설정 시 기존 고정 동작 유지

#### 3D 경사거리(Slant Range) 반영
- `agents.py`: `_slant_range()` 유틸리티 함수 추가
  - `SensorAgent.detect()`, `ShooterAgent.can_engage()`, `compute_pk()`에 적용
  - 센서·사수는 지상(0km), 위협은 동적 고도 → 3D 거리 자동 반영

#### 최적 교전 시점(Optimal Engagement) 로직
- `config.py`: `ENGAGEMENT_POLICY` 파라미터 추가
  - `optimal_pk_threshold=0.30`, `emergency_pk_threshold=0.10`
  - `must_engage_distance=30km`, `emergency_opportunity_count=2`
- `model.py`: `_should_engage_now()` 메서드 추가
  - Pk ≥ 0.30 → 교전, Pk 부족 + 여유 있음 → 위협 접근 대기
  - 잔여 교전 기회(비행시간/교전시간) 계산 → 긴급도 판단
  - 방어지역 30km 이내 → 무조건 교전

### 성능 결과 (시나리오 1 포화공격, seed=42)

| 지표 | v0.1 Linear | v0.1 KillWeb | **v0.2 Linear** | **v0.2 KillWeb** |
|------|-------------|--------------|-----------------|------------------|
| 누출률 | 33.3% | 20.0% | 35.6% | **11.1%** |
| 교전 성공률 | 40.0% | 33.3% | 37.5% | **44.4%** |
| 평균 Pk | 0.347 | 0.309 | 0.430 | 0.405 |
| Pk<0.2 교전 | 10건 | 14건 | **0건** | **0건** |
| 격추수 | 14기 | 16기 | 12기 | **20기** |

**핵심**: Kill Web이 Linear C2 대비 전 지표(누출률, 성공률, 격추수)에서 우위 달성.
조기교전 역설(Pk<0.2 교전) 완전 해소.

### 발견된 문제
1. **defense_coverage 메트릭 항상 0.0** — `metric_9_defense_coverage()`에 shooters 미전달
2. **시나리오 3(전자전) 재밍 미분화** — `jamming_levels` 3단계 정의는 있으나 모델에서 미사용
   - 재밍이 `compute_pk()`의 `(1 - jamming * 0.3)` 패널티에만 반영
   - 센서 탐지 확률, C2 처리 지연에는 미적용
3. **시나리오 2~4 미검증** — config에 정의만 있고 실행 검증 없음
4. **EXPERIMENT_CONFIG 불완전** — 시나리오 1, 5만 포함 (2~4 누락)
5. **시나리오 4 시간 제약** — `duration=3600s` > `max_sim_time=1800s` → 30분만 실행됨
6. **tests/ 디렉토리 미존재** — 단위 테스트 없음

### 개선 계획 (v0.3)
- plan.md 상세 참조
- 시나리오 2~4 검증 및 전자전 재밍 고도화
- defense_coverage 메트릭 수정
- 단위 테스트 프레임워크 구축

---

## [v0.2-dev] — 진행 중

### 변경사항
- (아직 코드 변경 없음 — 분석 및 계획 수립 완료)

### 분석 결과: Kill Web 성능 역전 현상 규명
Kill Web이 S2S 시간(5s vs 309s)과 교전 횟수(44발 vs 32발)에서 우위이나,
누출률과 교전 성공률에서 선형 C2에 열세인 원인 3가지를 식별함:

1. **SRBM 고도 제약 (구조적 결함)**
   - SRBM 비행 고도 50km > 모든 사수 최대 교전 고도 (PAC-3: 30km)
   - 양쪽 아키텍처 모두 SRBM 15기 전량 누출 (교전 자체 불가)
   - 원인: 위협 고도가 초기값 고정 → 종말단계 하강 미반영

2. **조기 교전의 역설**
   - Kill Web: S2S 5초 → 사거리 경계(95%)에서 즉시 교전 → Pk ≈ 0.08
   - 선형 C2: S2S 309초 → 40~60% 사거리까지 접근 후 교전 → Pk ≈ 0.51~0.67
   - Kill Web 평균 Pk 0.229, 선형 C2 평균 Pk 0.287
   - 원인: 최적 교전 시점 로직 부재 (사거리 진입 즉시 발사)

3. **사수 분산 효과**
   - Kill Web: 4기 사수에 분산 교전 (각 12~25% 성공률)
   - 선형 C2: 2기 사수에 집중 교전 (44% 성공률)
   - 분산 자체는 바람직하나, 원거리 교전으로 인한 Pk 저하가 상쇄

### 개선 계획 (plan.md 상세 참조)
1. **위협 비행 프로파일 현실화** — 4종 위협 모두에 단계별 동적 고도·속도·기동 도입
   - SRBM: 부스트(0→50km) → 중간비행(50→30km) → 종말(30→0km, 풀업기동)
   - 순항미사일: 부스트 → 해면밀착 30m → 종말 기동
   - 항공기: 고고도 10km → 저고도 침투 1km → 공격 진입
   - UAS: 300m 접근 → 50m 종말 강하
2. **3D 경사거리(Slant Range)** — 탐지·교전 거리에 고도차 반영
3. (v0.3 예정) **최적 교전 시점 로직** — Pk 최적 구간까지 대기 후 교전

---

## [v0.1] — 2026-02-26

### 변경사항
초기 구현 완료. 핵심 시뮬레이션 엔진과 분석 프레임워크 구축.

**모듈 구현 (7개 파일, ~2,100 라인):**
- `config.py` — 센서 4종, C2 3종, 사수 4종, 위협 4종, 시나리오 5종 파라미터
- `agents.py` — Mesa 에이전트 4종 (SensorAgent, C2NodeAgent, ShooterAgent, ThreatAgent)
- `model.py` — Mesa+SimPy 통합 시뮬레이션 엔진 (AirDefenseModel)
- `network.py` — NetworkX 기반 선형 C2 / Kill Web 토폴로지 빌더
- `comms.py` — SimPy 통신 채널 + 킬체인 프로세스 (아키텍처별 분기)
- `metrics.py` — 10개 성능 지표 수집기
- `threats.py` — 5개 시나리오 위협 생성기 (파상/복합/EW/순차/노드파괴)

**노트북 구현 (4개):**
- notebook1: 모델 정의 및 검증
- notebook2: 시나리오 설정 및 실행 (시나리오 1, 5)
- notebook3: Monte Carlo 배치 실험 (300회)
- notebook4: 통계 분석 및 시각화 대시보드

**검증된 결과:**
- Kill Web S2S: ~5s vs 선형 C2: ~309s (63배 향상)
- Kill Web 동시 교전: 17% 향상
- 킬체인 타이밍이 설계 사양과 일치 (선형 48-160s, 킬웹 7-23s)
- 노드 파괴 시뮬레이션 정상 동작

### 발견된 문제
1. **위협 비행 모델 비현실적** — 고도·속도 고정, 직선 이동만 지원
   - SRBM 50km 고정 → PAC-3 교전 불가 (최대 30km)
   - 순항미사일 종말기동 없음 → 비현실적으로 쉬운 교전
   - 항공기 저고도 침투 없음 → 탐지 회피 미반영
2. **거리 계산 2D만 사용** — 고도차를 무시하여 경사거리 과소평가
3. **교전 시점 최적화 없음** — 사거리 진입 즉시 교전 → 원거리 저Pk 교전
4. **시나리오 2~4 미검증** — 시나리오 1, 5만 우선 실행

### 개선 계획
- v0.2에서 위협 비행 프로파일 + 3D 경사거리 + 최적 교전 시점 → **완료**
- v0.3에서 시나리오 확장 + 전자전 고도화 + 테스트 프레임워크

---

## [v0.0] — 2026-02-26

### 변경사항
- 초기 파일 업로드 (dev_blueprint.md, requirements.txt)
- 프로젝트 구조 및 개발 청사진 수립

### 발견된 문제
- 없음 (설계 단계)

### 개선 계획
- Phase 1~5 점진적 개발 착수 → v0.1에서 Phase 1~3 구현
