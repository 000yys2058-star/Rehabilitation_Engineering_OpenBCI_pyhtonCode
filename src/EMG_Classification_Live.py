# -*- coding: utf-8 -*-
"""
실시간 EMG 4-클래스 분류
보드 연결 → 필터 → RMS 추출 → 분류 (1,2,3,4)
"""
import numpy as np
from scipy import signal as sp_signal
from brainflow.board_shim import BoardShim, BrainFlowInputParams
import json
from pathlib import Path
from datetime import datetime
import sys

# ============ 설정 ============
BOARD_ID = 1  # Ganglion
FS = 200
WINDOW_SEC = 0.25
WIN_SAMPLES = int(FS * WINDOW_SEC)
OUTPUT_DIR = Path('../outputs')
OUTPUT_DIR.mkdir(exist_ok=True)

# 필터 파라미터
LOW, HIGH, NOTCH, Q, ORDER = 20, 95, 60, 30, 4

# 분류 임계값 (µV) - 실시간 조정 가능
THRESHOLDS = {
    1: 50,    # 약한 움직임
    2: 100,   # 중간 움직임
    3: 150,   # 강한 움직임
    4: 200    # 매우 강한 움직임
}

# COM 포트 (변경 필요시)
COM_PORT = "COM5"

# ============ 함수 ============
def connect_board():
    params = BrainFlowInputParams()
    params.serial_port = COM_PORT
    board = BoardShim(BOARD_ID, params)
    board.prepare_session()
    return board

def get_filters():
    """Bandpass + Notch 필터"""
    sos_bp = sp_signal.butter(ORDER, [LOW, HIGH], btype='band', fs=FS, output='sos')
    b_notch, a_notch = sp_signal.iirnotch(NOTCH, Q, FS)
    return sos_bp, (b_notch, a_notch)

def apply_filters(signal_data, sos_bp, ba_notch):
    """필터 적용"""
    filtered = sp_signal.sosfiltfilt(sos_bp, signal_data)
    b, a = ba_notch
    filtered = sp_signal.filtfilt(b, a, filtered)
    return filtered

def extract_rms(signal_segment):
    """한 윈도우의 RMS"""
    return np.sqrt(np.mean(signal_segment**2))

def extract_features(emg_data):
    """4채널 RMS 추출"""
    return np.array([extract_rms(ch) for ch in emg_data])

def classify(features, thresholds=THRESHOLDS):
    """
    RMS 크기로 4개 동작 분류 (1,2,3,4)
    4채널 중 가장 큰 RMS가 있는 채널 선택
    그 채널의 RMS로 동작 판정
    """
    max_ch = np.argmax(features)
    rms_max = features[max_ch]

    if rms_max < thresholds[1]:
        return 0, max_ch  # 휴식
    elif rms_max < thresholds[2]:
        return 1, max_ch
    elif rms_max < thresholds[3]:
        return 2, max_ch
    elif rms_max < thresholds[4]:
        return 3, max_ch
    else:
        return 4, max_ch

# ============ 메인 ============
def main():
    board = None
    try:
        print('=' * 70)
        print('실시간 EMG 4-클래스 분류')
        print('=' * 70)
        print(f'보드 ID: {BOARD_ID} (Ganglion)')
        print(f'COM 포트: {COM_PORT}')
        print(f'샘플링 레이트: {FS} Hz')
        print(f'윈도우: {WINDOW_SEC}초 ({WIN_SAMPLES} 샘플)')
        print(f'필터: {LOW}-{HIGH} Hz bandpass + {NOTCH} Hz notch (Q={Q})')
        print(f'분류 임계값 (µV): 1={THRESHOLDS[1]}, 2={THRESHOLDS[2]}, 3={THRESHOLDS[3]}, 4={THRESHOLDS[4]}')
        print('=' * 70)

        print('보드 연결 중...')
        board = connect_board()
        board.start_stream()

        print('필터 준비...')
        sos_bp, ba_notch = get_filters()

        print('수집 시작 (Ctrl+C 로 종료)\n')
        print('동작: 0=휴식, 1=약, 2=중, 3=강, 4=매우강')
        print('-' * 70)

        emg_channels = BoardShim.get_emg_channels(BOARD_ID)
        n_ch = len(emg_channels)

        data_log = []
        action_count = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}

        while True:
            # 새 데이터 읽기
            count = board.get_board_data_count()
            if count < WIN_SAMPLES:
                continue

            raw_data = board.get_board_data(count)
            emg_raw = raw_data[emg_channels, :]

            # 슬라이딩 윈도우로 분류
            for i in range(max(0, emg_raw.shape[1] - WIN_SAMPLES)):
                window = emg_raw[:, i:i + WIN_SAMPLES]

                # 필터 적용
                filtered = apply_filters(window, sos_bp, ba_notch)

                # 특성 추출 (RMS)
                features = extract_features(filtered)

                # 분류
                action, ch = classify(features)
                action_count[action] += 1

                # 콘솔 출력 (동작 발생시만)
                if action > 0:
                    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                    ch_label = f"Ch{ch+1}"
                    rms_str = " | ".join([f"Ch{j+1}={features[j]:.0f}" for j in range(n_ch)])
                    print(f'{timestamp} | 동작: {action} | {ch_label}: {features[ch]:6.1f}µV | {rms_str}')

                    data_log.append({
                        'action': int(action),
                        'channel': int(ch),
                        'rms': float(features[ch]),
                        'all_rms': features.tolist(),
                        'timestamp': timestamp
                    })

    except KeyboardInterrupt:
        print('\n' + '-' * 70)
        print('수집 중지')
        if board:
            board.stop_stream()
            board.release_session()

        # 통계
        print('\n통계:')
        for action in sorted(action_count.keys()):
            label = ['휴식', '약', '중', '강', '매우강'][action]
            print(f'  동작 {action} ({label}): {action_count[action]:5d}회')

        # 결과 저장
        if data_log:
            output_file = OUTPUT_DIR / f'classification_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data_log, f, indent=2, ensure_ascii=False)
            print(f'\n결과 저장: {output_file}')
    except Exception as e:
        print(f'\n에러: {e}')
        import traceback
        traceback.print_exc()
        if board:
            try:
                board.stop_stream()
                board.release_session()
            except:
                pass

if __name__ == '__main__':
    main()
