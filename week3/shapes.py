import os

import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "TestImages", "shapes.png")
OUT = os.path.join(HERE, "output")
MIN_AREA = 300


def segment(img):
    blur = cv2.GaussianBlur(img, (0, 0), 4)
    lab = cv2.cvtColor(blur, cv2.COLOR_BGR2LAB).astype(np.float32)
    bg = np.median(lab.reshape(-1, 3), axis=0)
    dist = np.linalg.norm(lab - bg, axis=2)
    dist = cv2.normalize(dist, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
    otsu, _ = cv2.threshold(dist, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    _, mask = cv2.threshold(dist, 0.5 * otsu, 255, cv2.THRESH_BINARY)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k)
    return mask


def shape_name(c):
    area = cv2.contourArea(c)
    per = cv2.arcLength(c, True)
    circ = 4 * np.pi * area / per ** 2
    solidity = area / cv2.contourArea(cv2.convexHull(c))
    (_, _), (w, h), _ = cv2.minAreaRect(c)
    fill = area / (w * h)
    n = len(cv2.approxPolyDP(c, 0.04 * per, True))
    if area < 3000:
        return "dot" if circ > 0.7 else "blob"
    if solidity < 0.8:
        return "irregular"
    if fill > 0.9 and n == 4:
        return "rectangle"
    if circ > 0.85:
        return "circle"
    if max(w, h) / min(w, h) > 1.8 and solidity > 0.93:
        return "ellipse"
    if n == 5:
        return "pentagon"
    return f"{n}-gon"


def main():
    os.makedirs(OUT, exist_ok=True)
    img = cv2.imread(IMG)
    mask = segment(img)
    cv2.imwrite(os.path.join(OUT, "shapes_mask.png"), mask)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    vis = img.copy()
    kept = [c for c in cnts if cv2.contourArea(c) >= MIN_AREA]
    for c in kept:
        name = shape_name(c)
        x, y, w, h = cv2.boundingRect(c)
        cv2.drawContours(vis, [c], -1, (0, 0, 0), 5)
        cv2.drawContours(vis, [c], -1, (0, 255, 255), 2)
        cv2.rectangle(vis, (x, y), (x + w, y + h), (255, 255, 255), 1)
        cv2.putText(vis, name, (x, max(y - 6, 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4)
        cv2.putText(vis, name, (x, max(y - 6, 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        print(f"{name:10s} bbox=({x},{y},{w},{h}) area={cv2.contourArea(c):.0f}")
    cv2.imwrite(os.path.join(OUT, "shapes_detected.png"), vis)


if __name__ == "__main__":
    main()
