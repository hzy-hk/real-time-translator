from PyQt5 import QtWidgets, QtCore, QtGui


class SubtitleOverlay(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint |
                            QtCore.Qt.WindowStaysOnTopHint |
                            QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # 屏幕大小
        self.screen = QtWidgets.QApplication.desktop().screenGeometry()
        self.setGeometry(self.screen)
        print('screen size (w, h)', self.screen.width(), self.screen.height())
        # 存放动态生成的 label
        self.active_labels = []

    def iou(self, boxA, boxB):
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        interArea = max(0, xB - xA) * max(0, yB - yA)
        boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
        boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
        iou_val = interArea / float(boxAArea + boxBArea - interArea + 1e-5)
        return iou_val

    def update_boxes_and_texts(self, boxes, text, img_h, img_w):
        """更新字幕文字"""

        new_active = []
        for box, txt in zip(boxes, text):
            x1, y1, x2, y2 = box
            x1, x2 = int(x1 / img_w * self.screen.width()), int(x2 / img_w * self.screen.width())
            y1, y2 = int(y1 / img_h * self.screen.height()), int(y2 / img_h * self.screen.height())

            matched = None
            for old_box, old_txt, lbl in self.active_labels:
                if txt == old_txt and self.iou(box, old_box) > 0.5:
                    matched = (old_box, old_txt, lbl)
                    # 更新位置（避免抖动）
                    lbl.setGeometry(x1, y1, x2 - x1, y2 - y1)
                    new_active.append((box, txt, lbl))
                    break

            if matched is None: # new a label
                w, h = x2 - x1, y2 - y1

                label = QtWidgets.QLabel(txt, self)
                label.setStyleSheet("color: white; background-color: rgba(0,0,0,150); font-size: 18px;")
                label.setAlignment(QtCore.Qt.AlignCenter)
                label.setGeometry(int(x1), int(y1), int(w), int(h))
                label.setWordWrap(True)
                label.show()
                new_active.append((box, txt, label))

        for old_box, old_txt, lbl in self.active_labels:
            if not any(lbl is l for _, _, l in new_active):
                lbl.deleteLater()

        self.active_labels = new_active


