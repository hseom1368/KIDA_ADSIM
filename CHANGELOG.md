# CHANGELOG — KIDA_ADSIM 버전 이력

> 각 버전에 [변경사항], [발견된 문제], [개선 계획]을 통합 기록하여
> 새 세션에서 맥락을 빠르게 파악할 수 있도록 함.

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
