# ControladorDelJuego.py
import time
import cv2
import mediapipe as mp

class HandGestureController:
    def __init__(self,
                 max_num_hands=1,
                 detection_confidence=0.7,
                 tracking_confidence=0.7):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=max_num_hands,
            min_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence
        )
        self.drawer = mp.solutions.drawing_utils

        # Cooldowns para no spamear acciones
        self.cooldowns = {"mover": 0.15, "rotar": 0.35, "abajo": 0.10}
        self._last_time = {"mover": 0, "rotar": 0, "abajo": 0}

        # Margen (tolerancia) para considerar “arriba” un dedo (normalizado)
        # Sube si aún cuesta que lo detecte (p.ej. 0.05)
        self.margin = 0.035

        self.last_action_text = "—"

    def _now(self): 
        return time.time()

    def _ready(self, key): 
        return (self._now() - self._last_time[key]) >= self.cooldowns[key]

    def _mark(self, key): 
        self._last_time[key] = self._now()

    def detect_gesture(self, frame):
        gesture = None
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb)

        info = []

        if results.multi_hand_landmarks:
            hand = results.multi_hand_landmarks[0]
            self.drawer.draw_landmarks(frame, hand, self.mp_hands.HAND_CONNECTIONS)
            lm = hand.landmark

            H = self.mp_hands.HandLandmark

            # Estados de dedos (1=arriba, 0=abajo) con tolerancia
            thumb  = self._finger_up(lm, H.THUMB_TIP,  H.THUMB_IP,  H.THUMB_MCP)
            index  = self._finger_up(lm, H.INDEX_FINGER_TIP,  H.INDEX_FINGER_PIP,  H.INDEX_FINGER_MCP)
            middle = self._finger_up(lm, H.MIDDLE_FINGER_TIP, H.MIDDLE_FINGER_PIP, H.MIDDLE_FINGER_MCP)
            ring   = self._finger_up(lm, H.RING_FINGER_TIP,   H.RING_FINGER_PIP,   H.RING_FINGER_MCP)
            pinky  = self._finger_up(lm, H.PINKY_TIP,         H.PINKY_PIP,         H.PINKY_MCP)

            # Para puño/mano abierta consideramos los 4 dedos largos (índice→meñique)
            longs_sum = index + middle + ring + pinky
            fingers_sum = thumb + longs_sum

            # --- Orden de prioridad de gestos ---
            # 1) Puño → Rotar (0 dedos largos arriba)
            if longs_sum == 0 and self._ready("rotar"):
                gesture = "rotar"; self._mark("rotar"); info.append("Puño → Rotar")

            # 2) Mano abierta → Abajo (>=3 de los 4 largos arriba)
            elif longs_sum >= 3 and self._ready("abajo"):
                gesture = "abajo"; self._mark("abajo"); info.append("Mano abierta → Abajo")

            else:
                # 3)  Amor y paz → Izquierda
                #    Reglas tolerantes: índice y medio arriba, anular y meñique abajo.
                #    El pulgar se IGNORA (puede estar arriba o abajo).
                peace_strict = (index == 1 and middle == 1 and ring == 0 and pinky == 0)
                peace_soft   = (index == 1 and middle == 1 and (ring + pinky) <= 1)
                if (peace_strict or peace_soft) and self._ready("mover"):
                    gesture = "izquierda"; self._mark("mover"); info.append(" Amor y paz → Izquierda")

                # 4) Solo índice → Derecha
                #    Estricto: índice=1 y otros largos=0; Suave: índice=1 y solo uno de (middle/ring/pinky) ruidoso
                elif self._ready("mover"):
                    index_strict = (index == 1 and middle == 0 and ring == 0 and pinky == 0)
                    index_soft   = (index == 1 and (middle + ring + pinky) <= 1)
                    if index_strict or index_soft:
                        gesture = "derecha"; self._mark("mover"); info.append("Índice → Derecha")
                    else:
                        info.append("Neutro / sin accion")

            # HUD con estados de dedos para depurar
            info.insert(0, f"Dedos: T{thumb} I{index} M{middle} A{ring} Me{pinky}")

            self._draw_hud(frame, gesture if gesture else "—", info)
        else:
            self._draw_hud(frame, "—", ["Sin mano detectada"])

        self.last_action_text = gesture if gesture else "—"
        return gesture

    def _finger_up(self, lm, tip, pip, mcp):
        """
        Considera 'arriba' si la punta del dedo está por encima (y menor) que PIP y MCP
        con un margen de tolerancia para ser robusto a inclinaciones.
        """
        tip_y = lm[tip].y
        pip_y = lm[pip].y
        mcp_y = lm[mcp].y
        # más estricto: por encima de PIP y MCP por al menos 'margin'
        return 1 if (tip_y < (pip_y - self.margin) and tip_y < (mcp_y - self.margin)) else 0

    def _draw_hud(self, frame, action, extra_lines=None):
        if extra_lines is None: 
            extra_lines = []
        x, y, lh = 10, 16, 24
        lines = [f"Accion: {action}"] + extra_lines
        for i, line in enumerate(lines):
            yy = y + i * lh
            cv2.rectangle(frame, (x-6, yy-18), (x+420, yy+6), (0, 0, 0), -1)
            cv2.putText(frame, line, (x, yy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
