import os
import cv2
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

app = Flask(__name__, template_folder='templates')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def analyze_video(video_path):
    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        return {
            "total_time": 0,
            "use_time": 0,
            "waste_time": 0,
            "water_used_liters": 0,
            "water_wasted_liters": 0,
            "save_ratio": 0
        }

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    total_seconds = frame_count / fps if fps > 0 else 0

    use_frames = 0
    waste_frames = 0

    ret, prev_frame = cap.read()
    if not ret:
        cap.release()
        return {}

    height, width, _ = prev_frame.shape

    # تحديد منطقة التحليل (منتصف الفيديو غالباً مكان الصنبور)
    roi_x1 = int(width * 0.3)
    roi_x2 = int(width * 0.7)
    roi_y1 = int(height * 0.3)
    roi_y2 = int(height * 0.8)

    prev_roi = prev_frame[roi_y1:roi_y2, roi_x1:roi_x2]
    prev_gray = cv2.cvtColor(prev_roi, cv2.COLOR_BGR2GRAY)
    prev_gray = cv2.GaussianBlur(prev_gray, (15, 15), 0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        roi = frame[roi_y1:roi_y2, roi_x1:roi_x2]
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (15, 15), 0)

        # الفرق بين الفريم السابق والحالي
        frame_diff = cv2.absdiff(prev_gray, gray)

        # تحويل إلى صورة ثنائية
        thresh = cv2.threshold(frame_diff, 30, 255, cv2.THRESH_BINARY)[1]

        motion_pixels = cv2.countNonZero(thresh)

        # حساب نسبة الحركة داخل المنطقة
        total_pixels = thresh.shape[0] * thresh.shape[1]
        motion_ratio = motion_pixels / total_pixels

        # إذا تحرك أكثر من 2% من المنطقة = استخدام
        if motion_ratio > 0.02:
            use_frames += 1
        else:
            waste_frames += 1

        prev_gray = gray

    cap.release()

    use_time = use_frames / fps if fps > 0 else 0
    waste_time = waste_frames / fps if fps > 0 else 0

    flow_rate_lps = 0.1  # 0.1 لتر لكل ثانية
    water_used_liters = total_seconds * flow_rate_lps
    water_wasted_liters = waste_time * flow_rate_lps

    save_ratio = (water_wasted_liters / water_used_liters * 100) if water_used_liters > 0 else 0

    return {
        "total_time": round(total_seconds, 2),
        "use_time": round(use_time, 2),
        "waste_time": round(waste_time, 2),
        "water_used_liters": round(water_used_liters, 2),
        "water_wasted_liters": round(water_wasted_liters, 2),
        "save_ratio": round(save_ratio, 2)
    }


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            error = "لم يتم اختيار أي ملف."
            return render_template('upload.html', error=error)

        file = request.files['file']

        if file.filename == '':
            error = "لم يتم اختيار أي ملف."
            return render_template('upload.html', error=error)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)

            result = analyze_video(save_path)

            return render_template('result.html', result=result, filename=filename)

        else:
            error = "نوع الملف غير مدعوم."
            return render_template('upload.html', error=error)

    return render_template('upload.html')


if __name__ == '__main__':
    app.run(debug=True)
