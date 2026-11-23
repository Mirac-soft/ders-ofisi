// Çalıştır: node tests/gunes.test.mjs
import assert from "node:assert/strict";
import { gunesYuksekligi, isikDurumu, yerelSaat, saatAyarla, KONUM } from "../web/gunes.js";

const yakin = (a, b, d, m) => assert.ok(Math.abs(a - b) <= d, `${m}: ${a.toFixed(2)} ≠ ${b}±${d}`);

yakin(gunesYuksekligi(new Date(Date.UTC(2026, 5, 21, 11, 15))), 71.5, 1.5, "Roma yaz öğlesi");
yakin(gunesYuksekligi(new Date(Date.UTC(2026, 11, 21, 11, 15))), 24.7, 1.5, "Roma kış öğlesi");
assert.ok(gunesYuksekligi(new Date(Date.UTC(2026, 10, 23, 23, 0))) < -30, "Roma kasım gecesi");
// 23 Kasım Roma gün batımı ~16:45 yerel (15:45 UTC): 15:30 UTC ufkun biraz üstünde, 16:30 UTC altında
assert.ok(gunesYuksekligi(new Date(Date.UTC(2026, 10, 23, 15, 30))) > 0, "batımdan önce");
assert.ok(gunesYuksekligi(new Date(Date.UTC(2026, 10, 23, 16, 30))) < 0, "batımdan sonra");

assert.equal(isikDurumu(-20).lambalar, true);
assert.equal(isikDurumu(30).lambalar, false);
assert.equal(isikDurumu(30).pencereIsigi, 0);
assert.equal(isikDurumu(-20).pencereIsigi, 1);
const ara = isikDurumu(0).pencereIsigi;
assert.ok(ara > 0 && ara < 1, "alacakaranlık ara değer");
// Bilgisayar saati Türkiye'de olsa da ofis İtalya saatini kullanır
assert.equal(yerelSaat(new Date(Date.UTC(2026, 10, 23, 16, 30)), "Europe/Rome"), 17.5);
assert.equal(yerelSaat(new Date(Date.UTC(2026, 6, 1, 16, 30)), "Europe/Rome"), 18.5); // yaz saati
const ayarli = saatAyarla(new Date(Date.UTC(2026, 10, 23, 1, 10)), 17, "Europe/Rome");
assert.equal(yerelSaat(ayarli, "Europe/Rome"), 17);
assert.equal(ayarli.getUTCDate(), 23);
assert.equal(KONUM.saatDilimi, "Europe/Rome");
console.log("gunes: tüm testler geçti");
