#!/usr/bin/env python3
"""
Run one full 8-tray scan cycle for a 2-axis Raspberry Pi motion system.

System layout:
  - X axis: 2 tray columns
  - Y axis: 4 tray rows
  - Camera mounted on the moving stage

Scan order is column-wise:
  Tray 1: X0, Y0
  Tray 2: X0, Y1
  Tray 3: X0, Y2
  Tray 4: X0, Y3
  Tray 5: X1, Y3
  Tray 6: X1, Y2
  Tray 7: X1, Y1
  Tray 8: X1, Y0

This second-column reverse-Y scan leaves Y at home at the end. After all
captures, only X is homed.

Run on the Raspberry Pi with:
    python3 tray_scan_cycle.py
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


# -------- Pin mapping (BCM numbering) --------
# Motor 1 is X, motor 2 is Y.
M1_PUL = 23
M1_DIR = 24

M2_DIR = 14
M2_PUL = 15

X_HOME_SWITCH = 19
Y_HOME_SWITCH = 26


# -------- Motion parameters --------
PULSE_US = 10
GAP_US = 30

X_STEPS_PER_TRAY = 75_000
Y_STEPS_BETWEEN_TRAYS = 465_000

X_COLUMNS = 2
Y_ROWS = 4

# Home is max CW.
HOME_DIRECTION = "cw"
AWAY_FROM_HOME_DIRECTION = "ccw"

# Safety thresholds for homing. These are intentionally larger than the normal
# travel needed for this 2 x 4 tray grid.
X_HOME_MAX_STEPS = 100_000
Y_HOME_MAX_STEPS = 1_600_000

# The request specifies: switch triggered == GPIO HIGH (1).
LIMIT_TRIGGERED_STATE = 1


try:
    import RPi.GPIO as GPIO  # type: ignore
except ModuleNotFoundError:
    class _MockGPIO:
        BCM = "BCM"
        OUT = "OUT"
        IN = "IN"
        LOW = 0
        HIGH = 1
        PUD_UP = "PUD_UP"

        @staticmethod
        def setmode(_mode: str) -> None:
            return None

        @staticmethod
        def setwarnings(_enabled: bool) -> None:
            return None

        @staticmethod
        def setup(_pin: int, _mode: str, pull_up_down: Optional[str] = None) -> None:
            return None

        @staticmethod
        def output(_pin: int, _value: int) -> None:
            return None

        @staticmethod
        def input(_pin: int) -> int:
            return 0

        @staticmethod
        def cleanup() -> None:
            return None

    GPIO = _MockGPIO()  # type: ignore


# -------- GPIO helpers: open-collector style --------
def drive_low(pin: int) -> None:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)


def hi_z(pin: int) -> None:
    GPIO.setup(pin, GPIO.IN)


def set_dir(dir_pin: int, direction: str) -> None:
    """
    direction: 'cw' or 'ccw'
    With DIR+ tied to 5V:
      - drive LOW  -> opto ON
      - Hi-Z       -> opto OFF
    Which one corresponds to CW vs CCW depends on motor wiring.
    """
    d = direction.strip().lower()
    if d in ("cw", "c", "1", "+"):
        hi_z(dir_pin)
    elif d in ("ccw", "cc", "0", "-", "rev", "r"):
        drive_low(dir_pin)
    else:
        raise ValueError("Direction must be cw or ccw (or + / -).")


def step_pulses(pul_pin: int, steps: int, pulse_us: int = PULSE_US, gap_us: int = GAP_US) -> None:
    for _ in range(steps):
        drive_low(pul_pin)
        time.sleep(pulse_us / 1_000_000)
        hi_z(pul_pin)
        time.sleep(gap_us / 1_000_000)


def limit_triggered(pin: int) -> bool:
    return GPIO.input(pin) == LIMIT_TRIGGERED_STATE


def setup_gpio() -> None:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    for pin in (M1_PUL, M1_DIR, M2_PUL, M2_DIR):
        hi_z(pin)

    GPIO.setup(X_HOME_SWITCH, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(Y_HOME_SWITCH, GPIO.IN, pull_up_down=GPIO.PUD_UP)


class MotionSafetyError(RuntimeError):
    """Raised when motion must stop because a limit switch or homing check failed."""


class CameraSource:
    """RPi camera capture wrapper. Uses the same Picamera2/OpenCV pattern tested in the GUI."""

    def __init__(self, width: int = 640, height: int = 480) -> None:
        self.width = width
        self.height = height
        self.backend = "disabled"
        self._picam2 = None
        self._capture = None
        self._cv2 = None

        self.start()

    def start(self) -> None:
        if self._picam2 is not None or self._capture is not None:
            return
        self.backend = "disabled"
        self._start_picamera2() or self._start_opencv()

    def _start_picamera2(self) -> bool:
        try:
            from picamera2 import Picamera2  # type: ignore
        except ModuleNotFoundError:
            return False

        picam2 = None
        try:
            picam2 = Picamera2()
            config = picam2.create_still_configuration(
                main={"size": (self.width, self.height), "format": "RGB888"}
            )
            picam2.configure(config)
            picam2.start()
        except Exception:
            if picam2 is not None:
                try:
                    picam2.close()
                except Exception:
                    pass
            return False

        self._picam2 = picam2
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
        if self._picam2 is not None:
            return self._picam2.capture_array()

        if self._capture is not None and self._cv2 is not None:
            ok, frame = self._capture.read()
            if not ok:
                return None
            return self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)

        return None

    def stop(self) -> None:
        if self._picam2 is not None:
            try:
                self._picam2.stop()
            finally:
                self._picam2.close()
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
        self._np = None
        self._rs = None
        self._pipeline = None
        self._align = None
        self._colorizer = None
        self._started = False
        self._warmed_up = False

    def _load_dependencies(self) -> None:
        if self._np is not None and self._rs is not None:
            return
        try:
            import numpy as np  # type: ignore
            import pyrealsense2 as rs  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "RealSense capture needs pyrealsense2 and numpy. "
                "Install the Intel RealSense SDK Python package on the Raspberry Pi."
            ) from exc

        self._np = np
        self._rs = rs

    def _start(self) -> None:
        self._load_dependencies()
        if self._started:
            return

        rs = self._rs
        assert rs is not None

        self._pipeline = rs.pipeline()
        config = rs.config()
        config.enable_stream(rs.stream.color, self.width, self.height, rs.format.rgb8, self.fps)
        config.enable_stream(rs.stream.depth, self.width, self.height, rs.format.z16, self.fps)

        self._pipeline.start(config)
        self._align = rs.align(rs.stream.color)
        self._colorizer = rs.colorizer()
        self._started = True
        self._warmed_up = False

    def stop(self) -> None:
        if self._pipeline is not None and self._started:
            self._pipeline.stop()
        self._pipeline = None
        self._align = None
        self._colorizer = None
        self._started = False
        self._warmed_up = False

    def _capture_once(self):
        np = self._np
        rs = self._rs
        assert np is not None
        assert rs is not None
        assert self._pipeline is not None
        assert self._align is not None
        assert self._colorizer is not None

        frames = None
        frame_count = 8 if not self._warmed_up else 1
        for _ in range(frame_count):
            frames = self._align.process(self._pipeline.wait_for_frames(10000))

        self._warmed_up = True
        if frames is None:
            raise RuntimeError("No frames received from the RealSense camera.")

        color_frame = frames.get_color_frame()
        depth_frame = frames.get_depth_frame()
        if not color_frame or not depth_frame:
            raise RuntimeError("RealSense did not return both RGB and depth frames.")

        rgb_frame = np.asanyarray(color_frame.get_data()).copy()
        depth_color_frame = self._colorizer.colorize(depth_frame)
        depth_frame_rgb = np.asanyarray(depth_color_frame.get_data()).copy()

        if depth_color_frame.get_profile().format() == rs.format.bgr8:
            depth_frame_rgb = depth_frame_rgb[:, :, ::-1]

        return rgb_frame, depth_frame_rgb

    def capture_rgb_and_depth(self):
        self._start()
        try:
            return self._capture_once()
        except Exception:
            self.stop()
            self._start()
            return self._capture_once()


def save_rgb_ppm(frame, path: Path) -> None:
    """Save an RGB/RGBA or grayscale numpy-like frame without adding new image dependencies."""
    path.parent.mkdir(parents=True, exist_ok=True)

    if len(frame.shape) == 2:
        height, width = frame.shape
        header = f"P5 {width} {height} 255\n".encode("ascii")
        data = frame.tobytes()
    else:
        height, width = frame.shape[:2]
        if frame.shape[2] == 4:
            frame = frame[:, :, :3]
        header = f"P6 {width} {height} 255\n".encode("ascii")
        data = frame.tobytes()

    path.write_bytes(header + data)


class TrayScanner:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.rpi_camera = CameraSource()
        self.realsense_camera = RealSenseCamera()
        self.tray_number = 0

    def close(self) -> None:
        self.realsense_camera.stop()
        self.rpi_camera.stop()

    def _axis_pins(self, axis: str) -> Tuple[int, int, int]:
        if axis == "x":
            return M1_PUL, M1_DIR, X_HOME_SWITCH
        if axis == "y":
            return M2_PUL, M2_DIR, Y_HOME_SWITCH
        raise ValueError("Axis must be 'x' or 'y'.")

    def _step_axis_monitored(
        self,
        axis: str,
        steps: int,
        direction: str,
        *,
        stop_on_home: bool,
        allow_initial_home_clear: bool = False,
    ) -> int:
        pul_pin, dir_pin, switch_pin = self._axis_pins(axis)
        set_dir(dir_pin, direction)

        released_after_start = not limit_triggered(switch_pin)
        pulse_delay = PULSE_US / 1_000_000
        gap_delay = GAP_US / 1_000_000

        for completed_steps in range(steps):
            switch_is_triggered = limit_triggered(switch_pin)
            if stop_on_home and switch_is_triggered:
                hi_z(pul_pin)
                return completed_steps

            if not stop_on_home:
                if switch_is_triggered:
                    if allow_initial_home_clear and not released_after_start:
                        pass
                    else:
                        hi_z(pul_pin)
                        raise MotionSafetyError(
                            f"{axis.upper()} home switch triggered unexpectedly during move."
                        )
                else:
                    released_after_start = True

            drive_low(pul_pin)
            time.sleep(pulse_delay)
            hi_z(pul_pin)
            time.sleep(gap_delay)

        if stop_on_home and limit_triggered(switch_pin):
            return steps

        if stop_on_home:
            hi_z(pul_pin)
            raise MotionSafetyError(
                f"{axis.upper()} homing failed: switch did not trigger within {steps} steps."
            )

        return steps

    def move_x_steps(self, steps: int) -> None:
        direction = AWAY_FROM_HOME_DIRECTION if steps >= 0 else HOME_DIRECTION
        print(f"Moving X {abs(steps)} steps {direction}")
        self._step_axis_monitored(
            "x",
            abs(steps),
            direction,
            stop_on_home=False,
            allow_initial_home_clear=(direction == AWAY_FROM_HOME_DIRECTION),
        )

    def move_y_steps(self, steps: int, *, stop_on_home: bool = False) -> None:
        direction = AWAY_FROM_HOME_DIRECTION if steps >= 0 else HOME_DIRECTION
        print(f"Moving Y {abs(steps)} steps {direction}")
        self._step_axis_monitored(
            "y",
            abs(steps),
            direction,
            stop_on_home=stop_on_home,
            allow_initial_home_clear=(direction == AWAY_FROM_HOME_DIRECTION),
        )

    def home_x(self) -> None:
        print("Homing X...")
        if limit_triggered(X_HOME_SWITCH):
            print("X already home.")
            return
        steps = self._step_axis_monitored(
            "x",
            X_HOME_MAX_STEPS,
            HOME_DIRECTION,
            stop_on_home=True,
        )
        print(f"X homed after {steps} steps.")

    def home_y(self) -> None:
        print("Homing Y...")
        if limit_triggered(Y_HOME_SWITCH):
            print("Y already home.")
            return
        steps = self._step_axis_monitored(
            "y",
            Y_HOME_MAX_STEPS,
            HOME_DIRECTION,
            stop_on_home=True,
        )
        print(f"Y homed after {steps} steps.")

    def scan_tray(self, x_index: int, y_index: int) -> None:
        self.tray_number += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        name_prefix = f"tray{self.tray_number:02d}_x{x_index}_y{y_index}_{timestamp}"
        print(f"Capturing Tray {self.tray_number}: X{x_index}, Y{y_index}")

        rpi_frame = self.rpi_camera.read_rgb_frame()
        if rpi_frame is None:
            raise RuntimeError("RPi camera did not return an image.")

        realsense_rgb, realsense_depth = self.realsense_camera.capture_rgb_and_depth()

        save_rgb_ppm(rpi_frame, self.output_dir / f"{name_prefix}_rpi_rgb.ppm")
        save_rgb_ppm(realsense_rgb, self.output_dir / f"{name_prefix}_realsense_rgb.ppm")
        save_rgb_ppm(realsense_depth, self.output_dir / f"{name_prefix}_realsense_depth.ppm")

    def run_scan_cycle(self) -> None:
        print("Starting scan cycle.")
        self.home_x()
        self.home_y()

        self.scan_tray(0, 0)
        for y_index in range(1, Y_ROWS):
            self.move_y_steps(Y_STEPS_BETWEEN_TRAYS)
            self.scan_tray(0, y_index)

        self.move_x_steps(X_STEPS_PER_TRAY)
        self.scan_tray(1, Y_ROWS - 1)

        for y_index in range(Y_ROWS - 2, -1, -1):
            self.move_y_steps(-Y_STEPS_BETWEEN_TRAYS, stop_on_home=(y_index == 0))
            self.scan_tray(1, y_index)

        if not limit_triggered(Y_HOME_SWITCH):
            raise MotionSafetyError("Y axis is not at home after the final tray.")

        self.home_x()
        print("Scan cycle complete.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one 8-tray scan cycle.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Folder for captured images. Defaults to scan_images/run_<timestamp>.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or Path("scan_images") / f"run_{run_timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    setup_gpio()
    scanner = TrayScanner(output_dir)
    print(f"Saving images to: {output_dir.resolve()}")

    try:
        scanner.run_scan_cycle()
    except KeyboardInterrupt:
        print("\nScan interrupted by user.")
    except Exception as exc:
        print(f"\nERROR: {exc}")
        raise
    finally:
        scanner.close()
        GPIO.cleanup()
        print("GPIO cleaned up.")


if __name__ == "__main__":
    main()
