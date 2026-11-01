import argparse
import csv
import sys
from pathlib import Path

import cv2
import numpy as np

from ying import Ying_2017_CAIP


IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
METRIC_NAMES = ("brightness", "contrast", "sharpness", "dark_pixels_pct", "bright_pixels_pct")


def measure_quality(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return {
        "brightness": float(np.mean(gray)),
        "contrast": float(np.std(gray)),
        "sharpness": float(np.var(cv2.Laplacian(gray, cv2.CV_64F))),
        "dark_pixels_pct": float(np.mean(gray <= 8) * 100),
        "bright_pixels_pct": float(np.mean(gray >= 247) * 100),
    }


def save_comparison(original, enhanced, output_path):
    panels = []
    for image, title in ((original, "Original"), (enhanced, "Ying 2017")):
        panel = cv2.copyMakeBorder(
            image, 32, 0, 0, 0, cv2.BORDER_CONSTANT, value=(35, 35, 35)
        )
        cv2.putText(
            panel,
            title,
            (10, 22),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            1,
            cv2.LINE_AA,
        )
        panels.append(panel)

    comparison = cv2.hconcat(panels)
    if not cv2.imwrite(str(output_path), comparison):
        raise OSError(f"Could not write comparison image: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Run Ying 2017 enhancement on captured images and compare quality metrics."
    )
    app_dir = Path(__file__).resolve().parent
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=app_dir / "data" / "captures",
        help="Folder containing input images (default: data/captures).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=app_dir / "data" / "ying_quality_review",
        help="Folder for enhanced images, comparisons, and CSV report.",
    )
    args = parser.parse_args()

    input_dir = args.input_dir.resolve()
    output_dir = args.output_dir.resolve()
    if not input_dir.is_dir():
        parser.error(f"Input folder does not exist: {input_dir}")
    if output_dir == input_dir or input_dir in output_dir.parents:
        parser.error("Output folder must not be inside the input folder.")

    image_paths = sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not image_paths:
        parser.error(f"No supported images found in: {input_dir}")

    enhanced_dir = output_dir / "enhanced"
    comparisons_dir = output_dir / "comparisons"
    enhanced_dir.mkdir(parents=True, exist_ok=True)
    comparisons_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "quality_report.csv"

    fieldnames = [
        "image",
        "width",
        "height",
        *(f"before_{name}" for name in METRIC_NAMES),
        *(f"after_{name}" for name in METRIC_NAMES),
    ]
    with report_path.open("w", newline="", encoding="utf-8-sig") as report_file:
        writer = csv.DictWriter(report_file, fieldnames=fieldnames)
        writer.writeheader()

        for image_path in image_paths:
            original = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
            if original is None:
                raise OSError(f"Could not read image: {image_path}")
            enhanced = Ying_2017_CAIP(original)
            relative_path = image_path.relative_to(input_dir)
            enhanced_path = enhanced_dir / relative_path
            comparison_path = comparisons_dir / relative_path.with_suffix(".jpg")
            enhanced_path.parent.mkdir(parents=True, exist_ok=True)
            comparison_path.parent.mkdir(parents=True, exist_ok=True)

            if not cv2.imwrite(str(enhanced_path), enhanced):
                raise OSError(f"Could not write enhanced image: {enhanced_path}")
            save_comparison(original, enhanced, comparison_path)

            before = measure_quality(original)
            after = measure_quality(enhanced)
            row = {
                "image": str(relative_path),
                "width": original.shape[1],
                "height": original.shape[0],
                **{f"before_{name}": f"{before[name]:.3f}" for name in METRIC_NAMES},
                **{f"after_{name}": f"{after[name]:.3f}" for name in METRIC_NAMES},
            }
            writer.writerow(row)
            print(
                f"{relative_path}: brightness {before['brightness']:.1f} -> "
                f"{after['brightness']:.1f}, sharpness {before['sharpness']:.1f} -> "
                f"{after['sharpness']:.1f}"
            )

    print(f"\nProcessed {len(image_paths)} image(s).")
    print(f"Side-by-side comparisons: {comparisons_dir}")
    print(f"Enhanced images: {enhanced_dir}")
    print(f"Metrics report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
