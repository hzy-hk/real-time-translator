import numpy as np
import mss

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
    return resized_img

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

