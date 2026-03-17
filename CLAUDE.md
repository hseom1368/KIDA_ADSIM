# KIDA_ADSIM — Claude Code 프로젝트 컨텍스트

## 프로젝트 개요
한국군 방공체계 C2 아키텍처(선형 C2 vs Kill Web) 비교 M&S.
Mesa(ABM) + SimPy(DES) + NetworkX 기반 에이전트 시뮬레이션.

## 디렉터리 구조
```
modules/
  config.py    — 모든 파라미터 (센서, C2, 사수, 위협, 시나리오, 통신, 교전정책, COP, 적응형교전, 통신열화)
  agents.py    — Mesa 에이전트 4종 (Sensor, C2Node, Shooter, Threat) + _slant_range() + BIHO 이중모드
  model.py     — 통합 시뮬레이션 엔진 (AirDefenseModel) + COP 차별화 + 적응형 교전 + 스냅샷
  network.py   — NetworkX 토폴로지 빌더 (선형/킬웹)
  comms.py     — SimPy 통신 채널 + 킬체인 프로세스 + 링크별 동적 열화
  metrics.py   — 12개 성능 지표 수집기
  threats.py   — 위협 생성기 (5개 시나리오)
  viz.py       — 2D 전술 시각화 (matplotlib.animation 기반)
  batch.py     — Monte Carlo 배치 실행기 (multiprocessing 병렬화, 체크포인팅)
  stats.py     — 통계 분석 모듈 (정규성 검정, t-test/Mann-Whitney, Cohen's d, Bonferroni)
tests/         — pytest 단위/통합 테스트 (15개 파일, 136개)
notebook1~5    — Jupyter 노트북 (모델정의, 시나리오, 배치실험, 분석, 전술시각화)
output/gif/    — 전술 시각화 GIF 애니메이션 + 비교 스냅샷 (14 GIF + 21 PNG)
results/       — Monte Carlo 실험 결과 CSV + 분석 차트 (gitignore)
```

## 기술 스택
- Python 3.10+, SimPy 4.1, Mesa 3.0, NetworkX 3.0
- numpy, pandas, scipy, matplotlib, seaborn

## 코딩 규칙
- 주석·변수명: 한국어 주석 허용, 변수·함수명은 영문 snake_case
- config.py에 모든 상수 집중 관리 — 매직 넘버 금지
- 에이전트 간 통신은 반드시 SimPy yield를 통한 지연 모델링
- 거리 계산: 고도 반영 시 `_slant_range()` 사용 (구현 완료)
- 교전 시점 판단: `_should_engage_now()` → ENGAGEMENT_POLICY 참조
- 테스트: 변경 후 반드시 `python -m pytest tests/` 및 시나리오 1 스모크 테스트 실행

## 핵심 아키텍처 비교 (v0.6a 기준, 시나리오 1 seed=42)
| 항목 | 선형 C2 | Kill Web |
|------|---------|----------|
| S2S 시간 | ~352s | ~5s (70배 빠름) |
| 누출률 | 37.8% | **35.6%** |
| 교전 성공률 | 33.3% | 29.4% |
| 다중교전율 | 3.7% | **5.9%** |
| 토폴로지 | 계층 체인 (MCRC SPOF) | 완전 메시 (분산) |
| COP 품질 | 위협 항적만 | **위협 + 아군 상태 + 교전 계획** |
| 센서 융합 | 단일 센서 (σ=0.5km) | **√N 오차 감소 (min 0.1km)** |
| 사수 선택 | 유형 우선 고정 | **COP 기반 최적 점수 (아군 상태 반영)** |
| 교전 정책 | 고정 다중 교전 | **적응형 (탄약 기반 자동 전환)** |
| 통신 열화 | 전역 균일 | **링크별 차등 + 메시 다중경로 완화** |

> 참고: v0.6a에서 PAC-3 사거리 120→60km, 시나리오 1 파상 순서 변경(UAS 선행)으로 v0.5 대비 누출률 증가. S2 복합위협에서는 KillWeb 13.2% vs Linear 26.3%로 여전히 강한 이점.

## 현재 버전: v0.6b (완료)
**상태**: Monte Carlo 배치 프레임워크 + 통계 분석 모듈 + 전술 GIF 시각화 + 15개 파일 136개 테스트

## v0.6b에서 구현된 핵심 사항
1. **Monte Carlo 배치 실행기** — `modules/batch.py`, multiprocessing 병렬화, 4,200회 실행 지원
2. **통계 분석 모듈** — `modules/stats.py`, Shapiro-Wilk/t-test/Mann-Whitney/Cohen's d/Bonferroni
3. **notebook3 업데이트** — BatchRunner 연동, 수렴성 검사
4. **notebook4 업데이트** — stats.py 연동, 레이더 차트, 포레스트 플롯 추가
5. **전술 시각화 GIF** — 14개 GIF 애니메이션 + 21개 비교 스냅샷 (`output/gif/`)
6. **테스트 확장** — 15개 파일, 136개 테스트 (신규 20개: test_batch 6, test_stats 14)

## v0.6a에서 구현/수정된 핵심 사항
1. **PAC-3 MSE 교정** — max_range 120→60km, max_altitude 30→40km, ammo 16→12, engagement_time 5→9s
2. **천궁-II 교정** — max_range 40→45km (Block II)
3. **BIHO gun/missile 분리** — gun 3km/600발, missile 7km/2발, 이중 모드 교전 로직
4. **MCRC 재배치** — (100,140)→(100,50) 사수 후방 (C2 교리 반영)
5. **시나리오 1 파상 변경** — UAS→CM→SRBM (러-우 전쟁 교리)
6. **테스트 확장** — 11개 파일, 116개 테스트 (신규 30개)

## 알려진 문제 (v0.6b)
- 한글 폰트 미지원 — matplotlib 시각화에서 한글 글리프 경고
- 스냅샷 메모리 — record_snapshots=True 시 배치 실험에서 메모리 증가 가능 (batch.py에서 자동 비활성화)
- S1 누출률 증가 — PAC-3 사거리 축소 + 파상 변경 효과, v0.7 구조 개선으로 보완 예정
- 4,200회 전체 실행 시 멀티프로세싱 메모리 사용량 모니터링 필요

## 검증 보고서 기반 로드맵
근거: `KIDA_ADSIM_Unified_Validation_v2.docx` (15개 검증 영역, 13개 우선순위)

| 버전 | 범위 | 핵심 항목 |
|------|------|-----------|
| **v0.6a** ✅ | 파라미터 교정 | PAC-3/천궁/BIHO 교정, MCRC 재배치, 파상 변경 |
| **v0.6b** ✅ | Monte Carlo + 통계 | batch.py, stats.py, 레이더/포레스트 차트, 136개 테스트 |
| v0.7 | 구조적 개선 | 표적분류, 방위각, KF-16, 영역확대, THAAD, 시간스텝 |
| v0.8+ | 확장 체계 | AEW&C, Aegis, SBIRS, L-SAM |

## 다음 작업: v0.7 (구조적 개선) — 4 Phase, 10개 항목

**Phase A (기반 인프라, 선행 필수)**:
1. **시뮬레이션 영역 확대** — 200×200 → 800×600km (모든 좌표 기반)
2. **이중 시간 스텝** — 5s 일반 + 0.5s BMD

**Phase B (센서/탐지 현실화)**:
3. **레이더 수평선** — 4/3 지구 모델 (`d = 4.12*(√h_s + √h_t)`)
4. **레이더 방위각 제약** — MPQ-65: 90°, Green Pine: 120°
5. **표적 분류 + KN-25 오분류 모델** — RCS 기반 분류 + 혼동 행렬

**Phase C (교전 로직 고도화)**:
6. **교전 교리 확장** — 2발 salvo, S-L-S, 재장전
7. **BMD 사전 위임** — 선형 C2에서 SRBM 직접 교전 허용 (120s→20s)

**Phase D (체계/시나리오 확장)**:
8. **KF-16 동적 CAP 궤도** — 고정 위치 → 순회 궤도 모델
9. **THAAD 체계 추가** — AN/TPY-2 + 요격탄 48발, 200km 사거리
10. **시나리오 5b** — 동시 다중 노드 파괴

> 상세 구현 계획: `plan.md` 참조

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
- `README.md` — 프로젝트 목표, 개념, 아키텍처 비교, 로드맵
- `CHANGELOG.md` — 버전별 업데이트 이력 + 발견된 문제 + 개선 계획
- `plan.md` — v0.7 구조적 개선 상세 구현 계획 (4 Phase, 10개 항목, 항목별 수정 파일·테스트 명세)
- `dev_blueprint.md` — 초기 개발 청사진 (참조용, 동결)
- `KIDA_ADSIM_Unified_Validation_v2.docx` — 군사 현실성 통합 검증 보고서 (참조용, 동결)
