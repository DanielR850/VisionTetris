# main.py

import threading
import cv2
from ControladorDelJuego import HandGestureController
from tetris import TetrisGame

current_gesture = None

def vision_thread():
    global current_gesture
    cap = cv2.VideoCapture(0)
    detector = HandGestureController()

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        gesture = detector.detect_gesture(frame)
        current_gesture = gesture

        cv2.imshow("Hand Tracking", frame)
        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()

def main():
    global current_gesture

    thread = threading.Thread(target=vision_thread)
    thread.daemon = True
    thread.start()

    game = TetrisGame()

    while game.running:
        if current_gesture:
            game.handle_gesture(current_gesture)
            current_gesture = None  

        game.update()
        game.draw()

    print("Juego terminado.")

if __name__ == "__main__":
    main()
