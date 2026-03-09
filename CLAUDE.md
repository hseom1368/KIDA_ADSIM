# KIDA_ADSIM — Claude Code 프로젝트 컨텍스트

## 프로젝트 개요
한국군 방공체계 C2 아키텍처(선형 C2 vs Kill Web) 비교 M&S.
Mesa(ABM) + SimPy(DES) + NetworkX 기반 에이전트 시뮬레이션.

## 디렉터리 구조
```
modules/
  config.py    — 모든 파라미터 (센서, C2, 사수, 위협, 시나리오, 통신, 교전정책)
  agents.py    — Mesa 에이전트 4종 (Sensor, C2Node, Shooter, Threat) + _slant_range()
  model.py     — 통합 시뮬레이션 엔진 (AirDefenseModel) + _should_engage_now()
  network.py   — NetworkX 토폴로지 빌더 (선형/킬웹)
  comms.py     — SimPy 통신 채널 + 킬체인 프로세스
  metrics.py   — 10개 성능 지표 수집기
  threats.py   — 위협 생성기 (5개 시나리오)
notebook1~4    — Jupyter 노트북 (모델정의, 시나리오, 배치실험, 분석)
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

## 핵심 아키텍처 비교 (v0.2 기준)
| 항목 | 선형 C2 | Kill Web |
|------|---------|----------|
| S2S 시간 | ~354s | ~5s (71배 빠름) |
| 누출률 | 35.6% | **11.1%** |
| 교전 성공률 | 37.5% | **44.4%** |
| 토폴로지 | 계층 체인 (MCRC SPOF) | 완전 메시 (분산) |
| 사수 선택 | 유형 우선 고정 | 최적 점수 기반 |
| 교전 시점 | 킬체인 지연으로 자연 지연 | 최적 Pk 대기 후 교전 |

## 현재 버전: v0.2 (완료)
**상태**: 비행 프로파일 + 3D 경사거리 + 최적 교전 시점 구현 완료

## v0.2에서 구현된 핵심 기능
1. **비행 프로파일 엔진** — ThreatAgent._compute_phase_state()
   - 4종 위협 모두 단계별 동적 고도/속도/기동 (config.py flight_profile)
   - SRBM 종말단계 30→0km 하강 → PAC-3 교전 가능 창 생성
2. **3D 경사거리** — _slant_range(pos1, alt1, pos2, alt2)
   - 센서 탐지, 교전 범위, Pk 계산에 고도차 반영
3. **최적 교전 시점** — _should_engage_now(shooter, threat)
   - Pk ≥ 0.30이면 교전, 방어지역 ≤ 30km이면 무조건 교전
   - 잔여 교전 기회 ≤ 2회이면 emergency_pk_threshold(0.10) 적용
   - config.py ENGAGEMENT_POLICY에서 임계값 관리

## 다음 작업: v0.3 (plan.md 참조)
1. defense_coverage 메트릭 수정 (shooters 미전달 → 항상 0.0)
2. 시나리오 3(전자전) 재밍 레벨 동적 전환 구현
   - detection_factor → 센서 탐지 확률, latency_factor → C2 지연
3. 시나리오 2~4 검증 실행
4. EXPERIMENT_CONFIG에 시나리오 2~4 추가
5. 시나리오 4 max_sim_time 호환성 수정
6. tests/ 단위 테스트 프레임워크 구축

## 알려진 문제 (v0.2)
- defense_coverage 메트릭 항상 0.0 (metric_9에 shooters 미전달)
- 시나리오 3 jamming_levels 3단계 미활용 (scalar jamming_level만 사용)
- 시나리오 4 duration(3600s) > max_sim_time(1800s) 충돌
- tests/ 디렉토리 미존재

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
- `plan.md` — 현재 진행 중인 개선 작업의 상세 기술 계획 (현재: v0.3)
- `dev_blueprint.md` — 초기 개발 청사진 (참조용, 동결)
