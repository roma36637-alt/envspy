'use strict';
// envspy hook for Node.js, loaded with NODE_OPTIONS=--require.
// Wraps process.env in a Proxy and records every read.
// Only variable NAMES are recorded, never values.
const fs = require('fs');
const { fileURLToPath } = require('url');

function install(logPath) {
  const fd = fs.openSync(logPath, 'a');
  const seen = new Set();
  const hits = new Map();
  const NAME = /^[A-Za-z_][A-Za-z0-9_]*$/;
  const HERE = __filename;
  let busy = false;
  let bulk = null; // names being copied by spread / Object.assign / spawn in this tick

  const parseFrame = (frame) => {
    const text = frame.trim().replace(/^at\s+/, '');
    const m = /\((.*):(\d+):(\d+)\)$/.exec(text) || /^(.*):(\d+):(\d+)$/.exec(text);
    if (!m) return null;
    let file = m[1];
    if (file.startsWith('file://')) {
      try { file = fileURLToPath(file); } catch (_) { /* keep as is */ }
    }
    return { file, line: Number(m[2]) };
  };

  const categorize = (file) => {
    if (file.startsWith('node:') || !/[\\/]/.test(file)) return 'runtime';
    if (file.includes('node_modules')) return 'lib';
    return 'app';
  };

  const record = (name, wasSet) => {
    if (busy) return;
    const n = (hits.get(name) || 0) + 1;
    hits.set(name, n);
    if (n > 100) return; // hot loop: stop paying for stack traces
    busy = true;
    try {
      const limit = Error.stackTraceLimit;
      Error.stackTraceLimit = 20;
      const stack = String(new Error().stack);
      Error.stackTraceLimit = limit;
      for (const frame of stack.split('\n').slice(1)) {
        const loc = parseFrame(frame);
        if (!loc || loc.file === HERE) continue;
        const key = `${name}|${loc.file}|${loc.line}|${wasSet}`;
        if (seen.has(key)) return;
        seen.add(key);
        const event = {
          k: name, m: 'optional', s: wasSet,
          f: loc.file, l: loc.line, c: categorize(loc.file), p: process.pid,
        };
        fs.writeSync(fd, JSON.stringify(event) + '\n');
        return;
      }
    } catch (_) {
      /* never break the app */
    } finally {
      busy = false;
    }
  };

  const interesting = (prop) =>
    typeof prop === 'string' && NAME.test(prop) && !(prop in Object.prototype);

  process.env = new Proxy(process.env, {
    get(target, prop) {
      if (bulk && typeof prop === 'string' && bulk.delete(prop)) return target[prop];
      if (interesting(prop)) record(prop, Object.prototype.hasOwnProperty.call(target, prop));
      return target[prop];
    },
    has(target, prop) {
      const present = Reflect.has(target, prop);
      if (interesting(prop)) record(prop, present);
      return present;
    },
    ownKeys(target) {
      const keys = Reflect.ownKeys(target);
      bulk = new Set(keys.filter((k) => typeof k === 'string'));
      process.nextTick(() => { bulk = null; });
      return keys;
    },
  });
}

const logPath = process.env.ENVSPY_LOG;
if (logPath) {
  try { install(logPath); } catch (_) { /* never break the app */ }
}