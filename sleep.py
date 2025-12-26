import cv2
import mediapipe as mp
import numpy as np
import time
import pygame

# -----------------------------
# Initialize pygame mixer
# -----------------------------
pygame.mixer.init()
BUZZER_SOUND = "buzzer.mp3"

def play_buzzer():
    if not pygame.mixer.music.get_busy():
        pygame.mixer.music.load(BUZZER_SOUND)
        pygame.mixer.music.play(-1)  # loop until stopped

def stop_buzzer():
    pygame.mixer.music.stop()

# -----------------------------
# Mediapipe Face Mesh
# -----------------------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

# Eye landmark indices
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# -----------------------------
# EAR calculation
# -----------------------------
def calculate_ear(eye):
    A = np.linalg.norm(eye[1] - eye[5])
    B = np.linalg.norm(eye[2] - eye[4])
    C = np.linalg.norm(eye[0] - eye[3])
    return (A + B) / (2.0 * C)

# -----------------------------
# Parameters
# -----------------------------
EAR_THRESHOLD = 0.23
CONSEC_FRAMES = 15

counter = 0
status = "AWAKE"
sleep_start_time = None
total_sleep_time = 0
buzzer_on = False

# -----------------------------
# Camera
# -----------------------------
cap = cv2.VideoCapture(0)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    h, w = frame.shape[:2]
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb_frame)

    if results.multi_face_landmarks:
        mesh_points = np.array([
            [int(p.x * w), int(p.y * h)]
            for p in results.multi_face_landmarks[0].landmark
        ])

        left_eye = mesh_points[LEFT_EYE]
        right_eye = mesh_points[RIGHT_EYE]

        left_ear = calculate_ear(left_eye)
        right_ear = calculate_ear(right_eye)
        avg_ear = (left_ear + right_ear) / 2.0

        # -----------------------------
        # Drowsiness logic
        # -----------------------------
        if avg_ear < EAR_THRESHOLD:
            counter += 1
            if counter >= CONSEC_FRAMES:
                if status != "SLEEPING":
                    sleep_start_time = time.time()
                    play_buzzer()
                    buzzer_on = True
                status = "SLEEPING"
        else:
            if status == "SLEEPING" and sleep_start_time is not None:
                total_sleep_time += time.time() - sleep_start_time
                sleep_start_time = None

            counter = 0
            status = "AWAKE"
            if buzzer_on:
                stop_buzzer()
                buzzer_on = False

        # -----------------------------
        # Display status
        # -----------------------------
        cv2.putText(
            frame,
            f"Status: {status}",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 0, 255) if status == "SLEEPING" else (0, 255, 0),
            2
        )

        # Sleep time calculation
        display_sleep_time = total_sleep_time
        if status == "SLEEPING" and sleep_start_time is not None:
            display_sleep_time += time.time() - sleep_start_time

        minutes = int(display_sleep_time // 60)
        seconds = int(display_sleep_time % 60)

        cv2.putText(
            frame,
            f"Sleep Time: {minutes:02}:{seconds:02}",
            (30, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 0),
            2
        )

    cv2.imshow("Driver Drowsiness Detection", frame)

    if cv2.waitKey(1) & 0xFF == 27:  # ESC key
        break

# -----------------------------
# Cleanup
# -----------------------------
cap.release()
cv2.destroyAllWindows()
stop_buzzer()
pygame.mixer.quit()
