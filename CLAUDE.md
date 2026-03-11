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

## 핵심 아키텍처 비교 (v0.4 기준, 시나리오 1 seed=42)
| 항목 | 선형 C2 | Kill Web |
|------|---------|----------|
| S2S 시간 | ~344s | ~5s (69배 빠름) |
| 누출률 | 35.6% | **22.2%** |
| 교전 성공률 | 37.1% | 36.7% |
| 격추수 | 13기 | **18기** |
| 총 교전수 | 35발 | **49발** (다중교전) |
| 다중교전율 | 14.3% | **16.3%** |
| 토폴로지 | 계층 체인 (MCRC SPOF) | 완전 메시 (분산) |
| 사수 선택 | 유형 우선 고정 | 최적 점수 기반 (3D 거리) |
| 교전 시점 | 킬체인 지연으로 자연 지연 | 최적 Pk 대기 후 교전 |
| 교전 방식 | 위협당 1사수 | **위협 유형별 복수 사수** |

## 현재 버전: v0.4 (완료)
**상태**: v0.3 이슈 전량 해소 + 다중 교전 모델링 + 12개 메트릭 + 57개 테스트

## v0.4에서 구현/수정된 핵심 사항
1. **jamming_level 오버라이드 정리** — 명시적 > 시나리오 > 기본값 우선순위
2. **comms.py 죽은 코드 삭제** — linear_killchain/killweb_killchain 제거
3. **config.py 죽은 설정 삭제** — scenario_3_ew 원본 제거
4. **다중 교전 모델링** — SRBM=3기, CRUISE_MISSILE=2기 동시 교전
5. **메트릭 확장** — 12개 (multi_engagement_rate, avg_shooters 추가)
6. **테스트 확장** — 6개 파일, 57개 테스트 (다중교전 12개 추가)
7. **노트북 업데이트** — Cohen's d 효과 크기, 다중교전 분석 섹션

## 알려진 문제 (v0.4)
- 다중 교전의 탄약 고갈 가속 — SRBM에 3기 사수 투입 시 탄약 소모 빠름
- S5 Kill Web 누출률 미개선 — 노드 파괴 시 가용 사수 부족으로 다중교전 효과 제한

## 다음 작업: v0.5
- 잔여 탄약 기반 적응형 교전 정책 (임계값 이하 시 단일 교전 전환)
- 센서 융합 고도화 (COP 품질 차별화)
- 통신 네트워크 동적 열화 (재밍 링크별 차등)

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
