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


# التحقق من نوع الملف
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# دالة تحليل الفيديو (سريعة + ديناميكية)
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

    # تقليل الدقة لتسريع التحليل
    prev_frame = cv2.resize(prev_frame, (240, 180))
    height, width, _ = prev_frame.shape

    # تحديد منطقة الصنبور (منتصف الصورة تقريبًا)
    y1, y2 = int(height * 0.3), int(height * 0.8)
    x1, x2 = int(width * 0.35), int(width * 0.65)

    prev_roi = prev_frame[y1:y2, x1:x2]
    prev_gray = cv2.cvtColor(prev_roi, cv2.COLOR_BGR2GRAY)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_index += 1

        # تحليل كل 5 فريمات (أسرع)
        if frame_index % 5 != 0:
            continue

        frame = cv2.resize(frame, (240, 180))
        roi = frame[y1:y2, x1:x2]

        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

        diff = cv2.absdiff(prev_gray, gray)
        motion_pixels = cv2.countNonZero(diff)

        motion_ratio = motion_pixels / (diff.shape[0] * diff.shape[1])

        # معدل تدفق ديناميكي
        flow_rate = 0.03 + (motion_ratio * 0.4)

        seconds_step = 5 / fps if fps > 0 else 0

        if motion_ratio > 0.02:
            use_time += seconds_step
            water_used_liters += flow_rate * seconds_step
        else:
            waste_time += seconds_step
            water_wasted_liters += flow_rate * seconds_step

        prev_gray = gray

    cap.release()

    total_water = water_used_liters + water_wasted_liters
    save_ratio = (water_wasted_liters / total_water * 100) if total_water > 0 else 0

    # نظام التقييم الذكي
    score = max(0, 100 - save_ratio)

    if save_ratio > 40:
        advice = "⚠️ نسبة الهدر مرتفعة. حاول إغلاق الصنبور أثناء فرك اليدين."
    elif save_ratio > 20:
        advice = "👍 استهلاكك جيد، لكن يمكنك تحسينه أكثر."
    else:
        advice = "🌱 ممتاز! استهلاكك اقتصادي جداً."

    return {
        "total_time": round(total_seconds, 2),
        "use_time": round(use_time, 2),
        "waste_time": round(waste_time, 2),
        "water_used_liters": round(water_used_liters, 3),
        "water_wasted_liters": round(water_wasted_liters, 3),
        "save_ratio": round(save_ratio, 2),
        "score": round(score, 1),
        "advice": advice
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
