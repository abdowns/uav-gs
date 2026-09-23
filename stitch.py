import argparse
import glob
import os
import sys

import cv2

VIDEO = "Minecraft_stitch_test.mp4"
FRAME_DIR = "frames"
OUTPUT = "panorama.png"

STATUS = {
    0: "OK",
    1: "ERR_NEED_MORE_IMGS",
    2: "ERR_HOMOGRAPHY_EST_FAIL",
    3: "ERR_CAMERA_PARAMS_ADJUST_FAIL",
}


def extract(video, frame_dir):
    os.makedirs(frame_dir, exist_ok=True)
    existing = sorted(glob.glob(os.path.join(frame_dir, "frame_*.jpg")))
    if existing:
        print(f"reusing {len(existing)} frames in {frame_dir}/")
        return existing

    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        sys.exit(f"could not open {video}")

    paths = []
    i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        path = os.path.join(frame_dir, f"frame_{i:04d}.jpg")
        cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        paths.append(path)
        i += 1
    cap.release()

    print(f"extracted {len(paths)} frames to {frame_dir}/")
    return paths


def stitch(paths, step, scale):
    frames = []
    for path in paths[::step]:
        img = cv2.imread(path)
        if scale != 1.0:
            img = cv2.resize(img, None, fx=scale, fy=scale)
        frames.append(img)
    print(f"stitching {len(frames)} frames at scale {scale}")

    # scans mode uses an affine model which suits a flat nadir flight
    stitcher = cv2.Stitcher_create(cv2.Stitcher_SCANS)
    status, pano = stitcher.stitch(frames)
    print(f"status {status} {STATUS.get(status, 'UNKNOWN')}")
    if status != 0:
        sys.exit(1)
    return pano


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=int, default=15)
    parser.add_argument("--scale", type=float, default=1.0)
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)

    paths = extract(VIDEO, FRAME_DIR)
    pano = stitch(paths, args.step, args.scale)

    cv2.imwrite(OUTPUT, pano)
    h, w = pano.shape[:2]
    print(f"wrote {OUTPUT} {w}x{h}")


if __name__ == "__main__":
    main()