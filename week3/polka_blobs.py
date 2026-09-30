import os
import sys

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(HERE, "TestImages")
OUT_DIR = os.path.join(HERE, "output")


def dominant_color(img):
    q = (img // 16).reshape(-1, 3)
    keys, counts = np.unique(q, axis=0, return_counts=True)
    key = keys[counts.argmax()]
    mask = np.all(q == key, axis=1)
    return img.reshape(-1, 3)[mask].mean(axis=0)


def local_background(img, ksize=61, scale=0.25):
    small = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    bg = cv2.medianBlur(small, ksize)
    return cv2.resize(bg, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_LINEAR)


def foreground_map(img, bg, gain=4):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB).astype(np.float32)
    bg = np.asarray(bg, dtype=np.uint8)
    if bg.ndim == 1:
        bg = np.full_like(img, bg)
    bg_lab = cv2.cvtColor(bg, cv2.COLOR_BGR2LAB).astype(np.float32)
    dist = np.linalg.norm(lab - bg_lab, axis=2)
    return np.clip(dist * gain, 0, 255).astype(np.uint8)


def make_detector(min_area, max_area, min_circ=0.75, min_inertia=0.5, min_conv=0.8):
    p = cv2.SimpleBlobDetector_Params()
    p.minThreshold, p.maxThreshold, p.thresholdStep = 40, 200, 20
    p.minDistBetweenBlobs = 5
    p.minRepeatability = 2
    p.filterByColor = True
    p.blobColor = 255
    p.filterByArea = True
    p.minArea, p.maxArea = min_area, max_area
    p.filterByCircularity = True
    p.minCircularity = min_circ
    p.filterByInertia = True
    p.minInertiaRatio = min_inertia
    p.filterByConvexity = True
    p.minConvexity = min_conv
    return cv2.SimpleBlobDetector_create(p)


CONFIGS = {
    "polka_dots_1.png": dict(bg=(255, 255, 255), min_area=40, max_area=9000),
    "polka_dots_2.jpg": dict(min_area=150, max_area=30000, blur=9, local_bg=61, gain=2,
                             min_circ=0.65),
    "polka_dots_3.jpg": dict(bg_patch=(180, 590, 20), min_area=20, max_area=9000,
                             blur=3, gain=8, min_circ=0.8),
}


def detect(name, cfg):
    img = cv2.imread(os.path.join(IMG_DIR, name))
    if cfg.get("local_bg"):
        bg = local_background(img, cfg["local_bg"])
    elif cfg.get("bg_patch"):
        x, y, r = cfg["bg_patch"]
        bg = np.median(img[y - r:y + r, x - r:x + r].reshape(-1, 3), axis=0)
    elif cfg.get("bg") is not None:
        bg = cfg["bg"]
    else:
        bg = dominant_color(img)
    work = img
    if cfg.get("blur"):
        work = cv2.GaussianBlur(img, (0, 0), cfg["blur"] / 2)
    fg = foreground_map(work, bg, cfg.get("gain", 4))
    det = make_detector(cfg["min_area"], cfg["max_area"],
                        cfg.get("min_circ", 0.75))
    kps = det.detect(fg)
    return img, fg, kps


def annotate(img, kps):
    vis = img.copy()
    for k in kps:
        c, r = (int(k.pt[0]), int(k.pt[1])), int(k.size / 2)
        cv2.circle(vis, c, r, (0, 0, 0), 4)
        cv2.circle(vis, c, r, (0, 255, 255), 2)
        cv2.circle(vis, c, 2, (0, 0, 255), -1)
    cv2.putText(vis, f"{len(kps)} dots", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1,
                (0, 0, 0), 4)
    cv2.putText(vis, f"{len(kps)} dots", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1,
                (255, 255, 255), 2)
    return vis


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, cfg in CONFIGS.items():
        img, fg, kps = detect(name, cfg)
        stem = os.path.splitext(name)[0]
        cv2.imwrite(os.path.join(OUT_DIR, f"{stem}_blobs.png"), annotate(img, kps))
        cv2.imwrite(os.path.join(OUT_DIR, f"{stem}_fgmap.png"), fg)
        print(f"{name}: {len(kps)} blobs")


if __name__ == "__main__":
    main()
