# 개발 계획 — 검증 보고서 기반 로드맵

> 작성일: 2026-03-17
> 기반: v0.6a (116개 테스트 PASS, 파라미터 교정 완료)
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

## v0.6a: 파라미터 교정 ✅ 완료

> 완료일: 2026-03-17
> 테스트: 116개 PASS (11개 파일)

### 완료된 작업
1. PAC-3 MSE 파라미터 교정 ✅ — max_range 120→60km, max_altitude 30→40km, ammo 16→12, engagement_time 5→9s
2. 천궁-II max_range 40→45km ✅
3. BIHO gun/missile 분리 ✅ — gun 3km/600발, missile 7km/2발, 이중 모드 교전 로직
4. MCRC 재배치 ✅ — (100,140)→(100,50) 사수 후방
5. 시나리오 1 파상 순서 변경 ✅ — UAS→CM→SRBM (러-우 교리 반영)
6. 테스트 확장 ✅ — 86개 → 116개 (신규 30개: param_corrections 15개, biho_split 15개)

### 성능 기준선 (v0.6a, seed=42)

| 시나리오 | 아키텍처 | 누출률 | S2S | 성공률 | 다중교전 |
|----------|----------|--------|-----|--------|----------|
| S1 포화공격 | Linear | 37.8% | 351.8s | 33.3% | 3.7% |
| S1 포화공격 | **KillWeb** | **35.6%** | **5.0s** | 29.4% | 5.9% |
| S2 복합위협 | Linear | 26.3% | 317.2s | 47.4% | 15.8% |
| S2 복합위협 | **KillWeb** | **13.2%** | **5.0s** | 43.3% | 6.7% |
| S3 EW Light | Linear | 26.3% | 345.1s | 37.5% | 8.3% |
| S3 EW Light | **KillWeb** | **18.4%** | **7.3s** | 37.9% | 3.4% |
| S3 EW Moderate | Linear | 36.8% | 517.8s | 29.4% | 5.9% |
| S3 EW Moderate | **KillWeb** | **21.1%** | **15.2s** | 36.7% | 3.3% |
| S3 EW Heavy | Linear | 39.5% | 573.3s | 33.3% | 16.7% |
| S3 EW Heavy | **KillWeb** | **26.3%** | **24.5s** | 50.0% | 5.6% |
| S4 순차교전 | Linear | 52.2% | 146.5s | 20.8% | 2.1% |
| S4 순차교전 | **KillWeb** | **38.8%** | **5.0s** | 39.6% | 10.4% |
| S5 노드파괴 | Linear | 26.7% | 105.9s | 45.5% | 3.0% |
| S5 노드파괴 | **KillWeb** | 26.7% | **5.0s** | 34.1% | 9.1% |

---

## v0.6b: Monte Carlo 통계 분석 ✅ 완료

> 완료일: 2026-03-17
> 테스트: 136개 PASS (13개 파일)

### 완료된 작업
1. `modules/batch.py` 신규 ✅ — BatchRunner (multiprocessing 병렬화, 체크포인팅, 수렴 검사)
2. `modules/stats.py` 신규 ✅ — 정규성 검정, t-test/Mann-Whitney, Cohen's d, Bonferroni, full_comparison
3. notebook3 업데이트 ✅ — BatchRunner 연동, 파일럿→본실험→수렴 검사 파이프라인
4. notebook4 업데이트 ✅ — stats.py 연동, 레이더 차트, 포레스트 플롯 추가
5. 테스트 확장 ✅ — test_batch.py (6개), test_stats.py (14개) = 신규 20개
6. 문서 업데이트 ✅ — CHANGELOG v0.6b, CLAUDE.md, plan.md 갱신

---

## v0.7: 구조적 개선 (검증 보고서 #1-4, #8-11)

| # | 기능 | 주요 파일 | 영향도 |
|---|------|-----------|--------|
| 1 | 표적 분류 + KN-25/KN-09 오분류 모델 | agents.py, config.py, model.py | CRITICAL |
| 2 | 레이더 방위각 제약 (MPQ-65: 90°, GP: 120°) | config.py, agents.py | CRITICAL |
| 3 | KF-16 동적 CAP 궤도 모델 | agents.py, config.py | CRITICAL |
| 4 | 시뮬레이션 영역 확대 200×200→800×600km | config.py, model.py | CRITICAL |
| 5 | 레이더 수평선 4/3 지구 모델 | agents.py | HIGH |
| 6 | 이중 시간 스텝 (5s 일반 + 0.5s BMD) | model.py, config.py | HIGH |
| 7 | 교전 교리 확장 (2발 salvo, S-L-S, 재장전) | model.py, config.py | HIGH |
| 8 | BMD 사전 위임 (선형 C2, auth 120s→20s) | model.py | HIGH |
| 9 | THAAD 체계 추가 (AN/TPY-2 + 요격탄) | agents.py, config.py | HIGH |
| 10 | 시나리오 5b 동시 다중 노드 파괴 | config.py, threats.py | MEDIUM |

**목표 테스트**: ~140개 (신규 ~14개: azimuth, classification, KF-16, horizon, doctrine, pre-deleg.)

---

## v0.8+: 확장 체계

- E-737 AEW&C (Peace Eye): MESA 레이더, 600+km, 360°, Link 16 융합
- Navy Aegis (KDX-III): SPY-1D + SM-2/SM-3, 동해 초계
- SBIRS: 우주 기반 IR 조기경보, 2-4분 BM 발사 경보
- L-SAM: 150km 사거리, 50-60km 고도, 2027-28 배치
- 요격탄 비용 모델 (비용-교환비 분석)
- 한반도 지형 차폐 효과

---

## v0.5 완료 기록

> 작업 완료일: 2026-03-12
> 테스트: 86개 전부 PASS (9개 파일)

### 완료된 작업 (v0.5)
1. COP 품질 차별화 ✅ — 센서 융합 √N 오차, 아군 상태 공유, 교전 계획 공유
2. 적응형 교전 정책 ✅ — 탄약 30%/10% 임계치 기반 자동 전환
3. 통신 네트워크 동적 열화 ✅ — 링크별 차등 재밍, 메시 다중경로 완화
4. 2D 전술 시각화 모듈 ✅ — TacticalVisualizer (렌더/애니메이션/비교/타임라인)
5. 시각화 노트북 ✅ — notebook5 (전술 애니메이션 + 아키텍처 비교)
6. 테스트 확장 ✅ — 57개 → 86개 (COP 11개, 적응형 13개, 시각화 5개)
7. 문서 업데이트 ✅ — CHANGELOG, CLAUDE.md, README 갱신

---

## v0.4 완료 기록

> 작업 완료일: 2026-03-11
> 테스트: 57개 전부 PASS

### 완료된 작업 (v0.4)
1. jamming_level 오버라이드 정리 ✅
2. comms.py 죽은 코드 삭제 ✅
3. config.py 죽은 설정 삭제 ✅
4. 다중 교전 모델링 ✅ (SRBM=3, CM=2)
5. 메트릭 확장 12개 ✅
6. 테스트 확장 57개 ✅
7. 노트북 업데이트 ✅
