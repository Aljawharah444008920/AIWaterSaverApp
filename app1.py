from flask import Flask, render_template, request
import os
import cv2
from werkzeug.utils import secure_filename

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"mp4", "mov", "avi"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def analyze_video(video_path):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        return {}

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_seconds = frame_count / fps if fps > 0 else 0

    frame_index = 0
    use_time = 0
    waste_time = 0

    water_used_liters = 0
    water_wasted_liters = 0

    ret, prev_frame = cap.read()
    if not ret:
        cap.release()
        return {}

    # تصغير الدقة لتسريع المعالجة
    prev_frame = cv2.resize(prev_frame, (320, 240))
    height, width, _ = prev_frame.shape

    # تحديد منطقة الصنبور (منتصف الصورة تقريباً)
    y1, y2 = int(height * 0.3), int(height * 0.8)
    x1, x2 = int(width * 0.35), int(width * 0.65)

    prev_roi = prev_frame[y1:y2, x1:x2]
    prev_gray = cv2.cvtColor(prev_roi, cv2.COLOR_BGR2GRAY)
    prev_gray = cv2.GaussianBlur(prev_gray, (7, 7), 0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_index += 1

        # تحليل فريم كل 3 فريمات لتسريع الأداء
        if frame_index % 3 != 0:
            continue

        frame = cv2.resize(frame, (320, 240))
        roi = frame[y1:y2, x1:x2]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7, 7), 0)

        diff = cv2.absdiff(prev_gray, gray)
        thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)[1]

        motion_pixels = cv2.countNonZero(thresh)
        total_pixels = thresh.shape[0] * thresh.shape[1]
        motion_ratio = motion_pixels / total_pixels

        # معدل تدفق ديناميكي
        flow_rate = 0.03 + (motion_ratio * 0.5)

        seconds_per_step = 3 / fps if fps > 0 else 0

        if motion_ratio > 0.015:
            use_time += seconds_per_step
            water_used_liters += flow_rate * seconds_per_step
        else:
            waste_time += seconds_per_step
            water_wasted_liters += flow_rate * seconds_per_step

        prev_gray = gray

    cap.release()

    total_water = water_used_liters + water_wasted_liters
    save_ratio = (water_wasted_liters / total_water * 100) if total_water > 0 else 0

    return {
        "total_time": round(total_seconds, 2),
        "use_time": round(use_time, 2),
        "waste_time": round(waste_time, 2),
        "water_used_liters": round(water_used_liters, 3),
        "water_wasted_liters": round(water_wasted_liters, 3),
        "save_ratio": round(save_ratio, 2)
    }


@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":

        if "file" not in request.files:
            return render_template("upload.html", error="لم يتم اختيار ملف")

        file = request.files["file"]

        if file.filename == "":
            return render_template("upload.html", error="يرجى اختيار فيديو")

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)

            result = analyze_video(save_path)

            return render_template("result.html", result=result)

        else:
            return render_template("upload.html", error="نوع الملف غير مدعوم")

    return render_template("upload.html")


if __name__ == "__main__":
    app.run(debug=True)
