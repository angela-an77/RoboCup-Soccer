#include <Encoder.h>

int led = 13;
String com = "";
String mode = "stop";
unsigned long lastSend = 0;
const int sendInterval = 20;
float STALL_RPM = 2.0f;      // below this we consider it stalled
int stallCount = 0;
const int STALL_THRESH = 7; // 10 consecutive slow readings = stall
bool buttontoggle = false;


const float MAX_RPM_OUT = 1000.0f;          
const float kF = 255.0f / MAX_RPM_OUT;    

static float rpmFilt_A = 0.0f;
static float rpmFilt_D = 0.0f;
const float ALPHA = 0.3f;
int tick = 0;
float targetRPM_A;
float targetRPM_D;
float pwmCmd_A;
float pwmCmd_D;  
float integ_A;
float integ_D;

float MAX_RPM = 600;

float Kp = 0.08f;
float Ki = 0.05f;

float PWM_MIN = 0.0f;

float ICLAMP = 50.0f;

const float    KICK_PWM     = 120.0f;  
const uint32_t KICK_DUR_US  = 50000;    // kick duration: 80 ms

static bool     kicking_A    = false;
static uint32_t kickStart_A  = 0;
static bool     kicking_D    = false;
static uint32_t kickStart_D  = 0;
static float    lastTarget_A = 0.0f;
static float    lastTarget_D = 0.0f;
// -------------------------------------------------------------------

constexpr int EA_D = 2;
constexpr int EB_D = 3;

constexpr int EA_A = 4;
constexpr int EB_A = 5;

const int IND1 = 34;
const int IND2 = 33;
const int PWMD = 14;

const int INA1 = 36;
const int INA2 = 35;
const int PWMA = 15;

constexpr float CPR = 979.62f;

Encoder enc_A(EA_A, EB_A);
Encoder enc_D(EA_D, EB_D);

static inline float deg2rad(float d) { return d * (3.14159265358979323846f / 180.0f); }

static inline int clamp255(int x) {
  if (x < 0) return 0;
  if (x > 255) return 255;
  return x;
}

void setMotorSigned(int in1, int in2, int pwmPin, float cmd) {
  if (cmd > 255.0f) cmd = 255.0f;
  if (cmd < -255.0f) cmd = -255.0f;

  int pwm = clamp255((int)lroundf(fabsf(cmd)));

  if (pwm == 0) {
    digitalWrite(in1, LOW);
    digitalWrite(in2, LOW);
  } else if (cmd > 0) {
    digitalWrite(in1, HIGH);
    digitalWrite(in2, LOW);
  } else {
    digitalWrite(in1, LOW);
    digitalWrite(in2, HIGH);
  }

  analogWrite(pwmPin, pwm);
}

void driveVector4(float speed, float angleDeg, float &cmdA, float &cmdD) {
  if (speed < 0) speed = 30;
  if (speed > 255) speed = 255;

  angleDeg = fmodf(angleDeg, 360.0f);
  if (angleDeg < 0) angleDeg += 360.0f;
  
  float th = deg2rad(angleDeg);
  float Vx = speed * cosf(th);
  float Vy = speed * sinf(th);

  const float aA = deg2rad(120.0f);
  const float aD = deg2rad(240.0f);

  cmdA = Vx * cosf(aA) + Vy * sinf(aA);
  cmdD = Vx * cosf(aD) + Vy * sinf(aD);

  float maxAbs = fmaxf(fabsf(cmdA), fabsf(cmdD));
  if (maxAbs > 255.0f) {
    float k = 255.0f / maxAbs;
    cmdA *= k; cmdD *= k;
  }
}

void setup() {
  
  Serial.begin(115200);
  pinMode(led, OUTPUT);
  
  digitalWrite(led, LOW);
  while(!Serial && millis() < 1500) {}
  pinMode(INA1, OUTPUT); pinMode(INA2, OUTPUT); pinMode(PWMA, OUTPUT);
  pinMode(IND1, OUTPUT); pinMode(IND2, OUTPUT); pinMode(PWMD, OUTPUT);
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    
    if (c == '\n') {
      com.trim();
      Serial.print("Command: ");
      Serial.println(com);
      if (com == "button") {buttontoggle = !buttontoggle; Serial.print("received button");}
      else if (com == "forward"){ mode = "forward"; Serial.print("received forward"); }
      else if (com == "right")  { mode = "right"; }
      else if (com == "left")   { mode = "left"; }
      else if (com == "stop")   { mode = "stop"; }
      else if (com == "back")   { mode = "back"; }
      com = "";
    } else {
      com += c;
    }
  }
  if (buttontoggle) {
    Serial.print("button wipe");
    kicking_D = false;
    kicking_A = false;
    integ_A = 0;
    integ_D = 0;
    pwmCmd_A = 0;
    pwmCmd_D = 0;
    targetRPM_A = 0;
    targetRPM_D = 0;
  }
  else if (mode == "right") {
    targetRPM_A = 90.0f;
    targetRPM_D = 90.0f;
    digitalWrite(led, HIGH);
  }
  else if (mode == "left") {
    digitalWrite(led, HIGH);
    targetRPM_A = -90.0f;
    targetRPM_D = -90.0f;
  }
  else if (mode == "forward") {
    Serial.print("Moving forward");
    digitalWrite(led, LOW);
    float cmdA = 0, cmdD = 0;
    driveVector4(600, 270, cmdA, cmdD);
    targetRPM_A = (cmdA / 255.0f) * MAX_RPM; 
    targetRPM_D = (cmdD / 255.0f) * MAX_RPM;
  } else if (mode == "stop") {
    kicking_D = false;
    kicking_A = false;
    integ_A = 0;
    integ_D = 0;
    pwmCmd_A = 0;
    pwmCmd_D = 0;
    targetRPM_A = 0;
    targetRPM_D = 0;
  }
  else if (mode == "back") {
    digitalWrite(led, LOW);
    float cmdA = 0, cmdD = 0;
    driveVector4(600, 90, cmdA, cmdD);
    targetRPM_A = (cmdA / 255.0f) * MAX_RPM; 
    targetRPM_D = (cmdD / 255.0f) * MAX_RPM;
  }
  static uint32_t lastUs    = 0;
  static long lastCount_A   = 0;
  static long lastCount_D   = 0;

  uint32_t nowUs = micros();
  uint32_t dtUS  = nowUs - lastUs;

  if (dtUS >= 20000) {
    lastUs    = nowUs;
    float dt  = dtUS * 1e-6f;

    // ---- Motor A ----
    // Detect transition from stopped to moving -> trigger kickstart
    if (fabsf(lastTarget_A) < 1e-3f && fabsf(targetRPM_A) > 1e-3f) {
      kicking_A   = true;
      kickStart_A = nowUs;
      integ_A     = 0.0f;   // clear integrator so it doesn't wind up during kick
      rpmFilt_A   = 0.0f;
    }
    lastTarget_A = targetRPM_A;

    long count_A  = enc_A.read();
    long dcount_A = count_A - lastCount_A;
    lastCount_A   = count_A;
    float rpm_A   = ((dcount_A / dt) / CPR) * 60.0f;
    rpmFilt_A    += ALPHA * (rpm_A - rpmFilt_A);

    if (fabsf(targetRPM_A) < 1e-3f) {
      integ_A   = 0.0f;
      rpmFilt_A = 0.0f;
      kicking_A = false;
      pwmCmd_A  = 0.0f;
    } else if (kicking_A) {
      // Still in kickstart window?
      if ((nowUs - kickStart_A) < KICK_DUR_US) {
        pwmCmd_A = (targetRPM_A > 0) ? KICK_PWM : -KICK_PWM;
      } else {
        kicking_A = false;   // kick done, hand off to PID
      }
    }

    if (!kicking_A && fabsf(targetRPM_A) > 1e-3f) {
      float err_A = targetRPM_A - rpmFilt_A;
      integ_A    += err_A * dt;
      integ_A     = constrain(integ_A, -ICLAMP, ICLAMP);
      pwmCmd_A    = constrain(kF*targetRPM_A + Kp*err_A + Ki*integ_A, -255.0f, 255.0f);
      if (fabsf(pwmCmd_A) < PWM_MIN) pwmCmd_A = (pwmCmd_A > 0) ? PWM_MIN : -PWM_MIN;
    }

    setMotorSigned(INA1, INA2, PWMA, pwmCmd_A);

    // ---- Motor D ----
    if (fabsf(lastTarget_D) < 1e-3f && fabsf(targetRPM_D) > 1e-3f) {
      kicking_D   = true;
      kickStart_D = nowUs;
      integ_D     = 0.0f;
      rpmFilt_D   = 0.0f;
    }
    lastTarget_D = targetRPM_D;

    long count_D  = enc_D.read();
    long dcount_D = count_D - lastCount_D;
    lastCount_D   = count_D;
    float rpm_D   = ((dcount_D / dt) / CPR) * 60.0f;
    rpmFilt_D    += ALPHA * (rpm_D - rpmFilt_D);

    if (fabsf(targetRPM_D) < 1e-3f) {
      integ_D   = 0.0f;
      rpmFilt_D = 0.0f;
      kicking_D = false;
      pwmCmd_D  = 0.0f;
    } else if (kicking_D) {
      if ((nowUs - kickStart_D) < KICK_DUR_US) {
        pwmCmd_D = (targetRPM_D > 0) ? KICK_PWM : -KICK_PWM;
      } else {
        kicking_D = false;
      }
    }

    if (!kicking_D && fabsf(targetRPM_D) > 1e-3f) {
      float err_D = targetRPM_D - rpmFilt_D;
      integ_D    += err_D * dt;
      integ_D     = constrain(integ_D, -ICLAMP, ICLAMP);
      pwmCmd_D    = constrain(kF*targetRPM_D + Kp*err_D + Ki*integ_D, -255.0f, 255.0f);
      if (fabsf(pwmCmd_D) < PWM_MIN) pwmCmd_D = (pwmCmd_D > 0) ? PWM_MIN : -PWM_MIN;
    }

    setMotorSigned(IND1, IND2, PWMD, pwmCmd_D);

    // ---- Stall detection ----
    if (fabsf(rpm_A) < STALL_RPM && fabsf(targetRPM_A) > 1e-3f &&
        fabsf(rpm_D) < STALL_RPM && fabsf(targetRPM_D) > 1e-3f) {
      if (++stallCount > STALL_THRESH) {
        rpmFilt_A = rpmFilt_D = integ_A = integ_D = 0.0f;
        stallCount = 0;
        //Serial.println("Stall");
        // Re-trigger kick if we still have a target
        if (fabsf(targetRPM_A) > 1e-3f) {
          kicking_A = true;
          kickStart_A = nowUs;
        }
        if (fabsf(targetRPM_D) > 1e-3f) {
          kicking_D = true;
          kickStart_D = nowUs;
        }
      }
    } else {
      stallCount = 0;
    }

    tick++;
    if (tick % 2 == 0) {
      /**
      Serial.print("A{t="); Serial.print(targetRPM_A,1);
      Serial.print(" dc="); Serial.print(dcount_A);
      Serial.print(" rpm="); Serial.print(rpm_A,1);
      Serial.print(" pwm="); Serial.print(pwmCmd_A,0);
      Serial.print(" kick="); Serial.print(kicking_A);
      Serial.print(" I="); Serial.print(integ_A,2);
      Serial.print("} D{t="); Serial.print(targetRPM_D,1);
      Serial.print(" dc="); Serial.print(dcount_D);
      Serial.print(" rpm="); Serial.print(rpm_D,1);
      Serial.print(" pwm="); Serial.print(pwmCmd_D,0);
      Serial.print(" kick="); Serial.print(kicking_D);
      Serial.print(" I="); Serial.println(integ_D,2);
      **/ 
      
    }
  }

}
