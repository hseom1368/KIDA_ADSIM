# 한국군 방공체계 M&S 개발 청사진
## Linear C2 vs Kill Web 비교 시뮬레이션

---

## 1. 프로젝트 구조 (Colab 노트북 4권 체계)

```
📁 K-ADS_Simulation/
├── 📓 Notebook 1: model_definition.ipynb     ← 모델 정의 (에이전트, 네트워크, 채널)
├── 📓 Notebook 2: scenario_config.ipynb      ← 시나리오 설정 & 실행
├── 📓 Notebook 3: batch_experiment.ipynb     ← Monte Carlo 실험 & DOE
├── 📓 Notebook 4: analysis_viz.ipynb         ← 결과 분석 & 시각화
├── 📁 modules/
│   ├── agents.py          # Mesa 에이전트 클래스
│   ├── network.py         # NetworkX 토폴로지 빌더
│   ├── comms.py           # SimPy 통신 채널 모델
│   ├── threats.py         # 위협 생성기
│   ├── metrics.py         # 성능 측정 수집기
│   └── config.py          # 파라미터 설정
└── 📁 results/            # 실험 결과 저장
```

---

## 2. 개발 단계 (5단계 점진적 통합)

### Phase 1: 기반 구축 (Notebook 1 전반부)
**목표**: Mesa 에이전트 + NetworkX 토폴로지만으로 정적 구조 검증

- [ ] Mesa Agent 클래스 정의 (SensorAgent, C2NodeAgent, ShooterAgent, ThreatAgent)
- [ ] 2D 공간(200×200km) 배치
- [ ] NetworkX 그래프 2종 구축 (선형 C2 / Kill Web)
- [ ] 탐지 확률 함수 구현: P(detect) = max(0, 1-(d/R_max)²) × (1-jam)
- [ ] 기본 시각화 (matplotlib 토폴로지 + 에이전트 위치)

**검증**: 토폴로지 시각화, 노드 연결성 확인, 탐지 범위 오버레이

### Phase 2: 킬체인 프로세스 (Notebook 1 후반부)
**목표**: SimPy 이산사건 시뮬레이션으로 시간 흐름 구현

- [ ] SimPy 환경 + Mesa 스케줄러 동기화
- [ ] 선형 킬체인 프로세스 (순차적 + 큐잉)
- [ ] Kill Web 프로세스 (병렬 + 자동화)
- [ ] C2 노드의 SimPy Resource (처리 용량 제한)
- [ ] 교전 판정 (Pk 기반 베르누이 시행)

**검증**: 단일 위협 추적 → 교전까지 타임라인 로그

### Phase 3: 시나리오 구성 (Notebook 2)
**목표**: 5개 시나리오 파라미터화 및 단일 실행 검증

- [ ] 시나리오 1: 포화공격 (20-40 위협, 2-3 파상)
- [ ] 시나리오 2: 복합위협 (SRBM+CM+UAS 혼합)
- [ ] 시나리오 3: 전자전 환경 (재밍 3단계)
- [ ] 시나리오 4: 순차교전 (포아송 도착)
- [ ] 시나리오 5: 노드 파괴 (C2 노드 제거)
- [ ] 위협 생성기 (유형별 파라미터, 도착 패턴)
- [ ] 통신 열화 모델 (재밍, 장비고장, 과부하)

**검증**: 각 시나리오별 단일 실행 → 이벤트 로그 & 타임라인

### Phase 4: 실험 설계 (Notebook 3)
**목표**: Mesa batch_run + Monte Carlo 반복실험

- [ ] Mesa batch_run 파라미터 스윕 설정
- [ ] 시나리오 × 아키텍처(2) × 반복(100-500회) 매트릭스
- [ ] 10개 성능 메트릭 자동 수집
- [ ] Google Drive 결과 저장 + 체크포인팅
- [ ] 진행률 표시 및 중간 저장

**검증**: 소규모 파일럿 (10회 반복) → 통계 분포 확인

### Phase 5: 분석 & 시각화 (Notebook 4)
**목표**: 통계 분석 + 비교 시각화

- [ ] Box plot: 선형 vs Kill Web 메트릭 비교
- [ ] CDF: 센서-투-슈터 시간 분포
- [ ] Heatmap: 시나리오 × 메트릭 성능 매트릭스
- [ ] 네트워크 다이어그램: 노드 제거 전/후 토폴로지
- [ ] 통계 검정 (t-test, ANOVA)
- [ ] 종합 결과 요약 대시보드

---

## 3. 에이전트 상세 설계

### 3.1 SensorAgent (탐지체)

```
속성:
  - sensor_type: str        # 'EWR', 'PATRIOT_RADAR', 'MSAM_MFR', 'SHORAD_RADAR'
  - detection_range: float  # km
  - tracking_capacity: int  # 동시 추적 수
  - scan_rate: float        # 초당 스캔
  - pos: (x, y)            # km 좌표
  - is_operational: bool    # 가동 상태
  - current_tracks: list    # 현재 추적 중인 위협

메서드:
  - detect(threat) → bool   # 탐지 확률 계산
  - track(threat) → dict    # 추적 정보 생성 (위치오차 포함)
  - report(c2_node) → msg   # C2 노드에 탐지보고 전송
```

| 센서 유형 | 탐지거리(km) | 추적용량 | 비고 |
|-----------|-------------|---------|------|
| EWR (그린파인급) | 500 | 100+ | 조기경보, 2기 |
| PATRIOT Radar (AN/MPQ-65) | 170(TBM)/100(항공기) | 100+ | PAT 포대 유기, 2기 |
| M-SAM MFR | 100 | 동시 다수 | 천궁 유기, 2기 |
| SHORAD Radar (TPS-830K) | 17 | 제한적 | 비호 유기, 2기 |

### 3.2 C2NodeAgent (지휘통제 노드)

```
속성:
  - node_type: str          # 'MCRC', 'BATTALION_TOC', 'EOC'
  - processing_capacity: int # 동시 처리 가능 위협 수
  - auth_delay_dist: tuple  # (min, max) 초 — 승인 지연 분포
  - is_operational: bool
  - pos: (x, y)
  - threat_queue: SimPy.Resource  # 처리 대기열
  - air_picture: dict       # 항적 종합 (인지 상태)

메서드:
  - receive_track(track_info)     # 탐지보고 수신
  - evaluate_threat(threat) → priority  # 위협 평가
  - authorize_engagement() → bool  # 교전 승인
  - assign_shooter(threat, shooter) # 사수 지정
  - update_air_picture()          # 항적 종합 갱신
```

| C2 노드 유형 | 처리용량 | 승인지연(선형) | 승인지연(Kill Web) |
|-------------|---------|-------------|-----------------|
| MCRC | 5 동시 | 15-120초 | 2-5초 |
| 대대 TOC | 3 동시 | 3-10초 | 1-3초 |
| EOC (Kill Web) | 5 동시 | N/A | 1-3초 |

### 3.3 ShooterAgent (사격체)

```
속성:
  - weapon_type: str         # 'PATRIOT_PAC3', 'CHEONGUNG2', 'BIHO', 'KF16'
  - max_range: float         # km
  - min_range: float         # km
  - max_altitude: float      # km
  - pk_table: dict           # {threat_type: Pk} 위협유형별 명중률
  - ammo_count: int          # 잔여 탄수
  - reload_time: float       # 재장전 시간(초)
  - engagement_time: float   # 교전 소요시간(초)
  - is_engaged: bool         # 현재 교전 중
  - pos: (x, y)

메서드:
  - can_engage(threat) → bool  # 교전 가능 여부 (사거리, 탄약, 상태)
  - engage(threat) → bool      # 교전 실행 (Pk 기반 판정)
  - compute_pk(threat) → float # 위협 유형별 Pk 계산
  - reload() → SimPy process   # 재장전 프로세스
```

| 사격체 | 사거리(km) | 고도(km) | Pk(TBM) | Pk(CM) | Pk(항공기) | Pk(UAS) | 탄수 | 재장전(초) |
|--------|----------|---------|---------|--------|----------|---------|------|----------|
| PATRIOT PAC-3 MSE | 120 | 30+ | 0.85 | 0.80 | 0.90 | 0.70 | 16 | 1800 |
| 천궁-II | 40 | 20 | 0.75 | 0.80 | 0.85 | 0.65 | 8 | 1200 |
| 비호 복합 | 7(미사일)/3(기관포) | 3 | N/A | 0.30 | 0.50 | 0.60 | 500+2 | 5(기관포) |
| KF-16 (CAP) | 100(AIM-120) | 15+ | N/A | 0.75 | 0.85 | 0.50 | 6 | N/A |

### 3.4 ThreatAgent (위협체)

```
속성:
  - threat_type: str     # 'SRBM', 'CRUISE_MISSILE', 'AIRCRAFT', 'UAS'
  - speed: float         # km/s
  - altitude: float      # km
  - rcs: float           # m² (레이더 반사 면적)
  - pos: (x, y)         # 현재 위치
  - target_pos: (x, y)  # 목표 위치
  - is_alive: bool
  - is_detected: bool
  - maneuvering: bool    # 기동 여부 (Pk 감소 요인)
  - launch_time: float   # 발사 시각

메서드:
  - move(dt)             # 시간 스텝별 이동
  - reached_target() → bool  # 방어구역 돌파 여부
```

| 위협 유형 | 속도(km/s) | 고도(km) | RCS(m²) | 기동 | 비행시간(200km) |
|----------|----------|---------|---------|------|--------------|
| SRBM (KN-23형) | 2.0-2.7 (M6-8) | 37-60(정점) | 0.1-1.0 | 종말기동 | ~90초 |
| 순항미사일 (금성-3형) | 0.27 (M0.8) | 0.015-0.05 | 0.01-0.1 | 해면밀착 | ~740초 |
| 고정익 항공기 | 0.27-0.41 | 5-15 | 1-10 | 제한적 | ~500-740초 |
| UAS 군집 | 0.03-0.06 | 0.05-0.5 | 0.001-0.01 | 무 | ~3300-6600초 |

---

## 4. 네트워크 토폴로지 상세 설계

### 4.1 선형 C2 토폴로지 (기존 체계)
```
[EWR_1] ──→ [MCRC] ──→ [TOC_PAT] ──→ [PAT_1]
[EWR_2] ──→ [MCRC]     [TOC_PAT] ──→ [PAT_2]
                        
[PAT_RADAR_1] → [TOC_PAT]   (유기 레이더 → 전용 TOC)
[PAT_RADAR_2] → [TOC_PAT]

[MSAM_MFR_1] → [TOC_MSAM] → [MSAM_1]
[MSAM_MFR_2] → [TOC_MSAM] → [MSAM_2]

[SHORAD_RADAR_1] → [TOC_SHORAD] → [BIHO_1]
[SHORAD_RADAR_2] → [TOC_SHORAD] → [BIHO_2]

특성:
  - MCRC가 단일 허브 (SPOF)
  - 센서-사수 쌍이 고정 (교차운용 불가)
  - 육군/공군 계통 분리
  - 에지 속성: latency=30-120초 (음성/수동 중계)
```

### 4.2 Kill Web 토폴로지 (통합 체계)
```
[모든 센서] ←──→ [모든 C2 노드] ←──→ [모든 사격체]
  EWR_1  ←→  MCRC      ←→  PAT_1
  EWR_2  ←→  EOC_1     ←→  PAT_2
  PAT_R1 ←→  EOC_2     ←→  MSAM_1
  PAT_R2 ←→  EOC_3     ←→  MSAM_2
  MFR_1  ←→            ←→  BIHO_1
  MFR_2  ←→            ←→  BIHO_2
  SH_R1  ←→            ←→  KF16_1
  SH_R2

특성:
  - 완전 메시 연결 (모든 센서 → 모든 C2 → 모든 사수)
  - 자동 페일오버 (노드 손실 시 대체 경로)
  - 공유 COP (모든 C2 노드 동일 항적 보유)
  - 에지 속성: latency=1-3초 (IFCN급 자동 데이터링크)
```

### 4.3 통신 링크 파라미터

| 파라미터 | 선형 C2 | Kill Web |
|---------|---------|----------|
| 센서→C2 지연 | 5-15초 | 1-2초 |
| C2 내부 처리 | 10-30초 | 1-3초 |
| C2→사수 지연 | 5-15초 | 1-2초 |
| 승인 지연 | 15-120초 | 자동화(0-5초) |
| 대역폭(kbps) | 16-75 | 500-2000 |
| 재밍 내성 | 낮음(60-85%) | 높음(85-95%) |
| 단일장애점 | MCRC 손실 → 전역 마비 | 개별 노드 손실 → 부분 열화 |

---

## 5. 킬체인 프로세스 상세 설계

### 5.1 선형 킬체인 (SimPy 프로세스)

```
[탐지] → [보고 전달] → [MCRC 큐 대기] → [위협평가] → [교전승인] → [사수지정] → [교전]
  5-15s    10-30s       가변(큐잉)       10-30s       15-60s       5-15s      3-10s

총 소요시간: 48-160초+ (큐잉 지연 추가)
MCRC 큐: SimPy.Resource(capacity=5)
→ 포화공격 시 큐 대기시간 급증 (핵심 병목)
```

### 5.2 Kill Web 프로세스 (SimPy 프로세스)

```
[탐지] → [자동 COP 융합] → [최적 사수 선정] → [교전]
  2-5s      1-3s              1-5s              3-10s

총 소요시간: 7-23초
EOC 큐: SimPy.Resource(capacity=5) × 4개 노드
→ 부하 분산으로 큐잉 최소화
→ 최적사수 선정: Score = Pk × in_envelope × (1/load) × (1/distance)
```

### 5.3 교전 판정 로직

```python
def engage(shooter, threat):
    base_pk = shooter.pk_table[threat.threat_type]
    
    # 보정 요인
    range_factor = max(0, 1 - (distance/max_range)**2)
    maneuver_penalty = 0.85 if threat.maneuvering else 1.0
    jamming_penalty = 1 - (jamming_level * 0.3)
    
    final_pk = base_pk * range_factor * maneuver_penalty * jamming_penalty
    
    # 베르누이 시행
    hit = random.random() < final_pk
    shooter.ammo_count -= 1
    return hit
```

---

## 6. 시나리오 파라미터 상세

### 시나리오 1: 포화공격
```yaml
threats:
  wave_1 (t=0): 10 SRBM + 5 CM (동시)
  wave_2 (t=60s): 5 SRBM + 10 UAS
  wave_3 (t=120s): 5 CM + 10 UAS
total: 45 위협
approach: 북쪽 120도 부채꼴, 200km 외곽에서 진입
```

### 시나리오 2: 복합위협
```yaml
threats:
  SRBM: 10기, Mach 6-8, 고도 37-60km
  CM: 5기, Mach 0.8, 고도 15-50m
  Aircraft: 3기, Mach 0.8-1.2, 고도 5-15km
  UAS: 20기 군집, 100-200km/h, 고도 50-500m
approach: 다축선 동시 (북, 동북, 서북)
```

### 시나리오 3: 전자전 환경
```yaml
jamming_levels:
  light: detection_prob × 0.8, latency × 1.5
  moderate: detection_prob × 0.5, latency × 3.0
  heavy: detection_prob × 0.2, latency × 5.0
threats: 시나리오 2와 동일
```

### 시나리오 4: 순차교전 (지속작전)
```yaml
arrival: Poisson(λ=1/60), 60분간
total: ~60 위협 (확률적)
mix: SRBM 30%, CM 25%, Aircraft 15%, UAS 30%
```

### 시나리오 5: 노드 파괴
```yaml
base: 시나리오 1 (포화공격)
degradation:
  t=30s: MCRC 파괴 (선형) / EOC_1 파괴 (Kill Web)
  t=60s: TOC_PAT 파괴 (선형) / EOC_2 파괴 (Kill Web)
  t=90s: TOC_MSAM 파괴 (선형) / EOC_3 파괴 (Kill Web)
```

---

## 7. 10대 성능 메트릭 정의

| # | 메트릭 | 단위 | 수집 방법 | 핵심 비교 포인트 |
|---|--------|------|----------|----------------|
| 1 | 센서-투-슈터 시간 | 초 | SimPy 이벤트 타임스탬프 차이 | Kill Web의 핵심 우위 |
| 2 | 누출률 (Leaker Rate) | % | 방어구역 돌파 위협/전체 위협 | 작전적 최종 성과 |
| 3 | 교전 성공률 | % | 격추 수/교전 수 | C2 최적화 품질 |
| 4 | 표적 할당 효율 | % | 최적 Pk 사수 배정 비율 | 사수 선정 알고리즘 효과 |
| 5 | 동시 교전 능력 | 건/스텝 | 시간스텝당 최대 동시 교전 수 | 포화공격 대응 능력 |
| 6 | 탄약 효율 | 발/격추 | 소모 요격탄/확인 격추 | 경제성 |
| 7 | 체계 회복탄력성 | % | 노드 제거 후 잔존 성능 비율 | 가장 극적인 차이 예상 |
| 8 | C2 의사결정 처리량 | 건/분 | C2 노드 처리 완료 위협 수/시간 | 선형 병목 가시화 |
| 9 | 방어 커버리지 | km² | 교전 가능 포락선 합집합 면적 | 센서 공유 효과 |
| 10 | 노드 손실 후 복구시간 | 초 | C2 손실→교전 재개까지 시간 | 자가치유 네트워크 |

---

## 8. 기술 의존성 & 환경 설정

### Colab 설치 셀
```python
!pip install simpy mesa networkx matplotlib pandas numpy scipy plotly seaborn --quiet
```

### 라이브러리 역할 매핑
| 라이브러리 | 버전 | 역할 |
|-----------|------|------|
| mesa | ≥3.0 | ABM 프레임워크 (에이전트, 스케줄러, batch_run) |
| simpy | ≥4.1 | DES 엔진 (킬체인 프로세스, 큐잉) |
| networkx | ≥3.0 | 토폴로지 그래프 (선형/메시 C2 네트워크) |
| numpy | ≥1.24 | 난수 생성, 수학 연산 |
| pandas | ≥2.0 | 데이터 수집, 결과 분석 |
| scipy | ≥1.10 | 통계 검정 (t-test, ANOVA) |
| matplotlib | ≥3.7 | 기본 시각화 |
| seaborn | ≥0.12 | 통계 시각화 (boxplot, heatmap) |
| plotly | ≥5.0 | 인터랙티브 대시보드 (선택) |

### Colab 제약 대응
- RAM: ~12.7GB → 에이전트 500개 이내 (충분)
- 세션: 12시간 → batch_run 체크포인팅 필수
- 저장: Google Drive 마운트 → 결과 자동 저장

---

## 9. 검증 & 확인 (V&V) 계획

### 검증 (Verification) — "모델을 올바르게 만들었는가?"
| 단계 | 검증 방법 | 기준 |
|------|----------|------|
| Phase 1 | 토폴로지 시각화 + 연결성 확인 | nx.is_connected(), 경로 존재 |
| Phase 2 | 단일 위협 이벤트 로그 | 킬체인 각 단계 시간 범위 내 |
| Phase 3 | 경계값 테스트 | 탄약 0 → 교전 불가, 범위 밖 → 교전 불가 |
| Phase 4 | 수렴성 검사 | 반복 횟수 증가 시 평균 안정화 |

### 확인 (Validation) — "올바른 모델을 만들었는가?"
| 방법 | 내용 |
|------|------|
| Face Validation | 킬체인 시간 범위가 문헌값과 일치 (선형 48-160초, KW 7-23초) |
| 민감도 분석 | Pk, 지연시간, 재밍율 변화 → 출력 반응 방향 합리성 |
| 극단값 테스트 | 위협 0기 → 교전 0, 재밍 100% → 탐지 0 |
| 벤치마크 | IBCS 시험결과(20초 센서-투-슈터)와 KW 모델 비교 |

---

## 10. 핵심 설계 결정 사항 (사용자 확인 필요)

아래 항목들은 코드 작업 시작 전 결정이 필요합니다:

### Q1. 시뮬레이션 시간 해상도
- 1초 단위 (높은 정밀도, 느린 실행)
- 5초 단위 (적정 정밀도, 빠른 실행) ← 권장
- 10초 단위 (낮은 정밀도, 매우 빠른 실행)

### Q2. 에이전트 규모
- 소규모: 센서 4, C2 3, 사수 6, 위협 10-20 ← 권장(프로토타입)
- 중규모: 센서 8, C2 6, 사수 12, 위협 20-40
- 대규모: 센서 12, C2 8, 사수 18, 위협 40-60

### Q3. Monte Carlo 반복 횟수
- 100회 (빠른 파일럿)
- 300회 (적정 통계) ← 권장
- 500회+ (높은 신뢰도, 실행 시간 길어짐)

### Q4. 코드 구조
- 단일 노트북 (모든 코드 1개 파일, Colab 편의성 높음)
- 4노트북 분리 (위 구조대로, 모듈화) ← 권장
- 하이브리드 (핵심 클래스는 .py 모듈, 실행은 노트북)

### Q5. 시각화 수준
- 기본 (matplotlib 정적 차트만)
- 중급 (matplotlib + seaborn + 네트워크 다이어그램) ← 권장
- 고급 (plotly 인터랙티브 대시보드 포함)

### Q6. Kill Web 사수 선정 알고리즘
- 단순 (최고 Pk 사수 우선)
- 가중합 (Pk × 거리 × 부하 × 탄약 잔량) ← 권장
- 최적화 (헝가리안 알고리즘으로 전역 최적 할당)

### Q7. 개발 우선순위
- 전체 5개 시나리오 완성 후 분석
- 시나리오 1(포화공격) + 5(노드파괴)만 먼저 구현 → 확장 ← 권장
- 모든 시나리오 동시 병렬 개발
