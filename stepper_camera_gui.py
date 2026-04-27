#!/usr/bin/env python3
"""
Tkinter GUI for controlling two Raspberry Pi stepper motors while viewing a
normal camera feed and capturing Intel RealSense RGB/depth images on demand.

The GPIO behavior mirrors the original open-collector style script:
  - DIR/PUL opto input ON  = drive pin LOW
  - DIR/PUL opto input OFF = configure pin as input (Hi-Z)

Camera support:
  - Picamera2 is used for the live preview when available.
  - OpenCV VideoCapture(0) is used as a live-preview fallback.
  - Intel RealSense RGB and depth snapshots are captured through pyrealsense2
    only when the capture button is clicked.

Run on the Raspberry Pi with:
    python3 stepper_camera_gui.py
"""

from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, Optional


# -------- Pin mapping (BCM numbering) --------
M1_PUL = 23
M1_DIR = 24

M2_DIR = 14
M2_PUL = 15

# -------- Timing defaults from the original script --------
DEFAULT_PULSE_US = 50
DEFAULT_GAP_US = 200

# The original script did not define a step-count default. This follows its
# first example command: "m 1 1600 cw".
DEFAULT_STEPS = 1600


try:
    import RPi.GPIO as GPIO  # type: ignore

    GPIO_AVAILABLE = True
except ModuleNotFoundError:
    GPIO_AVAILABLE = False

    class _MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        IN = "IN"
        LOW = 0

        @staticmethod
        def setmode(_mode: str) -> None:
            return None

        @staticmethod
        def setwarnings(_enabled: bool) -> None:
            return None

        @staticmethod
        def setup(_pin: int, _mode: str) -> None:
            return None

        @staticmethod
        def output(_pin: int, _value: int) -> None:
            return None

        @staticmethod
        def cleanup() -> None:
            return None

    GPIO = _MockGPIO()  # type: ignore


class StepperController:
    """Controls the two stepper drivers using the original open-collector logic."""

    def __init__(self, pulse_us: int = DEFAULT_PULSE_US, gap_us: int = DEFAULT_GAP_US) -> None:
        self.pulse_us = pulse_us
        self.gap_us = gap_us
        self._lock = threading.Lock()

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in (M1_PUL, M1_DIR, M2_PUL, M2_DIR):
            self.hi_z(pin)

    @staticmethod
    def drive_low(pin: int) -> None:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)

    @staticmethod
    def hi_z(pin: int) -> None:
        GPIO.setup(pin, GPIO.IN)

    def set_timing(self, pulse_us: int, gap_us: int) -> None:
        if pulse_us <= 0:
            raise ValueError("Pulse width must be greater than 0 microseconds.")
        if gap_us < 0:
            raise ValueError("Gap must be 0 microseconds or greater.")
        self.pulse_us = pulse_us
        self.gap_us = gap_us

    def set_dir(self, dir_pin: int, direction: str) -> None:
        d = direction.strip().lower()
        if d in ("cw", "c", "1", "+"):
            self.hi_z(dir_pin)
        elif d in ("ccw", "cc", "0", "-", "rev", "r"):
            self.drive_low(dir_pin)
        else:
            raise ValueError("Direction must be cw or ccw.")

    def step_pulses(self, pul_pin: int, steps: int) -> None:
        if steps <= 0:
            raise ValueError("Steps must be greater than 0.")

        pulse_delay = self.pulse_us / 1_000_000
        gap_delay = self.gap_us / 1_000_000
        for _ in range(steps):
            self.drive_low(pul_pin)
            time.sleep(pulse_delay)
            self.hi_z(pul_pin)
            time.sleep(gap_delay)

    def move_motor(self, motor: int, steps: int, direction: str) -> None:
        with self._lock:
            if motor == 1:
                self.set_dir(M1_DIR, direction)
                self.step_pulses(M1_PUL, steps)
            elif motor == 2:
                self.set_dir(M2_DIR, direction)
                self.step_pulses(M2_PUL, steps)
            else:
                raise ValueError("Motor must be 1 or 2.")

    def move_both_sequential(self, steps: int, direction1: str, direction2: str) -> None:
        with self._lock:
            self.set_dir(M1_DIR, direction1)
            self.step_pulses(M1_PUL, steps)
            self.set_dir(M2_DIR, direction2)
            self.step_pulses(M2_PUL, steps)

    def cleanup(self) -> None:
        GPIO.cleanup()


class CameraSource:
    """Live camera wrapper that prefers Picamera2 and falls back to OpenCV."""

    def __init__(self, width: int = 640, height: int = 480) -> None:
        self.width = width
        self.height = height
        self.backend = "disabled"
        self._picam2 = None
        self._capture = None
        self._cv2 = None
        self._lock = threading.Lock()

        self.start()

    def start(self) -> None:
        with self._lock:
            if self._picam2 is not None or self._capture is not None:
                return
            self.backend = "disabled"
            self._start_picamera2() or self._start_opencv()

    def _start_picamera2(self) -> bool:
        try:
            from picamera2 import Picamera2  # type: ignore
        except ModuleNotFoundError:
            return False

        self._picam2 = Picamera2()
        config = self._picam2.create_preview_configuration(
            main={"size": (self.width, self.height), "format": "RGB888"}
        )
        self._picam2.configure(config)
        self._picam2.start()
        self.backend = "Picamera2"
        return True

    def _start_opencv(self) -> bool:
        try:
            import cv2  # type: ignore
        except ModuleNotFoundError:
            return False

        capture = cv2.VideoCapture(0)
        if not capture.isOpened():
            capture.release()
            return False

        capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cv2 = cv2
        self._capture = capture
        self.backend = "OpenCV"
        return True

    def read_rgb_frame(self):
        with self._lock:
            if self._picam2 is not None:
                return self._picam2.capture_array()

            if self._capture is not None and self._cv2 is not None:
                ok, frame = self._capture.read()
                if not ok:
                    return None
                return self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)

            return None

    def stop(self) -> None:
        with self._lock:
            if self._picam2 is not None:
                self._picam2.stop()
                self._picam2 = None
            if self._capture is not None:
                self._capture.release()
                self._capture = None
            self.backend = "disabled"


class RealSenseCamera:
    """Captures one RGB frame and one colorized depth frame from a RealSense camera."""

    def __init__(self, width: int = 640, height: int = 480, fps: int = 30) -> None:
        self.width = width
        self.height = height
        self.fps = fps

    def capture_rgb_and_depth(self):
        try:
            import numpy as np  # type: ignore
            import pyrealsense2 as rs  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "RealSense capture needs pyrealsense2 and numpy. "
                "Install the Intel RealSense SDK Python package on the Raspberry Pi."
            ) from exc

        pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.color, self.width, self.height, rs.format.rgb8, self.fps)
        config.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, self.fps)

        started = False
        try:
            pipeline.start(config)
            started = True
            align = rs.align(rs.stream.color)
            colorizer = rs.colorizer()

            frames = None
            # Discard a few initial frames so auto-exposure has a chance to settle.
            for _ in range(8):
                frames = align.process(pipeline.wait_for_frames())

            if frames is None:
                raise RuntimeError("No frames received from the RealSense camera.")

            color_frame = frames.get_color_frame()
            depth_frame = frames.get_depth_frame()
            if not color_frame or not depth_frame:
                raise RuntimeError("RealSense did not return both RGB and depth frames.")

            rgb_frame = np.asanyarray(color_frame.get_data()).copy()
            depth_color_frame = colorizer.colorize(depth_frame)
            depth_frame_rgb = np.asanyarray(depth_color_frame.get_data()).copy()

            if depth_color_frame.get_profile().format() == rs.format.bgr8:
                depth_frame_rgb = depth_frame_rgb[:, :, ::-1]

            return rgb_frame, depth_frame_rgb
        finally:
            if started:
                pipeline.stop()


def rgb_frame_to_ppm(frame) -> bytes:
    """Convert an RGB/RGBA numpy-like image array into Tk PhotoImage PPM bytes."""
    if len(frame.shape) == 2:
        height, width = frame.shape
        header = f"P5 {width} {height} 255\n".encode("ascii")
        return header + frame.tobytes()

    height, width = frame.shape[:2]
    if frame.shape[2] == 4:
        frame = frame[:, :, :3]
    header = f"P6 {width} {height} 255\n".encode("ascii")
    return header + frame.tobytes()


class StepperCameraGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self.title("Stepper Motor Controller")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.controller = StepperController()
        self.preview_camera = CameraSource()
        self.realsense_camera = RealSenseCamera()
        self._preview_image: Optional[tk.PhotoImage] = None
        self._rgb_image: Optional[tk.PhotoImage] = None
        self._depth_image: Optional[tk.PhotoImage] = None
        self._capturing = False
        self._busy = False

        self.status_var = tk.StringVar(value=self._initial_status())
        self.pulse_var = tk.StringVar(value=str(DEFAULT_PULSE_US))
        self.gap_var = tk.StringVar(value=str(DEFAULT_GAP_US))

        self._build_ui()
        self.after(50, self._update_camera)

    def _initial_status(self) -> str:
        gpio_state = "GPIO ready" if GPIO_AVAILABLE else "GPIO not found; simulation mode"
        camera_state = f"Live camera: {self.preview_camera.backend}. RealSense snapshot ready"
        return f"{gpio_state}. {camera_state}."

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.grid(row=0, column=0, sticky="nsew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        camera_frame = ttk.LabelFrame(root, text="Camera")
        camera_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        live_frame = ttk.LabelFrame(camera_frame, text="Live Camera Feed")
        live_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=8, pady=(8, 4))

        self.preview_label = ttk.Label(live_frame, text="Starting camera...", anchor="center")
        self.preview_label.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        live_frame.columnconfigure(0, weight=1)
        live_frame.rowconfigure(0, weight=1)

        ttk.Button(
            camera_frame,
            text="Capture RealSense Images",
            command=self.capture_realsense_images,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(8, 4))

        ttk.Label(camera_frame, text="RealSense RGB").grid(row=2, column=0, padx=8, pady=(4, 0))
        ttk.Label(camera_frame, text="RealSense Depth").grid(row=2, column=1, padx=8, pady=(4, 0))

        self.rgb_label = ttk.Label(camera_frame, text="Click capture to show RGB image", anchor="center")
        self.rgb_label.grid(row=3, column=0, sticky="nsew", padx=8, pady=8)

        self.depth_label = ttk.Label(camera_frame, text="Click capture to show depth image", anchor="center")
        self.depth_label.grid(row=3, column=1, sticky="nsew", padx=8, pady=8)

        camera_frame.columnconfigure(0, weight=1)
        camera_frame.columnconfigure(1, weight=1)
        camera_frame.rowconfigure(0, weight=2)
        camera_frame.rowconfigure(3, weight=1)

        controls = ttk.Frame(root)
        controls.grid(row=0, column=1, sticky="new")

        self._build_timing_controls(controls)
        self._build_motor_controls(controls, motor=1, row=1)
        self._build_motor_controls(controls, motor=2, row=2)
        self._build_both_controls(controls, row=3)

        status = ttk.Label(root, textvariable=self.status_var, anchor="w")
        status.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

    def _build_timing_controls(self, parent: ttk.Frame) -> None:
        frame = ttk.LabelFrame(parent, text="Speed / Timing")
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ttk.Label(frame, text="Gap (us)").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(frame, textvariable=self.gap_var, width=10).grid(row=0, column=1, padx=6, pady=4)

        ttk.Label(frame, text="Pulse (us)").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(frame, textvariable=self.pulse_var, width=10).grid(row=1, column=1, padx=6, pady=4)

        ttk.Button(frame, text="Apply", command=self.apply_timing).grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=(4, 6)
        )

    def _build_motor_controls(self, parent: ttk.Frame, motor: int, row: int) -> None:
        frame = ttk.LabelFrame(parent, text=f"Motor {motor}")
        frame.grid(row=row, column=0, sticky="ew", pady=(0, 10))

        steps_var = tk.StringVar(value=str(DEFAULT_STEPS))
        direction_var = tk.StringVar(value="cw")
        setattr(self, f"m{motor}_steps_var", steps_var)
        setattr(self, f"m{motor}_direction_var", direction_var)

        ttk.Label(frame, text="Steps").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(frame, textvariable=steps_var, width=10).grid(row=0, column=1, padx=6, pady=4)

        ttk.Label(frame, text="Direction").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Combobox(
            frame,
            textvariable=direction_var,
            values=("cw", "ccw"),
            state="readonly",
            width=7,
        ).grid(row=1, column=1, padx=6, pady=4)

        ttk.Button(
            frame,
            text=f"Move Motor {motor}",
            command=lambda: self.move_motor(motor),
        ).grid(row=2, column=0, columnspan=2, sticky="ew", padx=6, pady=(4, 6))

    def _build_both_controls(self, parent: ttk.Frame, row: int) -> None:
        frame = ttk.LabelFrame(parent, text="Both Motors (Sequential)")
        frame.grid(row=row, column=0, sticky="ew")

        self.both_steps_var = tk.StringVar(value=str(DEFAULT_STEPS))
        self.both_m1_direction_var = tk.StringVar(value="cw")
        self.both_m2_direction_var = tk.StringVar(value="ccw")

        ttk.Label(frame, text="Steps").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(frame, textvariable=self.both_steps_var, width=10).grid(row=0, column=1, padx=6, pady=4)

        ttk.Label(frame, text="M1 dir").grid(row=1, column=0, sticky="w", padx=6, pady=4)
        ttk.Combobox(
            frame,
            textvariable=self.both_m1_direction_var,
            values=("cw", "ccw"),
            state="readonly",
            width=7,
        ).grid(row=1, column=1, padx=6, pady=4)

        ttk.Label(frame, text="M2 dir").grid(row=2, column=0, sticky="w", padx=6, pady=4)
        ttk.Combobox(
            frame,
            textvariable=self.both_m2_direction_var,
            values=("cw", "ccw"),
            state="readonly",
            width=7,
        ).grid(row=2, column=1, padx=6, pady=4)

        ttk.Button(frame, text="Move Both", command=self.move_both).grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=6, pady=(4, 6)
        )

    def apply_timing(self) -> None:
        try:
            gap_us = int(self.gap_var.get())
            pulse_us = int(self.pulse_var.get())
            self.controller.set_timing(pulse_us=pulse_us, gap_us=gap_us)
        except ValueError as exc:
            messagebox.showerror("Invalid timing", str(exc))
            return

        self.status_var.set(f"Set GAP_US={gap_us}us, PULSE_US={pulse_us}us.")

    def move_motor(self, motor: int) -> None:
        steps_var: tk.StringVar = getattr(self, f"m{motor}_steps_var")
        direction_var: tk.StringVar = getattr(self, f"m{motor}_direction_var")
        try:
            steps = int(steps_var.get())
            direction = direction_var.get()
        except ValueError:
            messagebox.showerror("Invalid move", "Steps must be a whole number.")
            return

        self._run_motion(
            description=f"Moving motor {motor}: {steps} steps {direction}",
            action=lambda: self.controller.move_motor(motor, steps, direction),
        )

    def move_both(self) -> None:
        try:
            steps = int(self.both_steps_var.get())
            direction1 = self.both_m1_direction_var.get()
            direction2 = self.both_m2_direction_var.get()
        except ValueError:
            messagebox.showerror("Invalid move", "Steps must be a whole number.")
            return

        self._run_motion(
            description=f"Moving both: M1 {steps} {direction1}, then M2 {steps} {direction2}",
            action=lambda: self.controller.move_both_sequential(steps, direction1, direction2),
        )

    def _run_motion(self, description: str, action: Callable[[], None]) -> None:
        if self._busy:
            messagebox.showinfo("Motor busy", "A motor move is already running.")
            return

        self._busy = True
        self.status_var.set(description)

        def worker() -> None:
            try:
                action()
            except Exception as exc:  # Keep GPIO worker errors visible in the GUI.
                self.after(0, lambda: messagebox.showerror("Motor error", str(exc)))
                self.after(0, lambda: self.status_var.set(f"Error: {exc}"))
            else:
                self.after(0, lambda: self.status_var.set(f"Done. {description}"))
            finally:
                self.after(0, self._clear_busy)

        threading.Thread(target=worker, daemon=True).start()

    def _clear_busy(self) -> None:
        self._busy = False

    def capture_realsense_images(self) -> None:
        if self._capturing:
            messagebox.showinfo("Camera busy", "A RealSense capture is already running.")
            return

        self._capturing = True
        self.status_var.set("Capturing RealSense RGB and depth images...")

        def worker() -> None:
            try:
                self.preview_camera.stop()
                rgb_frame, depth_frame = self.realsense_camera.capture_rgb_and_depth()
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("RealSense error", str(exc)))
                self.after(0, lambda: self.status_var.set(f"RealSense error: {exc}"))
            else:
                self.after(0, lambda: self._display_realsense_images(rgb_frame, depth_frame))
            finally:
                self.preview_camera.start()
                self.after(0, self._clear_capture_busy)

        threading.Thread(target=worker, daemon=True).start()

    def _display_realsense_images(self, rgb_frame, depth_frame) -> None:
        try:
            self._rgb_image = tk.PhotoImage(data=rgb_frame_to_ppm(rgb_frame), format="PPM")
            self._depth_image = tk.PhotoImage(data=rgb_frame_to_ppm(depth_frame), format="PPM")
        except tk.TclError as exc:
            messagebox.showerror("Camera display error", str(exc))
            self.status_var.set(f"Camera display error: {exc}")
            return

        self.rgb_label.configure(image=self._rgb_image, text="")
        self.depth_label.configure(image=self._depth_image, text="")
        self.status_var.set("Captured RealSense RGB and depth images.")

    def _clear_capture_busy(self) -> None:
        self._capturing = False

    def _update_camera(self) -> None:
        if self._capturing:
            self.preview_label.configure(text="Live feed paused during RealSense capture", image="")
            self.after(50, self._update_camera)
            return

        frame = self.preview_camera.read_rgb_frame()
        if frame is None:
            self.preview_label.configure(text="No live camera feed available")
        else:
            try:
                self._preview_image = tk.PhotoImage(data=rgb_frame_to_ppm(frame), format="PPM")
                self.preview_label.configure(image=self._preview_image, text="")
            except tk.TclError as exc:
                self.preview_label.configure(text=f"Live camera display error: {exc}")

        self.after(50, self._update_camera)

    def on_close(self) -> None:
        self.preview_camera.stop()
        self.controller.cleanup()
        self.destroy()


def main() -> None:
    app = StepperCameraGui()
    app.mainloop()


if __name__ == "__main__":
    main()
