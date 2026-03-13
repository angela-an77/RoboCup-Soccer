
#include <Encoder.h>

const float MAX_RPM_OUT = 1000.0f;          
const float kF = 255.0f / MAX_RPM_OUT;    

static float rpmFilt_A = 0.0f;
static float rpmFilt_D = 0.0f;
const float ALPHA = 0.2f;
int tick = 0;
float targetRPM_A;
float targetRPM_D;
float pwmCmd_A;
float pwmCmd_D;  
float integ_A;
float integ_D;

float MAX_RPM = 800;

float Kp = 0.8f;
float Ki = 0.0f; //temp 0

float PWM_MIN = 0.0f;

float ICLAMP = 120.0f;

constexpr int EA_D = 2;
constexpr int EB_D = 3;

constexpr int EA_A = 4;
constexpr int EB_A = 5;

const int IND2 = 33;
const int IND1 = 34;
const int PWMD = 14;

const int INA1 = 38;
const int INA2 = 39;
const int PWMA = 15;

constexpr float CPR = 464.64f;

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
  } else { // cmd < 0
    digitalWrite(in1, LOW);
    digitalWrite(in2, HIGH);
  }

  analogWrite(pwmPin, pwm);
}

void driveVector4(float speed, float angleDeg, float &cmdA, float &cmdD) {
  if (speed < 0) speed = 0;
  if (speed > 255) speed = 255;

  angleDeg = fmodf(angleDeg, 360.0f);
  if (angleDeg < 0) angleDeg += 360.0f;
  
  float th = deg2rad(angleDeg);
  float Vx = speed * cosf(th);
  float Vy = speed * sinf(th);

  const float aA = deg2rad(90.0f);
  const float aD = deg2rad(210.0f);

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

  while(!Serial && millis() < 1500) {}
  pinMode(INA1, OUTPUT); pinMode(INA2, OUTPUT); pinMode(PWMA, OUTPUT);
  pinMode(IND1, OUTPUT); pinMode(IND2, OUTPUT); pinMode(PWMD, OUTPUT);
  
}

void loop() {
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 'F') {
      float cmdA = 0, cmdD = 0;
      driveVector4(30, 100, cmdA, cmdD);
      targetRPM_A = (cmdA / 255.0f) * MAX_RPM; 
      targetRPM_D = (cmdD / 255.0f) * MAX_RPM;
      } 
    if (cmd == 'S') {
      targetRPM_A = 0.0f;
      targetRPM_D = 0.0f;
      integ_A = 0.0f;
      integ_D = 0.0f;
      pwmCmd_A = 0.0f;
      pwmCmd_D = 0.0f;
      setMotorSigned(IND1, IND2, PWMD, 0.0f);
      setMotorSigned(INA1, INA2, PWMA, 0.0f);
      }
    }
  static uint32_t lastUs = micros();
  //micros is time since boot 
  //Us = Microseconds
  static long lastCount_A = 0;
  static long lastCount_D = 0;

  //static to keep
  uint32_t nowUs = micros();
  uint32_t dtUS = nowUs - lastUs;

  if (dtUS >= 20000) {
  lastUs = nowUs;
  float dt = dtUS * 1e-6f;

  long count_A  = enc_A.read();
  long dcount_A = count_A - lastCount_A;
  lastCount_A   = count_A;

  float cps_A = dcount_A / dt;
  float rpm_A = (cps_A / CPR) * 60.0f;
  rpm_A = rpm_A; //flip sign

  rpmFilt_A += ALPHA * (rpm_A - rpmFilt_A);
  float err_A = targetRPM_A - rpmFilt_A;
  
  if (fabsf(targetRPM_A) < 1e-3f) {
    integ_A = 0.0f;
    rpmFilt_A = 0.0f;
  } else {
    integ_A += err_A * dt;
    integ_A  = constrain(integ_A, -ICLAMP, ICLAMP);
  }

  float ua = kF * targetRPM_A + Kp * err_A + Ki * integ_A;
  
  pwmCmd_A = constrain(ua, -255.0f, 255.0f);

  if (fabsf(targetRPM_A) > 1e-3f && fabsf(pwmCmd_A) > 0 && fabsf(pwmCmd_A) < PWM_MIN) {
    pwmCmd_A = (pwmCmd_A > 0) ? PWM_MIN : -PWM_MIN;
  }

  setMotorSigned(INA1, INA2, PWMA, pwmCmd_A);

  long count_D  = enc_D.read();
  long dcount_D = count_D - lastCount_D;
  lastCount_D   = count_D;

  float cps_D = dcount_D / dt;
  float rpm_D = (cps_D / CPR) * 60.0f;
  rpm_D = rpm_D; // flip sign
  rpmFilt_D += ALPHA * (rpm_D - rpmFilt_D);
  float err_D = targetRPM_D - rpmFilt_D;

  if (fabsf(targetRPM_D) < 1e-3f) {
    integ_D = 0.0f;
    rpmFilt_D = 0.0f;
  } else {
    integ_D += err_D * dt;
    integ_D  = constrain(integ_D, -ICLAMP, ICLAMP);
  }
  float ud = kF * targetRPM_D + Kp * err_D + Ki * integ_D;
  
  pwmCmd_D  = constrain(ud, -255.0f, 255.0f);
  
  tick++;
  if (tick % 10 == 0) { // prints ~5x/sec (50Hz / 10)
      Serial.print("A{t="); Serial.print(targetRPM_A,1);
      Serial.print(" dc="); Serial.print(dcount_A);
      Serial.print(" rpm="); Serial.print(rpm_A,1);
      Serial.print(" pwm="); Serial.print(pwmCmd_A,0);
      Serial.print("} ");

      Serial.print("D{t="); Serial.print(targetRPM_D,1);
      Serial.print(" dc="); Serial.print(dcount_D);
      Serial.print(" rpm="); Serial.print(rpm_D,1);
      Serial.print(" pwm="); Serial.println(pwmCmd_D,0);
      
    }

  
  if (fabsf(targetRPM_D) > 1e-3f && fabsf(pwmCmd_D) > 0 && fabsf(pwmCmd_D) < PWM_MIN) {
    pwmCmd_D = (pwmCmd_D > 0) ? PWM_MIN : -PWM_MIN;
  }

  setMotorSigned(IND1, IND2, PWMD, pwmCmd_D);

  }
}
