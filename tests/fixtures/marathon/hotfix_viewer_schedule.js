// data from spreadsheet
const DATA_URL = "https://script.google.com/macros/s/AKfycbyxanGFzAWbQV4Fso__LJh5eOb4GDjBYHx6sK79FTu3ww6z0sYs603UbQeEr-aKRoK7/exec";

// Eastern always (EDT or EST)
let selectedTimezone = "America/New_York";

// -------------------------------------------------------------
// Data cache — fetched once, re-used on every timezone change.
// Set to null to force a fresh fetch (e.g. when Apply is clicked).
// -------------------------------------------------------------
let cachedRows = null;

// Show names and showrunner names
const showLinks = {
  "creature corner": "https://youtube.com/playlist?list=PLz8YL4HVC87UKC3XkXFvdtBUSWEY3yUQf&si=jBRc0S240tx8E49Y",
  "crosshair": "https://youtube.com/playlist?list=PLz8YL4HVC87VcaUDbDWdEbWFEq5VsV6d1&si=bPlmWBGWF7daDQBu",
  "do all the things": "https://www.youtube.com/playlist?list=PLz8YL4HVC87WNnWalkZ1_Y0Akj7XWW4Vw",
  "express lane": "https://www.youtube.com/playlist?list=PLz8YL4HVC87V34Lpnb_pZfAeWD7x621Bd",
  "fast travel": "https://www.youtube.com/watch?v=SrWGCa3ySjs",
  "game masters": "https://www.youtube.com/playlist?list=PLz8YL4HVC87XLYlt1uzi27QHHmayv3oGS",
  "hidden heroes": "https://youtube.com/playlist?list=PLz8YL4HVC87WjPar_Eq90pvlG2DTPhSYX&si=TNH8UfeZz1oqTbzl",
  "make your own victory": "https://youtube.com/playlist?list=PLz8YL4HVC87XcumtO80kwUxENXbyqZef0&si=9TDZsWN0PshWRblS",
  "out of the box": "https://youtube.com/playlist?list=PLz8YL4HVC87WaX9WEEyn66SFc92Z9UdUi&si=JolFPAxGQ4zMdknD",
  "parallel universe": "https://www.youtube.com/playlist?list=PLz8YL4HVC87V6qlkU5tHzXQRSw0vPmTau",
  "passion project": "https://www.youtube.com/playlist?list=PLz8YL4HVC87UBkPm9UtoEkAr8pJPgkXMD",
  "perilous paths": "https://www.youtube.com/playlist?list=PLz8YL4HVC87UHCbLaUJrsFSHHKlQQ6l5o",
  "random number generation": "https://www.youtube.com/playlist?list=PLz8YL4HVC87WvvILEYCszbneK4sp1eU8K",
  "speedruns from the crypt": "https://www.youtube.com/playlist?list=PLz8YL4HVC87X6rZMXsh-EW663t7zTnxNG",
  "the scenic route": "https://www.youtube.com/watch?v=AWPTBpfYD0Q",
  "think fast": "https://www.youtube.com/playlist?list=PLz8YL4HVC87X9I54nPFBYLnJs4nKVs4zI",
  "dnd": "https://awnnetwork.org/"
};

const hostLinks = {
  "satanherself": "https://twitch.tv/SatanIsntHerself",
  "danejerus": "https://twitch.tv/danejerus",
  "mr_shasta": "https://twitch.tv/Mr_Shasta",
  "asuka424": "https://twitch.tv/Asuka424",
  "nickrpgreen": "https://twitch.tv/NickRPGreen",
  "kiara_tv": "https://twitch.tv/Kiara_TV",
  "anarchy": "https://twitch.tv/anarchyasf",
  "quacksilver": "https://twitch.tv/QuacksilverPlays",
  "ateatree": "https://twitch.tv/ateatree",
  "helix": "https://twitch.tv/Helix13_",
  "ambercyprian": "https://twitch.tv/AmberCyprian",
  "queuety": "https://twitch.tv/Queuety",
  "skybilz": "https://twitch.tv/Skybilz",
  "ecdycis": "https://twitch.tv/Ecdycis",
  "ozmourn": "https://twitch.tv/Ozmourn",
  "swooce": "https://twitch.tv/swooce19",
  "jyggy": "https://twitch.tv/jyggy",
  "churchnsarge": "https://twitch.tv/ChurchnSarge",
  "sparkle": "https://twitch.tv/Sparkle"
};

// Load schedule data (fetches once, then uses cache).
async function loadSchedule() {
  if (cachedRows) return cachedRows;
  const res = await fetch(`${DATA_URL}?t=${Date.now()}`);
  cachedRows = await res.json();
  return cachedRows;
}

// -------------------------------------------------------------
// Returns the number of hours ET is behind UTC on a given date.
//   EST (winter): 5
//   EDT (summer): 4
//
// We ask Intl.DateTimeFormat what the timezone abbreviation is
// in New York for a given date. "EST" = 5, "EDT" = 4.
// This is only used for Show Date (midnight ET) conversion.
// -------------------------------------------------------------
function getEasternOffsetHours(dateForContext) {
  const d = dateForContext instanceof Date ? dateForContext : new Date(dateForContext);
  const noon = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate(), 12, 0, 0));
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    timeZoneName: "short"
  }).formatToParts(noon);
  const abbr = parts.find(p => p.type === "timeZoneName")?.value;
  return abbr === "EDT" ? 4 : 5;
}

// -------------------------------------------------------------
// Field parsers
//
// Show Date:  "2026-03-15T04:00:00.000Z" → midnight ET (EDT: UTC-4 → 04:00Z)
//             "2026-03-01T05:00:00.000Z" → midnight ET (EST: UTC-5 → 05:00Z)
//
// Show Start: "1899-12-30T18:00:00.000Z" → time-only serial.
//             Google Sheets ALWAYS encodes these with UTC-5 (EST) baked in,
//             regardless of what date the show falls on.
//             So 18:00Z - 5 = 13:00 ET (1 PM Eastern) always.
//
// Estimate:   "1899-12-30T07:15:00.000Z" → duration serial.
//             Also ALWAYS encoded with UTC-5 (EST) baked in by Sheets.
//             So 07:15Z - 5 = 2h15m always.
//             This is a fixed duration, NOT a clock time — DST never applies.
// -------------------------------------------------------------

/**
 * parseShowDate(raw)
 * Returns a Date representing midnight ET on the show date.
 * The UTC value from Sheets is already the correct moment.
 */
function parseShowDate(raw) {
  if (!raw) return null;
  const d = new Date(raw);
  return isNaN(d) ? null : d;
}

/**
 * parseShowStart(raw)
 * Extracts the ET time-of-day from the Sheets time serial.
 * Sheets always encodes these serials with UTC-5 baked in.
 * Returns { h, m } in Eastern time.
 */
function parseShowStart(raw) {
  if (!raw) return { h: 0, m: 0 };
  const d = new Date(raw);
  if (isNaN(d)) return { h: 0, m: 0 };
  let h = d.getUTCHours() - 5; // always 5 — Sheets serials are always UTC-5 encoded
  const m = d.getUTCMinutes();
  if (h < 0) h += 24;
  return { h, m };
}

/**
 * parseEstimate(raw)
 * Extracts the run duration from the Sheets time serial.
 * Sheets always encodes these serials with UTC-5 baked in.
 * This is a pure duration — DST is irrelevant.
 * Returns { h, m, s } as a duration.
 */
function parseEstimate(raw) {
  if (!raw) return { h: 0, m: 0, s: 0 };
  const d = new Date(raw);
  if (isNaN(d)) return { h: 0, m: 0, s: 0 };
  let h = d.getUTCHours() - 5; // always 5 — Sheets serials are always UTC-5 encoded
  const m = d.getUTCMinutes();
  const s = d.getUTCSeconds();
  if (h < 0) h += 24;
  return { h, m, s };
}

function estimateToMs(raw) {
  const { h, m, s } = parseEstimate(raw);
  return (h * 3600 + m * 60 + s) * 1000;
}

