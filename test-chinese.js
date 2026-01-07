/**
 * Test script to send Chinese characters to the API
 */

const http = require('http');

const testData = JSON.stringify({
  model: 'gpt-3.5-turbo',
  messages: [
    {
      role: 'user',
      content: '你好，這是測試中文'
    }
  ]
});

console.log('[TEST] Sending request with Chinese content:', testData);
console.log('[TEST] Content hex:', Buffer.from('你好，這是測試中文', 'utf8').toString('hex'));

const options = {
  hostname: '127.0.0.1',
  port: 11434,
  path: '/v1/chat/completions',
  method: 'POST',
  headers: {
    'Content-Type': 'application/json; charset=utf-8',
    'Authorization': 'Bearer fhiahio3FJo33LWMFwald',
    'Content-Length': Buffer.byteLength(testData, 'utf8')
  }
};

const req = http.request(options, (res) => {
  console.log('[TEST] Status:', res.statusCode);
  console.log('[TEST] Headers:', res.headers);

  let data = '';
  res.on('data', (chunk) => {
    data += chunk;
  });

  res.on('end', () => {
    console.log('[TEST] Response:', data);
  });
});

req.on('error', (error) => {
  console.error('[TEST] Error:', error);
});

req.write(testData);
req.end();
