// Kullanıcının bulunduğu yer. Bilgisayar saati Türkiye'ye ayarlı olsa da ofis buna göre aydınlanır.
// Başka bir yere taşınınca yalnızca burayı değiştir.
export const KONUM = { saatDilimi: "Europe/Rome", enlem: 41.9, boylam: 12.5 };
const R = Math.PI / 180;

// Verilen anın o saat dilimindeki saati (ör. 17.5 = 17:30)
export function yerelSaat(tarih, saatDilimi = KONUM.saatDilimi) {
  const p = Object.fromEntries(new Intl.DateTimeFormat("en-GB", {
    timeZone: saatDilimi, hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(tarih).map((x) => [x.type, x.value]));
  return +p.hour + +p.minute / 60;
}

// Aynı günde, o saat dilimine göre saati `saat` olan an (önizleme için ?saat=)
export function saatAyarla(tarih, saat, saatDilimi = KONUM.saatDilimi) {
  return new Date(tarih.getTime() + (saat - yerelSaat(tarih, saatDilimi)) * 3600e3);
}

export function gunesYuksekligi(tarih, enlem = KONUM.enlem, boylam = KONUM.boylam) {
  const yilBasi = Date.UTC(tarih.getUTCFullYear(), 0, 1);
  const gun = (tarih.getTime() - yilBasi) / 864e5; // yılın günü (kesirli)
  const sapma = -23.44 * Math.cos(2 * Math.PI * (gun + 10) / 365);
  const utcSaat = tarih.getUTCHours() + tarih.getUTCMinutes() / 60;
  const saatAcisi = (utcSaat + boylam / 15 - 12) * 15;
  const s = Math.sin(enlem * R) * Math.sin(sapma * R) +
            Math.cos(enlem * R) * Math.cos(sapma * R) * Math.cos(saatAcisi * R);
  return Math.asin(s) / R;
}

const karistir = (a, b, t) => a + (b - a) * t;
const renkKaristir = (a, b, t) => {
  const c = (h, k) => (h >> k) & 255;
  return [16, 8, 0].reduce((s, k) => s | (Math.round(karistir(c(a, k), c(b, k), t)) << k), 0);
};

// > 6° gündüz, -6°..6° alacakaranlık, < -6° gece
export function isikDurumu(yukseklik) {
  const gece = { gok: 0x0a1030, gunes: 0.0, ortam: 0.25 };
  const alaca = { gok: 0xf08a4b, gunes: 0.6, ortam: 0.45 };
  const gunduz = { gok: 0x87c4ff, gunes: 1.6, ortam: 0.7 };
  let a, b, t;
  if (yukseklik <= -6) { a = b = gece; t = 0; }
  else if (yukseklik < 0) { a = gece; b = alaca; t = (yukseklik + 6) / 6; }
  else if (yukseklik < 6) { a = alaca; b = gunduz; t = yukseklik / 6; }
  else { a = b = gunduz; t = 0; }
  const pencereIsigi = yukseklik >= 6 ? 0 : yukseklik <= -6 ? 1 : (6 - yukseklik) / 12;
  return {
    gokRengi: renkKaristir(a.gok, b.gok, t),
    gunesYogunluk: karistir(a.gunes, b.gunes, t),
    ortamYogunluk: karistir(a.ortam, b.ortam, t),
    pencereIsigi,
    lambalar: yukseklik < 3,
  };
}
