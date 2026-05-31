// ─── Constants ───────────────────────────────────────────────────────────────

const GEMINI_MODEL       = 'gemini-2.5-flash-lite';
const GEMINI_API_BASE    = 'https://generativelanguage.googleapis.com/v1beta/models/';
const MAX_HISTORY_TURNS  = 8;
const LINE_REPLY_API_URL = 'https://api.line.me/v2/bot/message/reply';
const LINE_PUSH_API_URL  = 'https://api.line.me/v2/bot/message/push';
const SHEET_NAME         = 'daily_log';
const SHEET_HEADERS      = [
  'date', 'weight_kg', 'water_glasses', 'exercise_min',
  'sleep_hr', 'mood_1to5', 'note', 'source_message', 'updated_at'
];

// Drop any extracted value outside these bounds (hallucination guard).
const SANITY_BOUNDS = {
  weight_kg:     [40, 200],
  water_glasses: [0, 25],
  exercise_min:  [0, 300],
  sleep_hr:      [0, 15],
  mood_1to5:     [1, 5]
};

const CONTEXT_WINDOW_DAYS = 7;
const GEMINI_MAX_RETRIES = 1;
const GEMINI_MAX_RETRY_DELAY_MS = 5000;
const SOURCE_MSG_MAX_LEN  = 200;
const EVENING_CHECKIN_MESSAGE = 'วันนี้เป็นยังไงบ้างครับ 😊 ดื่มน้ำกี่แก้ว ออกกำลังกายกี่นาที นอนกี่ชั่วโมง อารมณ์ 1-5 เท่าไร? ถ้าชั่งน้ำหนักหรือมีน้ำหวาน/ขนม บอกเพิ่มได้เลยนะ';
const EVENING_REMINDER_MESSAGE = 'ก่อนพักผ่อน แวะบอกโค้ชสั้นๆ ได้นะครับ 😊 วันนี้ดื่มน้ำกี่แก้ว และได้ขยับร่างกายบ้างไหม?';
const EVENING_STATE_PROPERTIES = [
  'LAST_EVENING_CHECKIN_DATE',
  'LAST_EVENING_CHECKIN_RESPONSE_DATE',
  'LAST_EVENING_REMINDER_DATE'
];

// ─── System Prompt ────────────────────────────────────────────────────────────

const SYSTEM_PROMPT = `คุณคือโค้ชสุขภาพส่วนตัวที่เป็นเพื่อนสนิท ชื่อ "โค้ชแบงค์"
คุณดูแลเพื่อนชาย อายุ 33 ปี ที่มีภาวะเมตาบอลิกและสงสัย MASLD (ไขมันพอกตับ)

ข้อมูลสุขภาพปัจจุบัน (ผลเลือดล่าสุด):
- GGT: 371 (สูงมาก ตับกำลังเครียด)
- กรดยูริก: 11.0 (สูงมาก เสี่ยงเกาต์และไตเสียหาย)
- TG (ไตรกลีเซอไรด์): 221 (สูง สัมพันธ์กับน้ำตาล/แป้ง)
- LDL: 139 (เริ่มสูง)
- eGFR: 75 (ไตทำงานลดลงเล็กน้อย ต้องระวัง)
- ไม่ดื่มแอลกอฮอล์ ไม่ใช้สารใดๆ

คันโยก 80/20 ที่สำคัญที่สุด (เรียงลำดับ):
1. ตัดน้ำตาล/ฟรุกโตส — น้ำอัดลม น้ำผลไม้ ขนมหวาน (ต้นเหตุหลักของ TG สูงและไขมันพอกตับ)
2. ดื่มน้ำเปล่า 8-10 แก้วต่อวัน (ช่วยไต ช่วยกรดยูริก)
3. ออกกำลังกาย 30 นาที อย่างน้อย 5 วัน/สัปดาห์ (เดิน วิ่ง ว่ายน้ำ ปั่นจักรยาน)
4. ควบคุมน้ำหนัก — ลด 5-10% จะเปลี่ยนค่าตับได้ชัดเจน

บทบาทของคุณ:
- ติดตามพฤติกรรมรายวัน ถามสั้นๆ ว่าวันนี้ดื่มน้ำกี่แก้ว ออกกำลังกายไหม กินอะไรบ้าง
- ให้กำลังใจเมื่อทำดี บอกทางออกเมื่อสะดุด
- ส่งข้อความเชิงรุกตอนเช้าเพื่อเริ่มต้นวันให้ดี
- จำบทสนทนาล่าสุดเพื่อต่อยอด ไม่ถามซ้ำ

กฎที่ต้องปฏิบัติเสมอ (ห้ามฝ่าฝืนทุกกรณี):
- คุณเป็นโค้ช ไม่ใช่แพทย์ ห้ามวินิจฉัยโรคหรือตีความผลเลือดแทนแพทย์
- ห้ามแนะนำปรับ ลด หรือหยุดยาที่แพทย์สั่ง
- ห้ามแนะนำอาหารเสริม วิตามิน สมุนไพร หรือยาใดๆ โดยไม่ผ่านแพทย์
- ถ้าเพื่อนบอกอาการที่น่าเป็นห่วง (เจ็บหน้าอก หายใจลำบาก ปวดท้องรุนแรง ปัสสาวะผิดปกติ) ให้แนะนำพบแพทย์ทันที
- อย่าขยายความข้อมูลสุขภาพที่ไม่มีใน system prompt โดยไม่มีหลักฐาน

สไตล์การสื่อสาร:
- ตอบเป็นภาษาไทยเสมอ
- ข้อความสั้น กระชับ อ่านง่ายบนมือถือ ไม่เกิน 5-6 ประโยคต่อครั้ง
- ใช้อีโมจิพอประมาณ (1-3 ตัวต่อข้อความ) อย่าใช้มากเกินไป
- ห้ามใช้ ## หรือ ** (LINE ไม่แสดง Markdown)
- พูดเหมือนเพื่อน ไม่ต้องเป็นทางการ แต่ให้ความรู้สึกจริงจังเรื่องสุขภาพ`;

// Morning message templates — one per weekday, no Gemini call needed
const MORNING_MESSAGES = {
  0: 'สวัสดีวันอาทิตย์ครับ! 🌅 วันหยุดแบบนี้เหมาะมากเลยนะสำหรับเดินหรือปั่นจักรยาน วันนี้วางแผนอะไรไว้บ้าง?',
  1: 'สวัสดีวันจันทร์ครับ! 💪 สัปดาห์ใหม่ เริ่มต้นดีๆ ด้วยน้ำ 8 แก้ว วันนี้ตั้งเป้าดื่มน้ำไว้กี่แก้ว?',
  2: 'อรุณสวัสดิ์ครับ 🌤 เมื่อวานเป็นยังไงบ้าง? วันนี้ออกกำลังกายได้ไหม แม้แค่เดิน 30 นาทีก็ช่วยได้มาก',
  3: 'สวัสดีตอนเช้าครับ! ☀️ กลางสัปดาห์แล้ว ตรวจสอบน้ำตาลในมื้ออาหารวันนี้ด้วยนะ วันนี้จะเลี่ยงของหวานอะไรได้บ้าง?',
  4: 'อรุณสวัสดิ์ครับ 🙌 เกือบถึงสุดสัปดาห์แล้ว ดื่มน้ำเปล่าให้ครบ 8 แก้ววันนี้นะ วันนี้จะพกน้ำไว้ใกล้ตัวไหม?',
  5: 'สวัสดีวันศุกร์ครับ! 🎉 ใกล้วันหยุดแล้ว วางแผนออกกำลังกายช่วงวันหยุดไว้บ้างไหม?',
  6: 'สวัสดีวันเสาร์ครับ! 😊 วันนี้มีเวลาว่าง ลองทำอาหารเองสักมื้อ หลีกเลี่ยงน้ำตาลได้ง่ายกว่าสั่งข้างนอก วันนี้อยากทำเมนูอะไร?'
};

// ─── Webhook Entry Point ──────────────────────────────────────────────────────

function doPost(e) {
  try {
    const body = JSON.parse(e.postData.contents);
    const props = PropertiesService.getScriptProperties();

    for (const event of body.events) {
      if (event.type !== 'message' || event.message.type !== 'text') continue;
      if (!event.replyToken) continue;

      const userId    = event.source.userId;
      const replyToken = event.replyToken;
      const userText  = event.message.text;

      // Auto-save userId on first message
      if (!props.getProperty('LINE_USER_ID')) {
        props.setProperty('LINE_USER_ID', userId);
      }

      markEveningCheckinResponse_();
      handleMessage_(userId, replyToken, userText);
    }
  } catch (err) {
    Logger.log('doPost error: ' + err.message);
  }

  return ContentService.createTextOutput('OK').setMimeType(ContentService.MimeType.TEXT);
}

// ─── Message Orchestrator ─────────────────────────────────────────────────────

function handleMessage_(userId, replyToken, userText) {
  logToDoc_('IN', userText);

  let history = getHistory_();
  let replyText;

  try {
    replyText = callGemini_(userText, history);
  } catch (err) {
    Logger.log('Gemini error: ' + err.message);
    replyText = 'ขอโทษนะ ตอนนี้ระบบขัดข้องชั่วคราว ลองใหม่อีกครั้งนะ 🙏';
  }

  // Update rolling history
  history.push({ role: 'user',  parts: [{ text: userText }] });
  history.push({ role: 'model', parts: [{ text: replyText }] });

  // Trim to MAX_HISTORY_TURNS pairs (2 entries per turn)
  while (history.length > MAX_HISTORY_TURNS * 2) {
    history.splice(0, 2);
  }

  saveHistory_(history);
  replyLine_(replyToken, replyText);
  logToDoc_('OUT', replyText);

  // Phase A: structured capture (best-effort, never blocks reply)
  try {
    const data = extractHealthData_(userText);
    if (Object.keys(data).length > 0) {
      logToSheet_(data, userText);
    }
  } catch (err) {
    Logger.log('capture pipeline error: ' + err.message);
  }
}

// ─── Gemini API ───────────────────────────────────────────────────────────────

function parseRetryDelayMs_(responseText) {
  const retryMatch = String(responseText || '').match(/"retryDelay"\s*:\s*"(\d+)s"/);
  if (!retryMatch) return 5000;

  const retryMs = Number(retryMatch[1]) * 1000;
  if (!Number.isFinite(retryMs) || retryMs <= 0) return 5000;

  return Math.min(retryMs, GEMINI_MAX_RETRY_DELAY_MS);
}

function recordGeminiError_(httpStatus, category) {
  const diagnostic = {
    timestamp: new Date().toISOString(),
    model: GEMINI_MODEL,
    http_status: httpStatus === null ? '' : httpStatus,
    category: category
  };

  PropertiesService.getScriptProperties()
    .setProperty('LAST_GEMINI_ERROR', JSON.stringify(diagnostic));
  Logger.log(
    'Gemini diagnostic: model=' + diagnostic.model +
    ' status=' + (diagnostic.http_status || 'none') +
    ' category=' + diagnostic.category
  );
}

function classifyGeminiError_(responseCode) {
  if (responseCode === 400) return 'BAD_REQUEST';
  if (responseCode === 401 || responseCode === 403) return 'AUTH_ERROR';
  if (responseCode === 404) return 'MODEL_NOT_FOUND';
  if (responseCode === 429) return 'RATE_LIMIT';
  if (responseCode >= 500) return 'PROVIDER_ERROR';
  return 'HTTP_ERROR';
}

function readGeminiText_(responseBody, errorPrefix) {
  const text = responseBody &&
    responseBody.candidates &&
    responseBody.candidates[0] &&
    responseBody.candidates[0].content &&
    responseBody.candidates[0].content.parts &&
    responseBody.candidates[0].content.parts[0] &&
    responseBody.candidates[0].content.parts[0].text;

  if (typeof text !== 'string' || !text.trim()) {
    recordGeminiError_(200, 'MISSING_TEXT');
    throw new Error(errorPrefix + ': missing candidate text');
  }

  return text.trim();
}

function fetchGeminiResponse_(requestBody, errorPrefix) {
  const apiKey = PropertiesService.getScriptProperties().getProperty('GEMINI_API_KEY');
  if (!apiKey) {
    recordGeminiError_(null, 'MISSING_API_KEY');
    throw new Error(errorPrefix + ': GEMINI_API_KEY is not set');
  }

  const url = GEMINI_API_BASE + GEMINI_MODEL + ':generateContent?key=' + apiKey;

  for (let attempt = 0; attempt <= GEMINI_MAX_RETRIES; attempt++) {
    let response;
    try {
      response = UrlFetchApp.fetch(url, {
        method: 'POST',
        contentType: 'application/json',
        payload: JSON.stringify(requestBody),
        muteHttpExceptions: true
      });
    } catch (err) {
      recordGeminiError_(null, 'FETCH_EXCEPTION');
      throw new Error(errorPrefix + ': fetch failed');
    }

    const responseCode = response.getResponseCode();
    const responseText = response.getContentText();

    if (responseCode === 200) {
      try {
        return JSON.parse(responseText);
      } catch (err) {
        recordGeminiError_(responseCode, 'INVALID_JSON_RESPONSE');
        throw new Error(errorPrefix + ': invalid JSON response');
      }
    }

    if (responseCode === 429 && attempt < GEMINI_MAX_RETRIES) {
      const retryDelayMs = parseRetryDelayMs_(responseText);
      Logger.log(errorPrefix + ' rate limited; retrying in ' + retryDelayMs + 'ms');
      Utilities.sleep(retryDelayMs);
      continue;
    }

    const category = classifyGeminiError_(responseCode);
    recordGeminiError_(responseCode, category);
    throw new Error(errorPrefix + ' ' + responseCode + ': ' + category);
  }

  recordGeminiError_(null, 'EXHAUSTED_RETRIES');
  throw new Error(errorPrefix + ' exhausted retries');
}

function callGemini_(userText, history) {
  // Build contents: existing history + new user message
  const contents = history.concat([{ role: 'user', parts: [{ text: userText }] }]);
  const userContext = PropertiesService.getScriptProperties().getProperty('USER_CONTEXT') || '';
  const systemText = userContext
    ? SYSTEM_PROMPT + '\n\nบริบทพฤติกรรม 7 วันล่าสุดของผู้ใช้:\n' + userContext
    : SYSTEM_PROMPT;

  const requestBody = {
    systemInstruction: { parts: [{ text: systemText }] },
    contents: contents,
    generationConfig: {
      temperature: 0.7,
      maxOutputTokens: 400,
      topP: 0.9
    }
  };

  const parsed = fetchGeminiResponse_(requestBody, 'Gemini API error');
  return sanitizeLineText_(readGeminiText_(parsed, 'Gemini API error'));
}

function sanitizeLineText_(text) {
  return String(text || '')
    .replace(/\*\*/g, '')
    .replace(/^#{1,6}\s*/gm, '')
    .trim();
}

function runGeminiSmokeTest() {
  const responseBody = fetchGeminiResponse_({
    contents: [{
      role: 'user',
      parts: [{ text: 'ตอบคำว่า OK เท่านั้น' }]
    }],
    generationConfig: {
      temperature: 0,
      maxOutputTokens: 20
    }
  }, 'Gemini smoke test error');
  const text = readGeminiText_(responseBody, 'Gemini smoke test error');

  Logger.log('runGeminiSmokeTest PASS: model=' + GEMINI_MODEL + ' response=' + text);
}

// ─── LINE Messaging ───────────────────────────────────────────────────────────

function replyLine_(replyToken, text) {
  const token = PropertiesService.getScriptProperties().getProperty('LINE_CHANNEL_ACCESS_TOKEN');

  const response = UrlFetchApp.fetch(LINE_REPLY_API_URL, {
    method: 'POST',
    contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + token },
    payload: JSON.stringify({
      replyToken: replyToken,
      messages: [{ type: 'text', text: text }]
    }),
    muteHttpExceptions: true
  });

  Logger.log('replyLine status: ' + response.getResponseCode());
}

function pushLine_(userId, text) {
  const token = PropertiesService.getScriptProperties().getProperty('LINE_CHANNEL_ACCESS_TOKEN');

  const response = UrlFetchApp.fetch(LINE_PUSH_API_URL, {
    method: 'POST',
    contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + token },
    payload: JSON.stringify({
      to: userId,
      messages: [{ type: 'text', text: text }]
    }),
    muteHttpExceptions: true
  });

  const responseCode = response.getResponseCode();
  Logger.log('pushLine status: ' + responseCode);
  return responseCode;
}

// ─── Proactive Check-ins (cron) ───────────────────────────────────────────────

function bangkokDate_() {
  return Utilities.formatDate(new Date(), 'Asia/Bangkok', 'yyyy-MM-dd');
}

function isSuccessfulHttpStatus_(statusCode) {
  return statusCode >= 200 && statusCode < 300;
}

function markEveningCheckinResponse_() {
  const props = PropertiesService.getScriptProperties();
  const today = bangkokDate_();

  if (props.getProperty('LAST_EVENING_CHECKIN_DATE') !== today) return;

  props.setProperty('LAST_EVENING_CHECKIN_RESPONSE_DATE', today);
  Logger.log('markEveningCheckinResponse_: recorded response for ' + today);
}

function shouldSendEveningReminder_(props, today) {
  return props.getProperty('LAST_EVENING_CHECKIN_DATE') === today &&
    props.getProperty('LAST_EVENING_CHECKIN_RESPONSE_DATE') !== today &&
    props.getProperty('LAST_EVENING_REMINDER_DATE') !== today;
}

function morningCheckin() {
  const props  = PropertiesService.getScriptProperties();
  const userId = props.getProperty('LINE_USER_ID');

  if (!userId) {
    Logger.log('morningCheckin: LINE_USER_ID not set yet, skipping');
    return;
  }

  const dayOfWeek = new Date().getDay(); // 0 = Sunday
  const message   = MORNING_MESSAGES[dayOfWeek];

  const responseCode = pushLine_(userId, message);
  if (isSuccessfulHttpStatus_(responseCode)) {
    logToDoc_('OUT (CRON)', message);
  }
}

function eveningCheckin() {
  const props = PropertiesService.getScriptProperties();
  const userId = props.getProperty('LINE_USER_ID');
  const today = bangkokDate_();

  if (!userId) {
    Logger.log('eveningCheckin: LINE_USER_ID not set yet, skipping');
    return;
  }
  if (props.getProperty('LAST_EVENING_CHECKIN_DATE') === today) {
    Logger.log('eveningCheckin: already sent for ' + today + ', skipping');
    return;
  }

  const responseCode = pushLine_(userId, EVENING_CHECKIN_MESSAGE);
  if (!isSuccessfulHttpStatus_(responseCode)) {
    Logger.log('eveningCheckin: push failed with status ' + responseCode);
    return;
  }

  props.setProperty('LAST_EVENING_CHECKIN_DATE', today);
  logToDoc_('OUT (CRON)', EVENING_CHECKIN_MESSAGE);
}

function eveningCheckinReminder() {
  const props = PropertiesService.getScriptProperties();
  const userId = props.getProperty('LINE_USER_ID');
  const today = bangkokDate_();

  if (!userId) {
    Logger.log('eveningCheckinReminder: LINE_USER_ID not set yet, skipping');
    return;
  }
  if (!shouldSendEveningReminder_(props, today)) {
    Logger.log('eveningCheckinReminder: reminder not needed for ' + today + ', skipping');
    return;
  }

  const responseCode = pushLine_(userId, EVENING_REMINDER_MESSAGE);
  if (!isSuccessfulHttpStatus_(responseCode)) {
    Logger.log('eveningCheckinReminder: push failed with status ' + responseCode);
    return;
  }

  props.setProperty('LAST_EVENING_REMINDER_DATE', today);
  logToDoc_('OUT (CRON)', EVENING_REMINDER_MESSAGE);
}

// ─── Google Doc Logging ───────────────────────────────────────────────────────

function logToDoc_(direction, text) {
  try {
    const props   = PropertiesService.getScriptProperties();
    const docId   = props.getProperty('LOG_DOC_ID');
    if (!docId) return;

    const now       = new Date();
    const timestamp = Utilities.formatDate(now, 'Asia/Bangkok', 'yyyy-MM-dd HH:mm:ss');
    const today     = Utilities.formatDate(now, 'Asia/Bangkok', 'yyyy-MM-dd');

    const doc  = DocumentApp.openById(docId);
    const body = doc.getBody();

    // Add date section header when the date changes
    const lastDate = props.getProperty('LOG_LAST_DATE');
    if (lastDate !== today) {
      body.appendParagraph(''); // spacing
      body.appendParagraph('=== ' + today + ' ===');
      props.setProperty('LOG_LAST_DATE', today);
    }

    body.appendParagraph('[' + timestamp + '] [' + direction + ']: ' + text);
  } catch (err) {
    Logger.log('logToDoc_ error: ' + err.message);
  }
}

// ─── Structured Health Capture ────────────────────────────────────────────────

function setupSheet() {
  setupSheet_();
}

function setupSheet_() {
  const sheetId = PropertiesService.getScriptProperties().getProperty('SHEET_ID');
  if (!sheetId) {
    throw new Error('SHEET_ID Script Property is not set');
  }

  const spreadsheet = SpreadsheetApp.openById(sheetId);
  let sheet = spreadsheet.getSheetByName(SHEET_NAME);

  if (!sheet) {
    sheet = spreadsheet.insertSheet(SHEET_NAME);
  }

  const lastColumn = sheet.getLastColumn();
  const headerWidth = Math.max(lastColumn, SHEET_HEADERS.length);
  const currentHeaders = sheet.getRange(1, 1, 1, SHEET_HEADERS.length).getValues()[0];
  const headersMatch = lastColumn === SHEET_HEADERS.length &&
    SHEET_HEADERS.every((header, index) => currentHeaders[index] === header);

  if (!headersMatch) {
    sheet.getRange(1, 1, 1, headerWidth).clearContent();
    sheet.getRange(1, 1, 1, SHEET_HEADERS.length).setValues([SHEET_HEADERS]);
  }

  sheet.setFrozenRows(1);
  return sheet;
}

function fallbackExtractHealthData_(userText) {
  const text = String(userText || '');
  const fallback = {};
  const findNumber_ = pattern => {
    const match = text.match(pattern);
    return match ? Number(match[1]) : null;
  };

  const weightKg = findNumber_(/(?:น้ำหนัก|หนัก)[^\d]{0,12}(\d+(?:\.\d+)?)/i) ||
    findNumber_(/(\d+(?:\.\d+)?)\s*(?:kg|กก\.?)/i);
  const waterGlasses = findNumber_(/(?:ดื่มน้ำ|น้ำ)[^\d]{0,12}(\d+(?:\.\d+)?)\s*แก้ว/i) ||
    findNumber_(/(\d+(?:\.\d+)?)\s*แก้ว/i);
  const exerciseMin = findNumber_(/(?:เดิน|วิ่ง|ออกกำลังกาย|ปั่น|ว่ายน้ำ)[^\d]{0,12}(\d+(?:\.\d+)?)\s*(?:นาที|min)/i);
  const sleepHr = findNumber_(/(?:นอน|หลับ)[^\d]{0,12}(\d+(?:\.\d+)?)\s*(?:ชั่วโมง|ชม\.?|hr)/i);
  const mood = findNumber_(/(?:อารมณ์|มู้ด)[^\d]{0,12}([1-5])/i);

  if (Number.isFinite(weightKg)) fallback.weight_kg = weightKg;
  if (Number.isFinite(waterGlasses)) fallback.water_glasses = waterGlasses;
  if (Number.isFinite(exerciseMin)) fallback.exercise_min = exerciseMin;
  if (Number.isFinite(sleepHr)) fallback.sleep_hr = sleepHr;
  if (Number.isFinite(mood)) fallback.mood_1to5 = mood;

  return fallback;
}

function sanitizeHealthData_(extracted) {
  const cleaned = {};

  Object.keys(SANITY_BOUNDS).forEach(key => {
    if (!Object.prototype.hasOwnProperty.call(extracted, key)) return;

    const value = Number(extracted[key]);
    const bounds = SANITY_BOUNDS[key];

    if (!Number.isFinite(value) || value < bounds[0] || value > bounds[1]) {
      Logger.log('extractHealthData_: dropped out-of-range ' + key + '=' + extracted[key]);
      return;
    }

    cleaned[key] = value;
  });

  if (typeof extracted.note === 'string' && extracted.note.trim()) {
    cleaned.note = extracted.note.trim();
  }

  return cleaned;
}

function extractHealthData_(userText) {
  const prompt = [
    'ดึงเฉพาะข้อมูลสุขภาพที่ผู้ใช้ระบุจริงจากข้อความด้านล่าง',
    'ตอบเป็น JSON object เท่านั้น ถ้าไม่มีข้อมูลให้ตอบ {}',
    'ใช้เฉพาะ key เหล่านี้: weight_kg, water_glasses, exercise_min, sleep_hr, mood_1to5, note',
    'หน่วย: น้ำหนัก kg, น้ำเป็นจำนวนแก้ว, ออกกำลังกายเป็นนาที, นอนเป็นชั่วโมง, อารมณ์ 1-5',
    'ห้ามเดา ห้ามคำนวณข้อมูลที่ไม่ได้ระบุ ห้ามใส่ key ที่ไม่มีข้อมูล',
    'ข้อความผู้ใช้: ' + String(userText || '')
  ].join('\n');

  try {
    const responseBody = fetchGeminiResponse_({
      contents: [{ role: 'user', parts: [{ text: prompt }] }],
      generationConfig: {
        temperature: 0,
        responseMimeType: 'application/json'
      }
    }, 'Gemini extraction error');
    const rawText = readGeminiText_(responseBody, 'Gemini extraction error');
    let extracted;
    try {
      extracted = JSON.parse(rawText);
    } catch (err) {
      recordGeminiError_(200, 'INVALID_STRUCTURED_OUTPUT');
      throw new Error('Gemini extraction error: invalid structured output');
    }
    return sanitizeHealthData_(extracted);
  } catch (err) {
    Logger.log('extractHealthData_ error: ' + err.message);
    const fallback = fallbackExtractHealthData_(userText);
    if (Object.keys(fallback).length > 0) {
      Logger.log('extractHealthData_: using regex fallback');
      return sanitizeHealthData_(fallback);
    }
    return {};
  }
}

function logToSheet_(data, sourceText) {
  if (!data || Object.keys(data).length === 0) return;

  const lock = LockService.getScriptLock();
  let lockAcquired = false;

  try {
    lock.waitLock(5000);
    lockAcquired = true;

    const sheet = setupSheet_();
    const now = new Date();
    const today = Utilities.formatDate(now, 'Asia/Bangkok', 'yyyy-MM-dd');
    const lastRow = sheet.getLastRow();
    const dates = lastRow > 1
      ? sheet.getRange(2, 1, lastRow - 1, 1).getDisplayValues().map(row => row[0])
      : [];
    const existingIndex = dates.indexOf(today);
    const rowNumber = existingIndex === -1 ? null : existingIndex + 2;
    const row = rowNumber
      ? sheet.getRange(rowNumber, 1, 1, SHEET_HEADERS.length).getValues()[0]
      : new Array(SHEET_HEADERS.length).fill('');
    const mergeFields = [
      'weight_kg', 'water_glasses', 'exercise_min',
      'sleep_hr', 'mood_1to5', 'note'
    ];

    row[SHEET_HEADERS.indexOf('date')] = today;
    mergeFields.forEach(key => {
      if (Object.prototype.hasOwnProperty.call(data, key)) {
        row[SHEET_HEADERS.indexOf(key)] = data[key];
      }
    });
    row[SHEET_HEADERS.indexOf('source_message')] = String(sourceText || '').slice(0, SOURCE_MSG_MAX_LEN);
    row[SHEET_HEADERS.indexOf('updated_at')] = now.toISOString();

    if (rowNumber) {
      sheet.getRange(rowNumber, 1, 1, SHEET_HEADERS.length).setValues([row]);
    } else {
      sheet.appendRow(row);
    }
  } catch (err) {
    Logger.log('logToSheet_ error: ' + err.message);
  } finally {
    if (lockAcquired) {
      lock.releaseLock();
    }
  }
}

function summarizeContext_() {
  const props = PropertiesService.getScriptProperties();
  const sheet = setupSheet_();
  const lastRow = sheet.getLastRow();
  const rows = lastRow > 1
    ? sheet.getRange(2, 1, lastRow - 1, SHEET_HEADERS.length).getValues()
    : [];
  const todayText = Utilities.formatDate(new Date(), 'Asia/Bangkok', 'yyyy-MM-dd');
  const today = new Date(todayText + 'T00:00:00+07:00');
  const recentRows = rows.filter(row => {
    const rawDate = row[SHEET_HEADERS.indexOf('date')];
    const dateText = rawDate instanceof Date
      ? Utilities.formatDate(rawDate, 'Asia/Bangkok', 'yyyy-MM-dd')
      : String(rawDate || '').trim();
    const rowDate = new Date(dateText + 'T00:00:00+07:00');
    const ageDays = Math.floor((today.getTime() - rowDate.getTime()) / 86400000);

    return Number.isFinite(rowDate.getTime()) && ageDays >= 0 && ageDays < CONTEXT_WINDOW_DAYS;
  });

  if (recentRows.length === 0) {
    props.setProperty('USER_CONTEXT', '');
    return '';
  }

  const summaryColumns = [
    'date', 'weight_kg', 'water_glasses', 'exercise_min',
    'sleep_hr', 'mood_1to5', 'note'
  ];
  const tableText = [
    summaryColumns.join('\t'),
    ...recentRows.map(row => summaryColumns
      .map(key => {
        const value = row[SHEET_HEADERS.indexOf(key)];
        if (key === 'date' && value instanceof Date) {
          return Utilities.formatDate(value, 'Asia/Bangkok', 'yyyy-MM-dd');
        }
        return value === '' || value === null || typeof value === 'undefined' ? '' : String(value);
      })
      .join('\t'))
  ].join('\n');
  const prompt = [
    'สรุปพฤติกรรม 7 วันล่าสุดของผู้ใช้เป็นภาษาไทย 3-4 บรรทัด',
    'เน้น: น้ำ ออกกำลังกาย น้ำหนัก แนวโน้ม',
    'ห้ามวินิจฉัยโรค ห้ามแนะนำยา',
    '',
    tableText
  ].join('\n');
  const responseBody = fetchGeminiResponse_({
    contents: [{ role: 'user', parts: [{ text: prompt }] }],
    generationConfig: {
      temperature: 0.3,
      maxOutputTokens: 250
    }
  }, 'Gemini summary error');
  const summary = readGeminiText_(responseBody, 'Gemini summary error');
  props.setProperty('USER_CONTEXT', summary);
  return summary;
}

function dailyContextUpdate() {
  try {
    summarizeContext_();
  } catch (err) {
    Logger.log('dailyContextUpdate error: ' + err.message);
  }
}

function runSelfTest_() {
  const sheet = setupSheet_();
  const today = Utilities.formatDate(new Date(), 'Asia/Bangkok', 'yyyy-MM-dd');
  const sourceMessageIndex = SHEET_HEADERS.indexOf('source_message');
  const findTodayRow_ = targetSheet => {
    const lastRow = targetSheet.getLastRow();
    if (lastRow < 2) return null;

    const dates = targetSheet.getRange(2, 1, lastRow - 1, 1).getDisplayValues().map(row => row[0]);
    const index = dates.indexOf(today);
    return index === -1 ? null : index + 2;
  };
  const assert_ = (condition, message) => {
    if (!condition) throw new Error('runSelfTest_: ' + message);
    Logger.log('runSelfTest_ PASS: ' + message);
  };
  const originalRowNumber = findTodayRow_(sheet);
  const originalRow = originalRowNumber
    ? sheet.getRange(originalRowNumber, 1, 1, SHEET_HEADERS.length).getValues()[0]
    : null;

  try {
    const currentHeaders = sheet.getRange(1, 1, 1, SHEET_HEADERS.length).getValues()[0];
    assert_(JSON.stringify(currentHeaders) === JSON.stringify(SHEET_HEADERS), 'headers match');

    const extracted = extractHealthData_('วันนี้ดื่มน้ำ 6 แก้ว เดิน 30 นาที น้ำหนัก 74.5');
    assert_(extracted.water_glasses === 6, 'water extraction');
    assert_(extracted.exercise_min === 30, 'exercise extraction');
    assert_(extracted.weight_kg === 74.5, 'weight extraction');

    const absurd = extractHealthData_('น้ำหนัก 750');
    assert_(!Object.prototype.hasOwnProperty.call(absurd, 'weight_kg'), 'sanity bound drops absurd weight');

    logToSheet_({ weight_kg: 74.5, water_glasses: 6 }, 'self-test #1');
    logToSheet_({ sleep_hr: 7 }, 'self-test #2');

    const todayRowNumber = findTodayRow_(sheet);
    assert_(todayRowNumber !== null, 'today row exists');

    const todayDates = sheet.getRange(2, 1, sheet.getLastRow() - 1, 1)
      .getDisplayValues()
      .map(row => row[0])
      .filter(date => date === today);
    assert_(todayDates.length === 1, 'same-day logs merge into one row');

    const todayRow = sheet.getRange(todayRowNumber, 1, 1, SHEET_HEADERS.length).getValues()[0];
    assert_(todayRow[SHEET_HEADERS.indexOf('weight_kg')] === 74.5, 'merged row keeps weight');
    assert_(todayRow[SHEET_HEADERS.indexOf('water_glasses')] === 6, 'merged row keeps water');
    assert_(todayRow[SHEET_HEADERS.indexOf('sleep_hr')] === 7, 'merged row adds sleep');
  } finally {
    try {
      const restoreSheet = setupSheet_();
      const restoreRowNumber = findTodayRow_(restoreSheet);

      if (restoreRowNumber) {
        const restoreRow = restoreSheet.getRange(restoreRowNumber, 1, 1, SHEET_HEADERS.length).getValues()[0];

        if (restoreRow[sourceMessageIndex] === 'self-test #2') {
          if (originalRow) {
            restoreSheet.getRange(restoreRowNumber, 1, 1, SHEET_HEADERS.length).setValues([originalRow]);
          } else {
            restoreSheet.deleteRow(restoreRowNumber);
          }
        } else {
          Logger.log('runSelfTest_: skipped row restore because source_message changed');
        }
      } else if (originalRow) {
        restoreSheet.appendRow(originalRow);
      }
    } catch (err) {
      Logger.log('runSelfTest_ row restore error: ' + err.message);
    }

  }
}

function runSelfTest() {
  runSelfTest_();
}

function runContextSelfTest_() {
  const sheet = setupSheet_();
  const props = PropertiesService.getScriptProperties();
  const previousUserContext = props.getProperty('USER_CONTEXT');
  const today = Utilities.formatDate(new Date(), 'Asia/Bangkok', 'yyyy-MM-dd');
  const sourceMessageIndex = SHEET_HEADERS.indexOf('source_message');
  const findTodayRow_ = targetSheet => {
    const lastRow = targetSheet.getLastRow();
    if (lastRow < 2) return null;

    const dates = targetSheet.getRange(2, 1, lastRow - 1, 1).getDisplayValues().map(row => row[0]);
    const index = dates.indexOf(today);
    return index === -1 ? null : index + 2;
  };
  const assert_ = (condition, message) => {
    if (!condition) throw new Error('runContextSelfTest_: ' + message);
    Logger.log('runContextSelfTest_ PASS: ' + message);
  };
  const originalRowNumber = findTodayRow_(sheet);
  const originalRow = originalRowNumber
    ? sheet.getRange(originalRowNumber, 1, 1, SHEET_HEADERS.length).getValues()[0]
    : null;

  try {
    logToSheet_({
      weight_kg: 74.5,
      water_glasses: 6,
      exercise_min: 30
    }, 'context-self-test');

    const summary = summarizeContext_();
    assert_(typeof summary === 'string' && summary.length > 0, 'summary generated');
    assert_(props.getProperty('USER_CONTEXT') === summary, 'USER_CONTEXT written');
  } finally {
    try {
      const restoreSheet = setupSheet_();
      const restoreRowNumber = findTodayRow_(restoreSheet);

      if (restoreRowNumber) {
        const restoreRow = restoreSheet.getRange(restoreRowNumber, 1, 1, SHEET_HEADERS.length).getValues()[0];

        if (restoreRow[sourceMessageIndex] === 'context-self-test') {
          if (originalRow) {
            restoreSheet.getRange(restoreRowNumber, 1, 1, SHEET_HEADERS.length).setValues([originalRow]);
          } else {
            restoreSheet.deleteRow(restoreRowNumber);
          }
        } else {
          Logger.log('runContextSelfTest_: skipped row restore because source_message changed');
        }
      } else if (originalRow) {
        restoreSheet.appendRow(originalRow);
      }
    } catch (err) {
      Logger.log('runContextSelfTest_ row restore error: ' + err.message);
    }

    if (previousUserContext === null) {
      props.deleteProperty('USER_CONTEXT');
    } else {
      props.setProperty('USER_CONTEXT', previousUserContext);
    }
  }
}

function runContextSelfTest() {
  runContextSelfTest_();
}

function runProactiveCheckinSelfTest() {
  const props = PropertiesService.getScriptProperties();
  const today = bangkokDate_();
  const originalValues = {};
  const assert_ = (condition, message) => {
    if (!condition) throw new Error('runProactiveCheckinSelfTest: ' + message);
    Logger.log('runProactiveCheckinSelfTest PASS: ' + message);
  };

  EVENING_STATE_PROPERTIES.forEach(key => {
    originalValues[key] = props.getProperty(key);
  });

  try {
    EVENING_STATE_PROPERTIES.forEach(key => props.deleteProperty(key));
    assert_(!shouldSendEveningReminder_(props, today), 'no reminder before evening check-in');

    props.setProperty('LAST_EVENING_CHECKIN_DATE', today);
    assert_(shouldSendEveningReminder_(props, today), 'reminder eligible after unanswered check-in');

    markEveningCheckinResponse_();
    assert_(
      props.getProperty('LAST_EVENING_CHECKIN_RESPONSE_DATE') === today,
      'text response recorded for current check-in'
    );
    assert_(!shouldSendEveningReminder_(props, today), 'response suppresses reminder');

    props.deleteProperty('LAST_EVENING_CHECKIN_RESPONSE_DATE');
    props.setProperty('LAST_EVENING_REMINDER_DATE', today);
    assert_(!shouldSendEveningReminder_(props, today), 'sent reminder is not repeated');

    props.setProperty('LAST_EVENING_CHECKIN_DATE', '2000-01-01');
    props.deleteProperty('LAST_EVENING_REMINDER_DATE');
    assert_(!shouldSendEveningReminder_(props, today), 'old check-in does not trigger reminder');
  } finally {
    EVENING_STATE_PROPERTIES.forEach(key => {
      if (originalValues[key] === null) {
        props.deleteProperty(key);
      } else {
        props.setProperty(key, originalValues[key]);
      }
    });
  }
}

// ─── Trigger Setup (run once manually) ───────────────────────────────────────

function setupTriggers() {
  // Remove existing daily triggers to avoid duplicates and keep Phase B dormant.
  ScriptApp.getProjectTriggers()
    .filter(t => [
      'morningCheckin',
      'eveningCheckin',
      'eveningCheckinReminder',
      'dailyContextUpdate'
    ].includes(t.getHandlerFunction()))
    .forEach(t => ScriptApp.deleteTrigger(t));
  PropertiesService.getScriptProperties().deleteProperty('USER_CONTEXT');

  // Create daily 7am Bangkok trigger
  ScriptApp.newTrigger('morningCheckin')
    .timeBased()
    .atHour(7)
    .everyDays(1)
    .inTimezone('Asia/Bangkok')
    .create();

  // Create daily 8pm Bangkok structured check-in trigger
  ScriptApp.newTrigger('eveningCheckin')
    .timeBased()
    .atHour(20)
    .everyDays(1)
    .inTimezone('Asia/Bangkok')
    .create();

  // Create daily reminder around 9:30pm Bangkok
  ScriptApp.newTrigger('eveningCheckinReminder')
    .timeBased()
    .atHour(21)
    .nearMinute(30)
    .everyDays(1)
    .inTimezone('Asia/Bangkok')
    .create();

  Logger.log('setupTriggers: Phase A.1 check-ins set for 07:00, 20:00, and reminder around 21:30 Asia/Bangkok daily');
}

// ─── History Helpers ──────────────────────────────────────────────────────────

function getHistory_() {
  const raw = PropertiesService.getScriptProperties().getProperty('HISTORY');
  if (!raw) return [];

  try {
    return JSON.parse(raw);
  } catch (err) {
    Logger.log('getHistory_ parse error, resetting: ' + err.message);
    PropertiesService.getScriptProperties().deleteProperty('HISTORY');
    return [];
  }
}

function saveHistory_(history) {
  PropertiesService.getScriptProperties().setProperty('HISTORY', JSON.stringify(history));
}
