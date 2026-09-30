import os

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "TestImages", "objects.jpg")
OUT = os.path.join(HERE, "output")

COLORS = {
    "cone": [((15, 150, 130), (35, 255, 255))],
    "cube": [((105, 90, 60), (140, 255, 255))],
    "ring": [((0, 120, 120), (10, 255, 255)), ((170, 120, 120), (179, 255, 255))],
}
BOX_BGR = {"cone": (0, 215, 255), "cube": (255, 0, 130), "ring": (0, 90, 255)}
MIN_AREA = 3000


def color_mask(hsv, ranges):
    mask = np.zeros(hsv.shape[:2], np.uint8)
    for lo, hi in ranges:
        mask |= cv2.inRange(hsv, np.array(lo), np.array(hi))
    return mask


def clean(mask, close=9, open_=5):
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close, close)))
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_, open_)))


def fill_holes(mask):
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    out = np.zeros_like(mask)
    cv2.drawContours(out, cnts, -1, 255, cv2.FILLED)
    return out


def split_touching(mask):
    dist = cv2.distanceTransform(mask, cv2.DIST_L2, 5)
    cores = (dist > 0.6 * dist.max()).astype(np.uint8)
    n, core_labels = cv2.connectedComponents(cores)
    dists = np.stack([cv2.distanceTransform((core_labels != k).astype(np.uint8), cv2.DIST_L2, 5)
                      for k in range(1, n)])
    nearest = dists.argmin(axis=0)
    return [((nearest == k) & (mask > 0)).astype(np.uint8) * 255 for k in range(n - 1)]


def find_objects(img):
    hsv = cv2.cvtColor(cv2.GaussianBlur(img, (0, 0), 2), cv2.COLOR_BGR2HSV)
    found = []
    for cls, ranges in COLORS.items():
        mask = clean(color_mask(hsv, ranges))
        parts = split_touching(fill_holes(mask)) if cls == "cube" else [mask]
        for part in parts:
            cnts, hier = cv2.findContours(part, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
            if hier is None:
                continue
            for i, c in enumerate(cnts):
                if hier[0][i][3] != -1 or cv2.contourArea(c) < MIN_AREA:
                    continue
                has_hole = any(hier[0][j][3] == i and cv2.contourArea(cnts[j]) > 0.15 * cv2.contourArea(c)
                               for j in range(len(cnts)))
                found.append(dict(color_class=cls, contour=c, has_hole=has_hole))
    return found


def classify(obj):
    c = obj["contour"]
    area = cv2.contourArea(c)
    hull = cv2.convexHull(c)
    solidity = area / cv2.contourArea(hull)
    (_, _), (w, h), _ = cv2.minAreaRect(c)
    obj["solidity"] = solidity
    obj["aspect"] = max(w, h) / max(min(w, h), 1)
    label = obj["color_class"]
    if obj["has_hole"] and label != "ring":
        label += "?"
    if label == "ring" and not obj["has_hole"]:
        label = "ring?"
    obj["label"] = label
    return obj


def main():
    os.makedirs(OUT, exist_ok=True)
    img = cv2.imread(IMG)
    objs = [classify(o) for o in find_objects(img)]
    vis = img.copy()
    for o in objs:
        col = BOX_BGR[o["color_class"]]
        x, y, w, h = cv2.boundingRect(o["contour"])
        cv2.drawContours(vis, [o["contour"]], -1, (0, 0, 0), 5)
        cv2.drawContours(vis, [o["contour"]], -1, col, 3)
        cv2.rectangle(vis, (x, y), (x + w, y + h), col, 2)
        cv2.putText(vis, o["label"], (x, max(y - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 5)
        cv2.putText(vis, o["label"], (x, max(y - 8, 20)), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        print(f'{o["label"]:6s} bbox=({x},{y},{w},{h}) area={cv2.contourArea(o["contour"]):.0f} '
              f'solidity={o["solidity"]:.2f} aspect={o["aspect"]:.2f} hole={o["has_hole"]}')
    cv2.imwrite(os.path.join(OUT, "objects_detected.png"), vis)


if __name__ == "__main__":
    main()
