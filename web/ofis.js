// 3D NYC ofisi. Ölçüler metre: ofis ~150 m yükseklikte bir katta, kamera odanın içinde.
import * as THREE from "three";
import { OrbitControls } from "three/addons/OrbitControls.js";
import { RoomEnvironment } from "three/addons/RoomEnvironment.js";
import { gunesYuksekligi, isikDurumu, yerelSaat, saatAyarla, KONUM } from "./gunes.js";

export const ASISTANLAR = [
  { id: "ozetci", ad: "Özetçi", emoji: "📝", renk: 0xc8553d, gorev: "PDF'i özetler, önemli noktaları işaretler." },
  { id: "formulcu", ad: "Formülcü", emoji: "∑", renk: 0x2a9d8f, gorev: "Formülleri orijinal görüntüsüyle çıkarır, nerede kullanılacağını açıklar." },
  { id: "sure", ad: "Süre analisti", emoji: "📊", renk: 0xd4a017, gorev: "Çalışma süreni tutar, sınava yetişip yetişmediğini gösterir." },
  { id: "arastirmaci", ad: "Soru araştırmacısı", emoji: "🌐", renk: 0x3d6b8c, gorev: "Üniversite sınavlarından soru arar, bulamazsa yazar." },
  { id: "not", ad: "Not tutucu", emoji: "📒", renk: 0x6b8f5e, gorev: "Önemli dediğin notları ders klasörüne kaydeder." },
  { id: "sinavci", ad: "Sınavcı", emoji: "🎯", renk: 0x9e2a2b, gorev: "Kolay-orta-zor sorularla seni test eder, eksiklerini söyler." },
  { id: "tekrar", ad: "Tekrar planlayıcı", emoji: "🔁", renk: 0x6a4c93, gorev: "Eksik konuları 1, 3 ve 7 gün sonra hatırlatır." },
  { id: "soru_cevap", ad: "Soru-cevap hocası", emoji: "💬", renk: 0x1d7874, gorev: "Anlamadığın yeri ders notlarına dayanarak açıklar." },
  { id: "mola", ad: "Mola", emoji: "☕", renk: 0x8d6e63, gorev: "50 dakikada bir 10 dakika mola hatırlatır." },
];
const TEN = [0xf1c27d, 0xe0ac69, 0xc68642, 0x8d5524, 0xffdbac, 0xd1a17a, 0xa5714e, 0xeac086, 0xb98865];
const SAC = [0x2b1d14, 0x3b2a20, 0x0f0f0f, 0x6b4423, 0x1a1a1a, 0x8a5a2b, 0x2b1d14, 0x4a3426, 0x111111];
const DURUM_SIMGE = { calisiyor: "…", bitti: "✅", bekliyor: "💤", hata: "⚠️" };

const ODA = { x: 10, z: 7, h: 3 }; // yarım genişlik, yarım derinlik, tavan
const KAT = 150; // ofisin bulunduğu yükseklik

function rastgele(tohum) {
  return () => ((tohum = (tohum * 1664525 + 1013904223) >>> 0) / 4294967296);
}

function tuvalDoku(boyut, ciz, tekrar = [1, 1]) {
  const c = document.createElement("canvas");
  c.width = c.height = boyut;
  ciz(c.getContext("2d"), boyut);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(...tekrar);
  t.anisotropy = 4;
  return t;
}

function parkeDokusu() {
  const r = rastgele(7);
  return tuvalDoku(512, (g, n) => {
    const satir = n / 8;
    for (let y = 0; y < 8; y++) {
      let x = -r() * 200;
      while (x < n) {
        const w = 160 + r() * 120;
        const ton = 120 + r() * 40;
        g.fillStyle = `rgb(${ton + 40},${ton + 10},${ton - 30})`;
        g.fillRect(x, y * satir, w, satir);
        for (let i = 0; i < 6; i++) { // damar çizgileri
          g.strokeStyle = `rgba(60,35,15,${0.05 + r() * 0.08})`;
          g.beginPath(); const yy = y * satir + r() * satir;
          g.moveTo(x, yy); g.lineTo(x + w, yy + (r() - 0.5) * 6); g.stroke();
        }
        g.fillStyle = "rgba(40,25,10,.55)";
        g.fillRect(x, y * satir, 2, satir);
        x += w;
      }
      g.fillStyle = "rgba(40,25,10,.5)";
      g.fillRect(0, y * satir, n, 2);
    }
  }, [ODA.x / 2, ODA.z / 2]);
}

function haliDokusu() {
  const r = rastgele(11);
  return tuvalDoku(256, (g, n) => {
    g.fillStyle = "#4a5361"; g.fillRect(0, 0, n, n);
    for (let i = 0; i < 9000; i++) {
      const v = 60 + r() * 50;
      g.fillStyle = `rgba(${v},${v + 8},${v + 20},.35)`;
      g.fillRect(r() * n, r() * n, 1.5, 1.5);
    }
  }, [6, 4]);
}

function yaziDokusu(satirlar, genislik = 512, yukseklik = 128) {
  const c = document.createElement("canvas");
  c.width = genislik; c.height = yukseklik;
  const g = c.getContext("2d");
  g.textAlign = "center"; g.textBaseline = "middle";
  satirlar.forEach(([metin, boyut, renk, y, zemin]) => {
    g.font = `600 ${boyut}px system-ui, "Segoe UI Emoji", sans-serif`;
    if (zemin) {
      const w = g.measureText(metin).width + 36, h = boyut * 1.35;
      g.fillStyle = zemin;
      g.beginPath(); g.roundRect(genislik / 2 - w / 2, y - h / 2, w, h, h / 2); g.fill();
    } else { g.lineWidth = 8; g.strokeStyle = "rgba(0,0,0,.55)"; g.strokeText(metin, genislik / 2, y); }
    g.fillStyle = renk; g.fillText(metin, genislik / 2, y);
  });
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

const std = (renk, puruz = 0.7, metal = 0) => new THREE.MeshStandardMaterial({ color: renk, roughness: puruz, metalness: metal });

function kutu(w, h, d, mat, x, y, z, golge = true) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  m.position.set(x, y, z);
  m.castShadow = golge; m.receiveShadow = true;
  return m;
}

function silueKur(sahne) {
  const r = rastgele(42);
  const binalar = [];
  for (let i = 0; i < 260; i++) {
    const uzak = 160 + Math.pow(r(), 0.7) * 650;
    const x = (r() - 0.5) * (120 + uzak * 2.4);
    const merkez = Math.abs(x) < uzak * 0.5 ? 1.25 : 1;
    const h = (70 + Math.pow(r(), 1.6) * 190) * merkez; // çoğu ofis hizasında, birkaçı çok yüksek
    binalar.push({ x, z: -uzak, w: 18 + r() * 26, d: 18 + r() * 26, h, ton: r() });
  }
  binalar.push({ x: 60, z: -480, w: 34, d: 34, h: 420, ton: 0.5 }); // ufukta yüksek kule
  const tonlar = [0x8f96a3, 0x9c8f80, 0x6f7783, 0xb0a99f, 0x5f6670];
  const binaMat = std(0xffffff, 0.85, 0.1);
  const binaMesh = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), binaMat, binalar.length);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), renk = new THREE.Color();
  binalar.forEach((b, i) => {
    m.compose(new THREE.Vector3(b.x, -KAT + b.h / 2, b.z), q, new THREE.Vector3(b.w, b.h, b.d));
    binaMesh.setMatrixAt(i, m);
    binaMesh.setColorAt(i, renk.set(tonlar[Math.floor(b.ton * tonlar.length)]));
  });
  sahne.add(binaMesh);
  const anten = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 1.5, 60, 8), std(0x777777, 0.5, 0.6));
  anten.position.set(60, -KAT + 420 + 30, -480);
  sahne.add(anten);

  // Sokak zemini (sis içinde kaybolur)
  const zemin = new THREE.Mesh(new THREE.PlaneGeometry(4000, 4000), std(0x2a2d33, 1));
  zemin.rotation.x = -Math.PI / 2; zemin.position.y = -KAT;
  sahne.add(zemin);

  // Pencereler: binaların ofise bakan yüzlerinde, 4 m kat yüksekliği
  const yerler = [];
  binalar.forEach((b) => {
    const sutun = Math.max(2, Math.floor(b.w / 4));
    const ust = -KAT + b.h;
    for (let y = Math.max(-KAT + 6, ust - 220); y < ust - 3; y += 4)
      for (let s = 0; s < sutun; s++) yerler.push([b.x - b.w / 2 + (s + 0.5) * (b.w / sutun), y, b.z + b.d / 2 + 0.05, r()]);
  });
  const pencereMat = new THREE.MeshBasicMaterial({ color: 0xffd27a, fog: true });
  const pencere = new THREE.InstancedMesh(new THREE.PlaneGeometry(2.6, 2.4), pencereMat, yerler.length);
  yerler.forEach(([x, y, z, sans], i) => {
    m.makeTranslation(x, y, z);
    pencere.setMatrixAt(i, m);
    pencere.setColorAt(i, renk.setScalar(sans < 0.5 ? 1 : 0.1));
  });
  sahne.add(pencere);
  // Kule tepesinde kırmızı uyarı ışığı (gece görünür)
  const uyari = new THREE.Mesh(new THREE.SphereGeometry(1.6, 8, 6), new THREE.MeshBasicMaterial({ color: 0xff2a2a }));
  uyari.position.set(60, -KAT + 420 + 61, -480);
  sahne.add(uyari);
  return { pencereMat, uyari, binaMat };
}

function odaKur(sahne) {
  const { x: X, z: Z, h: H } = ODA;
  const zemin = new THREE.Mesh(new THREE.PlaneGeometry(X * 2, Z * 2),
    new THREE.MeshStandardMaterial({ map: parkeDokusu(), roughness: 0.55 }));
  zemin.rotation.x = -Math.PI / 2; zemin.receiveShadow = true;
  sahne.add(zemin);
  const hali = new THREE.Mesh(new THREE.PlaneGeometry(16, 9.5), new THREE.MeshStandardMaterial({ map: haliDokusu(), roughness: 1 }));
  hali.rotation.x = -Math.PI / 2; hali.position.set(0, 0.005, -1.3); hali.receiveShadow = true;
  sahne.add(hali);

  const duvar = std(0xe8e4dc, 0.9);
  sahne.add(kutu(0.2, H, Z * 2, duvar, -X - 0.1, H / 2, 0, false));
  sahne.add(kutu(0.2, H, Z * 2, duvar, X + 0.1, H / 2, 0, false));
  sahne.add(kutu(X * 2, H, 0.2, duvar, 0, H / 2, Z + 0.1, false));
  const supurgelik = std(0x3a3a3a, 0.6);
  for (const sx of [-1, 1]) sahne.add(kutu(0.03, 0.1, Z * 2, supurgelik, sx * (X - 0.015), 0.05, 0, false));
  sahne.add(kutu(X * 2, 0.1, 0.03, supurgelik, 0, 0.05, Z - 0.015, false));

  // Tavan ve aydınlatma panelleri
  const tavan = new THREE.Mesh(new THREE.PlaneGeometry(X * 2, Z * 2), std(0xf2f2ef, 0.95));
  tavan.rotation.x = Math.PI / 2; tavan.position.y = H;
  sahne.add(tavan);
  const panelMat = new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: 0xfff4e0, emissiveIntensity: 1.2 });
  for (let px = -7.5; px <= 7.5; px += 3.75)
    for (let pz = -5; pz <= 5; pz += 2.5) {
      const p = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 0.6), panelMat);
      p.rotation.x = Math.PI / 2; p.position.set(px, H - 0.01, pz);
      sahne.add(p);
    }

  // Cam cephe: tavandan tabana cam, dikmeler, alt ve üst kirişler
  const cam = new THREE.Mesh(new THREE.PlaneGeometry(X * 2, H),
    new THREE.MeshPhysicalMaterial({ color: 0xcfe3f0, transparent: true, opacity: 0.12, roughness: 0.05, depthWrite: false }));
  cam.position.set(0, H / 2, -Z);
  sahne.add(cam);
  const dogrma = std(0x2b2f36, 0.4, 0.6);
  for (let x = -X; x <= X + 0.01; x += 2.5) sahne.add(kutu(0.08, H, 0.15, dogrma, x, H / 2, -Z));
  sahne.add(kutu(X * 2, 0.12, 0.3, dogrma, 0, 0.06, -Z));
  sahne.add(kutu(X * 2, 0.25, 0.3, dogrma, 0, H - 0.125, -Z));
  // Kolonlar
  const kolon = std(0xdedad2, 0.85);
  for (const x of [-X + 0.3, -3.3, 3.3, X - 0.3]) sahne.add(kutu(0.6, H, 0.6, kolon, x, H / 2, -Z + 0.35));

  // Sol duvarda beyaz tahta, sağ duvarda kitaplık
  sahne.add(kutu(0.06, 1.2, 2.5, std(0x9aa0a6, 0.4, 0.7), -X + 0.02, 1.55, 1.5, false));
  sahne.add(kutu(0.04, 1.1, 2.4, std(0xfafafa, 0.25), -X + 0.05, 1.55, 1.5, false));
  const raf = std(0x5b4636, 0.7);
  const rk = rastgele(3);
  for (let i = 0; i < 4; i++) {
    sahne.add(kutu(0.35, 0.03, 1.8, raf, X - 0.2, 0.4 + i * 0.45, 1.6));
    for (let k = 0; k < 14; k++) {
      const hgt = 0.25 + rk() * 0.12;
      sahne.add(kutu(0.25, hgt, 0.05 + rk() * 0.04, std(new THREE.Color().setHSL(rk(), 0.4, 0.35), 0.8),
        X - 0.22, 0.415 + i * 0.45 + hgt / 2, 0.8 + k * 0.115));
    }
  }
  sahne.add(kutu(0.35, 1.9, 0.03, raf, X - 0.2, 0.95, 0.7), kutu(0.35, 1.9, 0.03, raf, X - 0.2, 0.95, 2.5));

  // Saksı bitkileri
  const yaprakMat = std(0x3f6e3a, 0.8);
  for (const [x, z] of [[-X + 0.7, -Z + 0.9], [X - 0.7, -Z + 0.9], [-X + 0.6, Z - 0.8]]) {
    sahne.add(kutu(0.5, 0.55, 0.5, std(0x2e2e2e, 0.5), x, 0.275, z));
    const rr = rastgele(Math.round(x * 100 + z));
    for (let i = 0; i < 9; i++) {
      const y = new THREE.Mesh(new THREE.IcosahedronGeometry(0.28 + rr() * 0.15, 1), yaprakMat);
      y.position.set(x + (rr() - 0.5) * 0.5, 0.8 + rr() * 0.9, z + (rr() - 0.5) * 0.5);
      y.castShadow = true;
      sahne.add(y);
    }
  }
}

function koltuk(mat, metal) {
  const g = new THREE.Group();
  g.add(kutu(0.5, 0.08, 0.48, mat, 0, 0.48, 0));
  g.add(kutu(0.46, 0.55, 0.07, mat, 0, 0.82, 0.24));
  const direk = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.38), metal);
  direk.position.y = 0.26; g.add(direk);
  for (let i = 0; i < 5; i++) {
    const a = (i / 5) * Math.PI * 2;
    const bacak = kutu(0.04, 0.03, 0.3, metal, Math.sin(a) * 0.14, 0.07, Math.cos(a) * 0.14);
    bacak.rotation.y = a; g.add(bacak);
    const tek = new THREE.Mesh(new THREE.SphereGeometry(0.03, 8, 6), metal);
    tek.position.set(Math.sin(a) * 0.28, 0.03, Math.cos(a) * 0.28); g.add(tek);
  }
  return g;
}

function karakter(a, i) {
  const g = new THREE.Group();
  const kiyafet = std(a.renk, 0.85);
  const ten = std(TEN[i], 0.6);
  const pantolon = std(0x2f3440, 0.9);
  const govde = new THREE.Mesh(new THREE.CapsuleGeometry(0.17, 0.32, 6, 14), kiyafet);
  govde.scale.set(1.15, 1, 0.75); govde.position.set(0, 0.88, 0.02); govde.rotation.x = -0.12;
  const boyun = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.06, 0.08), ten);
  boyun.position.set(0, 1.14, -0.01);
  const kafa = new THREE.Mesh(new THREE.SphereGeometry(0.11, 20, 16), ten);
  kafa.scale.set(1, 1.15, 1.05); kafa.position.set(0, 1.27, -0.03);
  const sac = new THREE.Mesh(new THREE.SphereGeometry(0.118, 20, 12, 0, Math.PI * 2, 0, Math.PI * 0.55), std(SAC[i], 0.9));
  sac.scale.set(1, 1.15, 1.08); sac.position.set(0, 1.285, -0.02); sac.rotation.x = 0.35;
  g.add(govde, boyun, kafa, sac);
  for (const s of [-1, 1]) {
    const ust = new THREE.Mesh(new THREE.CapsuleGeometry(0.05, 0.22, 4, 8), kiyafet);
    ust.position.set(s * 0.22, 0.9, -0.08); ust.rotation.x = 0.6;
    const alt = new THREE.Mesh(new THREE.CapsuleGeometry(0.045, 0.24, 4, 8), kiyafet);
    alt.position.set(s * 0.17, 0.79, -0.3); alt.rotation.set(Math.PI / 2, 0, -s * 0.2);
    const el = new THREE.Mesh(new THREE.SphereGeometry(0.045, 10, 8), ten);
    el.position.set(s * 0.13, 0.79, -0.45);
    const uyluk = new THREE.Mesh(new THREE.CapsuleGeometry(0.075, 0.3, 4, 8), pantolon);
    uyluk.position.set(s * 0.1, 0.56, -0.15); uyluk.rotation.x = Math.PI / 2;
    const baldir = new THREE.Mesh(new THREE.CapsuleGeometry(0.06, 0.35, 4, 8), pantolon);
    baldir.position.set(s * 0.1, 0.3, -0.33);
    const ayakkabi = kutu(0.09, 0.07, 0.22, std(0x1b1b1b, 0.5), s * 0.1, 0.035, -0.38);
    g.add(ust, alt, el, uyluk, baldir, ayakkabi);
  }
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  return g;
}

function masaKur(a, i, x, z) {
  const grup = new THREE.Group();
  grup.position.set(x, 0, z);
  const tabla = std(0xd9c3a0, 0.45);
  const metal = std(0x3a3d42, 0.35, 0.8);
  const siyah = std(0x151515, 0.4, 0.2);
  grup.add(kutu(1.6, 0.03, 0.8, tabla, 0, 0.74, 0));
  for (const sx of [-0.75, 0.75]) {
    grup.add(kutu(0.05, 0.72, 0.05, metal, sx, 0.36, -0.33), kutu(0.05, 0.72, 0.05, metal, sx, 0.36, 0.33));
    grup.add(kutu(0.05, 0.04, 0.7, metal, sx, 0.02, 0));
  }
  grup.add(kutu(1.45, 0.35, 0.02, metal, 0, 0.52, -0.37)); // ön panel
  // Monitör
  grup.add(kutu(0.62, 0.37, 0.025, siyah, 0, 1.06, -0.25));
  const ekranMat = new THREE.MeshStandardMaterial({ color: 0x000000, emissive: 0x1c2a3a, emissiveIntensity: 1, roughness: 0.2 });
  const ekran = new THREE.Mesh(new THREE.PlaneGeometry(0.58, 0.33), ekranMat);
  ekran.position.set(0, 1.06, -0.236);
  grup.add(ekran, kutu(0.04, 0.2, 0.04, siyah, 0, 0.85, -0.28), kutu(0.2, 0.015, 0.15, siyah, 0, 0.76, -0.28));
  // Klavye, fare, kupa, defter
  grup.add(kutu(0.42, 0.02, 0.14, std(0x2a2a2a, 0.6), 0, 0.765, 0.02));
  grup.add(kutu(0.06, 0.02, 0.1, std(0x2a2a2a, 0.5), 0.32, 0.765, 0.04));
  const kupa = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.035, 0.1, 14), std(new THREE.Color().setHSL(i / 9, 0.5, 0.6), 0.4));
  kupa.position.set(-0.55, 0.805, -0.1); kupa.castShadow = true;
  grup.add(kupa, kutu(0.21, 0.015, 0.29, std(0xf5f0e6, 0.9), -0.45, 0.763, 0.12));
  // Koltuk ve karakter (ekrana, yani cama dönük)
  const k = koltuk(std(0x1f2226, 0.9), metal);
  k.position.set(0, 0, 0.62);
  grup.add(k);
  const kisi = karakter(a, i);
  kisi.position.set(0, 0, 0.72);
  grup.add(kisi);

  const etiket = new THREE.Sprite(new THREE.SpriteMaterial({ map: yaziDokusu([[`${a.emoji} ${a.ad}`, 40, "#fff", 64, "rgba(20,24,32,.72)"]]), depthTest: false }));
  etiket.scale.set(1.7, 0.42, 1);
  etiket.position.set(0, 1.68, 0.5);
  const simge = new THREE.Sprite(new THREE.SpriteMaterial({ depthTest: false }));
  simge.scale.set(1.4, 0.7, 1);
  simge.position.set(0, 2.08, 0.5);
  simge.visible = false;
  grup.add(etiket, simge);
  grup.traverse((o) => (o.userData.asistan = a.id));
  return { grup, ekranMat, simge, durum: "bosta", zamanlayici: null };
}

function saatiAl() {
  const p = new URLSearchParams(location.search).get("saat");
  const d = new Date();
  return p !== null && p !== "" && !isNaN(+p) ? saatAyarla(d, +p) : d;
}

export function ofisKur(kap, masaTiklandi) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  kap.appendChild(renderer.domElement);
  const sahne = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  sahne.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  sahne.fog = new THREE.Fog(0x000000, 150, 900);

  const kamera = new THREE.PerspectiveCamera(60, 1, 0.05, 3000);
  kamera.position.set(0, 2.45, 5.0);
  const kontrol = new OrbitControls(kamera, renderer.domElement);
  kontrol.target.set(0, 0.9, -2.8);
  kontrol.enablePan = false;
  kontrol.minDistance = 1.5;
  kontrol.maxDistance = 9;
  kontrol.minAzimuthAngle = -1.1;
  kontrol.maxAzimuthAngle = 1.1;
  kontrol.maxPolarAngle = 1.62;
  kontrol.update();

  const gunes = new THREE.DirectionalLight(0xfff0d8, 1);
  gunes.castShadow = true;
  gunes.shadow.mapSize.set(2048, 2048);
  Object.assign(gunes.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, near: 1, far: 120 });
  gunes.shadow.bias = -0.0005;
  gunes.shadow.normalBias = 0.02;
  sahne.add(gunes, gunes.target);
  const ortam = new THREE.HemisphereLight(0xdfe9ff, 0x5a4a3a, 0.5);
  sahne.add(ortam);
  const tavanIsiklari = [];
  for (const [x, z] of [[-5, -3], [5, -3], [-5, 2.5], [5, 2.5], [0, 0]]) {
    const l = new THREE.PointLight(0xfff1dc, 6, 0, 2);
    l.position.set(x, ODA.h - 0.15, z);
    tavanIsiklari.push(l);
    sahne.add(l);
  }

  odaKur(sahne);
  const { pencereMat, uyari, binaMat } = silueKur(sahne);
  const masalar = {};
  ASISTANLAR.forEach((a, i) => {
    const m = masaKur(a, i, [-4.3, 0, 4.3][i % 3], [-4.8, -2.6, -0.4][Math.floor(i / 3)]);
    masalar[a.id] = m;
    sahne.add(m.grup);
  });

  let bekleyen = false;
  const ciz = (t) => {
    bekleyen = false;
    let animasyon = false;
    for (const m of Object.values(masalar)) {
      if (m.durum === "calisiyor") {
        m.simge.position.y = 2.08 + Math.sin(t / 220) * 0.05;
        m.ekranMat.emissiveIntensity = 1.6 + Math.sin(t / 140) * 0.25;
        animasyon = true;
      }
    }
    renderer.render(sahne, kamera);
    if (animasyon) istek();
  };
  const istek = () => { if (!bekleyen) { bekleyen = true; requestAnimationFrame(ciz); } };
  // Kamera odanın içinde kalsın (duvar/tavan/camdan dışarı çıkmasın)
  kontrol.addEventListener("change", () => {
    const p = kamera.position;
    p.x = THREE.MathUtils.clamp(p.x, -ODA.x + 0.4, ODA.x - 0.4);
    p.y = THREE.MathUtils.clamp(p.y, 0.5, ODA.h - 0.2);
    p.z = THREE.MathUtils.clamp(p.z, -ODA.z + 0.6, ODA.z - 0.3);
    istek();
  });

  const isikGuncelle = () => {
    const simdi = saatiAl();
    const y = gunesYuksekligi(simdi);
    const d = isikDurumu(y);
    const gok = new THREE.Color(d.gokRengi);
    sahne.background = gok;
    sahne.fog.color.copy(gok);
    const saat = yerelSaat(simdi);
    const az = ((saat - 12) / 12) * Math.PI * 0.9;
    const el = Math.max(y, 4) * Math.PI / 180;
    gunes.position.set(Math.sin(az) * Math.cos(el) * 60, Math.sin(el) * 60, -Math.cos(az) * Math.cos(el) * 60);
    gunes.intensity = d.gunesYogunluk * 1.6;
    gunes.color.set(y < 10 ? 0xffb070 : 0xfff0d8);
    ortam.intensity = d.ortamYogunluk * 0.9;
    sahne.environmentIntensity = 0.15 + d.ortamYogunluk * 0.45;
    pencereMat.color.set(0x6d8296).lerp(new THREE.Color(0xffd48a), d.pencereIsigi);
    uyari.visible = d.lambalar;
    binaMat.color.set(0x1b1f27).lerp(new THREE.Color(0xffffff), 1 - d.pencereIsigi); // gece cepheler karanlık
    tavanIsiklari.forEach((l) => (l.intensity = d.lambalar ? 9 : 3));
    const evre = y > 6 ? "gündüz" : y > -6 ? (saat < 12 ? "şafak" : "gün batımı") : "gece";
    const etiket = document.getElementById("saat");
    if (etiket) etiket.textContent = `İtalya saati ${simdi.toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit", timeZone: KONUM.saatDilimi })} · ${evre}`;
    istek();
  };
  isikGuncelle();
  setInterval(isikGuncelle, 60_000);

  const boyutla = () => {
    renderer.setSize(kap.clientWidth, kap.clientHeight);
    kamera.aspect = kap.clientWidth / kap.clientHeight;
    kamera.updateProjectionMatrix();
    istek();
  };
  addEventListener("resize", boyutla);
  boyutla();

  const isin = new THREE.Raycaster();
  const fare = new THREE.Vector2();
  const hedef = (e) => {
    const r = renderer.domElement.getBoundingClientRect();
    fare.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    isin.setFromCamera(fare, kamera);
    const vurus = isin.intersectObjects(Object.values(masalar).map((m) => m.grup), true)[0];
    return vurus?.object.userData.asistan ?? null;
  };
  let basla = null;
  renderer.domElement.addEventListener("pointerdown", (e) => (basla = [e.clientX, e.clientY]));
  renderer.domElement.addEventListener("pointerup", (e) => {
    if (!basla || Math.hypot(e.clientX - basla[0], e.clientY - basla[1]) > 5) return; // sürükleme tıklama sayılmaz
    const id = hedef(e);
    if (id) masaTiklandi(id);
  });
  renderer.domElement.addEventListener("pointermove", (e) => {
    renderer.domElement.style.cursor = hedef(e) ? "pointer" : "grab";
  });

  function durumAyarla(asistan, durum, dersEtiketi = null) {
    const m = masalar[asistan];
    if (!m) return;
    clearTimeout(m.zamanlayici);
    m.durum = durum;
    const simge = DURUM_SIMGE[durum];
    m.simge.visible = Boolean(simge);
    if (simge) {
      m.simge.material.map?.dispose();
      const satirlar = [[simge, 64, "#fff", 50, "rgba(20,24,32,.72)"]];
      if (dersEtiketi) satirlar.push([dersEtiketi, 30, "#ffd27a", 108]);
      m.simge.material.map = yaziDokusu(satirlar, 512, 128);
      m.simge.material.needsUpdate = true;
      m.simge.position.y = 2.08;
    }
    m.ekranMat.emissive.set(durum === "calisiyor" ? 0x6fc8ff : durum === "hata" ? 0xff5a5a : 0x1c2a3a);
    m.ekranMat.emissiveIntensity = 1;
    if (durum === "bitti") m.zamanlayici = setTimeout(() => durumAyarla(asistan, "bosta"), 60_000);
    istek();
  }

  return { durumAyarla };
}
