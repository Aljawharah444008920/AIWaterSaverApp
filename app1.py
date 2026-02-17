import os
import cv2
from flask import Flask, render_template, request
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv'}

# نحدد مجلد القوالب templates صراحة
app = Flask(__name__, template_folder='templates')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# نتأكد أن مجلد الرفع موجود
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
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    total_seconds = frame_count / fps if fps > 0 else 0

    # توزيع افتراضي: 70٪ استخدام فعلي، 30٪ هدر
    use_time = total_seconds * 0.7
    waste_time = total_seconds * 0.3

    # معدل تدفق تقريبي: 0.1 لتر لكل ثانية
    flow_rate_lps = 0.1
    water_used_liters = total_seconds * flow_rate_lps
    water_wasted_liters = waste_time * flow_rate_lps

    save_ratio = (water_wasted_liters / water_used_liters * 100) if water_used_liters > 0 else 0

    cap.release()

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
            error = "نوع الملف غير مدعوم، حمّلي فيديو بصيغة mp4 أو mov أو avi أو mkv."
            return render_template('upload.html', error=error)

    # طلب GET عادي: يعرض صفحة رفع الفيديو
    return render_template('upload.html')


if __name__ == '__main__':
    app.run(debug=True)

