import { marked } from "./vendor/marked.esm.js";
import { api, dersApi, durum, dersYukle, molaDurumu, uyariGoster } from "./uygulama.js";

const kacis = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

// Claude/PDF kaynaklı Markdown: ham HTML kapalı, görseller yalnızca ders klasöründen, bağlantılar yalnızca http(s)
function mdHtml(md) {
  const temiz = String(md || "")
    .replace(/</g, "&lt;")
    .replace(/\]\((?:\.\.\/)+gorseller\/([^)]+)\)/g, (_, ad) => `](${dersApi(`/dosya/gorseller/${encodeURIComponent(ad)}`)})`);
  const kap = document.createElement("div");
  kap.innerHTML = marked.parse(temiz);
  kap.querySelectorAll("img").forEach((i) => { if (!i.getAttribute("src").startsWith("/api/")) i.remove(); else i.loading = "lazy"; });
  kap.querySelectorAll("a").forEach((a) => {
    if (/^https?:\/\//.test(a.getAttribute("href") || "")) { a.target = "_blank"; a.rel = "noopener"; } else a.replaceWith(a.textContent);
  });
  kap.querySelectorAll("blockquote").forEach((b) => { if (b.textContent.trim().startsWith("⭐")) b.classList.add("onemli"); });
  return kap.innerHTML;
}

const konuSecimi = (ad) => `<fieldset class="konular"><legend>Konular</legend>${durum.bilgi.konular.map((k) =>
  `<label><input type="checkbox" name="${ad}" value="${kacis(k.ad)}"> ${kacis(k.ad)}</label>`).join("") || "<i>Konu listesi boş — Süre analistinden ekle.</i>"}</fieldset>`;
const seciliKonular = (kap, ad) => [...kap.querySelectorAll(`input[name=${ad}]:checked`)].map((i) => i.value);

async function dosyaPaneli(kap, klasor, liste, bos) {
  const b = durum.bilgi;
  const ilerleme = b.pdfler.map((p) => `<div class="ilerleme">${kacis(p.ad)}: ${p.tamam}/${p.toplam ?? "?"} parça okundu</div>`).join("");
  if (!liste.length) { kap.innerHTML = ilerleme + `<p>${bos}</p>`; return; }
  const secili = kap.dataset[klasor] && liste.includes(kap.dataset[klasor]) ? kap.dataset[klasor] : liste[0];
  kap.innerHTML = ilerleme + (liste.length > 1 ? `<select class="pdf-sec">${liste.map((p) => `<option ${p === secili ? "selected" : ""}>${kacis(p)}</option>`).join("")}</select>` : "")
    + `<article class="md">Yükleniyor…</article>`;
  kap.querySelector(".pdf-sec")?.addEventListener("change", (e) => { kap.dataset[klasor] = e.target.value; dosyaPaneli(kap, klasor, liste, bos); });
  const md = await api(dersApi(`/dosya/${klasor}/${encodeURIComponent(secili)}.md`));
  kap.querySelector(".md").innerHTML = mdHtml(md);
}

// --- Sohbet (Sınavcı, Soru-cevap): geçmiş ders başına tarayıcıda tutulur ---
const sohbetAnahtar = (ad) => `sohbet|${durum.ders}|${ad}`;
const sohbetOku = (ad) => JSON.parse(localStorage.getItem(sohbetAnahtar(ad)) || "[]");
const sohbetYaz = (ad, l) => localStorage.setItem(sohbetAnahtar(ad), JSON.stringify(l.slice(-60)));

function sohbetCiz(kap, ad, gonder, bekliyor = false) {
  const l = sohbetOku(ad);
  const akis = kap.querySelector(".akis");
  akis.innerHTML = l.map((m) => `<div class="mesaj ${m.kim}">${m.kim === "ben" ? kacis(m.metin) : mdHtml(m.metin)}</div>`).join("")
    + (bekliyor ? `<div class="mesaj o">…</div>` : "");
  akis.scrollTop = akis.scrollHeight;
  const form = kap.querySelector("form.yaz");
  form.onsubmit = async (e) => {
    e.preventDefault();
    const metin = form.metin.value.trim();
    if (!metin) return;
    form.metin.value = "";
    sohbetYaz(ad, [...sohbetOku(ad), { kim: "ben", metin }]);
    await gonder(metin);
  };
}

async function sohbetGonder(kap, ad, yol, govde) {
  sohbetCiz(kap, ad, () => {}, true);
  try {
    const r = await api(dersApi(yol), govde);
    sohbetYaz(ad, [...sohbetOku(ad), { kim: "o", metin: r.mesaj }]);
    return r;
  } catch (e) {
    sohbetYaz(ad, [...sohbetOku(ad), { kim: "o", metin: `⚠️ ${e.message}` }]);
  }
}

const PANELLER = {
  async ozetci(kap) {
    await dosyaPaneli(kap, "ozet", durum.bilgi.ozetler, "Henüz özet yok. Yukarıdaki <b>📄 PDF bırak</b> alanına dönem notunu bırak; Özetçi parça parça okuyup özetleyecek. ⭐ işaretli satırlar sınav için önemli.");
  },
  async formulcu(kap) {
    await dosyaPaneli(kap, "formuller", durum.bilgi.formuller, "Henüz formül yok. PDF okundukça formüller hocanın notundaki orijinal görüntüsüyle burada görünecek. Görsele tıklayınca sayfanın tamamı açılır.");
  },
  sure(kap) {
    const a = durum.bilgi.analiz;
    const enCok = Math.max(1, ...a.son7.map((g) => g.saat));
    kap.innerHTML = `
      <p class="yorum ${a.yetisir === false ? "kotu" : a.yetisir ? "iyi" : ""}">${kacis(a.yorum)}</p>
      <dl class="ozet-tablo">
        <dt>Sınav</dt><dd>${kacis(a.sinav_tarihi)} (${a.kalan_gun} gün)</dd>
        <dt>Toplam çalışma</dt><dd>${a.toplam_saat.toFixed(1)} saat</dd>
        <dt>Konular</dt><dd>${a.bitti} bitti / ${a.kalan} kaldı</dd>
        <dt>Son 7 gün ort.</dt><dd>${a.gunluk_ort_saat.toFixed(1)} saat/gün</dd>
        ${a.gereken_saat != null ? `<dt>Gereken (tahmini)</dt><dd>~${a.gereken_saat.toFixed(0)} saat</dd><dt>Sınava kadar (bu hızla)</dt><dd>~${a.kapasite_saat.toFixed(0)} saat</dd>` : ""}
      </dl>
      <div class="grafik">${a.son7.map((g) => `<div title="${g.tarih}: ${g.saat.toFixed(1)} saat"><span style="height:${(g.saat / enCok) * 100}%"></span><small>${g.tarih.slice(8)}</small></div>`).join("")}</div>
      <h4>Konular (bitirdiklerini işaretle)</h4>
      <div class="konu-liste">${durum.bilgi.konular.map((k) => `<label><input type="checkbox" data-konu="${kacis(k.ad)}" ${k.bitti ? "checked" : ""}> ${kacis(k.ad)}</label>`).join("") || "<i>Konu yok</i>"}</div>
      <details><summary>Konu listesini düzenle</summary>
        <textarea rows="8" class="konu-duzen">${kacis(durum.bilgi.konular.map((k) => k.ad).join("\n"))}</textarea>
        <button class="konu-kaydet">Kaydet</button></details>`;
    kap.querySelectorAll("[data-konu]").forEach((c) => (c.onchange = async () => {
      await api(dersApi("/konu"), { konu: c.dataset.konu, bitti: c.checked }); dersYukle();
    }));
    kap.querySelector(".konu-kaydet").onclick = async () => {
      await api(dersApi("/konular"), { konular: kap.querySelector(".konu-duzen").value.split("\n") }); dersYukle();
    };
  },
  arastirmaci(kap) {
    const s = durum.bilgi.sorular;
    const grup = (z) => (s?.sorular || []).filter((x) => x.zorluk === z);
    kap.innerHTML = konuSecimi("ara") + `<button class="bul">🌐 Soru bul</button>
      <p class="kucuk">Yerli ve yabancı üniversite sınavlarından arar; bulamazsa kendisi yazar (“asistan yazdı”). Limit harcar.</p>
      ${s ? ["kolay", "orta", "zor"].map((z) => `<h4>${z[0].toUpperCase() + z.slice(1)}</h4><ol>${grup(z).map((q) => `<li>${kacis(q.metin)}
        <div class="kaynak">${q.kaynak ? `<a href="${kacis(q.kaynak)}" target="_blank" rel="noopener">kaynak ↗</a>` : "<span class='etiket'>asistan yazdı</span>"} · ${kacis(q.konu)}</div></li>`).join("")}</ol>`).join("") : "<p>Henüz soru aranmadı.</p>"}`;
    kap.querySelector(".bul").onclick = async () => {
      await api(dersApi("/soru-bul"), { konular: seciliKonular(kap, "ara") });
      uyariGoster("Soru araştırmacısı arıyor… bitince masasında ✅ görünecek.", true);
    };
  },
  not(kap) {
    kap.innerHTML = `<form class="not-form"><textarea name="metin" rows="3" placeholder="Önemli dediğin şeyi yaz…"></textarea><button>📒 Kaydet</button></form>
      <ul class="notlar">${durum.bilgi.notlar.slice().reverse().map((n) => `<li>${kacis(n.replace(/^- /, ""))}</li>`).join("") || "<i>Henüz not yok.</i>"}</ul>`;
    kap.querySelector("form").onsubmit = async (e) => {
      e.preventDefault();
      await api(dersApi("/not"), { metin: e.target.metin.value }); dersYukle();
    };
  },
  sinavci(kap) {
    const sonSinav = durum.bilgi.sinavlar.at(-1);
    kap.innerHTML = `${konuSecimi("sinav")}<button class="basla">🎯 Beni test et</button>
      ${sonSinav ? `<p class="kucuk">Son sınav: ${sonSinav.dogru} doğru, ${sonSinav.yanlis} yanlış. Eksik: ${kacis(sonSinav.eksik_konular.join(", ") || "yok")}</p>` : ""}
      <div class="akis"></div><form class="yaz"><input name="metin" placeholder="Cevabın…" autocomplete="off"><button>Gönder</button></form>`;
    const gonder = async (metin, konular) => {
      const r = await sohbetGonder(kap, "sinavci", "/sinav", konular ? { mesaj: metin, konular } : { mesaj: metin });
      if (r?.bitti) { uyariGoster("Sınav bitti. Eksik konular Tekrar planlayıcıya eklendi.", true); await dersYukle(); }
      else sohbetCiz(kap, "sinavci", gonder);
    };
    sohbetCiz(kap, "sinavci", gonder);
    kap.querySelector(".basla").onclick = () => {
      sohbetYaz("sinavci", []);
      gonder("Başlayalım.", seciliKonular(kap, "sinav"));
    };
  },
  tekrar(kap) {
    const l = durum.bilgi.bugun_tekrar;
    kap.innerHTML = l.length ? `<p>Bugün tekrar etmen gerekenler:</p><ul class="tekrar">${l.map((e) =>
      `<li>${kacis(e.konu)} <small>(${e.tarih})</small> <button data-konu="${kacis(e.konu)}">✔ Yaptım</button></li>`).join("")}</ul>`
      : "<p>Bugün tekrar edilecek konu yok. Sınavcı eksik bulduğu konuları 1, 3 ve 7 gün sonrasına buraya ekler.</p>";
    kap.querySelectorAll("button[data-konu]").forEach((b) => (b.onclick = async () => {
      await api(dersApi("/tekrar"), { konu: b.dataset.konu }); dersYukle();
    }));
  },
  soru_cevap(kap) {
    kap.innerHTML = `<p class="kucuk">Anlamadığın yeri sor; bu dersin notlarına dayanarak açıklar.</p>
      <div class="akis"></div><form class="yaz"><input name="metin" placeholder="Sorunu yaz…" autocomplete="off"><button>Sor</button></form>`;
    const gonder = async (metin) => { await sohbetGonder(kap, "soru_cevap", "/soru", { mesaj: metin }); sohbetCiz(kap, "soru_cevap", gonder); };
    sohbetCiz(kap, "soru_cevap", gonder);
  },
  mola(kap) {
    const m = molaDurumu();
    const kalan = m.molada ? Math.ceil((m.molaBitis - Date.now()) / 60000) : null;
    kap.innerHTML = m.molada ? `<p class="yorum iyi">☕ Moladasın — ${kalan} dk kaldı.</p>`
      : m.acik ? `<p>Sayaç çalışıyor. Her 50 dakikada bir 10 dakika mola hatırlatırım.</p>`
      : `<p>Sayaç durmuş. Yukarıdan ⏱ ▶ ile başlat; 50 dakikada bir mola hatırlatırım.</p>`;
  },
};

export async function panelGoster(id, kap) {
  const anahtar = `${id}|${durum.ders}`;
  if (kap.dataset.panel !== anahtar) { kap.innerHTML = ""; kap.dataset.panel = anahtar; }
  // Sohbet panelleri her durum değişiminde baştan çizilmesin (yazdığın kaybolmasın)
  if ((id === "sinavci" || id === "soru_cevap") && kap.querySelector(".akis")) return;
  try {
    await PANELLER[id](kap);
  } catch (e) {
    kap.innerHTML = `<p class="hata">${kacis(e.message)}</p>`;
  }
}
