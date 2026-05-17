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
import asyncio
import inspect
import os
import time
from datetime import date, datetime, timedelta
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
PULSE_US = 5
GAP_US = 20
M2_PULSE_US = 5
M2_GAP_US = 10

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

# When moving away from home, the home switch can remain triggered or bounce
# briefly while the axis clears the switch. Safety monitoring starts after the
# switch has been released for a small number of consecutive steps.
HOME_SWITCH_RELEASE_DEBOUNCE_STEPS = 50
HOME_SWITCH_CLEARANCE_MAX_STEPS = 50_000

SCAN_INTERVAL_SECONDS = 60 * 60
# Optional first scan start time. Set to "HH:MM" or "HH:MM:SS" to wait until
# that clock time before starting the first scan cycle. Leave as None to start
# immediately.
FIRST_SCAN_START_TIME = None

LIGHT_ON_HOUR = 7
LIGHT_OFF_HOUR = 21
LIGHT_INITIAL_OFF_DAYS = 4
LIGHT_SETTLE_SECONDS = 2.0
LIGHT_SCHEDULE_CHECK_SECONDS = 60.0


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
    """Captures RGB, colorized depth, and raw depth frames from a RealSense camera."""

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
        depth_raw_frame = np.asanyarray(depth_frame.get_data()).copy()
        depth_color_frame = self._colorizer.colorize(depth_frame)
        depth_frame_rgb = np.asanyarray(depth_color_frame.get_data()).copy()

        if depth_color_frame.get_profile().format() == rs.format.bgr8:
            depth_frame_rgb = depth_frame_rgb[:, :, ::-1]

        return rgb_frame, depth_frame_rgb, depth_raw_frame

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


def save_raw_depth_npy(frame, path: Path) -> None:
    """Save raw depth values with dtype and shape metadata for analysis."""
    path.parent.mkdir(parents=True, exist_ok=True)
    np = __import__("numpy")
    with path.open("wb") as output:
        np.save(output, frame)


class TapoLightController:
    """Controls a TP-Link Tapo P100 smart plug for capture lighting."""

    def __init__(
        self,
        host: Optional[str],
        username: Optional[str],
        password: Optional[str],
        *,
        collection_start_date: date,
        initial_off_days: int = LIGHT_INITIAL_OFF_DAYS,
        on_hour: int = LIGHT_ON_HOUR,
        off_hour: int = LIGHT_OFF_HOUR,
        settle_seconds: float = LIGHT_SETTLE_SECONDS,
        enabled: bool = True,
    ) -> None:
        self.host = host
        self.username = username
        self.password = password
        self.collection_start_date = collection_start_date
        self.initial_off_days = initial_off_days
        self.on_hour = on_hour
        self.off_hour = off_hour
        self.settle_seconds = settle_seconds
        self.enabled = enabled and bool(host)
        self._device = None
        self._on_off = None
        self._loop = None
        self._temporary_light_on = False

        if enabled and any((host, username, password)) and not all((host, username, password)):
            raise ValueError(
                "Tapo light control needs host, username, and password. "
                "Use --tapo-host/--tapo-username/--tapo-password or "
                "TAPO_HOST/TAPO_USERNAME/TAPO_PASSWORD."
            )

    def _desired_on_now(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now()
        initial_off_until = self.collection_start_date.toordinal() + self.initial_off_days
        if now.date().toordinal() < initial_off_until:
            return False
        return self.on_hour <= now.hour < self.off_hour

    def _run_async(self, coroutine):
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
        return self._loop.run_until_complete(coroutine)

    async def _ensure_connected(self) -> None:
        if self._device is not None and self._on_off is not None:
            return
        if not self.enabled:
            return
        try:
            from plugp100.common.credentials import AuthCredential  # type: ignore
            from plugp100.new.components.on_off_component import OnOffComponent  # type: ignore
            from plugp100.new.device_factory import DeviceConnectConfiguration, connect  # type: ignore
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "Tapo P100 light control needs plugp100. Install it on the Raspberry Pi with: "
                "python3 -m pip install plugp100"
            ) from exc

        assert self.host is not None
        assert self.username is not None
        assert self.password is not None

        credentials = AuthCredential(self.username.lower(), self.password)
        config = DeviceConnectConfiguration(host=self.host, credentials=credentials)
        device = await connect(config)
        try:
            await device.update()
            on_off = device.get_component(OnOffComponent)
            if on_off is None:
                raise RuntimeError("Tapo P100 OnOffComponent could not be loaded.")
        except Exception:
            await self._close_device(device)
            raise

        self._device = device
        self._on_off = on_off

    async def _close_device(self, device) -> None:
        try:
            client = getattr(device, "client", None)
            close = getattr(client, "close", None)
            if close is not None:
                result = close()
                if inspect.isawaitable(result):
                    await result
                return

            session = getattr(device, "_client_session", None)
            if session is not None:
                result = session.close()
                if inspect.isawaitable(result):
                    await result
        except Exception:
            pass

    async def _disconnect(self) -> None:
        if self._device is not None:
            await self._close_device(self._device)
        self._device = None
        self._on_off = None

    async def _call_plug(self, operation: str):
        await self._ensure_connected()
        if self._device is None or self._on_off is None:
            return None

        if operation == "is_on":
            await self._device.update()
            raw_state = getattr(self._device, "raw_state", None)
            if isinstance(raw_state, dict) and "device_on" in raw_state:
                return bool(raw_state["device_on"])
            raise RuntimeError(f"Tapo P100 status did not include device_on: {raw_state}")

        if operation == "turn_on":
            await self._on_off.turn_on()
            return None

        if operation == "turn_off":
            await self._on_off.turn_off()
            return None

        raise ValueError(f"Unknown Tapo operation: {operation}")

    def _run_plug_operation(self, operation: str):
        if not self.enabled:
            return None
        try:
            return self._run_async(self._call_plug(operation))
        except Exception:
            try:
                self._run_async(self._disconnect())
            except Exception:
                self._device = None
                self._on_off = None
            return self._run_async(self._call_plug(operation))

    def is_on(self) -> bool:
        if not self.enabled:
            return False
        return bool(self._run_plug_operation("is_on"))

    def turn_on(self) -> None:
        if self.enabled:
            print("Turning lights on.")
            self._run_plug_operation("turn_on")

    def turn_off(self) -> None:
        if self.enabled:
            print("Turning lights off.")
            self._run_plug_operation("turn_off")

    def close(self) -> None:
        if self._loop is None:
            return
        try:
            if not self._loop.is_closed():
                self._run_async(self._disconnect())
                self._loop.close()
        finally:
            self._loop = None
            self._device = None
            self._on_off = None

    def maintain_schedule(self) -> None:
        if not self.enabled:
            return
        should_be_on = self._desired_on_now()
        currently_on = self.is_on()
        if should_be_on and not currently_on:
            self.turn_on()
        elif not should_be_on and currently_on:
            self.turn_off()

    def prepare_for_capture(self) -> None:
        if not self.enabled:
            return

        if self.is_on():
            self._temporary_light_on = False
            return

        self.turn_on()
        self._temporary_light_on = not self._desired_on_now()
        if self.settle_seconds > 0:
            time.sleep(self.settle_seconds)

    def finish_capture(self) -> None:
        if self.enabled and self._temporary_light_on:
            self.turn_off()
        self._temporary_light_on = False


def parse_collection_start_date(value: Optional[str]) -> date:
    if not value:
        return date.today()
    return date.fromisoformat(value)


def next_first_scan_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None

    value = value.strip()
    if not value:
        return None

    for time_format in ("%H:%M:%S", "%H:%M"):
        try:
            parsed_time = datetime.strptime(value, time_format)
            break
        except ValueError:
            parsed_time = None
    else:
        raise ValueError("First scan start time must be HH:MM or HH:MM:SS.")

    now = datetime.now()
    first_scan_at = now.replace(
        hour=parsed_time.hour,
        minute=parsed_time.minute,
        second=parsed_time.second,
        microsecond=0,
    )
    if first_scan_at <= now:
        first_scan_at += timedelta(days=1)
    return first_scan_at


def sleep_with_light_schedule(
    seconds: float,
    light_controller: TapoLightController,
    check_seconds: float = LIGHT_SCHEDULE_CHECK_SECONDS,
) -> None:
    end_time = time.monotonic() + seconds
    check_seconds = max(1.0, check_seconds)
    light_controller.maintain_schedule()
    while True:
        remaining = end_time - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(remaining, check_seconds))
        light_controller.maintain_schedule()


class TrayScanner:
    def __init__(self, output_dir: Path, light_controller: Optional[TapoLightController] = None) -> None:
        self.output_dir = output_dir
        self.light_controller = light_controller
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

    def _axis_timing_us(self, axis: str) -> Tuple[int, int]:
        if axis == "x":
            return PULSE_US, GAP_US
        if axis == "y":
            return M2_PULSE_US, M2_GAP_US
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
        other_axis = "y" if axis == "x" else "x"
        _, _, other_switch_pin = self._axis_pins(other_axis)
        set_dir(dir_pin, direction)

        clearing_initial_home_switch = allow_initial_home_clear and not stop_on_home
        release_clear_count = 0
        other_switch_was_triggered = limit_triggered(other_switch_pin)
        pulse_us, gap_us = self._axis_timing_us(axis)
        pulse_delay = pulse_us / 1_000_000
        gap_delay = gap_us / 1_000_000

        for completed_steps in range(steps):
            switch_is_triggered = limit_triggered(switch_pin)
            if limit_triggered(other_switch_pin) and not other_switch_was_triggered:
                hi_z(pul_pin)
                raise MotionSafetyError(
                    f"{other_axis.upper()} home switch triggered unexpectedly during {axis.upper()} move."
                )

            if stop_on_home and switch_is_triggered:
                hi_z(pul_pin)
                return completed_steps

            if not stop_on_home:
                if clearing_initial_home_switch:
                    if switch_is_triggered:
                        release_clear_count = 0
                        if completed_steps >= HOME_SWITCH_CLEARANCE_MAX_STEPS:
                            hi_z(pul_pin)
                            raise MotionSafetyError(
                                f"{axis.upper()} home switch did not release within "
                                f"{HOME_SWITCH_CLEARANCE_MAX_STEPS} steps while moving away."
                            )
                    else:
                        release_clear_count += 1
                        if release_clear_count >= HOME_SWITCH_RELEASE_DEBOUNCE_STEPS:
                            clearing_initial_home_switch = False
                elif switch_is_triggered:
                    hi_z(pul_pin)
                    raise MotionSafetyError(
                        f"{axis.upper()} home switch triggered unexpectedly during move."
                    )

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

        if self.light_controller is not None:
            self.light_controller.prepare_for_capture()
        try:
            rpi_frame = self.rpi_camera.read_rgb_frame()
            if rpi_frame is None:
                raise RuntimeError("RPi camera did not return an image.")

            realsense_rgb, realsense_depth, realsense_depth_raw = (
                self.realsense_camera.capture_rgb_and_depth()
            )

            save_rgb_ppm(rpi_frame, self.output_dir / f"{name_prefix}_rpi_rgb.ppm")
            save_rgb_ppm(realsense_rgb, self.output_dir / f"{name_prefix}_realsense_rgb.ppm")
            save_rgb_ppm(realsense_depth, self.output_dir / f"{name_prefix}_realsense_depth.ppm")
            save_raw_depth_npy(
                realsense_depth_raw,
                self.output_dir / f"{name_prefix}_realsense_depth_raw.npy",
            )
        finally:
            if self.light_controller is not None:
                self.light_controller.finish_capture()

    def run_scan_cycle(self) -> None:
        self.tray_number = 0
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
            if y_index == 0:
                # The home switch can sit slightly past the nominal tray spacing.
                # Use the configured homing allowance for the last Y move.
                self.home_y()
            else:
                self.move_y_steps(-Y_STEPS_BETWEEN_TRAYS)
            self.scan_tray(1, y_index)

        if not limit_triggered(Y_HOME_SWITCH):
            raise MotionSafetyError("Y axis is not at home after the final tray.")

        self.home_x()
        print("Scan cycle complete.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run 8-tray scan cycles every hour.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Base folder for captured images. Defaults to scan_images.",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=SCAN_INTERVAL_SECONDS,
        help="Seconds between scan starts. Defaults to 3600.",
    )
    parser.add_argument(
        "--first-start-time",
        default=os.environ.get("FIRST_SCAN_START_TIME") or FIRST_SCAN_START_TIME,
        help=(
            "Clock time for the first scan cycle as HH:MM or HH:MM:SS. "
            "Can also be set with FIRST_SCAN_START_TIME. Defaults to starting immediately."
        ),
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one scan cycle and exit.",
    )
    parser.add_argument(
        "--tapo-host",
        default=os.environ.get("TAPO_HOST") or os.environ.get("PLUG_IP"),
        help="Tapo P100 IP address or hostname. Can also be set with TAPO_HOST or PLUG_IP.",
    )
    parser.add_argument(
        "--tapo-username",
        default=os.environ.get("TAPO_USERNAME") or os.environ.get("TAPO_EMAIL"),
        help="Tapo account username/email. Can also be set with TAPO_USERNAME or TAPO_EMAIL.",
    )
    parser.add_argument(
        "--tapo-password",
        default=os.environ.get("TAPO_PASSWORD"),
        help="Tapo account password. Can also be set with TAPO_PASSWORD.",
    )
    parser.add_argument(
        "--collection-start-date",
        default=os.environ.get("COLLECTION_START_DATE"),
        help=(
            "Data collection start date as YYYY-MM-DD. Lights stay off by default "
            "for the first 4 days. Defaults to today if omitted."
        ),
    )
    parser.add_argument(
        "--no-light-control",
        action="store_true",
        help="Disable Tapo light control even if Tapo settings are provided.",
    )
    parser.add_argument(
        "--light-settle-seconds",
        type=float,
        default=LIGHT_SETTLE_SECONDS,
        help="Seconds to wait after temporarily switching lights on before capturing.",
    )
    parser.add_argument(
        "--light-schedule-check-seconds",
        type=float,
        default=LIGHT_SCHEDULE_CHECK_SECONDS,
        help="How often to enforce the 7am-9pm light schedule while waiting between scans.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_output_dir = args.output_dir or Path("scan_images")
    base_output_dir.mkdir(parents=True, exist_ok=True)

    setup_gpio()
    collection_start_date = parse_collection_start_date(args.collection_start_date)
    light_controller = TapoLightController(
        args.tapo_host,
        args.tapo_username,
        args.tapo_password,
        collection_start_date=collection_start_date,
        settle_seconds=args.light_settle_seconds,
        enabled=not args.no_light_control,
    )
    if light_controller.enabled:
        print(
            "Light control enabled: lights are off by default for the first "
            f"{LIGHT_INITIAL_OFF_DAYS} days from {collection_start_date.isoformat()}, "
            f"then on from {LIGHT_ON_HOUR:02d}:00 to {LIGHT_OFF_HOUR:02d}:00."
        )
    else:
        print("Light control disabled. Provide --tapo-host, --tapo-username, and --tapo-password to enable it.")

    scanner = TrayScanner(base_output_dir, light_controller=light_controller)
    print(f"Saving scan runs under: {base_output_dir.resolve()}")

    try:
        first_scan_at = next_first_scan_datetime(args.first_start_time)
        if first_scan_at is not None:
            sleep_seconds = max(0.0, (first_scan_at - datetime.now()).total_seconds())
            print(f"First scan starts at approximately {first_scan_at.strftime('%Y-%m-%d %H:%M:%S')}.")
            sleep_with_light_schedule(
                sleep_seconds,
                light_controller,
                check_seconds=args.light_schedule_check_seconds,
            )

        while True:
            cycle_started = time.monotonic()
            run_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            scanner.output_dir = base_output_dir / f"run_{run_timestamp}"
            scanner.output_dir.mkdir(parents=True, exist_ok=True)

            print(f"\nSaving this scan to: {scanner.output_dir.resolve()}")
            scanner.run_scan_cycle()

            if args.once:
                break

            elapsed = time.monotonic() - cycle_started
            sleep_seconds = max(0.0, args.interval_seconds - elapsed)
            next_run = datetime.now().timestamp() + sleep_seconds
            next_run_text = datetime.fromtimestamp(next_run).strftime("%Y-%m-%d %H:%M:%S")
            print(f"Next scan starts at approximately {next_run_text}.")
            sleep_with_light_schedule(
                sleep_seconds,
                light_controller,
                check_seconds=args.light_schedule_check_seconds,
            )
    except KeyboardInterrupt:
        print("\nScan interrupted by user.")
    except Exception as exc:
        print(f"\nERROR: {exc}")
        raise
    finally:
        scanner.close()
        light_controller.close()
        GPIO.cleanup()
        print("GPIO cleaned up.")


if __name__ == "__main__":
    main()
