import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import * as giris from '../src/giris.js';

// Cloudflare çalışma ortamı ana modülün her adlı dışa aktarımını giriş noktası sayar; sabit dışa aktarılırsa
// Worker hiç başlamaz ("Incorrect type for map entry"). Ana modül yalnız varsayılan işleyiciyi vermeli.
test('Worker giriş modülü yalnız varsayılan işleyiciyi dışa aktarır', () => {
  assert.deepEqual(Object.keys(giris), ['default']);
  assert.equal(typeof giris.default.fetch, 'function');
  const toml = readFileSync(new URL('../wrangler.toml', import.meta.url), 'utf8');
  assert.match(toml, /^main = "src\/giris\.js"/m);
});
