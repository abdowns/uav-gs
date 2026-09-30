import os

import cv2
import numpy as np

import polka_blobs as pb


def _gauss(img, sigma):
    return cv2.GaussianBlur(img, (0, 0), sigma)


def scale_space(img, sigmas, method):
    img = img.astype(np.float32) / 255.0
    layers = []
    if method == "log":
        for s in sigmas:
            layers.append(-(s ** 2) * cv2.Laplacian(_gauss(img, s), cv2.CV_32F))
    elif method == "dog":
        blur_sigmas = list(sigmas) + [sigmas[-1] * sigmas[-1] / sigmas[-2]]
        blurred = [_gauss(img, s) for s in blur_sigmas]
        for i, s in enumerate(sigmas):
            k = blur_sigmas[i + 1] / s
            layers.append((blurred[i] - blurred[i + 1]) / (k - 1))
    elif method == "doh":
        for s in sigmas:
            g = _gauss(img, s)
            ixx = cv2.Sobel(g, cv2.CV_32F, 2, 0)
            iyy = cv2.Sobel(g, cv2.CV_32F, 0, 2)
            ixy = cv2.Sobel(g, cv2.CV_32F, 1, 1)
            det = (s ** 4) * (ixx * iyy - ixy ** 2)
            det[(ixx + iyy) > 0] = 0
            layers.append(det)
    else:
        raise ValueError(method)
    return np.stack(layers)


def local_maxima_3d(stack, threshold):
    kernel = np.ones((3, 3), np.uint8)
    pooled = np.stack([cv2.dilate(l, kernel) for l in stack])
    over_scale = pooled.copy()
    over_scale[1:] = np.maximum(over_scale[1:], pooled[:-1])
    over_scale[:-1] = np.maximum(over_scale[:-1], pooled[1:])
    mask = (stack >= over_scale) & (stack > threshold)
    return np.argwhere(mask)


def prune_overlaps(blobs):
    blobs = sorted(blobs, key=lambda b: -b[3])
    kept = []
    for x, y, r, s in blobs:
        if all(np.hypot(x - x2, y - y2) >= max(r, r2) for x2, y2, r2, _ in kept):
            kept.append((x, y, r, s))
    return kept


THRESHOLDS = {"log": 0.5, "dog": 0.5, "doh": 0.3}


def detect_scale_space(fg, method, min_sigma=3, max_sigma=40, n=24):
    threshold = THRESHOLDS[method]
    sigmas = np.geomspace(min_sigma, max_sigma, n)
    stack = scale_space(fg, sigmas, method)
    stack = stack / max(stack.max(), 1e-9)
    pts = local_maxima_3d(stack, threshold)
    blobs = [(float(x), float(y), float(sigmas[k] * np.sqrt(2)), float(stack[k, y, x]))
             for k, y, x in pts]
    return prune_overlaps(blobs)


def binarize(fg, thresh=60):
    return cv2.threshold(fg, thresh, 255, cv2.THRESH_BINARY)[1]


def detect_contours(fg, min_area=40, max_area=20000, min_circ=0.75, thresh=60):
    bw = binarize(fg, thresh)
    bw = cv2.morphologyEx(bw, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    cnts, _ = cv2.findContours(bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    blobs = []
    for c in cnts:
        area = cv2.contourArea(c)
        per = cv2.arcLength(c, True)
        if not (min_area <= area <= max_area) or per == 0:
            continue
        circ = 4 * np.pi * area / per ** 2
        if circ < min_circ:
            continue
        (x, y), r = cv2.minEnclosingCircle(c)
        blobs.append((x, y, r, circ))
    return blobs


PARAMS = {
    "polka_dots_1.png": dict(min_sigma=3, max_sigma=32, thresh=60),
    "polka_dots_2.jpg": dict(min_sigma=10, max_sigma=60, thresh=85),
    "polka_dots_3.jpg": dict(min_sigma=2, max_sigma=32, thresh=60),
}


def draw(img, blobs, label, color):
    vis = img.copy()
    for x, y, r, _ in blobs:
        cv2.circle(vis, (int(x), int(y)), int(r), (0, 0, 0), 4)
        cv2.circle(vis, (int(x), int(y)), int(r), color, 2)
    text = f"{label}: {len(blobs)}"
    cv2.putText(vis, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 4)
    cv2.putText(vis, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    return vis


def main():
    os.makedirs(pb.OUT_DIR, exist_ok=True)
    colors = {"LoG": (0, 255, 255), "DoG": (255, 0, 255), "DoH": (255, 255, 0),
              "Contours": (0, 255, 0)}
    for name, cfg in pb.CONFIGS.items():
        img, fg, _ = pb.detect(name, cfg)
        stem = os.path.splitext(name)[0]
        params = dict(PARAMS[name])
        thresh = params.pop("thresh")
        mask = cv2.GaussianBlur(binarize(fg, thresh), (0, 0), 1)
        results = {
            "LoG": detect_scale_space(mask, "log", **params),
            "DoG": detect_scale_space(mask, "dog", **params),
            "DoH": detect_scale_space(mask, "doh", **params),
            "Contours": detect_contours(fg, cfg["min_area"], cfg["max_area"], thresh=thresh),
        }
        panels = []
        for label, blobs in results.items():
            vis = draw(img, blobs, label, colors[label])
            cv2.imwrite(os.path.join(pb.OUT_DIR, f"{stem}_{label.lower()}.png"), vis)
            panels.append(vis)
            print(f"{name} {label}: {len(blobs)}")
        top = np.hstack(panels[:2])
        bottom = np.hstack(panels[2:])
        cv2.imwrite(os.path.join(pb.OUT_DIR, f"{stem}_methods.png"),
                    cv2.resize(np.vstack([top, bottom]), None, fx=0.5, fy=0.5,
                               interpolation=cv2.INTER_AREA))


if __name__ == "__main__":
    main()
