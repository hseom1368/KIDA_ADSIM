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

## 핵심 아키텍처 비교 (v0.3 기준, 시나리오 1 seed=42)
| 항목 | 선형 C2 | Kill Web |
|------|---------|----------|
| S2S 시간 | ~354s | ~5s (71배 빠름) |
| 누출률 | 35.6% | **11.1%** |
| 교전 성공률 | 37.5% | **44.4%** |
| 격추수 | 12기 | **20기** |
| 토폴로지 | 계층 체인 (MCRC SPOF) | 완전 메시 (분산) |
| 사수 선택 | 유형 우선 고정 | 최적 점수 기반 (3D 거리) |
| 교전 시점 | 킬체인 지연으로 자연 지연 | 최적 Pk 대기 후 교전 |

## 현재 버전: v0.3 (완료)
**상태**: v0.2 이슈 전량 해소 + 검증 심화 + 코드 품질 리뷰 완료

## v0.3에서 구현/수정된 핵심 사항
1. **defense_coverage 메트릭 수정** — MetricsCollector.shooters 필드 추가
2. **시나리오 3 EW 3단계 분할** — light/moderate/heavy 하위 시나리오
   - detection_factor → 센서 탐지 확률, latency_factor → C2 지연
3. **시나리오 2~5 전량 검증** — 7개 시나리오 × 2 아키텍처 = 14개 조합 PASS
4. **shooter_score() 3D 수정** — 2D math.dist() → 3D _slant_range()
5. **매직 넘버 6개 제거** — ENGAGEMENT_POLICY로 이동
6. **테스트 프레임워크** — 5개 파일, 45개 테스트 (엣지 케이스 포함)

## 알려진 문제 (v0.3)
- 생성자 `jamming_level` 파라미터가 시나리오 config에 의해 덮어씌워짐
- `comms.py` `linear_killchain()`/`killweb_killchain()` 미사용 (죽은 코드)
- `config.py` `scenario_3_ew` 원본 설정이 하위 시나리오로 대체됨 (죽은 설정)

## 다음 작업: v0.4 (plan.md 참조)
- 생성자 jamming_level 오버라이드 로직 정리
- comms.py 죽은 코드 정리 또는 model.py에서 위임 리팩토링
- 다중 교전 모델링 (동일 위협에 복수 사수 동시 교전)
- Monte Carlo 300회 배치 실험 및 통계 분석

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
