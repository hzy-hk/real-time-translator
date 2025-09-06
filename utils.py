import numpy as np
import mss

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import Quartz

def plot_image_with_boxes(image, boxes, color="red"):
    """
    Plot image (numpy array) with boxes.
    image: numpy array (H, W, 3)
    boxes: list of (x1, y1, x2, y2)
    """
    fig, ax = plt.subplots(1)
    ax.imshow(image)

    for (x1, y1, x2, y2) in boxes:
        rect = patches.Rectangle((x1, y1), x2 - x1, y2 - y1,
                                 linewidth=2, edgecolor=color, facecolor='none')
        ax.add_patch(rect)

    plt.show()


def mse(a, b):
    return np.mean((a - b) ** 2)


def remove_rep(boxes, texts, scores):
    # NMS
    # Sort boxes by scores in descending order
    order = sorted(range(len(scores)), key=lambda k: scores[k], reverse=True)
    keep_boxes = []
    keep_texts = []
    while order:   # may consider ranking by the area size
        keep_boxes.append(boxes[order[0]])
        keep_texts.append(texts[order[0]])

        unions = [cover(boxes[j], boxes[order[0]]) for j in order[1:]]
        order = order[1:]
        order = [order[i] for i in range(len(order)) if unions[i] == False ]

    return keep_boxes, keep_texts


def cover(boxA, boxB, threshold=0.9):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])
    interArea = max(0, xB - xA) * max(0, yB - yA)

    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    return interArea / min(boxAArea, boxBArea) > threshold

def scaled(x1, y1, x2, y2, h, w, scale):

    x1 = max(int(x1/scale) - 2, 0)
    y1 = max(int(y1/scale) - 2, 0)
    x2 = min(int(x2/scale) + 2, h-1)
    y2 = min(int(y2/scale) + 2, w-1)

    return x1, y1, x2, y2

def resize_image(img, max_size=480):
    """
    使用最近邻插值将图像缩放到最长边不超过 max_size
    输入: img (numpy数组, shape=(H, W, C))
    输出: 缩放后的图像 (numpy数组)
    """
    h, w = img.shape[:2]
    scale = max_size / max(h, w)

    # 如果已经小于 max_size 就不缩放
    if scale >= 1:
        return img

    new_h, new_w = int(h * scale), int(w * scale)

    # 生成新坐标（最近邻）
    row_idx = (np.linspace(0, h - 1, new_h)).astype(int)
    col_idx = (np.linspace(0, w - 1, new_w)).astype(int)

    # 索引采样
    resized_img = img[row_idx[:, None], col_idx, :]
    return resized_img, scale

def capture_screen(filename="screenshot.png"):
    with mss.mss() as sct:
        # 截取整个屏幕
        monitor = sct.monitors[1]  # monitor[0] 是所有屏幕的组合，通常 [1] 是主屏
        sct_img = sct.grab(monitor)
        # print(type(sct_img))
        np_img = np.array(sct_img)
        np_img = np_img[:, :, :3][:, :, ::-1]  # 先取前三个通道 BGR，再反转成 RGB
        # 保存成文件
        # mss.tools.to_png(sct_img.rgb, sct_img.size, output=filename)
        # print(f"Screenshot saved as {filename}")
        return np_img


def merge_lines(rec_texts, boxes, y_threshold=30):
    """
    合并 OCR 结果中属于同一行的文字
    rec_texts: list[str]，OCR 识别文字
    boxes: list[list[points]]，每个文字的框
    """
    lines = []
    for text, box in zip(rec_texts, boxes):
        y_min = np.min(box)  # 每个文本框的最小 y 值
        lines.append((y_min, text))

    # 按 y 坐标排序（上到下）
    lines.sort(key=lambda x: x[0])

    merged = []
    current_y = None
    buffer = []
    for y, text in lines:
        if current_y is None:
            current_y = y
            buffer.append(text)
        elif abs(y - current_y) < y_threshold:  # 同一行
            buffer.append(text)
        else:
            merged.append(" ".join(buffer))
            buffer = [text]
            current_y = y
    if buffer:
        merged.append(" ".join(buffer))

    return merged


def capture_window(window_id):
    # TBD: currently hardcode the position of the window to X = 0, Y = 25

    bounds = Quartz.CGWindowListCreateDescriptionFromArray([window_id])
    if not bounds:
        raise ValueError("Window not found or not visible")

    """返回窗口的 bounds (x, y, w, h)"""
    options = Quartz.kCGWindowListOptionIncludingWindow
    info = Quartz.CGWindowListCopyWindowInfo(options, window_id)
    if not info:
        raise ValueError("Window not found or not visible")
    bounds = info[0]['kCGWindowBounds']
    x, y, w, h = int(bounds['X']), int(bounds['Y']), int(bounds['Width']), int(bounds['Height'])

    # PID = 1192
    # Name =【心跳回忆GS4 / CC字幕_哔哩哔哩bilibili
    # Bounds = {
    # Height = 1055;
    # Width = 1920;
    # X = 0;
    # Y = 25;
    # } ID = 70

    rect = Quartz.CGRectMake(x, y, w, h)
    image = Quartz.CGWindowListCreateImage(
        rect,
        Quartz.kCGWindowListOptionIncludingWindow,
        window_id,
        Quartz.kCGWindowImageDefault
    )

    width = Quartz.CGImageGetWidth(image)
    height = Quartz.CGImageGetHeight(image)
    # print(width, height)
    # 转 numpy 数组
    bytes_per_row = Quartz.CGImageGetBytesPerRow(image)
    data_provider = Quartz.CGImageGetDataProvider(image)
    data = Quartz.CGDataProviderCopyData(data_provider)
    arr = np.frombuffer(data, dtype=np.uint8)
    # print(arr.shape)
    arr = arr.reshape((height, bytes_per_row // 4, 4))
    arr = arr[:, :width, :3]  # 只取 RGB
    # plt.imshow(arr)
    # plt.show()

    return arr, x, y, w, h
