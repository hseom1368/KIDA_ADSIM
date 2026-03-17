# 개발 계획 — 검증 보고서 기반 로드맵

> 갱신일: 2026-03-17
> 기반: v0.6b (136개 테스트 PASS, Monte Carlo + 통계 분석 완료)
> 참조: `KIDA_ADSIM_Unified_Validation_v2.docx` (15개 검증 영역, 13개 우선순위)

---

## 검증 보고서 13개 항목 × 버전 매핑

| # | 영역 | 영향도 | 버전 | 상태 |
|---|------|--------|------|------|
| 1 | 표적 분류 (KN-25 오분류) | CRITICAL | v0.7 | 미착수 |
| 2 | 레이더 방위각 제약 | CRITICAL | v0.7 | 미착수 |
| 3 | KF-16 동적 CAP 궤도 | CRITICAL | v0.7 | 미착수 |
| 4 | 시뮬레이션 영역 확대 | CRITICAL | v0.7 | 미착수 |
| 5 | 무기체계 파라미터 교정 | HIGH | **v0.6a** | ✅ 완료 |
| 6 | MCRC 재배치 | HIGH | **v0.6a** | ✅ 완료 |
| 7 | 위협 파상 순서 변경 | HIGH | **v0.6a** | ✅ 완료 |
| 8 | 레이더 수평선 | HIGH | v0.7 | 미착수 |
| 9 | 시간 해상도 이중화 | HIGH | v0.7 | 미착수 |
| 10 | 교전 교리 확장 | HIGH | v0.7 | 미착수 |
| 11 | BMD 사전 위임 | HIGH | v0.7 | 미착수 |
| 12 | AEW&C (E-737) | MEDIUM | v0.8+ | 미착수 |
| 13 | SBIRS 조기경보 | MEDIUM | v0.8+ | 미착수 |

---

## 완료된 버전 요약

### v0.6a: 파라미터 교정 ✅ (2026-03-17, 116개 테스트)
- PAC-3 MSE 교정, 천궁-II 교정, BIHO gun/missile 분리
- MCRC 재배치, 시나리오 1 파상 순서 변경

### v0.6b: Monte Carlo + 통계 분석 ✅ (2026-03-17, 136개 테스트)
- `batch.py`: BatchRunner (multiprocessing 병렬화, 체크포인팅, 수렴 검사)
- `stats.py`: 정규성 검정, t-test/Mann-Whitney, Cohen's d, Bonferroni
- notebook3/4 업데이트, 레이더 차트, 포레스트 플롯
- 14개 GIF 전술 애니메이션 + 21개 비교 스냅샷 (`output/gif/`)

### v0.5 이전 완료 기록
- v0.5: COP 차별화, 적응형 교전, 통신 열화, 2D 시각화, 86개 테스트
- v0.4: 다중 교전 모델링, 메트릭 12개, 57개 테스트
- v0.3: 시나리오 2~4 검증, EW 3단계, 45개 테스트
- v0.2: 비행 프로파일 현실화, 3D 경사거리, 최적 교전 시점
- v0.1: 핵심 시뮬레이션 엔진, 10개 지표

---

## v0.7: 구조적 개선 (다음 작업)

> 검증 보고서 #1-4, #8-11 반영
> 목표 테스트: ~160개 (신규 ~24개)
> 예상 수정 파일: config.py, agents.py, model.py, threats.py, network.py

### 구현 항목 총괄표

| # | 기능 | 주요 파일 | 영향도 | 의존성 |
|---|------|-----------|--------|--------|
| 1 | 표적 분류 + KN-25 오분류 모델 | agents.py, config.py, model.py | CRITICAL | #4 |
| 2 | 레이더 방위각 제약 | config.py, agents.py | CRITICAL | #4 |
| 3 | KF-16 동적 CAP 궤도 모델 | agents.py, config.py | CRITICAL | #4 |
| 4 | 시뮬레이션 영역 확대 200×200→800×600km | config.py, model.py, viz.py | CRITICAL | 없음 (선행) |
| 5 | 레이더 수평선 (4/3 지구 모델) | agents.py | HIGH | #4 |
| 6 | 이중 시간 스텝 (5s 일반 + 0.5s BMD) | model.py, config.py | HIGH | 없음 |
| 7 | 교전 교리 확장 (2발 salvo, S-L-S, 재장전) | model.py, config.py | HIGH | 없음 |
| 8 | BMD 사전 위임 (선형 C2 SRBM 직접 교전) | model.py | HIGH | #6 |
| 9 | THAAD 체계 추가 | agents.py, config.py, network.py | HIGH | #4 |
| 10 | 시나리오 5b (동시 다중 노드 파괴) | config.py, threats.py | MEDIUM | 없음 |

### 권장 구현 순서

**Phase A: 기반 인프라 (선행 필수)**
1. `#4` 시뮬레이션 영역 확대 — 모든 좌표·배치·거리 계산의 기반
2. `#6` 이중 시간 스텝 — BMD 정밀 시뮬레이션의 전제

**Phase B: 센서/탐지 현실화**
3. `#5` 레이더 수평선 — 4/3 지구 모델, 센서 탐지 제약
4. `#2` 레이더 방위각 제약 — MPQ-65: 90°, Green Pine: 120°
5. `#1` 표적 분류 + 오분류 — RCS 기반 분류 + KN-25 오분류 모델

**Phase C: 교전 로직 고도화**
6. `#7` 교전 교리 확장 — 2발 salvo, S-L-S, 재장전 모델
7. `#8` BMD 사전 위임 — 선형 C2 SRBM 직접 교전 허용

**Phase D: 체계/시나리오 확장**
8. `#3` KF-16 동적 CAP 궤도
9. `#9` THAAD 체계 추가
10. `#10` 시나리오 5b

---

### 항목별 상세 구현 계획

#### #4. 시뮬레이션 영역 확대 (Phase A-1)

**현황**: 200×200km → **목표**: 800×600km (동서 800km, 남북 600km)

**수정 사항**:
- `config.py`:
  - `SIMULATION_AREA = {'width': 800, 'height': 600}` 추가
  - 모든 센서/C2/사수 좌표를 새 영역에 맞게 재배치
  - 위협 진입 좌표를 북쪽 경계(y=600) 부근으로 조정
- `model.py`: 방어 영역 경계 판단 로직 수정 (`target_arrival_distance` 기준점 갱신)
- `viz.py`: 플롯 범위, 축 레이블, 범례 위치 갱신
- `threats.py`: 위협 생성 좌표 범위 갱신

**테스트**: 2개 신규 (영역 크기 검증, 좌표 범위 검증)

#### #6. 이중 시간 스텝 (Phase A-2)

**현황**: 균일 5s → **목표**: 5s 일반 + 0.5s BMD

**수정 사항**:
- `config.py`: `TIME_STEP = {'normal': 5, 'bmd': 0.5}`, BMD 활성화 조건 정의
- `model.py`:
  - `step()` 메서드에 동적 시간 스텝 분기 추가
  - SRBM 활성 시 0.5s 스텝으로 전환, 종료 시 5s 복귀
  - SimPy 환경 시간과 Mesa 스텝 간 동기화 로직

**테스트**: 2개 신규 (BMD 모드 전환 검증, 시간 동기화 검증)

#### #5. 레이더 수평선 (Phase B-1)

**현황**: 무제한 탐지 거리 → **목표**: 4/3 지구 모델

**수정 사항**:
- `agents.py`:
  - `_radar_horizon(sensor_height, target_altitude)` 유틸리티 함수 추가
  - 공식: `d = 4.12 * (√h_sensor + √h_target)` km (4/3 지구 근사)
  - `SensorAgent.detect()`: 수평선 초과 시 탐지 불가
- `config.py`: 센서별 안테나 높이(m) 파라미터 추가

**테스트**: 2개 신규 (수평선 거리 계산, 저고도 위협 탐지 차단)

#### #2. 레이더 방위각 제약 (Phase B-2)

**현황**: 360° 전방위 탐지 → **목표**: 레이더별 방위각 제한

**수정 사항**:
- `config.py`: 센서별 `azimuth_coverage` 파라미터 추가
  - MPQ-65 (PAC-3 FCS): 90° (±45°)
  - Green Pine (천궁-II): 120° (±60°)
  - EWR: 360° (회전식)
  - SHORAD: 360°
- `config.py`: 센서별 `boresight_azimuth` (정면 방향각) 파라미터 추가
- `agents.py`: `SensorAgent.detect()` — 위협 방위각이 커버리지 밖이면 탐지 불가

**테스트**: 2개 신규 (방위각 내/외 탐지 검증)

#### #1. 표적 분류 + KN-25 오분류 모델 (Phase B-3)

**현황**: 위협 유형 즉시 인지 → **목표**: RCS 기반 분류 + 오분류 확률

**수정 사항**:
- `config.py`:
  - `CLASSIFICATION_CONFIG`: 위협 유형별 분류 정확도, 혼동 행렬
  - KN-25 (RCS≈0.1m²): SRBM↔대형 UAS 오분류율 ~15%
  - KN-09 (MRL, RCS≈0.3m²): SRBM↔CM 오분류율 ~10%
- `agents.py`:
  - `C2NodeAgent.classify_threat()`: RCS + 속도 기반 분류 + 혼동 행렬 적용
  - 오분류 시 부적절한 사수 할당 (UAS 분류 → SHORAD 할당)
- `model.py`: 킬체인에서 분류 결과 기반 사수 선택 로직 적용

**테스트**: 3개 신규 (정상 분류, 오분류 발생, 오분류→사수 불일치)

#### #7. 교전 교리 확장 (Phase C-1)

**현황**: 단발 교전 → **목표**: 2발 salvo, S-L-S, 재장전

**수정 사항**:
- `config.py`:
  - `DOCTRINE_CONFIG`: 위협별 교전 교리 (Salvo 크기, S-L-S 여부)
  - SRBM: 2발 salvo (동시 발사)
  - CM: Shoot-Look-Shoot (발사 → 결과 관측 → 재발사)
  - 사수별 `reload_time` 파라미터 추가
- `model.py`:
  - `_execute_salvo()`: 동시 2발 발사, 독립 Bernoulli
  - `_execute_sls()`: 1발 발사 → 결과 대기 → 미격추 시 재발사
  - 탄약 소진 시 재장전 프로세스 (SimPy yield)

**테스트**: 3개 신규 (salvo, S-L-S, 재장전 타이밍)

#### #8. BMD 사전 위임 (Phase C-2)

**현황**: 선형 C2 모든 위협 동일 승인 지연 → **목표**: SRBM 직접 교전 허용

**수정 사항**:
- `config.py`: `BMD_PRE_DELEGATION = True`, `bmd_auth_delay = 20` (vs 기존 120s)
- `model.py`: 선형 C2 킬체인에서 SRBM 탐지 시 MCRC 승인 생략, TOC→사수 직접 교전

**테스트**: 2개 신규 (위임 교전 지연 검증, 비-BMD 위협 기존 경로 유지)

#### #3. KF-16 동적 CAP 궤도 (Phase D-1)

**현황**: KF-16 고정 위치 → **목표**: 순회 궤도 모델

**수정 사항**:
- `config.py`: KF-16 `cap_orbit` 파라미터 (중심점, 반경, 고도, 속도)
- `agents.py`:
  - `ShooterAgent` KF-16 전용 `move()` 메서드 — 매 스텝 궤도 위치 갱신
  - 원형/레이스트랙 궤도 모델
  - 교전 시 궤도 이탈 → 인터셉트 → 궤도 복귀

**테스트**: 2개 신규 (궤도 이동 검증, 교전 후 복귀)

#### #9. THAAD 체계 추가 (Phase D-2)

**현황**: PAC-3/천궁/비호/KF-16만 → **목표**: THAAD 추가

**수정 사항**:
- `config.py`:
  - THAAD 센서: AN/TPY-2 (탐지거리 1000km, 추적 600km, BMD 전용)
  - THAAD 사수: 요격탄 48발, 사거리 200km, 최대 고도 150km, Pk 0.87
  - THAAD 배치 위치 추가
- `agents.py`: THAAD 에이전트 (기존 Sensor/Shooter 재활용, 파라미터 차별화)
- `network.py`: THAAD 노드를 토폴로지에 추가

**테스트**: 2개 신규 (THAAD 탐지/교전, 토폴로지 통합)

#### #10. 시나리오 5b: 동시 다중 노드 파괴 (Phase D-3)

**현황**: S5 순차 노드 파괴 → **목표**: 동시 다중 노드 파괴

**수정 사항**:
- `config.py`: `scenario_5b_multi_node_destruction` 시나리오 추가
  - 2~3개 노드 동시 파괴 (MCRC + PAC-3 또는 MCRC + 천궁)
- `threats.py`: 동시 파괴 이벤트 생성 로직
- `EXPERIMENT_CONFIG`에 시나리오 5b 추가

**테스트**: 2개 신규 (다중 노드 동시 파괴, 회복탄력성 검증)

---

## v0.7 완료 후 예상 성과

- **센서 현실성**: 방위각 + 수평선으로 탐지 영역 현실화
- **교전 현실성**: salvo + S-L-S + 재장전 + BMD 위임
- **표적 분류**: 오분류에 의한 교전 실패 모델링
- **영역 확대**: 한반도 규모 방공전장 반영
- **BMD 정밀도**: 0.5s 시간 스텝으로 고속 표적 교전 정밀 모델링
- **THAAD**: 상층 방어 체계 추가로 다층 방어 완성도 향상

---

## v0.8+: 확장 체계

| 항목 | 내용 |
|------|------|
| E-737 AEW&C (Peace Eye) | MESA 레이더 600+km, 360°, Link 16 융합 |
| Navy Aegis (KDX-III) | SPY-1D + SM-2/SM-3, 동해 초계 |
| SBIRS | 우주 기반 IR 조기경보, 2-4분 BM 발사 경보 |
| L-SAM | 150km 사거리, 50-60km 고도, 2027-28 배치 |
| 요격탄 비용 모델 | 비용-교환비 분석 (요격탄 vs 위협 가치) |
| 한반도 지형 차폐 | DEM 기반 산악 지형 레이더 차폐 효과 |
