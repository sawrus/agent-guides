/** Independent tests against a delivered JavaScript calculator's public exports. */
import { pathToFileURL } from 'node:url';

const cases = [['addition', '9+4', 9, '+', 4, 13], ['subtraction', '9-4', 9, '-', 4, 5],
  ['multiplication', '9*4', 9, '*', 4, 36], ['division', '9/4', 9, '/', 4, 2.25]];
// One spelling per run: every case must pass with the same operator dialect.
const dialects = [{'+':'+','-':'-','*':'*','/':'/'}, {'+':'+','-':'−','*':'×','/':'÷'},
  {'+':'add','-':'subtract','*':'multiply','/':'divide'}];
for (const file of process.argv.slice(2)) {
  try {
    const before = new Map(Object.getOwnPropertyNames(globalThis).map(name => [name, globalThis[name]]));
    const module = await import(pathToFileURL(file));
    const exports = {...module.default, ...module};
    for (const name of Object.getOwnPropertyNames(globalThis)) {
      const value = globalThis[name];
      if (/calculat/i.test(name) && value && typeof value === 'object' && before.get(name) !== value) Object.assign(exports, value);
    }
    if (['createInitialState', 'transition', 'displayValue'].every(name => typeof exports[name] === 'function')) {
      const execute = (a, op, b) => {
        let state = exports.createInitialState();
        for (const digit of String(a)) state = exports.transition(state, {type:'digit', value:digit});
        state = exports.transition(state, {type:'operator', value:op});
        for (const digit of String(b)) state = exports.transition(state, {type:'digit', value:digit});
        return exports.transition(state, {type:'equals'});
      };
      const checks = {};
      try {
        for (const [label, , a, op, b, expected] of cases) {
          const state = execute(a,op,b);
          checks[label] = !state.error && Number(exports.displayValue(state)) === expected;
        }
        const zero = execute(9,'/',0);
        checks.division_by_zero = zero.error === true || /error|ошиб|zero|нол/i.test(String(exports.displayValue(zero)));
        if (Object.values(checks).every(Boolean)) {
          console.log(JSON.stringify({verified:true, checks, entrypoint:`${file}:public state transitions`}));
          process.exit(0);
        }
      } catch {}
    }
    // Keypad state APIs: one function per key, state object with display and an error flag.
    const keypad = {digit: ['inputDigit', 'enterDigit'], operator: ['chooseOperation', 'chooseOperator'], equals: ['calculate', 'equals']};
    const pick = names => names.find(name => typeof exports[name] === 'function');
    const [digitFn, operatorFn, equalsFn] = [pick(keypad.digit), pick(keypad.operator), pick(keypad.equals)];
    if (typeof exports.createCalculator === 'function' && digitFn && operatorFn && equalsFn) {
      for (const dialect of [...dialects.slice(0, 2), {'+':'add','-':'subtract','*':'multiply','/':'divide'}]) {
        const execute = (a, op, b) => {
          let state = exports.createCalculator();
          for (const digit of String(a)) state = exports[digitFn](state, digit) ?? state;
          state = exports[operatorFn](state, dialect[op]) ?? state;
          for (const digit of String(b)) state = exports[digitFn](state, digit) ?? state;
          return exports[equalsFn](state) ?? state;
        };
        const failed = state => state.hasError === true || state.error === true;
        try {
          const checks = {};
          for (const [label, , a, op, b, expected] of cases) {
            const state = execute(a, op, b);
            checks[label] = !failed(state) && Number(state.display) === expected;
          }
          try {
            const state = execute(9,'/',0);
            checks.division_by_zero = failed(state) || /error|ошиб|zero|нол/i.test(String(state.display));
          } catch (error) { checks.division_by_zero = /zero|division|нол|делен/i.test(String(error)); }
          if (Object.values(checks).every(Boolean)) {
            console.log(JSON.stringify({verified:true,checks,entrypoint:`${file}:public calculator state API`}));
            process.exit(0);
          }
        } catch {}
      }
    }
    for (const [name, fn] of Object.entries(exports)) {
      if (typeof fn !== 'function' || !/calculat|evaluat|compute/i.test(name)) continue;
      let invoke;
      if (fn.length === 1) invoke = (expr) => fn(expr);
      else if (fn.length === 3) {
        const params = fn.toString().match(/^[^(]*\(([^)]*)\)/)?.[1].split(',').map(s => s.trim()) ?? [];
        const opIndex = params.findIndex(p => /^(op|operator|operation)$/.test(p));
        if (opIndex < 0) continue;
        invoke = (_, a, op, b) => { const args = [a,b]; args.splice(opIndex,0,op); return fn(...args); };
      } else continue;
      for (const dialect of dialects) {
      const checks = {};
      try {
        for (const [label, expr, a, op, b, expected] of cases) {
          const actual = await invoke(expr, a, dialect[op], b);
          const value = actual && typeof actual === 'object' && actual.ok === true ? actual.value : actual;
          checks[label] = typeof value !== 'boolean' && value !== null && Number.isFinite(Number(value)) && Math.abs(Number(value)-expected) < 1e-10;
        }
        try {
          const zero = await invoke('9/0',9,dialect['/'],0);
          checks.division_by_zero = zero === null || typeof zero === 'string' && /error|ошиб|zero|нол|нуль/i.test(zero) || zero?.ok === false && /zero|division|нол|делен/i.test(String(zero.error));
        } catch (error) { checks.division_by_zero = /zero|division|finite|нол|нуль|делен/i.test(String(error)); }
        if (Object.values(checks).every(Boolean)) {
          console.log(JSON.stringify({verified:true, checks, entrypoint:`${file}:${name}`}));
          process.exit(0);
        }
      } catch {}
      }
    }
  } catch {}
}
console.log(JSON.stringify({verified:false,reason:'No supported JavaScript calculator export'}));
process.exit(1);
