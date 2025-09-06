import mss
import mss.tools
import numpy as np
from modelscope.utils.nlp.space import scores
from paddleocr import PaddleOCR
from PIL import Image
from googletrans import Translator
import cv2
import tkinter as tk

from PyQt5 import QtWidgets, QtCore, QtGui, QtTest
import sys
from utils import *
from overlay_mani import SubtitleOverlay
import time

import sys, queue, multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor

global ocr
ocr = None

def init_ocr():
    global ocr
    if ocr is None:
        ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False)


def run_ocr(args):
    global ocr
    img, offset = args
    result = ocr.predict(img)[0]
    texts = result['rec_texts']
    scores = result['rec_scores']
    boxes = [[b[0], b[1]+offset, b[2], b[3]+offset] for b in result['rec_boxes']]
    texts_output = [texts[i] for i in range(len(texts)) if scores[i] > 0.8 and len(texts[i]) > 1]
    boxes = [boxes[i] for i in range(len(boxes)) if scores[i] > 0.8 and len(texts[i]) > 1]
    areas = [(b[2] - b[0]) * (b[3] - b[1]) for b in boxes]
    assert len(areas) == len(texts_output) and len(areas) == len(boxes)
    return texts_output, boxes, areas


class OCRProcess(mp.Process):
    def __init__(self, in_q, out_q, length_threshold=5, score_threshold=0.6):
        super().__init__()
        self.in_q = in_q
        self.out_q = out_q
        self.length_threshold = length_threshold
        self.score_threshold = score_threshold
        self.pic_similarity_threshold = 0.1
        self.last_text_img = []
        self.last_text_text = []
        self.last_text_box = []

    def run(self):
        # global ocr
        n_strip = 3

        with ProcessPoolExecutor(max_workers=n_strip, initializer=init_ocr) as executor:
            while True:
                data = self.in_q.get()
                if data is None:   # 退出信号
                    break

                h, w = data.shape[:2]

                texts, boxes, areas = [], [], []

                futures = []
                for i in range( n_strip):
                    up = i * h // (n_strip + 1)
                    down = i * h // (n_strip + 1) + 2 * h // (n_strip + 1)
                    futures.append(executor.submit(run_ocr, (data[up:down, :], up)))

                for f in futures:
                    t, b, s = f.result()
                    texts += t
                    boxes += b
                    areas += s

                print(texts, boxes)
                if len(texts):
                    self.out_q.put((texts, boxes, areas, h, w))


class TranslatorWorker(QtCore.QThread):
    resultReady = QtCore.pyqtSignal(list, list, int, int)  # boxes, translations, h, w

    def __init__(self, q, dest='zh-CN'):
        super().__init__()
        self.q = q
        self.translator = Translator()
        self.running = True
        self.dest = dest
        self.cache = {'':''} # {'a':'', 'b':'yyy'}
        self.sep = '\n\n'

    def run(self):
        while self.running:
            if not self.q.empty():
                texts, boxes, areas, h, w = self.q.get()
                boxes, texts = remove_rep(boxes, texts, areas)
                # print(texts, boxes, h, w)
                # 批量翻译 + 缓存
                translations = []
                batch = ''
                batch_original = []
                for t in texts:
                    if t in self.cache and self.cache[t] != '**UNKNOWN**':
                        pass
                    else:
                        batch += t + self.sep
                        batch_original.append(t)
                        self.cache[t] = '**UNKNOWN**'
                print(batch)
                if len(batch) > 0:
                    tr = self.translator.translate(batch, dest=self.dest).text
                    # print(batch, tr)
                    tr = tr.split(self.sep) # ['aaa', 'bbb', '']

                    for i, txt in enumerate(batch_original):
                        self.cache[txt] = tr[i] if i < len(tr) else '**UNKNOWN**'

                for t in texts:
                    translations.append(self.cache[t])

                self.resultReady.emit(boxes, translations, h, w)

            else:
                self.msleep(500)  # 没任务就休息


def push_frame_quartz():
    global last_frame
    global window_id
    np_window, _, _, _, _ = capture_window(window_id)
    np_window, _ = resize_image(np_window, max_size=800)

    if last_frame is not None and mse(np_window, last_frame) < 0.1:
        return
    last_frame = np_window
    while True:
        try:
            in_q.get_nowait()  # 非阻塞方式获取并移除队列中的元素
        except queue.Empty:  # 当队列为空时，捕获异常并退出循环
            break
    in_q.put(np_window)


def test_window_shot(id):
    _, x, y, w, h = capture_window(id)
    return x, y, w, h

if __name__ == "__main__":

    # TODO:
    #  replace Googletranslate with offline translation model
    #       https://github.com/argosopentech/argos-translate?tab=readme-ov-file
    #       or other like NMT based

    window_id = 70
    screen_x, screen_y = 1920, 1080
    offset_x, offset_y, w, h = test_window_shot(window_id)

    app = QtWidgets.QApplication(sys.argv)
    overlay = SubtitleOverlay(offset_x=offset_x, offset_y=offset_y)
    overlay.show()


    in_q, out_q = mp.Queue(), mp.Queue()
    ocr_proc = OCRProcess(in_q, out_q)

    trans_thread = TranslatorWorker(out_q, 'zh-CN')

    # 更新 overlay
    trans_thread.resultReady.connect(overlay.update_boxes_and_texts)

    # 启动线程
    ocr_proc.start()
    trans_thread.start()

    last_frame = None

    # ✅ 在主线程里用 QTimer 定时截图
    timer = QtCore.QTimer()

    timer.timeout.connect(push_frame_quartz)
    timer.start(1000)  # 每 1000ms 截一次图

    # 清理
    exit_code = app.exec_()
    trans_thread.running = False
    in_q.put(None)  # 结束 OCR 进程
    ocr_proc.join()
    sys.exit(exit_code)



