# KIDA_ADSIM — Claude Code 프로젝트 컨텍스트

## 프로젝트 개요
한국군 방공체계 C2 아키텍처(선형 C2 vs Kill Web) 비교 M&S.
Mesa(ABM) + SimPy(DES) + NetworkX 기반 에이전트 시뮬레이션.

## 디렉터리 구조
```
modules/
  config.py    — 모든 파라미터 (센서, C2, 사수, 위협, 시나리오, 통신, 교전정책, COP, 적응형교전, 통신열화)
  agents.py    — Mesa 에이전트 4종 (Sensor, C2Node, Shooter, Threat) + _slant_range()
  model.py     — 통합 시뮬레이션 엔진 (AirDefenseModel) + COP 차별화 + 적응형 교전 + 스냅샷
  network.py   — NetworkX 토폴로지 빌더 (선형/킬웹)
  comms.py     — SimPy 통신 채널 + 킬체인 프로세스 + 링크별 동적 열화
  metrics.py   — 12개 성능 지표 수집기
  threats.py   — 위협 생성기 (5개 시나리오)
  viz.py       — 2D 전술 시각화 (matplotlib.animation 기반)
notebook1~5    — Jupyter 노트북 (모델정의, 시나리오, 배치실험, 분석, 전술시각화)
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

## 현재 버전: v0.5 (완료)
**상태**: COP 차별화 + 적응형 교전 + 통신 동적 열화 + 2D 시각화 + 86개 테스트

## v0.5에서 구현/수정된 핵심 사항
1. **COP 품질 차별화** — Kill Web: 센서 융합 √N 오차, 아군 상태 공유, 교전 계획 공유
2. **적응형 교전 정책** — 탄약 30% 이하 단일교전, 10% 이하 고위협만 교전
3. **통신 네트워크 동적 열화** — 링크별 차등 재밍, Kill Web 메시 다중경로 완화
4. **2D 전술 시각화 모듈** — TacticalVisualizer (렌더/애니메이션/비교/타임라인)
5. **시각화 노트북** — notebook5 (전술 애니메이션 + 아키텍처 비교)
6. **테스트 확장** — 9개 파일, 86개 테스트 (신규 29개)

## 알려진 문제 (v0.5)
- 한글 폰트 미지원 — matplotlib 시각화에서 한글 글리프 경고
- 스냅샷 메모리 — record_snapshots=True 시 배치 실험에서 메모리 증가 가능

## 다음 작업: v0.6
1. **Monte Carlo 300회 배치 실험** — 전 시나리오 × 2 아키텍처 × 300 시드
2. **인터랙티브 시각화** — plotly/dash 기반 웹 대시보드 (선택)
3. **최종 분석 보고서** — 통계 검정, 효과 크기, 정책 제언 종합 보고

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
- `plan.md` — 현재 진행 중인 개선 작업의 상세 기술 계획 (현재: v0.5 완료)
- `dev_blueprint.md` — 초기 개발 청사진 (참조용, 동결)
