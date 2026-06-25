/*
  Public excerpt from the minimal proportional controller branch.

  Firmware reference: VAA0.0.5.2_Mega2560_SimpleRefined
  Board reference: Arduino Mega 2560

  This is a documentation excerpt, not a complete firmware file.
*/

static int proportionalCommand(float errorMagnitude, float kp, int minPwm) {
  if (errorMagnitude <= DEADBAND_DEG) return 0;

  int cmd = (int)(kp * errorMagnitude + 0.5f);
  if (cmd > 0 && cmd < minPwm) cmd = minPwm;
  return clampPwm(cmd);
}

static void updateControl() {
  if (!running) {
    stopAllActuatorsSafe();
    return;
  }

  float avg = averageAngle();
  float error = targetAngle - avg;

  // Pressure / flexion:
  // Select the pressure path, then isolate only fingers that have already
  // reached the target region. Slower fingers stay connected.
  if (error > DEADBAND_DEG) {
    selectPressurePath();

    for (uint8_t i = 0; i < NUM_FINGERS; i++) {
      if (flexAngle[i] < (targetAngle - DEADBAND_DEG)) {
        openFingerValve(i);
      } else {
        closeFingerValve(i);
      }
    }

    modeChar = 'P';
    pumpPwm = 0;

    // Keep both pumps off during valve path settling.
    if (!valveSettled()) {
      setPumps(0, 0);
      return;
    }

    pumpPwm = proportionalCommand(error, KpPressure, MIN_PWM_PRESSURE);
    setPumps(pumpPwm, 0);
    return;
  }

  // Vacuum / opening:
  // During vacuum, all finger valves remain open so the shared manifold can
  // pull the glove back together.
  if ((-error) > DEADBAND_DEG) {
    selectVacuumPath();
    openAllFingerValves();

    modeChar = 'V';
    pumpPwm = 0;

    if (!valveSettled()) {
      setPumps(0, 0);
      return;
    }

    pumpPwm = proportionalCommand(-error, KpVacuum, MIN_PWM_VACUUM);
    setPumps(0, pumpPwm);
    return;
  }

  // Active hold while running.
  // STOP/not-running uses a different safe bench output state.
  setPumps(0, 0);
  closeAllFingerValves();
  pumpPwm = 0;
  modeChar = 'H';
}
