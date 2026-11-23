import { ofisKur, ASISTANLAR } from "./ofis.js";
import { panelGoster } from "./panel.js";

const $ = (s) => document.querySelector(s);
const MOLA_CALISMA = 50 * 60, MOLA_SURE = 10 * 60; // saniye
// Sunucudaki iş adı → ofisteki masa
const MASA = { cevirici: "ozetci", ozetci: "ozetci", formulcu: "formulcu", arastirmaci: "arastirmaci", sinavci: "sinavci", soru_cevap: "soru_cevap" };

export const durum = { ders: localStorage.getItem("ders") || null, bilgi: null, olaylar: new Map(), acikPanel: null };

export async function api(yol, govde, secenek = {}) {
  const r = await fetch(yol, govde === undefined ? secenek : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(govde), ...secenek,
  });
  const tur = r.headers.get("Content-Type") || "";
  const veri = tur.includes("json") ? await r.json() : await r.text();
  if (!r.ok) {
    const e = new Error(r.status === 429 ? "Claude kullanım limiti doldu. Limit açılınca tekrar dene." : (veri.hata || r.statusText));
    e.kod = r.status;
    throw e;
  }
  return veri;
}
export const dersApi = (ek = "") => `/api/ders/${encodeURIComponent(durum.ders)}${ek}`;

const ofis = ofisKur($("#sahne"), (id) => panelAc(id));

function panelAc(id) {
  const a = ASISTANLAR.find((x) => x.id === id);
  durum.acikPanel = id;
  $("#panel-baslik").textContent = `${a.emoji} ${a.ad}`;
  $("#panel").hidden = false;
  if (!durum.ders) {
    $("#panel-icerik").innerHTML = "<p>Önce yukarıdan bir ders seç ya da <b>＋ Ders</b> ile yeni ders oluştur.</p>";
    return;
  }
  panelGoster(id, $("#panel-icerik"));
}
export function paneliYenile() {
  if (durum.acikPanel && !$("#panel").hidden && durum.ders) panelGoster(durum.acikPanel, $("#panel-icerik"));
}
$("#kapat").onclick = () => { $("#panel").hidden = true; durum.acikPanel = null; };

// --- Masa durumları: aktif ders önce, başka dersin süren işi etiketle ---
function masalariCiz() {
  const masa = {};
  for (const o of durum.olaylar.values()) {
    const id = MASA[o.asistan];
    const aktif = o.ders === durum.ders;
    if (!id || (!aktif && o.durum !== "calisiyor")) continue; // başka dersin yalnızca süren işi görünür
    const puan = (aktif ? 2 : 0) + (o.durum === "calisiyor" ? 1 : 0);
    if (!masa[id] || puan > masa[id].puan) masa[id] = { durum: o.durum, ders: aktif ? null : o.ders, puan };
  }
  if (durum.bilgi?.bugun_tekrar?.length) masa.tekrar = { durum: "hatirlat", ders: null };
  if (molada) masa.mola = { durum: "mola", ders: null };
  for (const a of ASISTANLAR) {
    if (a.id === "sure" || a.id === "not") continue;
    const m = masa[a.id];
    ofis.durumAyarla(a.id, m?.durum || "bosta", m?.ders || null);
  }
  // Limit/hata ya da yeniden başlatma sonrası yarım kalan PDF varsa devam edilebilir
  const yarim = durum.bilgi?.pdfler?.some((p) => p.toplam == null || p.tamam < p.toplam);
  const takildi = [...durum.olaylar.values()].some((o) => o.ders === durum.ders && (o.durum === "bekliyor" || o.durum === "hata"));
  const suruyor = [...durum.olaylar.values()].some((o) => o.ders === durum.ders && o.asistan === "cevirici" && o.durum === "calisiyor");
  $("#devam").hidden = !(takildi || (yarim && !suruyor));
  // İlerleme: hangi PDF kaç parça okundu, tahmini kalan süre, kaç asistan çalışıyor
  const parcalar = (durum.bilgi?.pdfler || []).filter((p) => p.toplam == null || p.tamam < p.toplam).map((p) => {
    const kalan = p.parca_sn && p.toplam ? Math.ceil(((p.toplam - p.tamam) * p.parca_sn) / 60) : null;
    return `📖 ${p.ad}: ${p.tamam}/${p.toplam ?? "?"} parça${suruyor ? (kalan ? ` · ~${kalan} dk kaldı` : " · ilk parça okunuyor…") : " · durdu"}`;
  });
  const calisan = [...durum.olaylar.values()].filter((o) => o.durum === "calisiyor").length;
  if (calisan) parcalar.push(`⚙️ ${calisan} asistan çalışıyor`);
  $("#ilerleme").textContent = parcalar.join("  ·  ");
  $("#ilerleme").hidden = !parcalar.length;
}

function olaylariDinle() {
  const k = new EventSource("/api/olaylar");
  k.onmessage = (e) => {
    const o = JSON.parse(e.data);
    durum.olaylar.set(`${o.ders}|${o.asistan}`, o);
    masalariCiz();
    if (o.ders === durum.ders && o.durum !== "calisiyor") dersYukle(); // yeni çıktı gelmiş olabilir
  };
}

// --- Dersler ---
async function dersleriYukle() {
  const { dersler, uyari } = await api("/api/dersler");
  const sec = $("#ders-sec");
  sec.innerHTML = dersler.length ? "" : "<option value=''>— ders yok —</option>";
  for (const d of dersler) sec.add(new Option(d, d));
  if (!dersler.includes(durum.ders)) durum.ders = dersler[0] || null;
  sec.value = durum.ders || "";
  uyariGoster(uyari);
  await dersYukle();
}

export async function dersYukle() {
  if (!durum.ders) { durum.bilgi = null; sayaciGuncelle(); masalariCiz(); return; }
  try {
    durum.bilgi = await api(dersApi());
  } catch (e) { uyariGoster(e.message); return; }
  sayaciGuncelle();
  masalariCiz();
  paneliYenile();
}

$("#ders-sec").onchange = async (e) => {
  const calisiyordu = sayacAcik();
  durum.ders = e.target.value;
  localStorage.setItem("ders", durum.ders);
  if (calisiyordu) await api(dersApi("/sure"), { olay: "basla" }); // süre yeni derse geçer
  await dersYukle();
};

$("#ders-ekle").onclick = () => { $("#ders-hata").textContent = ""; $("#ders-formu").showModal(); };
$("#ders-kaydet").onclick = async (e) => {
  e.preventDefault();
  const f = new FormData($("#ders-form"));
  try {
    await api("/api/dersler", { ad: f.get("ad").trim(), sinav_tarihi: f.get("sinav_tarihi"),
      konular: f.get("konular").split("\n").map((s) => s.trim()).filter(Boolean) });
  } catch (err) { $("#ders-hata").textContent = err.message; return; }
  durum.ders = f.get("ad").trim();
  localStorage.setItem("ders", durum.ders);
  $("#ders-form").reset();
  $("#ders-formu").close();
  await dersleriYukle();
};

// --- PDF ---
async function pdfYukle(dosya) {
  if (!durum.ders) return uyariGoster("Önce bir ders oluştur.");
  if (!/\.pdf$/i.test(dosya.name)) return uyariGoster("Sadece PDF yükleyebilirsin.");
  $("#pdf-alan").firstChild.textContent = "⏳ Yükleniyor… ";
  try {
    await api(dersApi("/pdf"), undefined, { method: "POST", body: dosya, headers: { "X-Dosya-Adi": encodeURIComponent(dosya.name) } });
    uyariGoster(`“${dosya.name}” yüklendi. Özetçi okumaya başladı; parça parça sonuçlar gelecek.`, true);
  } catch (e) { uyariGoster(e.kod === 409 ? "Bu adla bir PDF zaten yüklü (dönem notu bir kez okunur)." : e.message); }
  $("#pdf-alan").firstChild.textContent = "📄 PDF bırak ";
  dersYukle();
}
$("#pdf-dosya").onchange = (e) => e.target.files[0] && pdfYukle(e.target.files[0]);
addEventListener("dragover", (e) => { e.preventDefault(); document.body.classList.add("surukle"); });
addEventListener("dragleave", (e) => { if (!e.relatedTarget) document.body.classList.remove("surukle"); });
addEventListener("drop", (e) => {
  e.preventDefault();
  document.body.classList.remove("surukle");
  const f = e.dataTransfer.files[0];
  if (f) pdfYukle(f);
});

$("#devam").onclick = async () => {
  $("#devam").hidden = true;
  try { await api(dersApi("/devam"), {}); uyariGoster("Kalan işlere devam ediliyor.", true); } catch (e) { uyariGoster(e.message); }
};

// --- Uyarı çubuğu ---
let uyariZaman;
export function uyariGoster(mesaj, bilgi = false) {
  const u = $("#uyari");
  u.hidden = !mesaj;
  u.textContent = mesaj || "";
  u.className = bilgi ? "bilgi" : "";
  clearTimeout(uyariZaman);
  if (mesaj && bilgi) uyariZaman = setTimeout(() => (u.hidden = true), 6000);
}
$("#uyari").onclick = () => ($("#uyari").hidden = true);

// --- Sayaç ve mola ---
let molada = false, molaBitis = 0, sonMola = null;
const acikOturum = () => durum.bilgi?.oturumlar?.find((o) => o.bitis === null);
const sayacAcik = () => Boolean(acikOturum());
function sayaciGuncelle() {
  const o = acikOturum();
  $("#sayac-dugme").textContent = o ? "⏸" : "▶";
  $("#sayac-dugme").setAttribute("aria-label", o ? "Duraklat" : "Başlat");
  const sn = o ? Math.max(0, (Date.now() - new Date(o.basla).getTime()) / 1000) : 0;
  const s = Math.floor(sn);
  $("#sayac-sure").textContent = [s / 3600, (s % 3600) / 60, s % 60].map((x) => String(Math.floor(x)).padStart(2, "0")).join(":");
  // Mola: her 50 dk kesintisiz çalışmada 10 dk
  const dongu = `${o?.basla}|${Math.floor(s / (MOLA_CALISMA + MOLA_SURE))}`;
  if (o && !molada && s % (MOLA_CALISMA + MOLA_SURE) >= MOLA_CALISMA && sonMola !== dongu) {
    molada = true;
    sonMola = dongu;
    molaBitis = Date.now() + MOLA_SURE * 1000;
    uyariGoster("☕ 50 dakika oldu — 10 dakika mola!", true);
    if (Notification?.permission === "granted") new Notification("Ders Ofisi", { body: "50 dakika oldu — 10 dakika mola!" });
    masalariCiz();
  }
  if (molada && (Date.now() > molaBitis || !o)) { molada = false; masalariCiz(); }
}
export const molaDurumu = () => ({ molada, molaBitis, acik: sayacAcik(), basla: acikOturum()?.basla });
setInterval(sayaciGuncelle, 1000);

$("#sayac-dugme").onclick = async () => {
  if (!durum.ders) return uyariGoster("Önce bir ders seç.");
  if (Notification?.permission === "default") Notification.requestPermission();
  await api(dersApi("/sure"), { olay: sayacAcik() ? "dur" : "basla" });
  await dersYukle();
};
// Pencere kapanırsa süre açık kalmasın
addEventListener("pagehide", () => {
  if (sayacAcik()) fetch(dersApi("/sure"), { method: "POST", keepalive: true, headers: { "Content-Type": "application/json" }, body: JSON.stringify({ olay: "dur" }) });
});
// Nabız: sayfa açıkken sunucu oturumu canlı bilir; bilgisayar uyur/çökerse süre son nabızda kesilir
setInterval(() => { if (sayacAcik()) api(dersApi("/sure"), { olay: "nabiz" }).catch(() => {}); }, 60_000);

// --- Görsele tıkla → hocanın notunda tam sayfa ---
document.addEventListener("click", (e) => {
  const img = e.target.closest("#panel-icerik img");
  if (img) {
    const m = decodeURIComponent(img.src).match(/gorseller\/(.+)-s(\d+)-\d+\.png$/);
    $("#buyut img").src = m ? dersApi(`/sayfa/${encodeURIComponent(m[1])}/${m[2]}`) : img.src;
    $("#buyut").hidden = false;
  } else if (e.target.closest("#buyut")) $("#buyut").hidden = true;
});

if (new URLSearchParams(location.search).has("demo")) {
  const durumlar = ["calisiyor", "bitti", "bekliyor", "hata", "bosta"];
  let i = 0;
  setInterval(() => {
    const a = ASISTANLAR[i % ASISTANLAR.length];
    ofis.durumAyarla(a.id, durumlar[Math.floor(i / ASISTANLAR.length) % durumlar.length], i % 4 === 0 ? "Math 1" : null);
    i++;
  }, 900);
} else {
  olaylariDinle();
  dersleriYukle().then(() => { const p = new URLSearchParams(location.search).get("panel"); if (p) panelAc(p); });
}
