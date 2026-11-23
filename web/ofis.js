import * as THREE from "three";
import { OrbitControls } from "three/addons/OrbitControls.js";
import { gunesYuksekligi, isikDurumu, yerelSaat, saatAyarla, KONUM } from "./gunes.js";

export const ASISTANLAR = [
  { id: "ozetci", ad: "Özetçi", emoji: "📝", renk: 0xe76f51, gorev: "PDF'i özetler, önemli noktaları işaretler." },
  { id: "formulcu", ad: "Formülcü", emoji: "∑", renk: 0x2a9d8f, gorev: "Formülleri orijinal görüntüsüyle çıkarır, nerede kullanılacağını açıklar." },
  { id: "sure", ad: "Süre analisti", emoji: "📊", renk: 0xe9c46a, gorev: "Çalışma süreni tutar, sınava yetişip yetişmediğini gösterir." },
  { id: "arastirmaci", ad: "Soru araştırmacısı", emoji: "🌐", renk: 0x457b9d, gorev: "Üniversite sınavlarından soru arar, bulamazsa yazar." },
  { id: "not", ad: "Not tutucu", emoji: "📒", renk: 0x8ab17d, gorev: "Önemli dediğin notları ders klasörüne kaydeder." },
  { id: "sinavci", ad: "Sınavcı", emoji: "🎯", renk: 0xd62828, gorev: "Kolay-orta-zor sorularla seni test eder, eksiklerini söyler." },
  { id: "tekrar", ad: "Tekrar planlayıcı", emoji: "🔁", renk: 0x9b5de5, gorev: "Eksik konuları 1, 3 ve 7 gün sonra hatırlatır." },
  { id: "soru_cevap", ad: "Soru-cevap hocası", emoji: "💬", renk: 0x00b4d8, gorev: "Anlamadığın yeri ders notlarına dayanarak açıklar." },
  { id: "mola", ad: "Mola", emoji: "☕", renk: 0xb5838d, gorev: "50 dakikada bir 10 dakika mola hatırlatır." },
];

const DURUM_SIMGE = { calisiyor: "…", bitti: "✅", bekliyor: "💤", hata: "⚠️" };

// Tekrarlanabilir rastgele (silüet her açılışta aynı görünsün)
function rastgele(tohum) {
  return () => ((tohum = (tohum * 1664525 + 1013904223) >>> 0) / 4294967296);
}

function yaziDokusu(satirlar, genislik = 512, yukseklik = 128) {
  const c = document.createElement("canvas");
  c.width = genislik; c.height = yukseklik;
  const g = c.getContext("2d");
  g.textAlign = "center"; g.textBaseline = "middle";
  satirlar.forEach(([metin, boyut, renk, y]) => {
    g.font = `600 ${boyut}px system-ui, "Segoe UI Emoji", sans-serif`;
    g.lineWidth = 8; g.strokeStyle = "rgba(0,0,0,.6)"; g.strokeText(metin, genislik / 2, y);
    g.fillStyle = renk; g.fillText(metin, genislik / 2, y);
  });
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

function silueKur(sahne) {
  const r = rastgele(42);
  const binaMat = new THREE.MeshLambertMaterial({ color: 0x8a93a3 });
  const pencereMat = new THREE.MeshBasicMaterial({ color: 0xffd27a });
  const kutu = new THREE.BoxGeometry(1, 1, 1);
  const binalar = [];
  for (let i = 0; i < 200; i++) {
    const w = 3 + r() * 6, d = 3 + r() * 6;
    const uzak = 26 + Math.pow(r(), 0.8) * 100;
    const x = (r() - 0.5) * (40 + uzak * 2.2);
    const merkez = Math.abs(x) < 25 ? 1.4 : 1; // ortada daha yüksek kuleler (Manhattan hissi)
    const h = (22 + r() * 40) * merkez;
    binalar.push({ x, z: -uzak, w, d, h });
  }
  binalar.push({ x: 4, z: -55, w: 6, d: 6, h: 95, kule: true }); // ufukta öne çıkan kule
  const taban = -45; // ofis yüksek bir katta: binaların tabanı çok aşağıda
  const binaMesh = new THREE.InstancedMesh(kutu, binaMat, binalar.length);
  const m = new THREE.Matrix4();
  binalar.forEach((b, i) => {
    m.compose(new THREE.Vector3(b.x, taban + b.h / 2, b.z), new THREE.Quaternion(), new THREE.Vector3(b.w, b.h, b.d));
    binaMesh.setMatrixAt(i, m);
  });
  sahne.add(binaMesh);
  const kuleUcu = new THREE.Mesh(new THREE.ConeGeometry(1.2, 18, 8), binaMat);
  kuleUcu.position.set(4, taban + 95 + 9, -55);
  sahne.add(kuleUcu);

  // Pencereler: her binanın ofise bakan yüzünde küçük dörtgenler
  const yerler = [];
  binalar.forEach((b) => {
    const sutun = Math.max(1, Math.floor(b.w / 1.1));
    const ust = taban + b.h;
    for (let y = Math.max(taban + 2, ust - 70); y < ust - 1; y += 1.6)
      for (let s = 0; s < sutun; s++) yerler.push([b.x - b.w / 2 + (s + 0.5) * (b.w / sutun), y, b.z + b.d / 2 + 0.02, r()]);
  });
  const pencere = new THREE.InstancedMesh(new THREE.PlaneGeometry(0.55, 0.8), pencereMat, yerler.length);
  const renk = new THREE.Color();
  yerler.forEach(([x, y, z, sans], i) => {
    m.makeTranslation(x, y, z);
    pencere.setMatrixAt(i, m);
    pencere.setColorAt(i, renk.setScalar(sans < 0.55 ? 1 : 0.12)); // yarısı açık, yarısı kapalı oda
  });
  sahne.add(pencere);
  return { pencereMat };
}

function odaKur(sahne) {
  const zemin = new THREE.Mesh(new THREE.PlaneGeometry(26, 18), new THREE.MeshLambertMaterial({ color: 0x7a6650 }));
  zemin.rotation.x = -Math.PI / 2;
  sahne.add(zemin);
  const halı = new THREE.Mesh(new THREE.PlaneGeometry(22, 13), new THREE.MeshLambertMaterial({ color: 0x3d4a5c }));
  halı.rotation.x = -Math.PI / 2; halı.position.y = 0.01;
  sahne.add(halı);
  const duvarMat = new THREE.MeshLambertMaterial({ color: 0xd9d4cc });
  for (const x of [-13, 13]) {
    const duvar = new THREE.Mesh(new THREE.BoxGeometry(0.3, 4.5, 18), duvarMat);
    duvar.position.set(x, 2.25, 0);
    sahne.add(duvar);
  }
  // Cam cephe ve doğramalar
  const cam = new THREE.Mesh(new THREE.PlaneGeometry(26, 4.5),
    new THREE.MeshBasicMaterial({ color: 0x9ecbff, transparent: true, opacity: 0.08, depthWrite: false }));
  cam.position.set(0, 2.25, -9);
  sahne.add(cam);
  const dogramaMat = new THREE.MeshLambertMaterial({ color: 0x1d2128 });
  for (let x = -13; x <= 13; x += 2.6) {
    const d = new THREE.Mesh(new THREE.BoxGeometry(0.12, 4.5, 0.12), dogramaMat);
    d.position.set(x, 2.25, -9);
    sahne.add(d);
  }
  for (const y of [0.05, 4.45]) {
    const d = new THREE.Mesh(new THREE.BoxGeometry(26, 0.12, 0.2), dogramaMat);
    d.position.set(0, y, -9);
    sahne.add(d);
  }
  // Köşelerde saksı bitkileri
  for (const [x, z] of [[-11.5, -7.5], [11.5, -7.5], [-11.5, 7.5], [11.5, 7.5]]) {
    const saksi = new THREE.Mesh(new THREE.CylinderGeometry(0.45, 0.35, 0.8, 12), new THREE.MeshLambertMaterial({ color: 0x5c4033 }));
    saksi.position.set(x, 0.4, z);
    const yaprak = new THREE.Mesh(new THREE.IcosahedronGeometry(0.9, 0), new THREE.MeshLambertMaterial({ color: 0x3f7d3a }));
    yaprak.position.set(x, 1.5, z);
    sahne.add(saksi, yaprak);
  }
}

function masaKur(a, x, z) {
  const grup = new THREE.Group();
  grup.position.set(x, 0, z);
  const ahsap = new THREE.MeshLambertMaterial({ color: 0xc8a27a });
  const koyu = new THREE.MeshLambertMaterial({ color: 0x222831 });
  const ust = new THREE.Mesh(new THREE.BoxGeometry(3, 0.12, 1.6), ahsap);
  ust.position.y = 1.0;
  grup.add(ust);
  for (const [lx, lz] of [[-1.35, -0.65], [1.35, -0.65], [-1.35, 0.65], [1.35, 0.65]]) {
    const ayak = new THREE.Mesh(new THREE.BoxGeometry(0.08, 1.0, 0.08), koyu);
    ayak.position.set(lx, 0.5, lz);
    grup.add(ayak);
  }
  // Monitör ekranı karaktere (kameraya) bakar
  const kasa = new THREE.Mesh(new THREE.BoxGeometry(1.3, 0.8, 0.07), koyu);
  kasa.position.set(0, 1.55, -0.35);
  const ekranMat = new THREE.MeshBasicMaterial({ color: 0x1c2a3a });
  const ekran = new THREE.Mesh(new THREE.PlaneGeometry(1.18, 0.68), ekranMat);
  ekran.position.set(0, 1.55, -0.31);
  const ayakM = new THREE.Mesh(new THREE.BoxGeometry(0.1, 0.25, 0.1), koyu);
  ayakM.position.set(0, 1.18, -0.35);
  grup.add(kasa, ekran, ayakM);
  // Masa lambası (gece yanar)
  const ampulMat = new THREE.MeshBasicMaterial({ color: 0x444444 });
  const ampul = new THREE.Mesh(new THREE.SphereGeometry(0.12, 10, 8), ampulMat);
  ampul.position.set(1.15, 1.45, -0.4);
  const lambaAyak = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.08, 0.4), koyu);
  lambaAyak.position.set(1.15, 1.25, -0.4);
  grup.add(ampul, lambaAyak);
  // Sandalye ve karakter (arkası kameraya dönük, ekrana bakıyor)
  const sandalye = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.1, 0.8), koyu);
  sandalye.position.set(0, 0.65, 1.15);
  const sirt = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.9, 0.1), koyu);
  sirt.position.set(0, 1.1, 1.55);
  const govdeMat = new THREE.MeshLambertMaterial({ color: a.renk });
  const govde = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.38, 0.9, 14), govdeMat);
  govde.position.set(0, 1.15, 1.1);
  const kafa = new THREE.Mesh(new THREE.SphereGeometry(0.27, 16, 12), new THREE.MeshLambertMaterial({ color: 0xf1c27d }));
  kafa.position.set(0, 1.85, 1.1);
  const sac = new THREE.Mesh(new THREE.SphereGeometry(0.28, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), new THREE.MeshLambertMaterial({ color: 0x3b2a20 }));
  sac.position.copy(kafa.position);
  grup.add(sandalye, sirt, govde, kafa, sac);

  const etiket = new THREE.Sprite(new THREE.SpriteMaterial({ map: yaziDokusu([[`${a.emoji} ${a.ad}`, 46, "#fff", 64]]), depthTest: false }));
  etiket.scale.set(2.8, 0.7, 1);
  etiket.position.set(0, 2.65, 0.4);
  const simge = new THREE.Sprite(new THREE.SpriteMaterial({ depthTest: false }));
  simge.scale.set(2.4, 1.2, 1);
  simge.position.set(0, 3.45, 0.4);
  simge.visible = false;
  grup.add(etiket, simge);
  grup.traverse((o) => (o.userData.asistan = a.id));
  return { grup, ekranMat, ampulMat, simge, durum: "bosta", zamanlayici: null };
}

function saatiAl() {
  const p = new URLSearchParams(location.search).get("saat");
  const d = new Date();
  return p !== null && p !== "" && !isNaN(+p) ? saatAyarla(d, +p) : d;
}

export function ofisKur(kap, masaTiklandi) {
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
  kap.appendChild(renderer.domElement);
  const sahne = new THREE.Scene();
  const kamera = new THREE.PerspectiveCamera(45, 1, 0.1, 400);
  kamera.position.set(0, 8.5, 17);
  const kontrol = new OrbitControls(kamera, renderer.domElement);
  kontrol.target.set(0, 1.2, -1);
  kontrol.enablePan = false;
  kontrol.minDistance = 6;
  kontrol.maxDistance = 25;
  kontrol.maxPolarAngle = Math.PI / 2.15;
  kontrol.update();

  const gunes = new THREE.DirectionalLight(0xfff1d6, 1);
  const ortam = new THREE.HemisphereLight(0xdde8ff, 0x4a3b2c, 0.6);
  const lambalar = [new THREE.PointLight(0xffd9a0, 0, 0, 2), new THREE.PointLight(0xffd9a0, 0, 0, 2)];
  lambalar[0].position.set(-6, 4, 0); lambalar[1].position.set(6, 4, 0);
  sahne.add(gunes, ortam, ...lambalar);
  sahne.fog = new THREE.Fog(0x000000, 40, 160);

  odaKur(sahne);
  const { pencereMat } = silueKur(sahne);
  const masalar = {};
  ASISTANLAR.forEach((a, i) => {
    const m = masaKur(a, [-7.5, 0, 7.5][i % 3], [-4.5, 0, 4.5][Math.floor(i / 3)]);
    masalar[a.id] = m;
    sahne.add(m.grup);
  });

  let bekleyen = false;
  const ciz = (t) => {
    bekleyen = false;
    let animasyon = false;
    for (const m of Object.values(masalar)) {
      if (m.durum === "calisiyor") {
        m.simge.position.y = 3.45 + Math.sin(t / 220) * 0.12;
        animasyon = true;
      }
    }
    renderer.render(sahne, kamera);
    if (animasyon) istek();
  };
  const istek = () => { if (!bekleyen) { bekleyen = true; requestAnimationFrame(ciz); } };
  kontrol.addEventListener("change", istek);

  let gece = false;
  const isikGuncelle = () => {
    const simdi = saatiAl();
    const y = gunesYuksekligi(simdi);
    const d = isikDurumu(y);
    sahne.background = new THREE.Color(d.gokRengi);
    sahne.fog.color.set(d.gokRengi);
    gunes.intensity = d.gunesYogunluk;
    const saat = yerelSaat(simdi);
    const saatAcisi = (saat - 12) / 12 * Math.PI;
    gunes.position.set(Math.sin(saatAcisi) * 40, 10 + Math.max(y, 0), 30); // binaların ofise bakan yüzünü aydınlatsın
    ortam.intensity = d.ortamYogunluk;
    pencereMat.color.set(0x5b7694).lerp(new THREE.Color(0xffd27a), d.pencereIsigi);
    gece = d.lambalar;
    lambalar.forEach((l) => (l.intensity = gece ? 45 : 0));
    for (const m of Object.values(masalar)) m.ampulMat.color.set(gece ? 0xffe6a8 : 0x444444);
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
      const satirlar = [[simge, 72, "#fff", 58]];
      if (dersEtiketi) satirlar.push([dersEtiketi, 34, "#ffd27a", 112]);
      m.simge.material.map = yaziDokusu(satirlar, 512, 128 + (dersEtiketi ? 16 : 0));
      m.simge.material.needsUpdate = true;
      m.simge.position.y = 3.45;
    }
    m.ekranMat.color.set(durum === "calisiyor" ? 0x6fd3ff : durum === "hata" ? 0xff6b6b : 0x1c2a3a);
    if (durum === "bitti") m.zamanlayici = setTimeout(() => durumAyarla(asistan, "bosta"), 60_000);
    istek();
  }

  return { durumAyarla };
}
