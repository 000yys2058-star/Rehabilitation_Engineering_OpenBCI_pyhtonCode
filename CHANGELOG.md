# 변경 이력 (CHANGELOG · 패치노트)

OpenBCI Ganglion **근전도(EMG) 실습** 프로젝트의 개발 기록입니다.
다른 세션·다른 PC에서도 지금까지의 맥락을 파악할 수 있도록,
"무엇을 왜 바꿨는지"와 **실측으로 확인한 사실**을 함께 남깁니다.

- GitHub: https://github.com/000yys2058-star/Rehabilitation_Engineering_OpenBCI_pyhtonCode
- 상세 기술 노트: [`.claude/openbci-bled112.md`](.claude/openbci-bled112.md)
- 세션 작업 로그: [`.claude/session-log_2026-07-25_classification.md`](.claude/session-log_2026-07-25_classification.md)
  — 분류 노트북·키보드 출력 구현 과정과 실패 기록
- 대상: UNIST 재활재생개론 수업, OpenBCI Ganglion + BLED112 동글

> 형식: 최신이 위. 각 항목은 날짜 · 요약 · 배경/근거 순.

---

## 프로젝트 핵심 사실 (한눈에)

새 세션에서 이것만 알면 됩니다. **바꾸기 전에 반드시 확인할 것.**

| 항목 | 값 · 이유 |
| --- | --- |
| **보드** | OpenBCI **Ganglion** (Cyton 아님) — 4채널 · 200 Hz |
| **연결** | **BLED112 USB 동글** → COM3 (내장 BLE 안 씀, 변수 최소화) |
| **라이브러리** | `brainflow==5.20.0` **고정**. 5.21+ 는 BLED112 지원이 죽어 연결 불가 |
| **다루는 신호** | **EMG 전용**. 뇌파(EEG) 안 함. 대역통과 20–95 Hz(1차시)/30–95 Hz(2차시) |
| **나이퀴스트** | 200 Hz 샘플링 → **100 Hz 까지만** 표현. EMG 위쪽 절반은 못 봄 |
| **에디터** | 사용자는 **VS Code** 사용 (브라우저 Jupyter 아님) |
| **파일 편집 주의** | .ipynb 를 스크립트로 고쳐도, VS Code 에서 열려 있으면 저장 시 덮어써짐 → 닫았다 다시 열 것 |
| **데이터 읽기** | 실시간 루프는 **`get_current_board_data(N)`**. `get_board_data()` 는 버퍼를 통째로 비우므로 루프에 쓰면 폭주 |
| **COM 포트** | 새 PC 기준 **COM5** (BLED112, VID:PID 2458:0001). COM3/COM4 는 내장 Bluetooth SPP |

---

## [분류 테스트 노트북 · 키보드 출력] 2026-07-25 ~ 26

### 새 파일: `src/Classification_convertSample.ipynb`

2차시 노트북의 **축약 테스트판**. 설명 없이 동작만: 연결 → 캘리브레이션 →
학습 → 실시간 판정 → **판정 결과를 키보드 입력으로 출력**.
동작은 4개이며 라벨을 `1·2·3·4` 로 둔다(`GESTURES` 에서 이름만 변경).

| 셀 | 내용 |
| --- | --- |
| 0 | 설정 + 필터 설계 + `extract_features` |
| 1 | 보드 연결 (3회 재시도) |
| 2 | 신호 확인 10초 |
| 3 | 캘리브레이션 (동작당 40회, 진행바) |
| 4 | Random Forest 학습 + 혼동행렬 |
| 5 | 실시간 판정 (다수결 + 확률 막대 + 이력 그래프) |
| 6-A | 키보드 출력 단독 테스트 |
| 6 | 판정 → 키보드 입력 |
| 7 | 연결 해제 |

### 판정 결과 → 키보드 입력 (신규)

0.5초마다 안정 판정을 내고 그 숫자를 **`SendInput` 으로 주입**한다.
메모장을 포커스에 두면 거기에 `1`/`2`/`3`/`4` 가 찍힌다.

- `ctypes` 로 user32 직접 호출 (추가 설치 없음)
- **스캔코드** 사용 (`1`=0x02 … `4`=0x05) → 한/영 상태와 무관하게 숫자 입력
- 안전장치: **ESC 즉시 중단**, `DURATION_SEC` 자동 종료,
  **포커스 창 제목을 매 프레임 표시**(키가 어디로 가는지 눈으로 확인)
- 옵션: `ONLY_ON_CHANGE`(판정 변화 시에만), `SEND_NEWLINE`, `KEY_MODE`(scan/vk)

#### `SendInput` 이 조용히 실패한 원인 — `INPUT` 구조체 크기 (실측)

`GetLastError=87 (ERROR_INVALID_PARAMETER)` 로 전부 실패했다.
원인은 **union 크기를 `KEYBDINPUT` 기준으로 잡은 것**.

`INPUT` 의 union 은 `MOUSEINPUT`/`KEYBDINPUT`/`HARDWAREINPUT` 중 **최대 크기**다.

| 구조체 | x64 크기 |
| --- | --- |
| `MOUSEINPUT` | **32** ← 최대 |
| `KEYBDINPUT` | 24 |
| union | 32 |
| **`INPUT`** | 4(type) + 4(패딩) + 32 = **40** |

`KEYBDINPUT` + `padding[24]` 로 잡으면 `sizeof(INPUT)` 이 **32** 가 되고,
이 값이 `cbSize` 로 들어가 Windows 가 거부한다. 세 구조체를 모두 정의해 해결.
셀 상단에서 `sizeof(INPUT)` 을 출력해 40 인지 자가 검증한다.

> 부수적으로 `SendInput.argtypes` 도 지정했다. 미지정이면 64비트에서
> 포인터가 잘려 역시 실패한다. `restype` 을 받아 **반환값을 반드시 검사**할 것 —
> 검사하지 않으면 "전송됨" 으로 보이지만 실제로는 아무것도 안 나간다.

### 실시간 루프 폭주 — `get_board_data` vs `get_current_board_data`

첫 구현이 초당 수천 줄을 쏟아내며 판정이 무의미했다.

| 함수 | 동작 |
| --- | --- |
| `get_board_data(n)` | 버퍼에서 **꺼내고 지운다**. 쌓인 만큼 전부 나옴 |
| `get_current_board_data(n)` | **최근 n 샘플만 훔쳐본다**. 버퍼 유지 |

루프에서 `get_board_data(count)` 로 받아 다시 슬라이딩 윈도우를 돌리니
같은 구간을 수백 번 재분류했다. → 2차시 원본대로
`get_current_board_data(WINDOW_SAMPLES)` + `sleep(0.25)` 로 **프레임당 1회** 판정.

### 특징·분류기를 2차시 원본에 맞춤

임의로 RMS + 최근접 centroid 로 짰다가 되돌렸다. 원본 기준:

| | 잘못 짠 것 | 원본(정답) |
| --- | --- | --- |
| 특징 | RMS | **Hilbert 포락선 평균** |
| 분류기 | centroid 최근접 | **RandomForest** + `predict_proba` |
| 대역통과 | 20–95 Hz | **30–95 Hz** (손동작용) |
| 판정 | 매 샘플 raw | **최근 5회 다수결** |

**교훈**: "참조해서 만들라"는 요청은 원본을 먼저 읽으라는 뜻이다.
읽지 않고 새로 설계해 여러 번 되돌렸다.

### 그 밖에 고친 것

- **한글 폰트** — `font_manager` 로 `Malgun Gothic` 탐색·설정.
  미설정 시 `Glyph ... missing from current font` 경고가 매 프레임 쏟아짐
- **진행 표시** — `\r` 만으로는 Jupyter 에서 갱신이 안 되고 줄이 쌓임.
  `IPython.display.clear_output(wait=True)` 로 교체
- **`input()` 제거** — Jupyter 에서 입력 대기가 걸려 다음 동작으로 안 넘어감.
  → 3·2·1 카운트다운 자동 진행
- **`iirnotch(..., output='sos')` 없음** — `iirnotch` 는 `(b, a)` 만 반환.
  대역통과는 sos(`sosfiltfilt`), 노치는 ba(`filtfilt`) 로 분리

### 1차시 노트북(`Ganglion_Tutorial_V.1.1.ipynb`) 수정 — 같은 기간

- **3단계 Data plot**: 스펙트로그램 → **원본 파형 + 단측 진폭 스펙트럼(FFT)**
  - MATLAB `fft` 예제와 동일한 계산(`P1[1:-1] *= 2`), `np.fft.rfft` 사용
  - 60 Hz 기준선 + EMG 대역(20–95 Hz) 음영, 60 Hz 대비 배율 표
  - 200 Hz 샘플링이라 가로축은 **100 Hz 까지**
- **1-5-C 전극 비교**: `EMG_CHANNELS` 미정의 시 `BoardShim.get_*()` 로 자동 보충
  (1-4 를 건너뛰어도 실행되도록)
- **NumPy 버전 호환**: `np.trapz`(1.x) ↔ `np.trapezoid`(2.0+) 이름 변경 대응
  → `getattr(np, 'trapezoid', None) or getattr(np, 'trapz')`
- **4-2 필터 전후 FFT 비교** 절 추가 — 60 Hz 진폭 감소율 표(70%+ 면 성공)
- **RMS 플롯**: 0.25초 비겹침 창(점 40개) → **슬라이딩 윈도우**(샘플마다 계산)

---

## [1차시·2차시 완성] 2026-07-24

### 새 기능

- **1차시 노트북** `Ganglion_Tutorial.ipynb` — EMG 신호 수집·처리
  - 연결 → 임피던스 점검 → 필터 → RMS → 주파수(MDF/MNF) → 저장
- **2차시 노트북** `Ganglion_Tutorial_2_Classification.ipynb` — 실시간 손동작 분류
  - EMG → 특징추출 → 캘리브레이션 → Random Forest → joblib 저장 → 실시간 판정(다수결)
- **안전 연결 게이트** — 강의실 다중 보드 문제 해결 (아래 상세)
- **전극 임피던스 점검(5-B)** + **전극 종류 비교 실험(5-C)**
- **COM 포트 점유 자동 진단** — 어느 커널이 잡고 있는지 찾아 표시

### 주요 결정과 근거

#### EMG 전용으로 범위 확정 (`9d36dcc`)

이 프로젝트가 다루는 정보는 **EMG 에만 국한**한다 (사용자 확정).
1차시가 EEG 기준(1–45 Hz, Alpha/Beta 대역)으로 작성돼 있어 전면 수정.

| | 이전(EEG) | 현재(EMG) |
| --- | --- | --- |
| 대역통과 | 1–45 Hz | **20–95 Hz** (움직임 잡음 제거 + 나이퀴스트 회피) |
| 주파수 지표 | Delta/Theta/Alpha/Beta/Gamma | **MDF·MNF** (근피로 지표) |
| 전극 | 두피 | **팔뚝 근육** |

> `get_eeg_channels()` 는 BrainFlow 가 생체전위 채널을 통칭하는 이름.
> API 호출은 그대로 두되 지역 변수는 `EMG_CHANNELS` 로 쓰고 주석을 붙임.
> 검증: 합성 EMG 로 RMS 휴식 5.3→수축 44.0 µV, MDF 68 Hz(대역 중심) 확인.

#### 전극 임피던스 점검 5-B / 비교 실험 5-C (`c18d9c9`)

전극 접촉 불량이 최대 실패 원인이라, 숫자로 확인하는 단계 추가.

- **단위 환산 확정 (실측)**: `resistance_channels` 원시값 **÷2 = kΩ**
  - 근거: GUI 화면 대조 — 원시 773→386.5 kΩ, 959→479.5 kΩ
  - GUI 소스(`W_GanglionImpedance.class`) 역어셈블로 `adjustedImpedance`·`idiv` 확인
- 명령: `config_board('z')` 시작 / `config_board('Z')` 종료 (EMG 자동 복구)
- 판정: 10 kΩ 미만 좋음 / 50 미만 보통 / 이상 나쁨. 미부착 시 400 kΩ 안팎
- **REF 전극이 나쁘면 전 채널 영향** → 따로 경고
- **5-C**: GUI 엔 임피던스 저장 기능이 없음 → 임피던스+잡음RMS+60Hz비율을
  `outputs/electrode_comparison.csv` 에 누적, 2종류 이상이면 비교 그래프.
  검증(모의): 젤(10kΩ,2.6µV,13%) vs 건전극(300kΩ,14.7µV,56%) 세 지표 동반 악화

#### 연결된 보드 정보 반환 (`34b70c7`)

순차 연결 방식을 쓰기로 함에 따라, 연결 후 어느 보드인지 표시.
- 게이트가 "1대"를 보장하므로 그 보드가 곧 연결된 보드
- 광고명(advertised name = BLE Complete Local Name)·MAC·RSSI 출력
- `CONNECTED_BOARD` 변수 + 1차시 CSV 열 / 2차시 joblib 메타데이터에 기록
- 2차시: 저장 모델을 불러올 때 학습 보드 ≠ 현재 보드면 경고

#### COM 포트 점유 진단 (`5450f2f` + 미커밋 개선)

`SerialException: PermissionError(13)` = 다른 프로세스가 포트 점유.
가장 흔한 원인: **14단계(연결 해제)를 안 하고 닫은 예전 커널.**
- 스캔 셀이 예외를 잡아 원인·해결법 안내, `SAFE_TO_CONNECT=False` 로 연결도 차단
- **[미커밋]** VS Code 대응 + 범인 프로세스 자동 조회 (아래 "진행 중" 참조)

---

## [강의실 다중 보드 문제] 2026-07-24

### 결론: MAC 으로는 보드를 못 고른다. "1대만 켜기"로 해결.

#### mac_address 는 무시된다 (`b5e1596`, `9fbc416`)

BLED112 경로에서 `params.mac_address` 는 **받기만 하고 안 쓴다.**
- **결정적 증거**: 실재하는 **청소기 MAC** 을 요청했더니 Ganglion 에 연결됨
  ```
  [info] search for bc:10:2f:e3:eb:38   ← 청소기 MAC
  [info] detected firmware version 2     ← Ganglion 에 연결, EEG 데이터 수신
  ```
- 존재하지 않는 가짜 MAC 으로도 1.5초 만에 연결됨
- **오판 주의**: 26초 타임아웃 실패는 "MAC 불일치"가 아니라 "보드 못 찾음".
  1.5초 연결=아무거나 붙음 / 26초 실패=보드 상태 문제. 반드시 구분

#### 안전 게이트 채택 (`d8ebce8`)

전략: **고를 수 없다면 고를 여지를 없앤다.**
연결 시점에 광고 중인 Ganglion 이 1대뿐이면 반드시 그 보드에 연결.

- 「내 보드 확인」 셀: 스캔 후 1대면 통과, 2대+/0대면 차단
- 강의실 절차: 모두 OFF → 한 명씩 ON → 확인 → 연결 → 유지
  (연결된 보드는 광고를 멈춰 다음 사람에게 안 잡힘)
- **실증**: 가까운 보드(-61dBm)를 BGAPI로 점유해 광고 차단 → BrainFlow 가
  먼 보드(-73dBm)에 연결됨. "1대면 그 보드" 보장 확인

#### 시도했으나 버린 방법 (`2de9796`→정정, `6d9ff9a`)

- ❌ "로그에서 MAC 추출" — BrainFlow 로그엔 MAC 이 안 찍힘
- ❌ "원치 않는 보드 미리 점유" — BrainFlow 가 포트 열 때 동글을 리셋해 점유가 풀림
- ✅ BGAPI 직접 스캔(MAC·이름·RSSI) 및 `gap_connect_direct` 연결은 **동작 확인**
  (자체 드라이버의 절반. 나머지는 GATT 구독+패킷 디코딩이라 교육용엔 과함)
- 남은 길: `GANGLION_NATIVE_BOARD`(내장 BLE) — 이 PC엔 BLE 없어 미검증

---

## [연결 안정화] 2026-07-23

### brainflow 5.20.0 고정 — 가장 중요한 발견 (`6d9516a`, `cb3f488`)

**최신 brainflow(5.22.2)는 BLED112 연결이 아예 안 된다.**

| brainflow | 결과 |
| --- | --- |
| **5.20.0** | ✅ 연결 성공(2.3초), 200Hz 수집 |
| 5.22.2 | ❌ 0.0초 만에 실패, 스캔조차 안 함 |

- 5.22.2 는 존재하지 않는 포트(COM99)로도 똑같이 에러 13 → 포트를 보지도 않음
- 5.20.0 은 `pkg_resources` 사용 → `setuptools<81` 동반 필요
- **커널 재시작 함정**: DLL 은 한 번 로드되면 파일 교체해도 메모리에선 안 바뀜.
  `importlib.metadata` 는 디스크만 봄 → **`BoardShim.get_version()`** 으로
  실제 로드된 버전 확인. 1단계 셀이 불일치 시 재시작 안내 후 중단

### 노트북 파일 형식 함정 (`c9a53b2`)

nbformat 의 `source` 는 리스트일 수도 문자열일 수도 있음.
문자열을 for 로 돌리면 글자 단위로 쪼개져 파일이 깨짐(크기 2배).
→ `''.join(s) if isinstance(s, list) else s` 로 정규화. 문법검사는 통과하니 주의.

### 기타 초기 수정

- `d502982` brainflow 는 `__version__` 없음 → `importlib.metadata.version()` 사용.
  cp949 콘솔의 µ 기호 깨짐 → `sys.stdout.reconfigure('utf-8')`
- `67eee56` 연결 진단 셀(5-A) 추가 — 실패까지 걸린 시간으로 원인 구분

---

## [프로젝트 시작] 2026-07-23

### 전면 재작성 (`cfc97bd`)

초기 커밋(`c456079`)은 **Cyton 전용 시리얼 드라이버 + 네이티브 BLE(bleak)** 로
Ganglion 에서 동작하지 않았음. 채널·샘플링도 Cyton 기준(8ch/250Hz)으로 오인.

→ OpenBCI GUI v5 도 쓰는 **BrainFlow** 로 전면 재작성.
`BoardIds.GANGLION_BOARD`(BLED112 동글), 4채널·200Hz, 코드에서 사양 조회.
잘못된 Cyton/BLE 코드는 `src/_deprecated_cyton/` 로 이동(삭제 아님, 사유 기록).

**교훈**: 보드 모델을 먼저 확정하고, 채널·샘플링은 `BoardShim.get_*()` 로 조회.
deprecated 경고는 실제 동작 여부와 별개 → 직접 돌려서 확인.

---

## 진행 중 / 다음 세션 할 일

- [ ] **[미커밋] VS Code 포트 점유 안내 재적용** — 지난 세션에서 개선했으나
  사용자의 VS Code 가 열린 채 노트북을 저장해 덮어써짐(옛 브라우저 Jupyter 안내로 롤백됨).
  개선 내용: PowerShell 로 ipykernel/javaw 프로세스를 조회해 PID·시작시각 표시,
  자기 PID 도 표시해 범인 식별. VS Code 기준 해결법(탭 Restart Kernel) 우선 안내.
  → **노트북을 닫은 상태에서 재적용해야 함.**
- [ ] 실제 전극으로 5-C 전극 비교 실험 검증(현재 모의 보드로만 검증)
- [ ] 임피던스 판정 임계값(10/50 kΩ)을 실제 전극 상황에 맞게 조정
- [ ] 2차시 실제 EMG 로 세 손동작이 구분되는지 검증(근육 없이는 불가)
- [ ] **4동작 분류 정확도 개선** — 테스트 시 판정 확신도가 36~76%로 낮고 흔들림.
  전극 위치 재배치 또는 특징 추가(포락선 평균 외 표준편차·최대값) 검토
- [ ] `Classification_convertSample.ipynb` 의 키보드 출력을 정식 노트북에 반영할지 결정
- [ ] `src/EMG_Classification_Live.py` — 노트북판으로 대체됨. 유지할지 삭제할지 결정
- [ ] (선택) 3차시: 분류 결과로 아두이노 로봇 손 제어
  (키보드 출력이 그 전 단계 프로토타입 역할)

---

*이 파일은 커밋 메시지와 실측 기록을 사람이 읽기 좋게 정리한 것입니다.*
*정확한 diff 는 `git log` 를, 세부 기술 근거는 `.claude/openbci-bled112.md` 를 참조하세요.*
