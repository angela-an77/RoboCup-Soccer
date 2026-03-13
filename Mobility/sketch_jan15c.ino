
#include <Encoder.h>

const float MAX_RPM_OUT = 1000.0f;          
const float kF = 255.0f / MAX_RPM_OUT;    

float targetRPM;      
float pwmCmd;     
float integ;
int tick = 0;
static float rpmFilt = 0.0f;
const float ALPHA = 0.2f;

float MAX_RPM = 800;

float Kp = 0.8f;
float Ki = 1.0f;

float PWM_MIN = 0.0f;

float ICLAMP = 120.0f;

constexpr int EA = 2;
constexpr int EB = 3;

const int INB1 = 38;
const int INB2 = 39;
const int PWMB = 15;

//const int INB1 = 33;
//const int INB2 = 34;
//const int PWMB = 14;


//const int INC1 = 38;
//const int INC2 = 39;
//const int PWMC = 15;

constexpr float CPR = 464.64f;

Encoder enc(EA, EB);

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

float driveVector4(float speed, float angleDeg) {
  if (speed < 0) speed = 0;
  if (speed > 255) speed = 255;

  angleDeg = fmodf(angleDeg, 360.0f);
  if (angleDeg < 0) angleDeg += 360.0f;

  float th = deg2rad(angleDeg);
  float Vx = speed * cosf(th);
  float Vy = speed * sinf(th);

  const float aB = deg2rad(330.0f);
  //const float aC = deg2rad(285.0f);

  float cmdB = Vx * cosf(aB) + Vy * sinf(aB);
  //float cmdC = Vx * cosf(aC) + Vy * sinf(aC);

  float maxAbs = fabsf(cmdB);
  if (maxAbs > 255.0f) {
    float k = 255.0f / maxAbs;
    cmdB *= k; //cmdC *= k;
  }

  return cmdB;
  //setMotorSigned(INC1, INC2, PWMC, cmdC);
}

void setup() {
  Serial.begin(115200);
  // bps
  while(!Serial && millis() < 1500) {}
  //wait until connection
  
  pinMode(INB1, OUTPUT); pinMode(INB2, OUTPUT); pinMode(PWMB, OUTPUT);
  //pinMode(INC1, OUTPUT); pinMode(INC2, OUTPUT); pinMode(PWMC, OUTPUT);
}

void loop() {
  if (Serial.available()) {
    char cmd = Serial.read();
    if (cmd == 'F') {
      float cmdB = driveVector4(10, 100);
      targetRPM = (cmdB / 255.0f) * MAX_RPM;  
      } 
    if (cmd == 'S') {
      targetRPM = 0.0f;
      integ = 0.0f;
      pwmCmd = 0.0f;
      setMotorSigned(INB1, INB2, PWMB, 0.0f);
      }
    }
  
  static uint32_t lastUs = micros();
  //micros is time since boot 
  //Us = Microseconds
  static long lastCount = 0;
  //static to keep
  uint32_t nowUs = micros();
  uint32_t dtUS = nowUs - lastUs;

  if (dtUS >= 20000){
    lastUs = nowUs;
    long count = enc.read();
    long dcount = count - lastCount;
    lastCount = count;
    float dt = dtUS / 1e6f;
    float cps = dcount / dt;
    float rpm = (cps / CPR) * 60.0f;
    rpm = -rpm;   // flip sign
    
    rpmFilt += ALPHA * (rpm - rpmFilt);
    float err = targetRPM - rpmFilt;
    

    if(fabs(targetRPM)< 1e-3f) {
        rpmFilt = 0.0f;
        integ = 0.0f;
      } else{
        integ += err * dt;
        integ = constrain(integ, -ICLAMP, ICLAMP);
      }

    float u = kF * targetRPM + Kp * err + Ki * integ;
    pwmCmd = constrain(u, -255.0f, 255.0f);

    tick++;
    if (tick % 10 == 0) { // prints ~5x/sec (50Hz / 10)
      Serial.print("tgt=");   Serial.print(targetRPM, 2);
      Serial.print(" dc=");   Serial.print(dcount);
      Serial.print(" rpm=");  Serial.print(rpm, 2);
      Serial.print(" filt="); Serial.print(rpmFilt, 2);
      Serial.print(" I=");    Serial.print(integ, 2);
      Serial.print(" pwm=");  Serial.println(pwmCmd, 1);
      
    }
    
    if(fabs(targetRPM) > 1e-30 && fabs(pwmCmd) > 0 && fabs(pwmCmd) < PWM_MIN){
      pwmCmd = (pwmCmd > 0) ? PWM_MIN: -PWM_MIN;
      }

    setMotorSigned(INB1, INB2, PWMB, pwmCmd);

  }
}
