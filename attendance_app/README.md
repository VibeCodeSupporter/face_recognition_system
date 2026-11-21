# Attendance Device App

PyQt6 desktop application for local face enrollment and recognition. Camera capture feeds two independent paths: a live GUI preview and a latest-frame face-processing pipeline. The app uses local ONNX models, SQLite, and FAISS. It currently reports recognition results; it does not write attendance records or control a door lock.

## Features and scope

- Live camera preview with a fixed center ROI guide. The GUI displays the camera image and ROI boundary; it does not draw detector boxes or landmarks.
- Full-frame YuNet face detection, followed by an ROI inclusion check and temporary ByteTrack IDs.
- Five-pose enrollment: front, left, right, down, and up.
- Recognition against local face embeddings with pose, image-quality, and Silent-Face anti-spoof gates.
- SQLite is the durable source for employees and embeddings. FAISS is the local nearest-vector search index.
- OTP, hardware access control, door sensors, and synchronization modules are scaffolding and are not connected to the current flow.

## Run

On Windows, first install the dependencies from this directory:

```powershell
uv sync
```

Then start the app by double-clicking `run.bat` or running it from this directory:

```powershell
.\run.bat
```

`run.bat` activates `.venv`, runs `python main.py`, and leaves the terminal open after exit. The model files are local and are not downloaded by the app. The default `.env` expects:

```text
attendance_app/
├── .env
├── main.py
└── weights/
    ├── face_detection_yunet_2026may.onnx
    ├── GhostFaceNet_W1.3_S1_ArcFace.onnx
    ├── 2.7_80x80_MiniFASNetV2.onnx
    └── 4_0_0_80x80_MiniFASNetV1SE.onnx
```

Set model paths in `.env` if the files are elsewhere. Relative model paths resolve from `attendance_app`. Grant the process permission to use the camera; set `CAMERA_INDEX` in `.env` to select a different camera.

## Camera and frame processing

`CameraManager` continuously captures frames and retains the newest frame instead of building a queue. `PreviewWorker` reads that newest frame independently and sends it to the GUI. Preview does not wait for detection, FAS, embedding, or gallery lookup. The green ROI is drawn by the GUI over the preview; the detector box is not drawn there.

`FrameWorker` processes the newest available frame. If inference is slower than camera capture, intermediate frames are dropped. Thus the gates below run in order on each frame the worker processes, not necessarily every frame captured by the camera. The `Frame stats` log reports camera/worker rates, dropped frames, detector and recognition rates, embeddings, gate skips, outcomes, and per-stage average/maximum processing times in milliseconds. Timed stages include YuNet detection, ROI filtering, tracking, pose, quality, Silent-Face crop preparation/inference, alignment, GhostFaceNet embedding, and total worker-frame processing. Gallery search is timed separately because it runs after the embedding signal reaches the recognition controller.

YuNet runs on the full camera frame. Its detections are mapped back to full-frame coordinates, then filtered to faces fully inside the inset center ROI. The pipeline proceeds only when exactly one such face remains. ByteTrack assigns temporary IDs across processed detections. The tracker does not smooth boxes or pose, and it does not verify identity across all five enrollment poses; it currently supports short-term continuity for UI guidance and registration state.

### Recognition

For each eligible processed frame:

1. Detect faces on the full frame, filter by the ROI, and require exactly one face.
2. Estimate pose; reject the frame if it is outside recognition limits.
3. Check face size/framing, sharpness, brightness, and quality pose limits; stop on failure.
4. Run Silent-Face on the original, unaligned face crop; stop if classified as spoof.
5. Align to 112×112, run GhostFaceNet, L2-normalize its 512-D vector, and search the FAISS gallery.

Each failed gate ends that frame; the next processed frame starts again at detection. While gallery matching is pending, the worker skips new detection/inference. After a successful match, it also pauses recognition for `RECOGNITION_SUCCESS_COOLDOWN_SECONDS`; camera capture and preview continue.

The recognition page shows guidance aggregated over a short time window to reduce message flicker. It shows the match result in a separate panel with the aligned face, name, ID, and squared-L2 distance. The result panel does not modify or pause the preview. A face/track change resets recent guidance history.

### Registration

Opening the registration page stops the recognition worker. The camera preview is available, but registration inference starts only after an employee ID and name are entered and **Bắt đầu đăng ký** is pressed. During enrollment, the ID, name, start button, and back button are disabled; **Reset enrollment** remains available to cancel the current attempt.

The app captures one embedding for each pose in order: front, left, right, down, up. For each eligible processed frame it requires exactly one face in the ROI, checks the requested pose, then quality. A failed stage ends that frame and a later frame retries.

After pose and quality pass, registration prepares the Silent-Face crop and the aligned 112×112 embedding image concurrently. It runs Silent-Face inference first; only a REAL result allows GhostFaceNet embedding inference. A spoof result does not run the embedding model. After an embedding is emitted, the current pose is captured once and the worker waits for the UI to advance to the next pose. Once all five samples are accepted, the service saves the employee and vectors locally. Track IDs help reset in-progress state when a tracked face changes, but the app does not yet enforce that all five poses belong to the same person; this can be added later.

The registration page displays the requested pose and instructions, current pose/quality details, FAS verdict, progress, and status messages. On a successful pose, it advances to the next one. On completion it stops the worker and confirms the saved enrollment.

## Models and preprocessing

### YuNet ONNX

The detector receives the BGR full-frame image resized so its longest side is 320 pixels, centered on a 320×320 canvas filled with value 114. Box and landmark coordinates are mapped back to the original full-frame coordinate system. OpenCV `FaceDetectorYN` applies confidence filtering and NMS. The mapped detections are then checked against the GUI's center ROI, with a small inset; the ROI is a selection guide and does not crop the detector input.

### Silent-Face ONNX

For each configured model (currently scales 2.7 and 4.0, read from the filename), the app expands the YuNet box on the original BGR frame using Silent-Face `CropImage` geometry, without alignment, then resizes the crop to 80×80. The ONNX tensor is BGR, NCHW, float32 in the 0–255 range. The app softmaxes each model's three logits, averages the model probabilities, and treats class 1 as REAL. `FACE_ANTISPOOF_REAL_THRESHOLD` controls the minimum REAL probability.

### GhostFaceNet embedding and matching

The five YuNet landmarks align the original frame to a 112×112 face image. The aligned BGR image is converted to RGB and normalized with `(pixel - 127.5) * 0.0078125`. GhostFaceNet returns a 512-D vector, which the app L2-normalizes. Alignment pixels may differ slightly from the benchmark helper because the app uses OpenCV warp while that helper uses scikit-image.

FAISS `IndexFlatL2` searches exact squared-L2 distance; smaller values mean closer vectors. For normalized vectors, `cosine_similarity = 1 - squared_L2 / 2`. The threshold is deployment configuration, not a GhostFaceNet-provided constant. The gallery stores five pose vectors per employee and searches the nearest individual vector; it does not average them into one prototype.

## Quality, pose, tracker, and UI guidance

The quality checker evaluates face size relative to the ROI, distance from ROI edges, Laplacian sharpness, mean LAB-L brightness, and pose estimated from five landmarks with `solvePnP`. Registration has its own requested-pose gate before quality. Recognition checks its allowed pose range before quality. These are lightweight heuristics; thresholds need calibration for the target camera and lighting.

The preview path remains independent from the inference path. The GUI shows the fixed ROI boundary but not per-frame detector boxes. Recognition guidance aggregates recent outcomes (pose, quality, FAS, missing/multiple faces) and refreshes on a timer; registration shows the latest frame's guidance and current enrollment step. A successful recognition is shown separately from the live image.

## Debugging and logs

Logging is controlled separately from debug images:

- `PIPELINE_CSV_LOG_ENABLED=1` appends per-processed-frame status to `data/pipeline_debug/frame_status.csv`; registration also appends pose details to `pose_debug.csv`. The default is `0`.
- `FRAME_DEBUG_SAVE_IMAGES=1` saves the actual camera and module input images under `data/pipeline_debug/`; each module folder is bounded to 50 images. The default is `0`.
- Runtime `Frame stats` are written to the application log regardless of the CSV switch.

The CSV includes frame ID, outcome, detection/track count, pose, quality and FAS status, scores, guidance, and errors. The saved module images help compare the exact inputs received by YuNet, quality, Silent-Face, and GhostFaceNet.

## Configuration

The app loads `attendance_app/.env` at startup. Environment variables override fallback defaults in `config/settings.py`. Current `.env` values are the deployment settings; adjust them there rather than relying on the defaults documented in source code.

| Variable | Purpose |
|---|---|
| `CAMERA_INDEX` | Operating-system camera index. |
| `FACE_DETECTOR_MODEL` | YuNet ONNX model path. |
| `FACE_DETECTOR_CONFIDENCE`, `FACE_DETECTOR_IOU` | YuNet score and NMS thresholds. |
| `FACE_TRACKER_LOST_BUFFER` | ByteTrack lost-frame buffer. |
| `FACE_EMBEDDING_MODEL` | GhostFaceNet ONNX model path. |
| `FACE_ANTISPOOF_MODEL` | Semicolon-separated Silent-Face ONNX paths; filenames encode crop scales. |
| `FACE_ANTISPOOF_REAL_THRESHOLD` | Minimum fused class-1 REAL probability. |
| `FACE_MATCH_THRESHOLD` | Maximum accepted squared-L2 distance. |
| `FACE_POSE_*` | Enrollment pose angles and cross-axis limits. |
| `FACE_RECOGNITION_MAX_*_DEGREES` | Recognition pose limits. |
| `FACE_QUALITY_*` | Recognition and registration framing, sharpness, brightness, and edge limits. |
| `RECOGNITION_UI_WINDOW_SECONDS`, `RECOGNITION_UI_UPDATE_INTERVAL_SECONDS` | Recognition guidance aggregation and refresh timing. |
| `RECOGNITION_SUCCESS_COOLDOWN_SECONDS` | Pause recognition after a successful match; preview continues. |
| `PIPELINE_CSV_LOG_ENABLED` | Enable per-frame CSV logs. |
| `FRAME_DEBUG_SAVE_IMAGES` | Enable bounded module-input image dumps. |

## Local data

- `data/faces.sqlite3`: employee records and embeddings.
- `data/faces.faiss`: persisted exact-L2 search index, rebuildable from SQLite.
- `data/enrollments/<employee_id>/`: aligned enrollment images.
- `data/pipeline_debug/frame_status.csv` and optional `pose_debug.csv`: per-frame diagnostics when CSV logging is enabled.
- `data/pipeline_debug/camera/`, `yunet/`, `quality/`, `silentface/`, `ghostfacenet/`: bounded module-input images when image logging is enabled.
- `data/captures/`: default location for manually captured ROI images.

The **Rebuild FAISS index** action rebuilds the index from SQLite; it does not delete enrollment records.

## Raspberry Pi notes

On Linux ARM, the project selects the ONNX Runtime CPU package. Use 64-bit Raspberry Pi OS and confirm wheel compatibility for the Pi OS/glibc and Python versions in use. Processing speed depends on Pi model, camera resolution, cooling, and model sizes. The latest-frame design drops stale frames instead of building latency, so preview remains independent while the worker may process fewer frames than the camera captures.

## Source layout

| Path | Responsibility |
|---|---|
| `main.py`, `run.bat` | App entry point and Windows launcher. |
| `config/` | Environment-backed runtime settings. |
| `camera/` | Camera capture, independent preview, and frame worker. |
| `face/` | YuNet, tracking, quality, Silent-Face, alignment, and GhostFaceNet. |
| `recognition/` | Per-frame recognition flow and gallery lookup. |
| `registration/` | Five-pose enrollment flow and persistence. |
| `ui/` | PyQt pages, ROI preview, guidance, and result display. |
| `storage/` | SQLite records and FAISS index. |

## Known limitations

- Recognition thresholds and image-quality limits require calibration on the deployment camera.
- ByteTrack currently provides temporary continuity IDs; it does not verify that five enrollment poses belong to one identity.
- Recognition result display is implemented, but attendance event persistence and access-control hardware are not connected.
- A camera read failure stops the worker; automatic recovery from transient camera failures is not implemented.
