#!/usr/bin/env python3
"""
soft_robotics_hand_sim.py
=========================
Five-finger real-time simulator for the Soft Robotic Rehabilitation Hand / Glove.

Models the CONTROL LAW of the bench firmware VAA0.0.5.2_Mega2560_SimpleRefined
(the minimal proportional controller line), NOT the older single-finger PID +
timed-FSM auto-cycle. A MATLAB counterpart of this demonstrator exists in the
private development repository.

FIRMWARE-FAITHFUL (mirrors updateControl()):
  * Operator sets ONE common target angle (0..80 deg).
  * Control acts on the AVERAGE of five flex angles.
  * Proportional-ONLY both directions (no I, no D):
        pump PWM = clamp(Kp * |error|), with a min-PWM floor.
  * error >  +deadband -> PRESSURE path (central 3/2 ON); each finger valve
        OPEN while that finger is still below (target - deadband), else CLOSED.
  * error <  -deadband -> VACUUM path (central 3/2 OFF); ALL finger valves OPEN.
  * |error| <= deadband -> HOLD: pumps OFF, ALL finger valves CLOSED (trap).
  * Central-valve path switch guarded by a settle window with pumps OFF.
  * Pressure and vacuum pumps are mutually exclusive.
  * Safe-Stop forces the firmware safe state: pumps OFF, vacuum/opening path,
        all finger valves OPEN.
  * Flex sensors are 10-bit (0..1023), per-finger linear cal from rawOpen[]/
        rawFlex[] in the .ino, trimmed mean of 5 samples.

SIMULATION-ONLY (NOT firmware behaviour):
  * The pneumatic plant (pressure -> finger motion) is a semi-empirical
        illustration; firmware models no plant.
  * "Auto target cycle" alternates the single operator target between a flex
        and an extend setpoint on a timer, i.e. it emulates an operator typing
        two ANGLE commands. The firmware holds one target (no auto-cycle).
  * Per-finger response spread is injected so isolation is visible.

Validation level: L1 (software simulation). NOT bench/pneumatic/hardware proof.

Run (interactive GUI):   python3 soft_robotics_hand_sim.py
Headless self-check:     python3 soft_robotics_hand_sim.py --selftest
"""

import argparse
import math
from datetime import datetime

import numpy as np

NF = 5                      # number of fingers
FLEX_SAMPLES = 5            # trimmed-mean sample count (mirrors firmware)
FINGER_NAMES = ["Thumb", "Index", "Middle", "Ring", "Pinky"]


# ======================================================================
#  MODEL  (pure; no plotting -- importable and testable on its own)
# ======================================================================
class HandControllerSim:
    """Five-finger glove controller + illustrative pneumatic plant.

    The controller half is a faithful port of updateControl() in
    VAA0.0.5.2. The plant half is simulation-only.
    """

    def __init__(self, seed: int = 7):
        self.rng = np.random.default_rng(seed)

        # ---- Control constants (mirrored from the .ino) ----
        self.dt = 0.02
        self.window_time = 22.0
        self.target_min = 0.0
        self.target_max = 80.0
        self.deadband_deg = 3.0          # DEADBAND_DEG
        self.kp_pressure = 10.0          # KpPressure
        self.kp_vacuum = 3.5             # KpVacuum
        self.min_pwm_pressure = 50       # MIN_PWM_PRESSURE
        self.min_pwm_vacuum = 50         # MIN_PWM_VACUUM
        self.pwm_max = 255
        self.valve_settle = 0.08         # VALVE_SETTLE_MS = 80 ms
        self.angle_at_flex = 80.0        # ANGLE_AT_FLEX_DEG

        # Per-finger 10-bit calibration, copied from the .ino defaults.
        self.raw_open = np.array([556, 560, 617, 463, 725], dtype=float)
        self.raw_flex = np.array([765, 746, 750, 699, 919], dtype=float)

        # ---- Plant model (SIMULATION ONLY, illustrative) ----
        self.pressure_max = 55.0         # kPa shared pressure source
        self.vacuum_mag = 30.0           # kPa shared vacuum magnitude
        self.p_half = 14.0
        self.angle_max = 85.0            # ceiling > 80 so 80 is reachable
        self.sensor_noise_adc = 4.0
        self.finger_spread_pct = 15.0
        self.safe_angle = 82.0
        self.finger_gain_base = np.array([1.12, 0.95, 1.05, 0.88, 1.00])

        # Two regimes for the pressure path. The LOSSY (slow-pressure) regime is
        # the physical truth: air builds slowly through valve/tubing restriction
        # while the membrane tracks pressure quickly, so per-finger isolation
        # catches each finger at the correct pressure -> no overshoot. The IDEAL
        # (fast-pressure) regime lets pressure outrun the actuator -> the
        # isolation point traps excess pressure -> overshoot / hunting.
        self.tau_pressure_fast = 0.18    # pump->manifold fill (lossless)
        self.tau_pressure_slow = 0.55    # pump->manifold fill (restricted)
        self.tau_vacuum_fast = 0.16
        self.tau_vacuum_slow = 0.45
        self.tau_couple_fast = 0.10      # manifold<->finger (lossless)
        self.tau_couple_slow = 0.45      # manifold<->finger (restricted)
        self.tau_motion_fast = 0.10      # membrane pressure->angle (tracks fast)
        self.tau_motion_slow = 0.16      # with viscoelastic creep

        # ---- Pneumatic losses (toggleable). These make the closed loop
        #      critically/over-damped for all 0 <= Kp <= 20, matching hardware.
        #      The firmware MIN_PWM floor (50) and 0..255 saturation upstream
        #      are NEVER changed. The pump dead-zone only models that a real
        #      pump moves almost no air at low PWM, so the floored 50-PWM kick
        #      is a *weak* input, not a strong impulse. NOTE: pump spin-up lag
        #      was deliberately omitted -- it adds phase lag that *reduces*
        #      stability, and the bench hardware shows no such lag-driven
        #      hunting. The dominant real damping is flow restriction. ----
        self.loss_flow = True            # valve/tubing flow restriction (slow P)
        self.loss_pump = True            # low-PWM pump dead-zone
        self.loss_leak = True            # continuous manifold / finger leakage
        self.loss_visc = True            # viscoelastic membrane creep
        self.pump_deadzone_pwm = 30.0    # below this PWM the pump moves ~no air
        self.q_max = 15.0                # max pressure transfer rate, kPa/s
        self.leak_man = 0.03             # manifold leak coefficient
        self.leak_finger = 0.006         # trapped-finger leak coefficient

        # ---- Auto target cycle (SIMULATION ONLY) ----
        self.auto_cycle = True
        self.flex_set = 60.0
        self.extend_set = 5.0
        self.flex_dwell = 5.5
        self.extend_dwell = 4.5
        self.manual_target = 60.0        # used when auto_cycle is off

        self.reset()

    # ------------------------------------------------------------------
    def reset(self):
        self.t = 0.0
        self.running = False             # firmware "running" flag
        self.central_pressure = False    # False = vacuum/opening path
        self.valve_switch_time = -10.0
        self.finger_open = np.ones(NF, dtype=bool)
        self.angle_true = np.zeros(NF)
        self.p_finger = np.zeros(NF)
        self.angle_filt = np.zeros(NF)
        self.manifold = 0.0
        self.src = 0.0                   # lagged pump source pressure (signed)
        self.mode = "H"
        self.p_pwm = 0
        self.v_pwm = 0
        self.target = self.flex_set
        self.error = 0.0
        self.peak_angle = 0.0
        self.peak_pressure = 0.0
        self.cycle_count = 0
        self.in_flex = True
        self.phase_start = 0.0

    # ---- calibration maps ----
    def _angle_to_raw(self, angle):
        span = self.raw_flex - self.raw_open
        return self.raw_open + (angle / self.angle_at_flex) * span

    def _raw_to_angle(self, raw):
        span = self.raw_flex - self.raw_open
        span = np.where(span == 0, 1.0, span)
        a = (raw - self.raw_open) * self.angle_at_flex / span
        return np.clip(a, self.target_min, self.target_max)

    def _effective_gains(self):
        s = self.finger_spread_pct / 15.0          # 15% == base spread
        g = 1.0 + (self.finger_gain_base - 1.0) * s
        return np.maximum(g, 0.2)

    def _proportional_command(self, err_mag, kp, min_pwm):
        # Direct port of proportionalCommand(): deadband, round, floor, clamp.
        if err_mag <= self.deadband_deg:
            return 0
        cmd = int(round(kp * err_mag))
        if 0 < cmd < min_pwm:
            cmd = min_pwm
        return int(min(max(cmd, 0), self.pwm_max))

    def _set_central(self, to_pressure):
        if to_pressure != self.central_pressure:
            self.valve_switch_time = self.t      # path changed -> settle timer
        self.central_pressure = to_pressure

    def _valve_settled(self):
        return (self.t - self.valve_switch_time) >= self.valve_settle

    # ------------------------------------------------------------------
    def _update_target(self):
        if self.auto_cycle:
            dwell = self.flex_dwell if self.in_flex else self.extend_dwell
            if (self.t - self.phase_start) >= dwell:
                if not self.in_flex:                 # extend -> flex = one cycle
                    self.cycle_count += 1
                self.in_flex = not self.in_flex
                self.phase_start = self.t
            self.target = self.flex_set if self.in_flex else self.extend_set
        else:
            self.target = self.manual_target
        self.target = float(np.clip(self.target, self.target_min, self.target_max))

    # ------------------------------------------------------------------
    def _control(self):
        """Faithful port of updateControl() acting on the average angle."""
        db = self.deadband_deg
        avg = float(np.mean(self.angle_filt))
        self.error = self.target - avg
        self.p_pwm = 0
        self.v_pwm = 0

        if not self.running:
            # stopAllActuatorsSafe(): vacuum path, all valves open, pumps off
            self._set_central(False)
            self.finger_open[:] = True
            self.mode = "H"
            return

        if self.error > db:
            # PRESSURE / FLEXION: isolate fingers that reached target
            self._set_central(True)
            self.finger_open = self.angle_filt < (self.target - db)
            self.mode = "P"
            if self._valve_settled():
                self.p_pwm = self._proportional_command(
                    self.error, self.kp_pressure, self.min_pwm_pressure)

        elif (-self.error) > db:
            # VACUUM / OPENING: never isolate
            self._set_central(False)
            self.finger_open[:] = True
            self.mode = "V"
            if self._valve_settled():
                self.v_pwm = self._proportional_command(
                    -self.error, self.kp_vacuum, self.min_pwm_vacuum)

        else:
            # HOLD: pumps off, all finger valves closed (trap pressure)
            self.finger_open[:] = False
            self.mode = "H"

    # ------------------------------------------------------------------
    def _plant(self):
        """Illustrative shared-manifold pneumatic plant (sim only).

        Damping comes from slowing the PRESSURE path (flow restriction) while
        the membrane tracks pressure quickly, so per-finger isolation traps the
        correct pressure and the average never overshoots the target. This is
        critically/over-damped for all 0 <= Kp <= 20. The control law, MIN_PWM
        floor and 0..255 saturation upstream are unchanged.
        """
        vac_max = -self.vacuum_mag
        dt = self.dt

        tau_p = self.tau_pressure_slow if self.loss_flow else self.tau_pressure_fast
        tau_v = self.tau_vacuum_slow if self.loss_flow else self.tau_vacuum_fast
        tau_c = self.tau_couple_slow if self.loss_flow else self.tau_couple_fast
        tau_m = self.tau_motion_slow if self.loss_visc else self.tau_motion_fast

        # Active pump PWM for the current central path (mutual exclusion holds).
        pwm = self.p_pwm if self.central_pressure else self.v_pwm

        # Pump dead-zone: at low PWM the pump moves almost no air, so the
        # firmware's floored 50-PWM kick is a weak input, not a hard step.
        if self.loss_pump and self.pump_deadzone_pwm > 0.0:
            thr = self.pump_deadzone_pwm
            duty_eff = 0.0 if pwm <= thr else (pwm - thr) / (self.pwm_max - thr)
        else:
            duty_eff = pwm / self.pwm_max
        shape = math.sqrt(max(duty_eff, 0.0))

        self.src = (self.pressure_max * shape) if self.central_pressure \
            else (-self.vacuum_mag * shape)

        # Manifold driven by the pump only while it runs; when the pump is off
        # the manifold / closed-valve volume holds pressure (it is not sucked to
        # zero), so a leak-driven re-kick does not dump finger pressure. Flow
        # rate-limited (orifice) when lossy.
        tau_src = tau_p if self.central_pressure else tau_v
        if pwm > 0:
            rate_man = (self.src - self.manifold) / tau_src
            if self.loss_flow:
                rate_man = max(-self.q_max, min(self.q_max, rate_man))
        else:
            rate_man = 0.0
        leak_m = (self.leak_man * self.manifold) if self.loss_leak else 0.0
        self.manifold = float(np.clip(self.manifold + dt * (rate_man - leak_m),
                                      vac_max - 5, self.pressure_max + 8))

        gains = self._effective_gains()

        # Per-finger: open valve couples to manifold (rate-limited), closed
        # valve traps pressure (bleed only). Leakage applies when enabled.
        rate_f = (self.manifold - self.p_finger) / tau_c
        if self.loss_flow:
            rate_f = np.clip(rate_f, -self.q_max, self.q_max)
        leak_f = (self.leak_finger * self.p_finger) if self.loss_leak else 0.0
        d_pf = np.where(self.finger_open, rate_f, 0.0) - leak_f
        self.p_finger = np.clip(self.p_finger + dt * d_pf,
                                vac_max - 5, self.pressure_max + 8)

        # Pressure -> equilibrium angle; membrane tracks (first-order).
        a_eq = np.where(self.p_finger > 0,
                        self.angle_max * (1.0 - np.exp(-np.maximum(self.p_finger, 0)
                                                       / self.p_half)),
                        0.0)
        d_a = gains * (a_eq - self.angle_true) / tau_m
        self.angle_true = np.clip(self.angle_true + dt * d_a,
                                  0.0, self.angle_max + 3)

        # ---- Sensor model: true angle -> 10-bit raw + noise, trimmed mean ----
        raw_t = self._angle_to_raw(self.angle_true)
        noise = self.rng.normal(0.0, self.sensor_noise_adc, size=(NF, FLEX_SAMPLES))
        samp = np.clip(raw_t[:, None] + noise, 0, 1023)
        samp.sort(axis=1)
        trimmed = samp[:, 1:FLEX_SAMPLES - 1].mean(axis=1)
        self.angle_filt = self._raw_to_angle(trimmed)

        self.peak_angle = max(self.peak_angle, float(self.angle_true.max()))
        self.peak_pressure = max(self.peak_pressure, float(self.p_finger.max()))

    # ------------------------------------------------------------------
    def step(self):
        """Advance one fixed simulation timestep (dt)."""
        self.t += self.dt
        self._update_target()
        self._control()
        self._plant()

    def safe_stop(self):
        self.running = False

    def start(self):
        self.running = True


# ======================================================================
#  DASHBOARD  (matplotlib widgets + animation)
# ======================================================================
def run_dashboard():
    import matplotlib
    import matplotlib.pyplot as plt
    from matplotlib.widgets import Slider, Button, CheckButtons
    from matplotlib.animation import FuncAnimation

    C = dict(
        bg="#0e1116", panel="#171b24", card="#1f2733", axis="#13171f",
        text="#f0f4ff", muted="#b3bcc8", grid="#5a606e",
        cyan="#15f2ff", red="#ff4d4d", green="#40ff59", magenta="#ff40ff",
        yellow="#ffd133", blue="#619eff", orange="#ff8c2e", white="#ffffff",
        gray="#8c95a3",
    )
    finger_colors = [C["cyan"], C["green"], C["yellow"], C["orange"], C["magenta"]]

    sim = HandControllerSim()
    N = int(round(sim.window_time / sim.dt)) + 1

    # rolling buffers
    t_log = np.linspace(-sim.window_time, 0, N)
    ang_log = np.full((NF, N), np.nan)
    pf_log = np.full((NF, N), np.nan)
    fv_log = np.full((NF, N), np.nan)
    avg_log = np.full(N, np.nan)
    tgt_log = np.full(N, np.nan)
    dbhi_log = np.full(N, np.nan)
    dblo_log = np.full(N, np.nan)
    ppwm_log = np.full(N, np.nan)
    vpwm_log = np.full(N, np.nan)
    man_log = np.full(N, np.nan)
    central_log = np.full(N, np.nan)

    def roll(arr, val):
        arr[:-1] = arr[1:]
        arr[-1] = val

    # ---------------- figure ----------------
    plt.rcParams.update({
        "figure.facecolor": C["bg"], "axes.facecolor": C["axis"],
        "savefig.facecolor": C["bg"], "text.color": C["text"],
        "axes.labelcolor": C["text"], "xtick.color": C["text"],
        "ytick.color": C["text"], "axes.edgecolor": C["grid"],
        "font.size": 9,
    })
    fig = plt.figure(figsize=(16, 9))
    fig.canvas.manager.set_window_title(
        "Soft Robotic Rehabilitation Hand | 5-Finger Proportional Controller (VAA0.0.5.2 model)")

    def style(ax, title, xlab, ylab):
        ax.set_title(title, color=C["text"], fontweight="bold")
        ax.set_xlabel(xlab); ax.set_ylabel(ylab)
        ax.grid(True, color=C["grid"], alpha=0.35)
        ax.set_facecolor(C["axis"])

    ax_angle = fig.add_axes([0.31, 0.56, 0.31, 0.38])
    ax_cmd = fig.add_axes([0.67, 0.56, 0.31, 0.38])
    ax_press = fig.add_axes([0.31, 0.09, 0.31, 0.38])
    ax_map = fig.add_axes([0.67, 0.09, 0.31, 0.38])
    style(ax_angle, "Per-Finger Angle vs Common Target", "Time (s)", "Angle (deg)")
    style(ax_cmd, "Shared Pump Commands", "Time (s)", "PWM (0-255)")
    style(ax_press, "Manifold and Finger Pressure", "Time (s)", "Pressure (kPa)")
    style(ax_map, "Valve Map (central + per-finger)", "Time (s)", "")

    # angle plot artists
    l_finger = [ax_angle.plot(t_log, ang_log[i], lw=2.0, color=finger_colors[i],
                              label=FINGER_NAMES[i])[0] for i in range(NF)]
    l_avg = ax_angle.plot(t_log, avg_log, lw=2.6, color=C["white"], label="Average")[0]
    l_tgt = ax_angle.plot(t_log, tgt_log, "--", lw=1.8, color=C["red"], label="Target")[0]
    l_dbhi = ax_angle.plot(t_log, dbhi_log, ":", lw=1.0, color=C["gray"])[0]
    l_dblo = ax_angle.plot(t_log, dblo_log, ":", lw=1.0, color=C["gray"])[0]
    ax_angle.axhline(sim.safe_angle, ls="-.", lw=1.2, color=C["orange"])
    ax_angle.set_ylim(-5, 90)
    ax_angle.legend(loc="upper right", ncol=2, fontsize=7,
                    facecolor=C["card"], edgecolor=C["gray"], labelcolor=C["text"])

    # command plot
    l_ppwm = ax_cmd.plot(t_log, ppwm_log, lw=2.2, color=C["green"],
                         label="Pressure pump PWM")[0]
    l_vpwm = ax_cmd.plot(t_log, vpwm_log, lw=2.2, color=C["magenta"],
                         label="Vacuum pump PWM")[0]
    ax_cmd.set_ylim(-10, 270)
    ax_cmd.legend(loc="upper right", fontsize=8,
                  facecolor=C["card"], edgecolor=C["gray"], labelcolor=C["text"])

    # pressure plot
    l_man = ax_press.plot(t_log, man_log, lw=2.6, color=C["blue"], label="Manifold")[0]
    l_pf = [ax_press.plot(t_log, pf_log[i], lw=1.3, color=finger_colors[i])[0]
            for i in range(NF)]
    ax_press.axhline(0, ls=":", lw=1.0, color=C["gray"])
    ax_press.set_ylim(-70, 110)
    ax_press.legend(loc="upper right", fontsize=8,
                    facecolor=C["card"], edgecolor=C["gray"], labelcolor=C["text"])

    # valve map: finger rows + central row, drawn as step lines
    l_fv = [ax_map.plot(t_log, fv_log[i], lw=2.0, color=finger_colors[i],
                        drawstyle="steps-post")[0] for i in range(NF)]
    l_central = ax_map.plot(t_log, central_log, lw=2.4, color=C["cyan"],
                            drawstyle="steps-post")[0]
    ax_map.set_yticks([1, 2, 3, 4, 5, 6])
    ax_map.set_yticklabels(["F1 close", "F2 close", "F3 close", "F4 close",
                            "F5 close", "Central=P"])
    ax_map.set_ylim(0.4, 6.8)

    # ---------------- left control column ----------------
    fig.text(0.045, 0.955, "Operator Panel", color=C["text"],
             fontsize=13, fontweight="bold")
    status_txt = fig.text(0.045, 0.93, "READY", color=C["text"],
                          fontsize=14, fontweight="bold")
    readout_txt = fig.text(0.045, 0.135, "", color=C["muted"], fontsize=9,
                           va="top", family="monospace")

    def slider_axes(y):
        ax = fig.add_axes([0.085, y, 0.135, 0.016])
        ax.set_facecolor(C["card"])
        return ax

    sl_specs = [
        ("Target", 0, 80, sim.manual_target),
        ("Kp P", 0, 20, sim.kp_pressure),
        ("Kp V", 0, 20, sim.kp_vacuum),
        ("Deadband", 0, 8, sim.deadband_deg),
        ("Flex set", 0, 80, sim.flex_set),
        ("Extend set", 0, 80, sim.extend_set),
        ("Press max", 20, 100, sim.pressure_max),
        ("Vac mag", 10, 60, sim.vacuum_mag),
        ("Spread %", 0, 30, sim.finger_spread_pct),
        ("Noise ADC", 0, 15, sim.sensor_noise_adc),
        ("Deadzone", 0, 80, sim.pump_deadzone_pwm),
        ("Flow cap", 10, 120, sim.q_max),
    ]
    sliders = {}
    y0 = 0.95
    for i, (name, lo, hi, init) in enumerate(sl_specs):
        ax = slider_axes(y0 - i * 0.0305)
        s = Slider(ax, name, lo, hi, valinit=init, color=C["blue"])
        s.label.set_color(C["text"]); s.label.set_fontsize(7.5)
        s.valtext.set_color(C["muted"]); s.valtext.set_fontsize(7.5)
        sliders[name] = s

    # pneumatic-loss toggles (sim plant fidelity; off => underdamped/ideal)
    fig.text(0.045, 0.593, "Pneumatic losses (hardware-matched)",
             color=C["yellow"], fontsize=8.5, fontweight="bold")
    ax_loss = fig.add_axes([0.045, 0.475, 0.21, 0.108]); ax_loss.set_facecolor(C["card"])
    loss_chk = CheckButtons(
        ax_loss, ["Flow restriction", "Pump dead-zone", "Leakage", "Viscoelastic creep"],
        [sim.loss_flow, sim.loss_pump, sim.loss_leak, sim.loss_visc])
    for lab in loss_chk.labels:
        lab.set_color(C["text"]); lab.set_fontsize(8)

    # auto-cycle checkbox
    ax_chk = fig.add_axes([0.045, 0.43, 0.21, 0.038]); ax_chk.set_facecolor(C["card"])
    chk = CheckButtons(ax_chk, ["Auto cycle (sim: emulates ANGLE cmds)"], [sim.auto_cycle])
    for lab in chk.labels:
        lab.set_color(C["text"]); lab.set_fontsize(8)

    # buttons
    def button(x, y, w, label, color):
        ax = fig.add_axes([x, y, w, 0.035])
        b = Button(ax, label, color=color, hovercolor=C["gray"])
        b.label.set_color(C["white"]); b.label.set_fontsize(9)
        return b

    b_start = button(0.045, 0.30, 0.062, "Start", "#1c8c33")
    b_pause = button(0.115, 0.30, 0.062, "Pause", "#996600")
    b_reset = button(0.185, 0.30, 0.062, "Reset", "#7a1f1f")
    b_stop = button(0.045, 0.255, 0.097, "Safe-Stop", "#5a1f66")
    b_save = button(0.150, 0.255, 0.097, "Save Image", "#294073")

    state = {"playing": False}

    def on_start(_):
        state["playing"] = True
        sim.start()

    def on_pause(_):
        state["playing"] = False

    def on_stop(_):
        sim.safe_stop()              # clock keeps running so relaxation is visible
        state["playing"] = True

    def on_reset(_):
        state["playing"] = False
        sim.reset()
        for a in (ang_log, pf_log, fv_log):
            a[:] = np.nan
        for a in (avg_log, tgt_log, dbhi_log, dblo_log, ppwm_log, vpwm_log,
                  man_log, central_log):
            a[:] = np.nan

    def on_save(_):
        fn = "soft_robotics_hand_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".png"
        fig.savefig(fn, dpi=140)
        status_txt.set_text("Saved " + fn)

    b_start.on_clicked(on_start)
    b_pause.on_clicked(on_pause)
    b_stop.on_clicked(on_stop)
    b_reset.on_clicked(on_reset)
    b_save.on_clicked(on_save)

    # ---------------- animation loop ----------------
    def update(_frame):
        # push live UI values into the model (mirrors reading sliders each tick)
        sim.kp_pressure = sliders["Kp P"].val
        sim.kp_vacuum = sliders["Kp V"].val
        sim.deadband_deg = sliders["Deadband"].val
        sim.flex_set = sliders["Flex set"].val
        sim.extend_set = sliders["Extend set"].val
        sim.pressure_max = sliders["Press max"].val
        sim.vacuum_mag = sliders["Vac mag"].val
        sim.finger_spread_pct = sliders["Spread %"].val
        sim.sensor_noise_adc = sliders["Noise ADC"].val
        sim.manual_target = sliders["Target"].val
        sim.auto_cycle = chk.get_status()[0]
        sim.pump_deadzone_pwm = sliders["Deadzone"].val
        sim.q_max = sliders["Flow cap"].val
        lf, lp, ll, lv = loss_chk.get_status()
        sim.loss_flow, sim.loss_pump, sim.loss_leak, sim.loss_visc = lf, lp, ll, lv

        if state["playing"]:
            sim.step()

            roll(avg_log, float(np.mean(sim.angle_filt)))
            roll(tgt_log, sim.target)
            roll(dbhi_log, sim.target + sim.deadband_deg)
            roll(dblo_log, sim.target - sim.deadband_deg)
            roll(ppwm_log, sim.p_pwm)
            roll(vpwm_log, sim.v_pwm)
            roll(man_log, sim.manifold)
            roll(central_log, 6.0 if sim.central_pressure else 5.45)
            roll(t_log, sim.t)
            for i in range(NF):
                roll(ang_log[i], sim.angle_filt[i])
                roll(pf_log[i], sim.p_finger[i])
                roll(fv_log[i], (i + 1) if not sim.finger_open[i] else (i + 1) - 0.55)

            # update artists
            for i in range(NF):
                l_finger[i].set_data(t_log, ang_log[i])
                l_pf[i].set_data(t_log, pf_log[i])
                l_fv[i].set_data(t_log, fv_log[i])
            l_avg.set_data(t_log, avg_log)
            l_tgt.set_data(t_log, tgt_log)
            l_dbhi.set_data(t_log, dbhi_log)
            l_dblo.set_data(t_log, dblo_log)
            l_ppwm.set_data(t_log, ppwm_log)
            l_vpwm.set_data(t_log, vpwm_log)
            l_man.set_data(t_log, man_log)
            l_central.set_data(t_log, central_log)

            xmax = max(sim.window_time, sim.t)
            xmin = xmax - sim.window_time
            for ax in (ax_angle, ax_cmd, ax_press, ax_map):
                ax.set_xlim(xmin, xmax)

            # status + readout
            mode_str = {"P": "PRESSURE", "V": "VACUUM", "H": "HOLD"}[sim.mode]
            if not sim.running:
                mode_str = "SAFE-STOP"
            status_txt.set_text(mode_str)
            path = "PRESS" if sim.central_pressure else "VAC"
            closed = [str(i + 1) for i in range(NF) if not sim.finger_open[i]]
            iso = " ".join(closed) if closed else "none"
            cyc_line = (f"flex {sim.flex_set:.0f} <-> extend {sim.extend_set:.0f}"
                        if sim.auto_cycle else "manual single target")
            readout_txt.set_text(
                f"mode    : {mode_str}   cycle {sim.cycle_count}\n"
                f"target  : {sim.target:5.1f} deg  ({cyc_line})\n"
                f"avg/err : {np.mean(sim.angle_filt):5.1f} / {sim.error:+.1f} deg\n"
                f"angles  : " + " ".join(f"{a:4.0f}" for a in sim.angle_filt) + "\n"
                f"pumps   : path {path}  P-PWM {sim.p_pwm:3d}  V-PWM {sim.v_pwm:3d}\n"
                f"isolated: {iso}\n"
                f"manifold: {sim.manifold:5.1f} kPa\n"
                f"peaks   : {sim.peak_angle:.1f} deg  {sim.peak_pressure:.1f} kPa")

        return []

    anim = FuncAnimation(fig, update, interval=int(sim.dt * 1000),
                         blit=False, cache_frame_data=False)
    fig._anim = anim   # keep a reference so it is not garbage-collected
    plt.show()


# ======================================================================
#  HEADLESS SELF-TEST  (no display; checks the control law converges)
# ======================================================================
def selftest():
    """Sweep Kp and report damping. Hardware shows NO oscillation for all Kp,
    so the lossy (default) model must produce ~zero overshoot at every Kp,
    while the ideal (lossless) model is allowed to overshoot/oscillate."""

    def metrics(lossy, kp, target=60.0, seconds=12.0):
        sim = HandControllerSim()
        sim.sensor_noise_adc = 0.0        # damping is a deterministic property
        sim.auto_cycle = False
        sim.manual_target = target
        sim.kp_pressure = kp
        sim.kp_vacuum = kp
        if not lossy:
            sim.loss_flow = sim.loss_pump = sim.loss_leak = sim.loss_visc = False
        sim.start()
        traj = np.empty(int(seconds / sim.dt))
        for k in range(traj.size):
            sim.step()
            traj[k] = float(np.mean(sim.angle_filt))
        overshoot = max(0.0, float(traj.max()) - target)
        tail = traj[-150:]                # last ~3 s
        ripple = float(tail.max() - tail.min())
        return overshoot, ripple, float(tail.mean())

    kps = [0.5, 1, 2, 5, 10, 15, 20]
    print("Kp damping sweep (target 60 deg, noise off):\n")
    hdr = f"{'Kp':>4} | {'LOSSY  over / ripple / final':>30} | {'IDEAL  over / ripple / final':>30}"
    print(hdr); print("-" * len(hdr))
    lossy_ok = True
    for kp in kps:
        oL, rL, fL = metrics(True, kp)
        oI, rI, fI = metrics(False, kp)
        if oL > 1.0:                       # overdamped => no overshoot
            lossy_ok = False
        print(f"{kp:>4} | {oL:6.2f} / {rL:6.2f} / {fL:5.1f}{'':9} | "
              f"{oI:6.2f} / {rI:6.2f} / {fI:5.1f}")
    print("-" * len(hdr))
    print("over = overshoot above target (deg); ripple = peak-to-peak of last 3 s (deg)")
    print("LOSSY overdamped for all Kp (no overshoot):",
          "PASS" if lossy_ok else "CHECK NUMBERS")
    return lossy_ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Five-finger soft robotic glove simulator.")
    ap.add_argument("--selftest", action="store_true",
                    help="run headless control-law check and exit")
    args = ap.parse_args()
    if args.selftest:
        selftest()
    else:
        run_dashboard()
