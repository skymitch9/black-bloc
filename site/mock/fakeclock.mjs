const Real = Date;
const raw = (process.env.BB_FAKE_NOW || '').trim();
const days = /^\+(\d+)d$/.exec(raw);
const target = days ? Real.now() + Number(days[1]) * 86400000 : Real.parse(raw);
if (raw && Number.isNaN(target)) throw new Error(`BB_FAKE_NOW=${raw} is not +Nd or an ISO instant`);
const offset = raw ? target - Real.now() : 0;

class FakeDate extends Real {
  constructor(...args) {
    if (args.length) super(...args);
    else super(Real.now() + offset);
  }

  static now() {
    return Real.now() + offset;
  }
}

if (offset) globalThis.Date = FakeDate;
