/*
  Public excerpt from the full ESP32-S3 controller line.

  Firmware reference: V008.7.1
  Board reference: ESP32-S3-WROOM-2-N32R16V

  This is a documentation excerpt, not a complete firmware file. It shows the
  state machine, the latched fault model, the safe-relief state, and one
  representative state handler. Wi-Fi/dashboard, SD logging, LCD, CLI, NVS
  settings, and the scheduler are omitted here; hooks into them are marked
  with comments.
*/

// ======================== State model ========================
// HOLD_ANGLE is the within-tolerance hold (pumps off, finger valves closed) used
// by the angle-setpoint mode. STOPPED_SAFE is the explicit stopped/relieved label
// (pumps off, vacuum/relief side, finger valves OPEN) used after boot / STOP /
// mode change / no-target reset.
enum State { INFLATING, HOLD_FLEX, VACUUMING, HOLD_VAC, HOLD_ANGLE, STOPPED_SAFE, FAULT };

// Operation mode is ORTHOGONAL to the FSM State above. It selects WHICH
// controller runs (common target-angle tracking vs the therapy flex/extend
// cycle); it does not replace the state machine.
enum OperationMode { MODE_ANGLE_SETPOINT, MODE_THERAPY_CYCLE };

// Latched fault reasons (strings in telemetry): INFLATE_TIMEOUT, VACUUM_TIMEOUT,
// ANGLE_TIMEOUT, SAFE_LIMIT, SENSOR. A latched fault requires a deliberate,
// operator-initiated reset; it never clears itself.

// ======================== Safe state ========================
// SAFE STATE for fault / stop: pumps OFF, central valve to the VACUUM/relief
// side, and ALL finger valves OPENED so every finger vents - never trap a
// flexed hand.
void relieveToSafe() {
  allOff();                            // immediate, un-slewed pump stop
  setValve(VALVE_VACUUM);
  openAllFingerValves();
  snap.valvePressureMode = false;
}

// ======================== Fault manager (LATCHED) ========================
void raiseFault(const char* reason) {
  if (snap.faultActive) return;                 // already latched (idempotent)
  snap.faultActive = true;
  strncpy(snap.faultReason, reason, sizeof(snap.faultReason) - 1);
  snap.faultReason[sizeof(snap.faultReason) - 1] = '\0';

  relieveToSafe();                              // pumps off, vacuum, OPEN fingers
  snap.state = FAULT;

  // Always-on fault trace: independent of logging config so a fault is never
  // invisible on the bench. SD-event and WebSocket-broadcast hooks omitted here.
  Serial.print(F("# FAULT "));
  Serial.println(reason);
}

// ======================== PI control (anti-windup) ========================
int computePI(PIDData &pid, float error, int minPower, int maxPower) {
  if (error <= PID_DEADBAND) return 0;
  unsigned long now = millis();
  float dt = (now - pid.lastTime) / 1000.0f;
  if (dt <= 0.001f || dt > 0.25f) dt = 0.02f;     // clamp dt to a sane control tick
  pid.lastTime = now;
  pid.integral += error * dt;
  pid.integral = constrain(pid.integral, 0.0f, INTEGRAL_LIMIT);   // anti-windup
  float derivative = 0.0f;
  if (pid.hasPrev) derivative = (error - pid.prevError) / dt;
  pid.prevError = error;
  pid.hasPrev = true;
  int output = (int)(pid.kp * error + pid.ki * pid.integral + pid.kd * derivative);
  return constrain(output, minPower, maxPower);
}

// ======================== State transitions ========================
void enterState(State next) {
  allOff();                          // immediate pump stop on every transition
  snap.state = next;
  stateEntryTime = millis();

  switch (next) {
    case INFLATING:
      setValve(VALVE_PRESSURE);
      snap.valvePressureMode = true;
      openAllFingerValves();
      for (int i = 0; i < 5; i++) snap.fingerDone[i] = false;
      resetPID(pressurePID);
      break;
    case HOLD_FLEX:
      setValve(VALVE_PRESSURE);
      snap.valvePressureMode = true;
      closeAllFingerValves();          // defensive trap (also closed per-finger at cut-off)
      break;
    case VACUUMING:
      setValve(VALVE_VACUUM);
      snap.valvePressureMode = false;
      openAllFingerValves();
      for (int i = 0; i < 5; i++) snap.fingerDone[i] = false;
      resetPID(vacuumPID);
      break;
    case HOLD_VAC:
      setValve(VALVE_VACUUM);
      snap.valvePressureMode = false;
      closeAllFingerValves();          // defensive trap of the extended (vacuum) state
      break;
    case HOLD_ANGLE:
      // within-tolerance hold for angle-setpoint mode: pumps already off,
      // valve parked on the (lower-energy) vacuum side, finger valves isolated.
      setValve(VALVE_VACUUM);
      snap.valvePressureMode = false;
      closeAllFingerValves();
      break;
    case STOPPED_SAFE:
      // explicit stopped-safe label. No actuation: pumps already off; park the
      // valve on the vacuum/relief side and OPEN all finger valves so no finger
      // stays pressurised (matches relieveToSafe()).
      setValve(VALVE_VACUUM);
      snap.valvePressureMode = false;
      openAllFingerValves();
      break;
    case FAULT:
      break;                           // entered only via raiseFault()
  }
}

bool valveSettledNow() { return (millis() - valveSwitchTime) >= VALVE_SETTLE_MS; }

// ======================== Representative state handler ========================
void tickInflating() {
  if (!valveSettledNow()) { setPressurePump(0); return; }   // wait out pneumatic settle

  float worstError = 0;
  for (int i = 0; i < 5; i++) if (!snap.fingerDone[i]) {
    float err = (float)(RAW_FLEX_TARGET - snap.raw[i]);
    if (err > worstError) worstError = err;
  }
  int targetPWM = computePI(pressurePID, worstError,
                            PRESSURE_MIN_PWM_ACTIVE, PRESSURE_MAX_PWM_ACTIVE);
  setVacuumPump(0);
  setPressurePump(targetPWM);          // pump writers apply a slew limit internally

  // Per-finger cut-off ALIGNED WITH THE DEADBAND: mark done the same tick the PI
  // stops driving (raw >= TARGET - DEADBAND), else a finger plateauing inside the
  // deadband never reaches the exact target and stalls until a spurious timeout.
  bool allReached = true;
  for (int i = 0; i < 5; i++) {
    if (!snap.fingerDone[i] && snap.raw[i] >= RAW_FLEX_TARGET - (int)PID_DEADBAND) {
      snap.fingerDone[i] = true;
      setFingerValve(i, false);          // trap pressure in this finger
    }
    if (!snap.fingerDone[i]) allReached = false;
  }
  if (allReached) enterState(HOLD_FLEX);
  else if (millis() - stateEntryTime > INFLATE_TIMEOUT_MS) raiseFault("INFLATE_TIMEOUT");
}

// ======================== Controller dispatch ========================
void tickController() {
  if (snap.faultActive || snap.sessionStopped) return;
  if (operationMode == MODE_ANGLE_SETPOINT) { tickAngleSetpoint(); return; }
  switch (snap.state) {
    case INFLATING: tickInflating(); break;
    case HOLD_FLEX: tickHoldFlex();  break;
    case VACUUMING: tickVacuuming(); break;
    case HOLD_VAC:  tickHoldVac();   break;
    default: break;
  }
}

// ======================== Sensor safety guard (20 ms task) ========================
void taskSensors() {
  snap.tms = millis();
  for (int i = 0; i < 5; i++) {
    int r = readFlexRaw(flexPins[i]);   // median-style filter: 7 samples, drop min & max
    snap.raw[i] = r;
    snap.deg[i] = rawToMCP(r);
    if (r >= RAW_SAFE_LIMIT) {
      // Suppress the over-flex re-fault ONLY inside the bounded post-reset relief
      // window AND only while actively VACUUMING; any other state (e.g. INFLATING)
      // re-arms the check, so inflation can never run with over-flex masked.
      bool relieving = (!snap.sessionStopped) &&
                       (snap.state == VACUUMING) &&
                       (safeLimitRecoveryUntil != 0) &&
                       ((long)(safeLimitRecoveryUntil - millis()) > 0);
      if (!relieving) { raiseFault("SAFE_LIMIT"); return; }
    }
    if (sensorIsInvalid(r)) sensorFaultCount[i]++;
    else                    sensorFaultCount[i] = 0;
    if (sensorFaultCount[i] >= SENSOR_FAULT_COUNT_LIMIT) { raiseFault("SENSOR"); return; }
  }
}
