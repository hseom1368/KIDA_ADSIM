# KIDA_ADSIM 시뮬레이션 현실화 보완계획

> 작성 목적: 선형 C2 → Kill Web 전환 효과 분석을 위한 시뮬레이션 현실화
> 기반 버전: v0.6.5
> 작성일: 2026-03-26

---

## 1. 시뮬레이션 목적 재정의

### 1.1 핵심 연구 질문

> "현재 MCRC(지역방공)/KAMD작전센터(탄도탄 방어)/육군 국지방공(저고도)으로 분리된
> 선형 방공 지휘구조를 통합 Kill Web(IBCS 개념)으로 전환하면,
> 탐지-교전 시간, 누출률, 중복교전 방지, 자산 효율성에서 얼마나 개선되는가?"

### 1.2 한국군 방공 지휘구조의 3축 분리 현황

한국군의 방공은 크게 **3개의 분리된 지휘계통**으로 운용됨:

1. **공군 MCRC (중앙방공통제소)** — 지역방공
   - 공군 방공관제사령부 소속, 오산기지 항공우주작전본부 내 위치
   - AN/FPS-117 등 방공관제레이더 정보를 종합하여 KADIZ 내 모든 항적(항공기, 순항미사일 등) 탐지·식별·통제
   - 전투기 긴급출격(scramble) 결정, 천궁-I/천궁-II 대항공기 교전 통제
   - 공중감시팀, 식별팀, 무기운영팀의 3개 팀으로 24시간 운영

2. **공군 KAMD작전센터** (구 KTMO-Cell/AMD-Cell) — 탄도탄 방어
   - 공군 미사일방어사령부 산하, 오산기지 항공우주작전본부 내 위치 (MCRC와 같은 건물이지만 별도 조직)
   - 그린파인/슈퍼그린파인 조기경보레이더, 이지스함 SPY-1D, 조기경보위성 등 탄도탄 탐지자산 정보를 종합
   - 탄도탄 항적정보 처리, 위협평가, 교전통제, 발사원점 기반 공격작전 지원
   - PAC-3 MSE, 천궁-II(대탄도탄), L-SAM, THAAD 등 요격포대에 교전 명령 하달
   - 5조 4교대 365일 24시간 운영
   - 한화시스템이 성능개량 완료(2023.6 전력화), 기존 대비 항적처리 시간·정보 전송주기 크게 단축

3. **육군 국지방공** — 저고도 야전방공
   - 육군 군단급 방공여단/방공대대가 독자적으로 운용
   - TPS-880K 국지방공레이더로 저고도 위협 탐지 → 방공지휘통제경보체계(C2A) 연동
   - 천마(K-SAM), 비호복합, 신궁 등으로 5km 이하 저고도 방어
   - 향후 LAMD(장사정포요격체계)도 육군이 주도적으로 운용 예정

### 1.3 검증해야 할 3대 비효율 가설

**가설 1: 3축 방공 지휘구조(MCRC/KAMD/육군 국지방공)의 분절로 인한 효율성 저하**

- 현황: 공군 MCRC(지역방공), 공군 KAMD작전센터(탄도탄 방어), 육군 국지방공(저고도 방어)이 각각 별도의 C2 체계로 운용
- 근거 1: 한국일보 김대영 군사평론가(2026.1) — "KAMD는 패트리어트, 천궁-II, L-SAM 등 다층 요격 수단 확충에는 성과를 거뒀지만, 센서·사격통제·교전 판단이 체계별로 단절돼 실제 운용에서는 '연결되지 않은 다층 방어'에 머물러 있다"
- 근거 2: 아산정책연구원 양욱 박사(2025.7) — "단편적인 무기체계 도입이나 군종 간 분리된 운용으로는 부족하다. 탐지·지휘·요격이 유기적으로 연동되는 통합 지능형 다층방공체계가 필요하다"
- 근거 3: 세계일보(2025.9) — "육군 방공체계 등과의 연계성 강화도 풀어야 할 과제다. 조기경보위성과 지상 레이더, 해군 이지스함, 공군 조기경보통제기, 육군 저고도 방공체계 등은 각각의 순간에 미사일을 부분적으로 포착한다"
- 시뮬레이션 검증: Linear(3축 분리 C2) vs Kill Web(통합 C2)에서 S2S 시간, 교전 배분 효율 비교

**가설 2: 위협 정보만 공유되고 아군 교전 상태가 공유되지 않아 중복교전 발생**

- 현황: COP(공통작전상황도)에 적 위협은 공유되나, 아군 자산(어떤 포대가 어떤 표적에 교전 중인지)은 3개 C2 간 실시간 공유 미흡
- 구체 사례: 전방군단 천마(육군 국지방공)가 저고도 표적에 교전 중인데, 공군 MCRC 통제 하의 천궁도 동일 표적에 교전 명령 → 고가 요격탄 낭비. 또는 KAMD작전센터가 탄도탄으로 판단한 표적에 PAC-3를 할당했는데, 해당 표적이 이미 L-SAM에 의해 교전 중일 수도 있음
- 시뮬레이션 검증: COP 공유 수준(위협만 vs 위협+아군 상태)에 따른 중복교전율, 탄약 효율 비교

**가설 3: 장사정포/방사포와 탄도미사일의 미식별로 고가 자산 소모**

- 현황: 300mm 이상 대구경 방사포(KN-25 등)는 탄도미사일과 동일한 궤적으로 탐지됨
- 문제점: KAMD 레이더가 장사정포 로켓을 탄도미사일로 오인식하면, PAC-3 MSE(발당 약 55억원)가 KN-25 로켓(상대적 저가)에 소모될 위험
- 근거: 서울경제(2022.10) — "장사정포는 주로 저층 상공에서 낮게 날아오는데다가 탄도미사일보다 값싸게 대량으로 동시에 발사할 수 있어 기존 KAMD로는 2단계 요격을 구현하기 어렵다. 값비싼 KAMD용 대공요격탄으로 상대적으로 저렴한 장사정포를 요격하는데 소모하는 것은 전략적으로 비효율적이다"
- 추가 근거: 육군 국감보고(2022) — "KN-23, KN-24, 600mm 대구경방사포(KN-25)를 요격할 수 있는 '장사정포요격체계-II' 개발 추진" → LAMD와 KAMD가 분리되면 위협 유형 식별 및 최적 자산 배분이 불가

---

## 2. 방공 대응전력 재설계

### 2.1 현재 시뮬레이션 vs 실제 전력 Gap

| 현재 시뮬레이션 | 실제 체계 | 조치 |
|---|---|---|
| PAC-3 (max_alt: 30km) | PAC-3 MSE (max_alt: ~40km, 사거리 ~90km) | 스펙 수정 |
| 천궁-II (max_alt: 20km) | 천궁-II (대탄도탄: ~15km, 대항공기: ~20km) | 탄종 이원화 |
| 비호 (max_alt: 3km) | 비호복합 (기관포 3~5km + 신궁 7km) | 복합무장 모델링 |
| KF-16 (max_alt: 15km) | KF-16 CAP (AIM-120, AIM-9X) | 대체로 적절 |
| **없음** | **THAAD (40~150km)** | **신규 추가** |
| **없음** | **L-SAM 대탄도탄 (40~60km)** | **신규 추가** |
| **없음** | **L-SAM 대항공기 (150~300km)** | **신규 추가** |
| **없음** | **천궁-I (항공기 전용, 40km)** | **신규 추가** |
| **없음** | **천마 K-SAM (9km, 5km 고도)** | **신규 추가** |
| **없음** | **신궁 MANPADS (5km)** | 선택 추가 |
| **없음** | **LAMD 장사정포요격체계** | 선택 추가 (미래전력) |

### 2.2 추가할 무기체계 파라미터

#### THAAD (주한미군 성주 배치)
```python
"THAAD": {
    "weapon_type": "THAAD",
    "max_range": 200,        # km
    "min_range": 0,
    "max_altitude": 150,     # km
    "min_altitude": 40,      # km (최저 요격고도 — 적외선 탐색기 한계)
    "pk_table": {
        "SRBM": 0.90,        # 표준 탄도궤적
        "SRBM_MANEUVER": 0.60, # KN-23 변칙기동
        "CRUISE_MISSILE": 0.0,
        "AIRCRAFT": 0.0,
        "UAS": 0.0,
    },
    "ammo_count": 48,        # 6 발사대 × 8발
    "reload_time": 1800,
    "engagement_time": 15,   # 요격미사일 비행시간 포함
    "intercept_method": "hit_to_kill",
    "label": "THAAD",
}
```

#### L-SAM 대탄도탄
```python
"LSAM_ABM": {
    "weapon_type": "LSAM_ABM",
    "max_range": 150,        # km (추정)
    "min_range": 0,
    "max_altitude": 60,      # km
    "min_altitude": 40,      # km (적외선 탐색기 한계)
    "pk_table": {
        "SRBM": 0.85,
        "SRBM_MANEUVER": 0.55,
        "CRUISE_MISSILE": 0.0,
        "AIRCRAFT": 0.0,
        "UAS": 0.0,
    },
    "ammo_count": 8,         # 발사대 2대 × 4발 (추정)
    "reload_time": 1800,
    "engagement_time": 12,
    "intercept_method": "hit_to_kill",
    "label": "L-SAM ABM",
}
```

#### L-SAM 대항공기
```python
"LSAM_AAM": {
    "weapon_type": "LSAM_AAM",
    "max_range": 200,        # km (최소 150~300km)
    "min_range": 10,
    "max_altitude": 20,      # km
    "pk_table": {
        "SRBM": 0.0,
        "CRUISE_MISSILE": 0.85,
        "AIRCRAFT": 0.90,
        "UAS": 0.50,
    },
    "ammo_count": 8,         # 발사대 2대 × 4발 (추정)
    "reload_time": 1200,
    "engagement_time": 10,
    "intercept_method": "proximity_fuse",
    "label": "L-SAM AAM",
}
```

#### 천궁-I (M-SAM Block 1, 항공기/순항미사일 전용)
```python
"CHEONGUNG1": {
    "weapon_type": "CHEONGUNG1",
    "max_range": 40,
    "min_range": 1,
    "max_altitude": 15,      # km
    "pk_table": {
        "SRBM": 0.0,         # 대탄도탄 능력 없음
        "CRUISE_MISSILE": 0.80,
        "AIRCRAFT": 0.85,
        "UAS": 0.60,
    },
    "ammo_count": 32,        # 발사대 4대 × 8발
    "reload_time": 600,
    "engagement_time": 5,
    "intercept_method": "proximity_fuse",
    "label": "Cheongung-I (M-SAM)",
}
```

#### 천마 K-SAM
```python
"CHUNMA": {
    "weapon_type": "CHUNMA",
    "max_range": 9,          # km 유효사거리
    "min_range": 0.5,
    "max_altitude": 5,       # km
    "pk_table": {
        "SRBM": 0.0,
        "CRUISE_MISSILE": 0.40,  # 저고도 순항미사일 대응 가능
        "AIRCRAFT": 0.65,
        "UAS": 0.55,
    },
    "ammo_count": 8,         # 미사일 8발
    "reload_time": 300,      # 야전 재장전
    "engagement_time": 3,
    "intercept_method": "command_guidance",  # 지령유도
    "sensor": {
        "search_radar_range": 20,   # km (S밴드 탐색레이더)
        "track_radar_range": 16,    # km (Ku밴드 추적레이더)
        "search_altitude": 5,       # km
    },
    "label": "Chunma (K-SAM)",
    "operating_org": "army",        # 육군 군단급 배치
}
```

> **천마 핵심 특성**: K-200 궤도 장갑차량에 탐색레이더(20km), 추적레이더(16km), 미사일 8발을 통합 탑재한 자주 대공 유도탄. 야전군 기동부대를 동행하며 5km 이하 저고도 방어를 담당. 약 100여 대 배치 완료. 마하 2.6 속도의 미사일을 사용하며, 적기를 탐지한 후 격추까지 약 10초 소요.

### 2.3 방어 계층 구조 (다층 교전 로직)

```
고도 150km ┌──────────────────────────────────────────┐
          │  THAAD (40~150km) — 탄도탄 전용           │
고도 60km  ├──────────────────────────────────────────┤
          │  L-SAM ABM (40~60km) — 탄도탄 전용        │
고도 40km  ├──────────────────────────────────────────┤
          │  PAC-3 MSE (~40km) — 탄도탄 + 항공기      │
          │  천궁-II (~15~20km) — 탄도탄 + 항공기      │
고도 15km  ├──────────────────────────────────────────┤
          │  천궁-I (~15km) — 항공기/순항미사일 전용    │
          │  L-SAM AAM (~20km) — 장거리 항공기/순항미사일│
고도 5km   ├──────────────────────────────────────────┤
          │  천마 (~5km) — 저고도 항공기/순항미사일      │
          │  비호복합 (~3~7km) — 드론/저고도 위협       │
고도 0km   └──────────────────────────────────────────┘
```

**다층 교전 흐름 (탄도미사일):**
1. THAAD가 고도 40~150km에서 1차 요격 시도
2. 실패 시 L-SAM ABM이 고도 40~60km에서 2차 요격
3. 실패 시 PAC-3 MSE가 고도 ~40km에서 3차 요격
4. 실패 시 천궁-II가 고도 ~15km에서 4차 요격 (최종)

**다층 교전 흐름 (순항미사일):**
1. L-SAM AAM이 원거리(~200km)에서 탐지·교전
2. 천궁-I/천궁-II가 중거리(~40km)에서 교전
3. 천마가 저고도(~5km)에서 교전
4. 비호복합/신궁이 최종 근접 방어

---

## 3. 레이더 체계 재설계

### 3.1 레이더 역할 분리 모델링

현재 시뮬레이션은 모든 센서가 동일한 탐지 로직을 사용. 실제로는 **감시→큐잉→추적→화력통제** 단계가 분리됨.

#### 1계층: 전략 조기경보 (탄도탄 전용)
```python
"GREEN_PINE": {
    "sensor_type": "BMD_EW",         # 탄도탄 조기경보
    "detection_range": 800,           # km (슈퍼 그린파인)
    "tracking_capacity": 200,
    "scan_rate": 0.1,                 # 지속 감시 (비회전)
    "detectable_types": ["SRBM", "MRBM"],  # 탄도탄만
    "role": "early_warning",          # 교전통제 불가, 큐잉만
    "provides_cueing_to": ["KAMD_OPS_CENTER"],  # KAMD작전센터로 정보 전송 → 센터가 요격포대에 교전명령
    "label": "Green Pine/Super Green Pine (BMD EW)",
    "quantity": 4,
}
```

#### 2계층: 방공관제 (영공 감시)
```python
"FPS117": {
    "sensor_type": "SURVEILLANCE",
    "detection_range": 470,           # km
    "tracking_capacity": 100,
    "scan_rate": 0.17,                # 6 RPM
    "detectable_types": ["AIRCRAFT", "CRUISE_MISSILE", "UAS_LARGE"],
    "role": "surveillance",
    "provides_cueing_to": ["MCRC"],
    "min_detection_altitude": 1.0,    # km (레이더 수평선 제한)
    "label": "AN/FPS-117 Surveillance Radar",
    "quantity": 10,
}
```

#### 3계층: 국지방공 (야전 저고도)
```python
"TPS880K": {
    "sensor_type": "LOCAL_AD",
    "detection_range": 40,            # km (추정, X밴드 AESA)
    "tracking_capacity": 30,
    "scan_rate": 1.0,
    "detectable_types": ["AIRCRAFT", "CRUISE_MISSILE", "UAS", "UAS_SMALL"],
    "role": "local_surveillance",
    "provides_cueing_to": ["CHUNMA", "BIHO", "C2A"],  # 방공지휘통제경보체계
    "min_detection_altitude": 0.05,   # km (50m, 저고도 특화)
    "is_3d": True,                    # 3차원 탐지 (방위+거리+고각)
    "label": "TPS-880K Local AD Radar",
}
```

#### 4계층: 무기체계 전용 레이더 (화력통제)
```python
# 각 무기체계에 통합 — 별도 센서 에이전트가 아닌 무기체계 속성으로 모델링
"WEAPON_RADARS": {
    "AN_MPQ65A": {  # PAC-3 전용
        "search_range": 170,          # km (TBM 모드)
        "track_range": 100,           # km
        "simultaneous_tracks": 100,
        "modes": ["TBM_SEARCH", "AIR_SEARCH"],
        "mode_switch_time": 5,        # 초 (모드 전환 소요시간)
    },
    "CHEONGUNG_MFR": {  # 천궁 전용
        "search_range": 100,          # km
        "track_range": 100,
        "simultaneous_tracks": 40,
        "rotation_rpm": 40,
    },
    "LSAM_MFR": {  # L-SAM 전용
        "search_range": 310,          # km (대탄도탄)
        "track_range": 230,           # km (대항공기)
        "simultaneous_tracks": 10,    # 탄도탄 기준
    },
    "THAAD_TPY2": {  # THAAD 전용
        "search_range": 1000,         # km (전방배치모드)
        "track_range": 600,           # km (종말모드)
    },
    "CHUNMA_RADAR": {  # 천마 전용
        "search_range": 20,           # km (S밴드)
        "track_range": 16,            # km (Ku밴드)
        "search_altitude": 5,         # km
    },
}
```

### 3.2 탐지→교전 흐름 모델링

**현재(비현실적)**: 센서가 위협 탐지 → 바로 C2 보고 → 교전

**개선(현실적)**:
```
[조기경보레이더] → 탄도탄 탐지 → [AMD-Cell] → 큐잉 정보 생성
                                      ↓
[방공관제레이더] → 항공기/CM 탐지 → [MCRC] → 교전 통제 명령
                                      ↓
[무기체계 전용 레이더] ← 큐잉 방향으로 빔 지향 → 정밀 추적 → 화력통제 품질 달성 → 교전
```

SimPy 프로세스로 모델링할 지연 요소:
- 조기경보 탐지 → AMD-Cell 경보 전파: 2~5초
- AMD-Cell → 무기체계 큐잉: 3~10초 (Linear), 1~3초 (Kill Web)
- 무기체계 레이더 빔 지향 → 추적 획득: 5~15초
- 추적 → 화력통제 품질 달성: 2~5초
- 교전 승인 → 요격미사일 발사: 1~5초

---

## 4. 지휘구조(C2) 재설계

### 4.1 현재 한국군 방공 지휘구조 (Linear C2) — 3축 분리

```
                        [합참/전구사]
                            │
               ┌────────────┼────────────┐
               │                         │
        [공군작전사령부]              [육군작전사령부]
               │                         │
    ┌──────────┼──────────┐              │
    │          │          │              │
 [방공관제사]  [미사일방어사] [방공유도탄사]  [군단]
    │          │          │              │
  [MCRC]   [KAMD작전센터]  │         [방공여단]
    │       (구 KTMO-Cell)  │            │
    │          │          │         ┌───┼───┐
    │          │      천궁/PAC-3   천마  비호  신궁
    │          │      L-SAM 포대   소대  소대
    │          │
  FPS-117    그린파인
  방공관제    조기경보
  레이더     레이더
    │          │
 항공기/CM   탄도탄
 감시·통제   탐지·교전통제
```

**오산기지 항공우주작전본부 내 핵심 조직:**
- MCRC: KADIZ 내 모든 항적 실시간 감시·통제 (지역방공)
- KAMD작전센터: 탄도탄 항적정보 처리·위협평가·교전통제 (탄도탄 전담)
- 두 조직이 같은 건물에 있지만 **별도 C2 체계**로 운용

**3축 분리의 핵심 문제점:**

1. **MCRC ↔ KAMD작전센터 간 단절**: 지역방공(항공기/CM)과 탄도탄 방어가 별도 체계로 운용. 섞어쏘기 시 순항미사일과 탄도미사일이 동시에 날아와도 각각의 C2가 독립적으로 대응 → 통합 교전배분 불가
2. **KAMD ↔ 육군 국지방공 간 단절**: KAMD작전센터가 탄도탄에 교전명령을 내려도, 육군 천마/비호가 동일 표적에 대해 독자 교전 가능 → 중복교전
3. **센서·교전 정보 비공유**: KAMD작전센터의 탄도탄 탐지 정보가 육군 국지방공 C2A에 실시간 전달 미흡. 역으로 TPS-880K의 저고도 탐지 정보가 KAMD작전센터로 통합되지 않음
4. **LAMD와 KAMD 간 미연동**: 장사정포(탄도궤적)를 KAMD 레이더가 탄도미사일로 오인식 → LAMD로 넘기지 못하고 PAC-3가 교전
5. **IBCS 미도입**: 주한미군은 2026년 상반기 IBCS 전력화 완료 예정이나, 한국군은 아직 미도입 → 한미 연합 방공작전 실시간 연동 제한

### 4.2 Kill Web 통합 지휘구조

```
              [통합 방공작전센터 (IAOC)]
          ┌───────┬───────┬───────┬───────┐
      [통합COP] [AI교전배분] [통합큐잉] [전투피해평가]
          │       │        │        │
    ┌─────┴───────┴────────┴────────┴─────┐
    │      통합 네트워크 (IBCS/Kill Web)      │
    │   Any Sensor → Best Shooter 원칙      │
    ├──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┬──┤
   그린 FPS TPS THAAD L-SAM PAC3 천궁2 천궁1 천마 비호 LAMD 이지스
   파인 117 880K
```

**Kill Web 핵심 개선:**
1. **통합 COP**: 적 위협 + 아군 교전 상태 + 잔여 탄약 + 센서 커버리지 실시간 공유
2. **Any Sensor, Best Shooter**: 어떤 센서가 탐지하든 최적의 요격체계에 자동 할당 (IBCS 개념)
3. **위협 유형 자동 식별**: 다중 센서 융합으로 탄도미사일/장사정포/순항미사일/UAS 식별 → 최적 자산 배분
4. **중복교전 방지**: 전 자산의 교전 상태 공유 → 미교전 표적 우선 배분
5. **크로스도메인 큐잉**: 그린파인이 탄도탄 탐지 시 동시에 모든 계층에 전파, TPS-880K가 저고도 CM 탐지 시 MCRC에도 즉시 공유

### 4.3 시뮬레이션 구현 방안

기존 `strategies.py`의 `LinearC2Strategy` / `KillWebStrategy`를 확장:

**Linear C2 (현재 체계 — 3축 분리):**
- 공군 MCRC: 지역방공 통제 (항공기/순항미사일 대응, 천궁-I 교전통제, 전투기 scramble)
- 공군 KAMD작전센터: 탄도탄 전담 (그린파인→위협평가→PAC-3/천궁-II/L-SAM 교전통제)
- 육군 국지방공: 독자 운용 (TPS-880K→천마/비호 교전)
- 3개 C2 간 위협 정보만 부분 공유, 교전 상태는 미공유
- 장사정포/탄도미사일 미식별 → KAMD작전센터의 PAC-3가 무차별 교전

**Kill Web (통합 체계):**
- 통합 IAOC: 모든 무기체계 교전 통제 (IBCS 개념)
- 위협 유형 자동 식별 → 최적 자산 배분 (장사정포→LAMD, 탄도탄→PAC-3, 항공기→천궁-I)
- 교전 상태 실시간 공유 → 중복교전 방지
- 센서 융합: 그린파인 + FPS-117 + TPS-880K + 무기체계 전용 레이더 + 이지스 SPY-1D

---

## 5. 위협 모델 보완

### 5.1 시간표적(TOT) 공격 모델링

현재 문제: 모든 위협이 동시 발사 → 탄도미사일만 먼저 도착

**개선**: 역산 발사 시각(TOT scheduling)
```python
# 목표 동시도착시각(T=0) 기준 역산
target_distance = 200  # km
tot_impact_time = T  # 동시 도착 목표 시각

# 각 위협의 비행시간 계산 (경로 가중치 포함)
bm_flight = target_distance / 2.0                    # ~100초
cm_flight = (target_distance * 1.3) / 0.27           # ~963초 (우회경로 30% 추가)
uas_flight = (target_distance * 1.2) / 0.05           # ~4800초

# 역산 발사시각
bm_launch = tot_impact_time - bm_flight               # 가장 나중에 발사
cm_launch = tot_impact_time - cm_flight                # 중간에 발사
uas_launch = tot_impact_time - uas_flight              # 가장 먼저 발사
```

### 5.2 장사정포/방사포 위협 추가

```python
"KN25_MLRS": {
    "threat_type": "MLRS_GUIDED",
    "speed": 1.5,               # km/s (Mach 4.4)
    "altitude": 40.0,           # km (최대 정점, 탄도궤적)
    "rcs": 0.1,                 # m²
    "maneuvering": False,
    "label": "KN-25 600mm MLRS",
    "radar_signature": "ballistic",  # 탄도미사일과 동일하게 탐지됨!
    "cost_ratio": 0.01,         # 탄도미사일 대비 1% 비용
}
```

### 5.3 위협 유형 식별 문제 모델링

Linear C2에서: KN-25 방사포가 탄도미사일로 오인식 → PAC-3가 교전 시도
Kill Web에서: 다중 센서 융합으로 궤적 특성 분석 → 방사포 식별 → LAMD로 교전 배분

```python
# 위협 식별 확률 모델
def identify_threat_type(threat, sensors_tracking, architecture):
    if architecture == "linear":
        # 단일 센서, 제한된 식별 능력
        if threat.radar_signature == "ballistic":
            return "SRBM"  # 장사정포도 탄도미사일로 오인
    elif architecture == "killweb":
        # 다중 센서 융합, 궤적 분석
        n_sensors = len(sensors_tracking)
        if n_sensors >= 2:
            # 교차 궤적 분석으로 정확한 유형 식별 가능
            return threat.actual_type  # 실제 유형 반환
```

---

## 6. 구현 우선순위

### Phase 1: 무기체계 파라미터 재설정 (config.py)
1. THAAD, L-SAM, 천궁-I, 천마 추가
2. 기존 PAC-3, 천궁-II, 비호 스펙 수정
3. 교전 고도대별 계층 구조 정의

### Phase 2: 다층 교전 로직 (model.py, strategies.py)
1. 고도 기반 순차 교전 흐름 구현
2. 위협이 특정 고도대 진입 시 해당 계층 사수가 교전
3. 1차 요격 실패 시 다음 계층으로 핸드오프

### Phase 3: C2 구조 이원화 (strategies.py)
1. LinearC2Strategy: 육군/공군 분리 C2 모델링
   - 공군 MCRC 통제 자산과 육군 방공여단 통제 자산 분리
   - 교전 상태 미공유 → 중복교전 발생 모델링
2. KillWebStrategy: 통합 IAOC 모델링
   - 모든 자산 통합 COP
   - 교전 상태 공유 → 중복교전 방지
   - 위협 유형 식별 → 최적 자산 배분

### Phase 4: TOT 공격 시나리오
1. threats.py에 TOT 스케줄링 로직 추가
2. 장사정포/방사포 위협 유형 추가
3. 위협 식별 모델 구현

### Phase 5: 검증 및 분석
1. 기존 시나리오 + 신규 시나리오(TOT 섞어쏘기, 장사정포 포화) 실행
2. Linear vs Kill Web 비교 지표:
   - 누출률, S2S 시간, 중복교전율
   - 탄약 효율 (고가 자산 소모량)
   - 위협 유형별 올바른 자산 배분율
   - 다층 요격 성공률

---

## 7. 핵심 비교 메트릭 추가

기존 12개 메트릭에 추가:

| # | 메트릭 | 설명 | 검증 가설 |
|---|---|---|---|
| 13 | 중복교전율 | 동일 표적에 2개 이상 지휘계통이 교전한 비율 | 가설 2 |
| 14 | 고가자산 소모율 | PAC-3/THAAD가 장사정포에 소모된 비율 | 가설 3 |
| 15 | 위협식별 정확도 | 위협 유형을 올바르게 식별한 비율 | 가설 3 |
| 16 | 다층 요격 기회 | 위협당 평균 요격 시도 횟수 | 구조적 개선 |
| 17 | 교전배분 효율 | 최적 자산에 배분된 교전 비율 | 가설 1, 2 |
| 18 | C2 간 정보지연 | 육군-공군 간 정보 전달 소요시간 | 가설 1 |

---

## 8. 방공 자산 배치 개략도 및 시뮬레이션 반영

### 8.1 한반도 방공 배치 개략 현황 (공개정보 기반)

실제 군사 배치는 보안사항이므로, 공개 보도 및 논리적 추론에 기반한 **개략적 방어구역** 개념으로 정리합니다.

```
=== 한반도 방공 배치 개략도 (남→북 기준) ===

[북한] ── 휴전선(DMZ) ────────────────────────
         │ 약 30~50km                          
     ┌───┴───────────────────────────────────┐
     │ ★ 전방군단 국지방공 (육군)              │
     │   천마(K-SAM) ~100대, 비호복합 ~160대    │
     │   TPS-880K 국지방공레이더               │
     │   군단·사단급 부대 방호                  │
     │   (1군단~8군단 각 방공여단/대대)          │
     └───────────────────────────────────────┘
         │ 약 50~80km (수도권)                
     ┌───┴───────────────────────────────────┐
     │ ★ 수도권 방공 (최고밀도)                │
     │                                        │
     │  [PAC-3 포대] 수도권 산악지대 다수 배치   │
     │   - 북악산 포대 (서울 직방 방호)          │
     │   - 수도권 외곽 산지 다수               │
     │                                        │
     │  [천궁-I/II 포대] 수도권·기지 방호        │
     │   - 주요 공군기지, 정부시설 인근          │
     │                                        │
     │  [MCRC / KAMD작전센터]                   │
     │   - 오산 공군기지 항공우주작전본부         │
     │   - 1MCRC + KAMD작전센터 공동 위치       │
     │                                        │
     │  [주한미군 PAC-3]                       │
     │   - 오산기지, 캠프 험프리스(평택)         │
     └───────────────────────────────────────┘
         │ 약 100~150km (중부권)               
     ┌───┴───────────────────────────────────┐
     │ ★ 중부권 전략 감시 (조기경보)           │
     │                                        │
     │  [그린파인 Block-B] 2대                  │
     │   - 충남 1대, 충북 1대                   │
     │   - 탐지거리 ~500km, 북한 전역 감시      │
     │                                        │
     │  [2MCRC] 대구 공군기지                   │
     │                                        │
     │  [AN/FPS-117 방공관제레이더]              │
     │   - 전국 산악 고지대 ~10여 대            │
     │   - 울릉도 (E1 모델, 독도 방어)          │
     │   - 백령도 등 전방 도서                  │
     └───────────────────────────────────────┘
         │ 약 200~300km (남부권)               
     ┌───┴───────────────────────────────────┐
     │ ★ 남부권 고고도 방어                    │
     │                                        │
     │  [THAAD] 경북 성주 (해발 680m)           │
     │   - 요격반경 ~200km                     │
     │   - 대구·부산·왜관 등 군수거점 방호       │
     │   - 수도권은 방어권 밖 (평택까지 한계)    │
     │   - AN/TPY-2 레이더 (탐지 ~1000km)       │
     │                                        │
     │  [슈퍼 그린파인 Block-C] 2대 추가 배치    │
     │   - 경상권 1대, 전라권 1대               │
     │   - 탐지거리 ~900km, 해상 SLBM 대응      │
     │                                        │
     │  [L-SAM] 배치 예정 (2027~28)             │
     │   - 주요 전략시설 인근                   │
     │                                        │
     │  [LAMD] 배치 예정 (2030~33)              │
     │   - 수도권 집중 배치 예상                │
     └───────────────────────────────────────┘
```

### 8.2 레이더 커버리지 개략 분석

```
탐지고도
 150km ┤ ···THAAD TPY-2 (성주→북한 전역)···
       │ ···그린파인/슈퍼그린파인 (중부→북한)···
  60km ┤
       │ ···L-SAM MFR (배치지역 주변 310km)···
  40km ┤
       │ ···PAC-3 MPQ-65A (수도권 170km)···
  20km ┤ ···천궁 MFR (기지 주변 100km)···
       │
  15km ┤ ···FPS-117 방공관제 (전국 470km)···
       │
   5km ┤ ···TPS-880K (야전 40km)···
       │ ···천마 탐색레이더 (20km)···
   0km ┼───┬───┬───┬───┬───┬───┬───┬───→ 수평거리
       0  50  100 150 200 300 400 500 km
```

**핵심 감시 공백:**
- FPS-117은 중·고고도(1km+) 전용 → **저고도(1km 미만) 공백** 존재
- TPS-880K가 저고도를 담당하나 **야전 배치(전방군단 위주)** → 후방 도시 저고도 방어 취약
- 그린파인은 탄도탄 전용 → 순항미사일/UAS 탐지 불가

### 8.3 시뮬레이션 배치 모델

실제 위치를 정확히 재현하는 것이 아니라, **방어구역(Defense Zone)** 개념으로 추상화합니다.

#### 배치 추상화 원칙

한반도를 **북→남 축(Y축)** 기준으로 5개 방어구역으로 구분:

```python
DEFENSE_ZONES = {
    "ZONE_A": {  # 전방 (DMZ~30km)
        "name": "Forward Corps Local AD",
        "y_range": (0, 30),        # km from DMZ
        "assets": {
            "CHUNMA": 12,          # 천마 소대 (1군단~8군단 분산)
            "BIHO": 16,            # 비호복합 소대
            "TPS880K": 8,          # 국지방공레이더
        },
        "c2": "ARMY_LOCAL_AD",
        "threats_facing": ["AIRCRAFT", "CRUISE_MISSILE", "UAS", "MLRS"],
    },
    "ZONE_B": {  # 수도권 (30~80km)
        "name": "Capital Area Multi-Layer AD",
        "y_range": (30, 80),
        "assets": {
            "PAC3_MSE": 4,         # PAC-3 포대 (한국군)
            "PAC3_USFK": 2,        # PAC-3 포대 (주한미군)
            "CHEONGUNG2": 6,       # 천궁-II 포대
            "CHEONGUNG1": 4,       # 천궁-I 포대
            "CHUNMA": 4,           # 천마 소대 (수도권 보강)
        },
        "c2": {
            "MCRC": ["CHEONGUNG1"],              # MCRC 통제
            "KAMD_OPS": ["PAC3_MSE", "PAC3_USFK", "CHEONGUNG2"],  # KAMD작전센터 통제
            "ARMY_LOCAL_AD": ["CHUNMA"],          # 육군 독자
        },
        "critical_assets": ["Seoul", "Osan AB", "Pyeongtaek (Camp Humphreys)"],
    },
    "ZONE_C": {  # 중부 (80~180km)
        "name": "Central Strategic Surveillance",
        "y_range": (80, 180),
        "assets": {
            "GREEN_PINE_B": 2,     # 그린파인 Block-B (충남, 충북)
            "FPS117": 4,           # 방공관제레이더
            "CHEONGUNG2": 4,       # 천궁-II
            "PAC3_MSE": 2,         # PAC-3
        },
        "c2": "KAMD_OPS",
    },
    "ZONE_D": {  # 남부 (180~350km)
        "name": "Southern High-Altitude Defense",
        "y_range": (180, 350),
        "assets": {
            "THAAD": 1,            # 성주 1포대
            "SUPER_GREEN_PINE": 2, # 슈퍼그린파인 (경상, 전라)
            "LSAM_ABM": 2,         # L-SAM 대탄도탄 (배치 예정)
            "LSAM_AAM": 2,         # L-SAM 대항공기 (배치 예정)
            "CHEONGUNG2": 4,       # 천궁-II
            "FPS117": 4,           # 방공관제레이더
        },
        "c2": "KAMD_OPS",
        "critical_assets": ["Daegu", "Busan Port", "Waegwan Logistics"],
    },
    "ZONE_E": {  # 지휘소/센서 (위치 특정)
        "name": "C2 Nodes",
        "fixed_positions": {
            "MCRC_1": {"location": "Osan AB", "y": 60},
            "MCRC_2": {"location": "Daegu AB", "y": 250},
            "KAMD_OPS": {"location": "Osan AB", "y": 60},
            "THAAD_RADAR": {"location": "Seongju", "y": 230},
        },
    },
}
```

#### 위협 발사원점 및 경로

```python
THREAT_ORIGINS = {
    "DMZ_FRONT": {       # 휴전선 인근
        "y": -10,        # DMZ 북쪽 10km
        "threat_types": ["MLRS_240", "MLRS_300", "KN25", "CRUISE_MISSILE", "UAS"],
    },
    "PYONGYANG_AREA": {  # 평양 인근
        "y": -180,       # DMZ 북쪽 180km
        "threat_types": ["SRBM_SCUD", "SRBM_KN23", "CRUISE_MISSILE"],
    },
    "NORTH_INTERIOR": {  # 북한 내륙
        "y": -400,       # DMZ 북쪽 400km
        "threat_types": ["MRBM_NODONG", "SRBM_KN23"],
    },
}
```

#### 방어 커버리지 겹침 분석 (시뮬레이션 검증 포인트)

| 위협 경로 | 통과 구역 | 교전 가능 자산 | 문제점 (Linear) |
|---|---|---|---|
| 평양→서울 SRBM | D→C→B | THAAD→L-SAM→PAC-3→천궁-II | 다층 요격 4회 기회 (이상적) |
| DMZ→수도권 KN-25 방사포 | A→B | PAC-3, 천궁-II, (LAMD) | PAC-3가 방사포에 소모 위험 |
| 평양→서울 CM (서해 우회) | 서해→B | 천궁-I, 천마 | MCRC가 탐지해도 KAMD와 미연동 |
| 평양→부산 SRBM | D | THAAD, L-SAM | 성주 THAAD만으로 방어 |
| DMZ→전방 항공기 | A | 천마, 비호, KF-16 | 육군 독자 대응, 천궁 미참여 |

### 8.4 시뮬레이션 지형 모델 구현 방안

현재 시뮬레이션은 2D 평면 좌표를 사용합니다. 한반도 방공을 반영하기 위해:

1. **Y축 = DMZ로부터의 남쪽 거리** (0km = DMZ, 350km ≈ 부산)
2. **X축 = 동서 폭** (0km = 서해안, 200km = 동해안)
3. **Z축 = 고도** (기존 altitude 모델 활용)

config.py에 각 방어자산의 position을 (x, y) 좌표로 지정하고, 위협은 Y<0 영역에서 발사되어 Y>0 영역(남한)으로 진입하는 구조로 설계합니다.

```python
# 시뮬레이션 좌표계 정의
SIMULATION_MAP = {
    "x_range": (0, 200),    # km (서해~동해)
    "y_range": (-400, 350),  # km (NK interior ~ Busan)
    "dmz_y": 0,              # DMZ 위치
    "seoul_y": 50,           # Seoul (50km south of DMZ)
    "osan_y": 60,            # Osan AB
    "daejeon_y": 150,        # Daejeon
    "seongju_y": 230,        # Seongju (THAAD)
    "daegu_y": 250,          # Daegu
    "busan_y": 330,          # Busan
}
```

이 좌표계를 사용하면 각 방어자산의 커버리지 겹침, 위협 경로별 교전 기회 수, C2 간 정보 전달 지연 등을 공간적으로 분석할 수 있습니다.
