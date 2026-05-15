#include <Encoder.h>

const int logic_pin = 23;

int led = 13;
String com = "";
String mode = "stop";
unsigned long lastSend = 0;
const int sendInterval = 20;
const float MAX_RPM_OUT = 800.0f;          
const float kF = 255.0f / MAX_RPM_OUT;    
const float STALL_RPM = 2.0f;      // below this we consider it stalled
int stallCount = 0;
const int STALL_THRESH = 7; // 10 consecutive slow readings = stall
bool buttontoggle = false;
bool dribble = false;

float targetRPM;      
float pwmCmd;     
float integ;
int tick = 0;
static float rpmFilt = 0.0f;
const float ALPHA = 0.3f;

float MAX_RPM = 600;

float Kp = 0.08f;
float Ki = 0.05f;

float PWM_MIN = 0.0f;

float ICLAMP = 50.0f;
const float    KICK_PWM    = 120.0f;
const uint32_t KICK_DUR_US = 50000;   // kick duration: 80 ms

static bool     kicking     = false;
static uint32_t kickStart   = 0;
static float    lastTarget  = 0.0f;
// -------------------------------------------------------------------

constexpr int EA = 2;
constexpr int EB = 3;

const int INB1 = 34;
const int INB2 = 33;
const int PWMB = 14;

const int INA1 = 36;
const int INA2 = 35;
const int PWMA = 15;

constexpr float CPR = 979.62f;

Encoder enc(EA, EB);

static inline float deg2rad(float d) { return d * (3.14159265358979323846f / 180.0f); }

static inline int clamp255(int x) {
  if (x < 0) return 0;
  if (x > 255) return 255;
  return x;
}

void shoot(int logic_pin) {
  digitalWrite(logic_pin, LOW);
  delay(500);
  digitalWrite(logic_pin, HIGH);
  delay(1000);
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

float driveVector4(float speed, float angleDeg) {
  if (speed < 0) speed = 0;
  if (speed > 255) speed = 255;

  angleDeg = fmodf(angleDeg, 360.0f);
  if (angleDeg < 0) angleDeg += 360.0f;

  float th = deg2rad(angleDeg);
  float Vx = speed * cosf(th);
  float Vy = speed * sinf(th);

  const float aB = deg2rad(0.0f);
  float cmdB = Vx * cosf(aB) + Vy * sinf(aB);

  if (fabsf(cmdB) > 255.0f) cmdB = (cmdB > 0) ? 255.0f : -255.0f;

  return cmdB;
}

void setup() {

  Serial.begin(115200);
  pinMode(led, OUTPUT);
  digitalWrite(led, LOW);
  while(!Serial && millis() < 1500) {}
  pinMode(INB1, OUTPUT); pinMode(INB2, OUTPUT); pinMode(PWMB, OUTPUT);
  pinMode(logic_pin, OUTPUT);
  digitalWrite(logic_pin, HIGH);
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {
      com.trim();
      Serial.print("Command: ");
      Serial.println(com);
      if (com == "button") {buttontoggle = !buttontoggle; Serial.print("received button");}
      else if (com == "forward")    { mode = "forward"; Serial.print("received forward");}
      else if (com == "right") { mode = "right"; }
      else if (com == "left")  { mode = "left"; }
      else if (com == "stop")  { mode = "stop"; }
      else if (com == "shoot") { mode = "shoot"; }
      else if (com == "dribble") {dribble = true;}
      else if (com == "ndribble") {dribble = false;}
      com = "";
    } else {
      com += c;
    }
  }
  if (dribble&&!buttontoggle) {
    setMotorSigned(INA1, INA2, PWMA, 200);
  } else {
    setMotorSigned(INA1, INA2, PWMA, 0);
  }
  if (buttontoggle) {
    Serial.print("button wipe");
    targetRPM = 0.0f;
    integ     = 0.0f;
    pwmCmd    = 0.0f;
    kicking   = false;
    targetRPM = 0;
    digitalWrite(led, LOW);
    setMotorSigned(INA1, INA2, PWMA, 0);
  }  
  else if (mode == "shoot") {
    shoot(logic_pin);
  } 
  else if (mode == "right") {
    targetRPM = 90.0f;
    digitalWrite(led, HIGH);
  }
  else if (mode == "left") {
    digitalWrite(led, HIGH);
    targetRPM = -90.0f;
  }
  else if (mode == "forward") {
    Serial.print("Moving forward");
    digitalWrite(led, LOW);
    float cmdB = driveVector4(600, 270);
    targetRPM = (cmdB / 255.0f) * MAX_RPM;
  }
  else if (mode == "stop") {
    targetRPM = 0.0f;
    integ     = 0.0f;
    pwmCmd    = 0.0f;
    kicking   = false;
    targetRPM = 0;
    digitalWrite(led, LOW);
  }

  static uint32_t lastUs  = 0;
  static long lastCount   = 0;

  uint32_t nowUs = micros();
  uint32_t dtUS  = nowUs - lastUs;

  if (dtUS >= 20000) {
    lastUs   = nowUs;
    float dt = dtUS / 1e6f;

    // Detect transition from stopped -> moving -> trigger kickstart
    if (fabsf(lastTarget) < 1e-3f && fabsf(targetRPM) > 1e-3f) {
      kicking   = true;
      kickStart = nowUs;
      integ     = 0.0f;   // clear integrator so it doesn't wind up during kick
      rpmFilt   = 0.0f;
    }
    lastTarget = targetRPM;

    long count  = enc.read();
    long dcount = count - lastCount;
    lastCount   = count;
    float rpm   = ((dcount / dt) / CPR) * 60.0f;
    rpmFilt    += ALPHA * (rpm - rpmFilt);

    if (fabsf(targetRPM) < 1e-3f) {
      rpmFilt = 0.0f;
      integ   = 0.0f;
      kicking = false;
      pwmCmd  = 0.0f;
    } else if (kicking) {
      // Still within kickstart window?
      if ((nowUs - kickStart) < KICK_DUR_US) {
        pwmCmd = (targetRPM > 0) ? KICK_PWM : -KICK_PWM;
      } else {
        kicking = false;  // kick done, hand off to PID
      }
    }

    if (!kicking && fabsf(targetRPM) > 1e-3f) {
      float err = targetRPM - rpmFilt;
      integ    += err * dt;
      integ     = constrain(integ, -ICLAMP, ICLAMP);
      float u   = kF * targetRPM + Kp * err + Ki * integ;
      pwmCmd    = constrain(u, -255.0f, 255.0f);
      if (fabsf(pwmCmd) < PWM_MIN) pwmCmd = (pwmCmd > 0) ? PWM_MIN : -PWM_MIN;
    }

    setMotorSigned(INB1, INB2, PWMB, pwmCmd);

    // Stall detection
    if (fabsf(rpm) < STALL_RPM && fabsf(targetRPM) > 1e-3f) {
      if (++stallCount > STALL_THRESH) {
        rpmFilt    = 0.0f;
        integ      = 0.0f;
        stallCount = 0;
        // Re-trigger kick if we still have a target
        if (fabsf(targetRPM) > 1e-3f) {
          kicking = true;
          kickStart = nowUs;
        }
      }
    } else {
      stallCount = 0;
    }

    tick++;
    if (tick % 2 == 0) {
      /*
      Serial.print("tgt=");   Serial.print(targetRPM, 2);
      Serial.print(" dc=");   Serial.print(dcount);
      Serial.print(" rpm=");  Serial.print(rpm, 2);
      Serial.print(" filt="); Serial.print(rpmFilt, 2);
      Serial.print(" kick="); Serial.print(kicking);
      Serial.print(" I=");    Serial.print(integ, 2);
      Serial.print(" pwm=");  Serial.println(pwmCmd, 1);
      */
    }
  }

}
