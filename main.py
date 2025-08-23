import mss
import mss.tools
import numpy as np
from paddleocr import PaddleOCR
from PIL import Image
from googletrans import Translator
import cv2
import tkinter as tk

from PyQt5 import QtWidgets, QtCore, QtGui
import sys
from utils import *
from overlay_mani import SubtitleOverlay

import sys, queue, multiprocessing as mp



class OCRProcess(mp.Process):
    def __init__(self, in_q, out_q, length_threshold=5, score_threshold=0.8):
        super().__init__()
        self.in_q = in_q
        self.out_q = out_q
        self.length_threshold = length_threshold
        self.score_threshold = score_threshold

    def run(self):
        ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False)
        while True:
            data = self.in_q.get()
            if data is None:   # 退出信号
                break
            np_screen, h, w = data
            # print(h, w)
            result = ocr.predict(np_screen.copy())[0]
            texts, boxes = result['rec_texts'], result['rec_boxes']
            scores = result['rec_scores']

            filtered = [(t, s, b) for t, s, b in zip(texts, scores, boxes) if
                        len(t) > self.score_threshold and s > self.score_threshold]
            filtered_texts, filtered_scores, filtered_boxes = zip(*filtered) if filtered else ([], [], [])
            for text, box in zip(filtered_texts, filtered_boxes):
                print(text, box[0], box[1], box[2], box[3])

            self.out_q.put((filtered_texts, list(filtered_boxes), h, w))


class TranslatorWorker(QtCore.QThread):
    resultReady = QtCore.pyqtSignal(list, list, int, int)  # boxes, translations, h, w

    def __init__(self, q, dest='en'):
        super().__init__()
        self.q = q
        self.translator = Translator()
        self.running = True
        self.dest = dest
        self.cache = {} # {'a':'', 'b':'yyy'}
        self.sep = '\n\n'

    def run(self):
        while self.running:
            if not self.q.empty():
                texts, boxes, h, w = self.q.get()
                # 批量翻译 + 缓存
                translations = []
                batch = ''
                batch_original = []
                for t in texts:
                    if t in self.cache:
                        pass
                    else:
                        batch += t + self.sep
                        batch_original.append(t)
                        self.cache[t] = '**UNKNOWN**'

                if len(batch) > 0:
                    tr = self.translator.translate(batch, dest=self.dest).text
                    # print(batch, tr)
                    tr = tr.split(self.sep) # ['aaa', 'bbb', '']

                    for i, txt in enumerate(batch_original):
                        self.cache[txt] = tr[i]

                for t in texts:
                    translations.append(self.cache[t])

                self.resultReady.emit(boxes, translations, h, w)

            else:
                self.msleep(500)  # 没任务就休息


def put_latest(q, item, max_keep=1):
    """往队列里放数据，确保只保留最近 max_keep 个"""
    try:
        while True:
            if q.qsize() <= max_keep - 1:  # Windows/Linux 可用
                break
            q.get_nowait()
    except (NotImplementedError, AttributeError):
        # macOS 下 qsize() 不可用 → 直接清空到 max_keep-1
        try:
            while True:
                q.get_nowait()
        except queue.Empty:
            pass
    q.put(item)


def push_frame():
    # 截屏前 → overlay透明化
    overlay.setWindowOpacity(0.0)

    np_screen = capture_screen()

    # 截屏后 → overlay恢复可见
    overlay.setWindowOpacity(1.0)
    np_screen = resize_image(np_screen, max_size=1080)
    h, w = np_screen.shape[:2]
    screen_ocr = np_screen.copy()
    put_latest(in_q, (screen_ocr, h, w), max_keep=2)  # 交给 OCR 线程处理


if __name__ == "__main__":

    app = QtWidgets.QApplication(sys.argv)
    overlay = SubtitleOverlay()
    overlay.show()

    in_q, out_q = mp.Queue(), mp.Queue()
    ocr_proc = OCRProcess(in_q, out_q)
    trans_thread = TranslatorWorker(out_q, 'en')

    # 更新 overlay
    trans_thread.resultReady.connect(overlay.update_boxes_and_texts)

    # 启动线程
    ocr_proc.start()
    trans_thread.start()

    # ✅ 在主线程里用 QTimer 定时截图
    timer = QtCore.QTimer()

    timer.timeout.connect(push_frame)
    timer.start(1000)  # 每 1000ms 截一次图

    # 清理
    exit_code = app.exec_()

    trans_thread.running = False
    in_q.put(None)  # 结束 OCR 进程
    ocr_proc.join()
    sys.exit(exit_code)




"""
page_index
doc_preprocessor_res
dt_polys
model_settings
text_det_params
text_type
text_rec_score_thresh
return_word_box
rec_texts
rec_scores
rec_polys
vis_fonts
textline_orientation_angles
rec_boxes
"""

