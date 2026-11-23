# Ders Ofisi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tarayıcıda açılan 3D NYC ofisinde dokuz ders asistanı; PDF'i bir kez okuyup ders klasörüne özet, formül görüntüsü, soru, not, sınav ve süre kayıtları üretir.

**Architecture:** Yerel Python sunucusu (`127.0.0.1`) statik 3D sayfayı sunar, REST + SSE ile durum yayınlar ve yapay zekâ işlerini `claude -p` alt süreçleriyle (aboneliğe giriş yapılmış Claude Code) en fazla 2 eşzamanlı çalıştırır. Claude yalnızca **okur ve JSON döndürür** (`--json-schema`); ders klasörüne dosyaları sunucu yazar. Böylece her iş yalnızca kendi ders klasörünü görür ve çıktı biçimi sabit kalır.

**Tech Stack:** Python 3.14 stdlib (`http.server`, `subprocess`, `threading`, `unittest`), PyMuPDF (tek ek paket), three.js + marked (ön yüz, `web/vendor/` altına kopyalanır).

**Spec:** `docs/tasarim.md`

## Global Constraints

- Proje kökü: `C:\Users\mirac\ders-ofisi\`; ders klasörleri `Dersler\<ders adı>\`.
- Sunucu yalnızca `127.0.0.1` dinler. Varsayılan port 8765.
- Python ek paketi yalnızca `pymupdf`. Test için `unittest` (pytest yok).
- Claude CLI: `C:\Users\mirac\.local\bin\claude.exe` (PATH'te değil — `ayarlar.json` içinde `claude_komutu` listesi olarak tutulur).
- Aynı anda en fazla **2** yapay zekâ işi; fazlası sıraya girer.
- PDF metne **20 sayfalık** parçalarla çevrilir; bir PDF bir kez çevrilir.
- Modeller: çevirme, Özetçi, Formülcü, Sınavcı, Soru-cevap → `sonnet`; Soru araştırmacısı → `haiku`. Hepsi `ayarlar.json`'da.
- Soru araştırmacısı otomatik çalışmaz, yalnızca istekle.
- Formüller ve önemli görseller her yerde **PDF'ten kesilmiş PNG** olarak gösterilir, yazıya çevrilmez.
- Kaynağı olmayan her soru `"kaynak": null` ve arayüzde "asistan yazdı" etiketiyle.
- Her yapay zekâ işi `cwd` = o dersin klasörü; izinli araçlar yalnızca `Read` (araştırmacıya ek `WebSearch WebFetch`).
- Mola: 50 dk çalışma / 10 dk mola. Tekrar: eksik konu +1, +3, +7 gün.
- Arayüz metinleri Türkçe.

## Review Focus

1. **Ders adında `..`, `/`, `\`, `:` gibi karakterler veya URL'de kodlanmış yol** → istek reddedilmeli, başka klasöre yazılmamalı. (Task 1 `test_gecersiz_ad`, Task 7 `test_yol_kacisi`)
2. **Limit dolu / Claude hata verdi, PDF yarıda** → durum `bekliyor`, tamamlanan parçalar korunur, "devam" kalan parçadan sürer. (Task 4 `test_limitte_durur_ve_devam_eder`)
3. **Claude geçersiz kutu döndürdü** (0–100 dışı, x0>x1, sayfa aralık dışı) → kutu düzeltilir veya o görsel için tam sayfa kesilir; çökme yok. (Task 3 `test_bozuk_kutu`)
4. **İş sürerken ders değişti** → çıktı başlatıldığı derse yazılır. (Task 2 `test_is_kendi_dersine_yazar`)
5. **Sunucu kapanıp açıldı / sayaç açık kaldı** → açık oturum tekrar başlatılınca kapatılır, süre kaybolmaz; yarım çeviri `durum.json`'dan devam eder. (Task 6 `test_acik_oturum_kapanir`, Task 4 `test_yeniden_baslatmada_devam`)

---

## Dosya yapısı

```
ders-ofisi/
  baslat.bat                 # pip kontrolü + sunucu + tarayıcı
  ayarlar.json
  ofis/
    ayarlar.py               # ayarları oku
    dersler.py               # ders klasörü, ders.json, ad doğrulama, güvenli yol
    claude_calistir.py       # claude -p çağrısı, LimitDolu, İş kuyruğu (2 eşzamanlı)
    olaylar.py               # SSE yayıncısı
    pdf_isleme.py            # parçalama, görüntü kesme (PyMuPDF)
    cevirme.py               # PDF → metin + görseller, devam edilebilir
    asistanlar.py            # Özetçi, Formülcü, Araştırmacı, Sınavcı, Soru-cevap
    hesap.py                 # süre, süre analizi, tekrar, notlar, mola yok (ön yüzde)
    sunucu.py                # HTTP uçları
  talimatlar/                # her asistanın sistem talimatı (.md) + şema (.json)
  web/
    index.html  ofis.js  panel.js  stil.css
    vendor/three.module.js  vendor/marked.esm.js
  tests/
    sahte_claude.py          # gerçek claude yerine; davranışı ortam değişkeniyle
    test_*.py
  Dersler/                   # .gitignore'da
```

---

### Task 0: 3D NYC ofis önizlemesi (önce bu — kullanıcı önce ofisi görmek istiyor)

Sunucu ve asistan bağlantısı yok; yalnızca görsel. Task 8 bunun üzerine panelleri ve gerçek durumları bağlar.

**Files:**
- Create: `web/index.html`, `web/stil.css`, `web/ofis.js`, `web/gunes.js`, `web/vendor/three.module.js`, `web/vendor/OrbitControls.js`, `tests/gunes.test.html`
- `git init` ve `.gitignore` bu task'ta yapılır (Task 1 Step 1 atlanır).

**Interfaces:**
- Produces:
  - `gunes.js` → `gunesYuksekligi(tarih: Date, enlem = 41.9, boylam = 12.5): number` (derece, ufuk = 0). Saat dilimi `tarih`'in yerel saatinden gelir (bilgisayar saati = kullanıcının bulunduğu yer).
  - `gunes.js` → `isikDurumu(yukseklik: number): {gokRengi, gunesYogunluk, ortamYogunluk, pencereIsigi: 0..1, lambalar: bool}` — `> 6°` gündüz, `-6°..6°` alacakaranlık (turuncu, ara değer), `< -6°` gece.
  - `ofis.js` → `ofisKur(kap, masaTiklandi)` → `{durumAyarla(asistan, durum, dersEtiketi | null)}` (Task 8'deki ile aynı).
- Güneş yüksekliği: standart yaklaşık formül (gün-yılı → sapma açısı, denklem-zaman ihmal edilebilir, saat açısı = (yerel güneş saati − 12) × 15°; yerel güneş saati = UTC saati + boylam/15). Hata ±1° kabul.

- [ ] **Step 1: Vendor dosyalarını indir** (`npm pack three`, gerekli iki dosyayı kopyala)
- [ ] **Step 2: Güneş testini yaz** — `tests/gunes.test.html` tarayıcıda `console.assert` ile:
  - Roma, 21 Haziran 11:15 UTC (yerel öğle ~13:15 CEST) → yükseklik 71.5° ± 1.5
  - Roma, 21 Aralık 11:15 UTC → 24.7° ± 1.5
  - Roma, 23 Kasım 23:00 UTC → < −30 (gece)
  - `isikDurumu(-20).lambalar === true`, `isikDurumu(30).lambalar === false`
- [ ] **Step 3: `gunes.js`'yi uygula, test sayfasında tüm assert'ler geçiyor** (konsolda "assertion failed" yok)
- [ ] **Step 4: Sahneyi uygula** — Task 8 "Sahne", "Durum gösterimi", "Performans" kararları geçerli; ışık `gunesYuksekligi(new Date())` ile açılışta ve dakikada bir. `?saat=21` parametresi önizleme için saati değiştirir. `?demo=1` masaları sırayla durumlardan geçirir. Masaya tıklayınca şimdilik sağda asistan adıyla boş panel.
- [ ] **Step 5: Kullanıcıya göster** — `python -m http.server 8765 --bind 127.0.0.1 -d web` ve `http://127.0.0.1:8765/?demo=1`; ayrıca `?saat=13`, `?saat=17`, `?saat=22` görünümleri. Kullanıcının geri bildirimini al, görsel düzeltmeleri bu task'ta yap.
- [ ] **Step 6: Commit** — `feat: 3d ofis önizlemesi`

---

### Task 1: İskelet, ayarlar, ders klasörü

**Files:**
- Create: `ayarlar.json`, `ofis/__init__.py`, `ofis/ayarlar.py`, `ofis/dersler.py`, `.gitignore`, `tests/test_dersler.py`

**Interfaces:**
- Produces:
  - `ayarlar.yukle(yol: Path | None = None) -> dict` — anahtarlar: `claude_komutu: list[str]`, `modeller: dict[str,str]`, `es_zamanli: int`, `parca_sayfa: int`, `port: int`, `dersler_klasoru: str`
  - `dersler.GecersizAd(ValueError)`
  - `dersler.ders_yolu(kok: Path, ad: str) -> Path` — adı doğrular
  - `dersler.ders_olustur(kok, ad, sinav_tarihi: str, konular: list[str]) -> dict`
  - `dersler.listele(kok) -> list[str]`
  - `dersler.oku(kok, ad) -> dict` / `dersler.yaz(kok, ad, veri: dict) -> None` (atomik: geçici dosya + `os.replace`)
  - `dersler.guvenli_dosya(kok, ad, goreli: str) -> Path` — sonuç ders klasörünün dışındaysa `GecersizAd`
  - `ders.json` biçimi: `{"ad", "sinav_tarihi": "YYYY-MM-DD", "konular": [{"ad": str, "bitti": bool}], "oturumlar": [{"basla": iso, "bitis": iso|null}], "sohbetler": {}}`

- [ ] **Step 1: `git init`, `.gitignore` (`Dersler/`, `__pycache__/`, `web/vendor/node_modules/`), tasarım belgesini commit et**
- [ ] **Step 2: Testleri yaz** (`tests/test_dersler.py`, `tempfile.TemporaryDirectory` kökü)

```python
def test_olustur_ve_oku(self):
    dersler.ders_olustur(self.kok, "Math 1", "2027-01-15", ["Limit", "Türev"])
    v = dersler.oku(self.kok, "Math 1")
    self.assertEqual(v["konular"], [{"ad": "Limit", "bitti": False}, {"ad": "Türev", "bitti": False}])
    self.assertEqual(dersler.listele(self.kok), ["Math 1"])
    for alt in ["pdf", "metin", "ozet", "formuller", "sorular", "sinavlar", "gorseller"]:
        self.assertTrue((self.kok / "Math 1" / alt).is_dir())

def test_gecersiz_ad(self):
    for ad in ["..", "../x", "a/b", "a\\b", "C:", "", " ", "con", "a*b"]:
        with self.assertRaises(dersler.GecersizAd):
            dersler.ders_yolu(self.kok, ad)

def test_guvenli_dosya(self):
    dersler.ders_olustur(self.kok, "Fizik", "2027-01-15", [])
    with self.assertRaises(dersler.GecersizAd):
        dersler.guvenli_dosya(self.kok, "Fizik", "../../ayarlar.json")
    self.assertEqual(dersler.guvenli_dosya(self.kok, "Fizik", "ozet/a.md"),
                     (self.kok / "Fizik" / "ozet" / "a.md").resolve())
```

- [ ] **Step 3: Çalıştır, FAIL gör** — `python -m unittest tests.test_dersler -v`
- [ ] **Step 4: Uygula.** Ad kuralı: boş/boşluk değil, `<>:"/\|?*` ve kontrol karakteri yok, `.` ile başlamaz/bitmez, Windows ayrılmış adları (`con, prn, aux, nul, com1-9, lpt1-9`, büyük/küçük harf duyarsız) değil, en fazla 60 karakter. `guvenli_dosya` `resolve()` sonrası `is_relative_to` ile kontrol.
- [ ] **Step 5: PASS gör, commit** — `feat: ders klasörü ve ayarlar`

---

### Task 2: Claude çalıştırıcı ve iş kuyruğu

**Files:**
- Create: `ofis/claude_calistir.py`, `ofis/olaylar.py`, `tests/sahte_claude.py`, `tests/test_claude_calistir.py`

**Interfaces:**
- Consumes: `ayarlar.yukle`
- Produces:
  - `claude_calistir.LimitDolu(Exception)`, `claude_calistir.ClaudeHatasi(Exception)`
  - `claude_calistir.cagir(ayar: dict, cwd: Path, istem: str, model: str, sistem_dosyasi: Path, sema: dict, araclar: list[str], oturum: str | None = None) -> tuple[dict, str]` — `(yapilandirilmis_sonuc, session_id)`
  - `olaylar.Yayinci` — `yayinla(olay: dict)`, `abone() -> queue.Queue`, `ayril(q)`. Olay biçimi: `{"ders": str, "asistan": str, "durum": "bosta"|"calisiyor"|"bitti"|"bekliyor"|"hata", "mesaj": str}`
  - `claude_calistir.Kuyruk(es_zamanli: int, yayinci: Yayinci)` — `ekle(ders: str, asistan: str, is_fn: Callable[[], None]) -> None`. `is_fn` çalışırken `calisiyor`, bitince `bitti`, `LimitDolu`'da `bekliyor`, diğer istisnada `hata` yayınlar.

Komut (bu sırayla; testte sahte_claude argümanları doğrular):
```
<claude_komutu...> -p <istem> --output-format json --model <model>
  --append-system-prompt-file <sistem_dosyasi> --json-schema <json.dumps(sema)>
  --allowedTools <araçlar boşlukla birleşik> [--resume <oturum>]
```
`subprocess.run(..., cwd=cwd, capture_output=True, text=True, encoding="utf-8", timeout=900)`. Çıktı JSON'u: `is_error`, `result`, `session_id`, `structured_output`. `is_error` ve (`result` + stderr) içinde `limit|usage|rate` (büyük/küçük harf duyarsız) → `LimitDolu`; diğer `is_error`/sıfırdan farklı çıkış/zaman aşımı → `ClaudeHatasi`. `structured_output` yoksa `result`'ı `json.loads` dene.

`sahte_claude.py`: `SAHTE_CLAUDE_MOD` ortam değişkeni `ok|limit|hata`; `ok` modunda `SAHTE_CLAUDE_CEVAP` (JSON metni) değerini `structured_output` olarak döndürür, `session_id` olarak `"s-" + cwd klasör adı` verir ve aldığı argümanları + cwd'yi `SAHTE_CLAUDE_KAYIT` dosyasına satır satır JSON olarak ekler.

- [ ] **Step 1: Testleri yaz**

```python
def test_argumanlar_ve_cwd(self): ...          # kayıtta "-p", "--json-schema", "--allowedTools", "Read"; cwd == ders klasörü
def test_resume(self): ...                     # oturum="abc" → "--resume","abc" kayıtta
def test_limit(self):  # MOD=limit
    with self.assertRaises(claude_calistir.LimitDolu): ...
def test_hata(self):   # MOD=hata → ClaudeHatasi
def test_kuyruk_en_fazla_iki(self):
    # 5 iş, her biri threading.Event bekler; aynı anda çalışan sayısı max 2
def test_kuyruk_durumlari(self):
    # biri LimitDolu atar → yayinci olaylarında ("bekliyor"); biri ValueError → "hata"; normal → "calisiyor" sonra "bitti"
def test_is_kendi_dersine_yazar(self):
    # Kuyruk'a ders="CS" ile eklenen iş, cwd=Dersler/CS ile cagir çağırır; sonra "Math 1" işi eklenir;
    # kayıtta ilk satırın cwd'si CS, olaylardaki "ders" alanları ilgili ders
```

- [ ] **Step 2: FAIL gör** — `python -m unittest tests.test_claude_calistir -v`
- [ ] **Step 3: Uygula** (`Kuyruk`: `threading.Semaphore(es_zamanli)` + her iş için daemon thread)
- [ ] **Step 4: PASS gör, commit** — `feat: claude çağrısı ve iş kuyruğu`

---

### Task 3: PDF parçalama ve görüntü kesme

**Files:**
- Create: `ofis/pdf_isleme.py`, `tests/test_pdf_isleme.py`

**Interfaces:**
- Produces:
  - `pdf_isleme.sayfa_sayisi(pdf: Path) -> int`
  - `pdf_isleme.parcala(pdf: Path, hedef: Path, parca_sayfa: int) -> list[tuple[Path, int, int]]` — `(parça_yolu, ilk_sayfa, son_sayfa)` 1'den başlayan, kapsayıcı. Dosya adı `parca-01.pdf`… Zaten varsa yeniden üretmez.
  - `pdf_isleme.kes(pdf: Path, sayfa: int, kutu: list[float], cikti: Path, dpi: int = 200, pay: float = 2.0) -> Path` — `kutu` = `[x0, y0, x1, y1]` sayfanın yüzdesi (0–100, sol üst köken). Her yana `pay` yüzde eklenir, sınırlara kırpılır. Geçersiz kutu (eksik eleman, sayı değil, x0≥x1 veya y0≥y1 sonrası alan 0) → tam sayfa. Geçersiz sayfa → `ValueError`.
  - `pdf_isleme.tam_sayfa(pdf: Path, sayfa: int, cikti: Path, dpi: int = 120) -> Path`

- [ ] **Step 1: `pip install pymupdf`; testleri yaz** (testte `fitz` ile 45 sayfalık PDF üret, 3. sayfaya sağ alta dolu bir dikdörtgen çiz)

```python
def test_parcala(self):
    p = pdf_isleme.parcala(self.pdf, self.d, 20)
    self.assertEqual([(a, b) for _, a, b in p], [(1, 20), (21, 40), (41, 45)])
def test_kes_boyut(self):
    c = pdf_isleme.kes(self.pdf, 3, [50, 50, 100, 100], self.d / "k.png")
    pix = fitz.Pixmap(str(c)); w, h = pdf_sayfa_px(200)
    self.assertAlmostEqual(pix.width / w, 0.52, delta=0.02)   # %50 + %2 pay (sağ kenarda kırpılır)
def test_bozuk_kutu(self):
    for kutu in [[90, 10, 10, 90], [-50, 0, 300, 100], [], ["a", 1, 2, 3]]:
        c = pdf_isleme.kes(self.pdf, 3, kutu, self.d / "b.png")
        self.assertTrue(c.exists())
    with self.assertRaises(ValueError):
        pdf_isleme.kes(self.pdf, 99, [0, 0, 10, 10], self.d / "x.png")
```

- [ ] **Step 2: FAIL gör** — `python -m unittest tests.test_pdf_isleme -v`
- [ ] **Step 3: Uygula** (`page.get_pixmap(dpi=..., clip=fitz.Rect(...))`; ters sıralı koordinatları `min/max` ile düzelt, sonra 0–100'e kırp; alan 0 ise tam sayfa)
- [ ] **Step 4: PASS gör, commit** — `feat: pdf parçalama ve görsel kesme`

---

### Task 4: Çevirme (PDF → metin + görseller), devam edilebilir

**Files:**
- Create: `ofis/cevirme.py`, `talimatlar/cevirici.md`, `talimatlar/cevirici.json`, `tests/test_cevirme.py`

**Interfaces:**
- Consumes: `claude_calistir.cagir`, `pdf_isleme.parcala/kes`, `dersler.oku/yaz`
- Produces:
  - `cevirme.cevir(ayar, kok: Path, ders: str, pdf_adi: str, parca_bitti: Callable[[int, Path], None]) -> None` — kaldığı parçadan sürer; her parça bitince `parca_bitti(parca_no, md_yolu)` çağrılır; `LimitDolu`'yu yukarı iletir.
  - Dosyalar (`<p>` = PDF adı uzantısız):
    - `metin/<p>/parca-NN.md` — metin; görseller `![açıklama](../../gorseller/<p>-s<sayfa>-<n>.png)` olarak
    - `metin/<p>/gorseller.json` — `[{"dosya", "sayfa", "tur": "formul"|"sekil", "aciklama", "parca"}]` (birikimli)
    - `metin/<p>/konular.json` — `{"<parça no>": ["konu adı", ...]}` (yalnızca `ders.json` konu adları; liste dışı adlar atılır)
    - `metin/<p>/durum.json` — `{"tamam": [1, 2], "toplam": 8}`
- Şema `talimatlar/cevirici.json`: `{"markdown": str, "gorseller": [{"yer_tutucu": "G1", "sayfa": int (parçadaki 1'den başlayan), "kutu": [4 sayı], "tur": "formul"|"sekil", "aciklama": str}], "konular": [str]}`
- İstem: parça yolu (`pdf/<p>-parcalar/parca-NN.pdf`, göreli), ders konu listesi, "metinde formül/şekil yerine `[[G1]]` yer tutucusu koy". Sunucu yer tutucuyu kesilmiş görüntü bağlantısıyla değiştirir; şemada olmayan yer tutucu metinden silinir.
- `talimatlar/cevirici.md`: Türkçe, kısa: Read ile parçayı oku; tüm metni Markdown'a çevir; **her formül ve önemli şekil/grafik/çizim** için yer tutucu ve yüzde kutu ver; formülü LaTeX/yazı olarak tekrar etme; konuları yalnızca verilen listeden seç.

- [ ] **Step 1: Testleri yaz** (Task 3'teki gibi 45 sayfalık PDF; sahte_claude `ok` cevabı: 1 görsel `G1` sayfa 2, `konular: ["Limit", "Uydurma"]`)

```python
def test_uc_parca_cevrilir(self):
    cevirme.cevir(ayar, kok, "Math 1", "notlar", geri)
    self.assertEqual(sorted(geri_cagrilan), [1, 2, 3])
    md = (ders/"metin/notlar/parca-02.md").read_text("utf-8")
    self.assertIn("gorseller/notlar-s22-1.png", md)            # parça 2'nin 2. sayfası = 22
    self.assertTrue((ders/"gorseller/notlar-s22-1.png").exists())
    self.assertEqual(json.loads((ders/"metin/notlar/konular.json").read_text())["2"], ["Limit"])
def test_limitte_durur_ve_devam_eder(self):
    # sahte_claude 2. çağrıda limit (SAHTE_CLAUDE_LIMIT_SONRA=1 → ilk 1 çağrıdan sonra limit)
    with self.assertRaises(LimitDolu): cevirme.cevir(...)
    self.assertEqual(durum["tamam"], [1])
    # limit kaldırılır, tekrar çağrılır → sadece 2 ve 3 için claude çağrılır
def test_yeniden_baslatmada_devam(self):
    # durum.json {"tamam":[1,2]} ile başla → tek çağrı (parça 3)
```

- [ ] **Step 2: FAIL gör** — `python -m unittest tests.test_cevirme -v`
- [ ] **Step 3: Uygula** (`sahte_claude.py`'ye `SAHTE_CLAUDE_LIMIT_SONRA` sayacını ekle; sayaç dosyası `SAHTE_CLAUDE_KAYIT` satır sayısından okunur). Her parçadan sonra `durum.json` atomik yazılır.
- [ ] **Step 4: PASS gör, commit** — `feat: pdf çevirme`

---

### Task 5: Yapay zekâ asistanları

**Files:**
- Create: `ofis/asistanlar.py`, `talimatlar/{ozetci,formulcu,arastirmaci,sinavci,soru_cevap}.{md,json}`, `tests/test_asistanlar.py`

**Interfaces:**
- Consumes: `claude_calistir.cagir`, `dersler.oku/yaz`, Task 4 dosyaları
- Produces (hepsi `(ayar, kok, ders, ...)` alır; `LimitDolu` yukarı iletilir):
  - `asistanlar.ozetle(ayar, kok, ders, pdf_adi, parca_no) -> None` → `ozet/<p>.md`'ye `## Parça NN` başlığıyla ekler. Şema `{"ozet_md": str}`; önemli noktalar `> ⭐ ` ile başlayan satır. Talimat: ilgili görsellerin Markdown bağlantılarını özette aynen kullan.
  - `asistanlar.formul_cikar(ayar, kok, ders, pdf_adi, parca_no) -> None` → istemde o parçanın `tur=="formul"` görsel listesi. Şema `{"formuller": [{"dosya": str, "ad": str, "anlam": str, "ne_zaman": str, "soru_tipi": str}]}`. Sunucu `formuller/<p>.md`'ye her formül için `![ad](../gorseller/<dosya>)` + üç açıklama yazar; listede olmayan `dosya` atılır.
  - `asistanlar.soru_ara(ayar, kok, ders, konular: list[str]) -> None` → model `haiku`, araçlar `Read WebSearch WebFetch`. Şema `{"sorular": [{"metin": str, "zorluk": "kolay"|"orta"|"zor", "kaynak": str|null, "konu": str}]}`. `sorular/<YYYY-MM-DD-HHMM>.json`'a yazılır. `kaynak` `http` ile başlamıyorsa `null` yapılır.
  - `asistanlar.sinav(ayar, kok, ders, mesaj: str, konular: list[str] | None) -> dict` — `konular` verilirse yeni oturum (eski `sohbetler["sinavci"]` silinir), değilse `--resume`. İstem ilk turda: seçilen konuları kapsayan `metin/*/parca-*.md` dosya yolları (konular.json'dan) + son `sorular/*.json`. Şema `{"mesaj": str, "bitti": bool, "sonuc": {"dogru": int, "yanlis": int, "eksik_konular": [str]} | null}`. `bitti` ise `sinavlar/<tarih>.json` yazılır, `eksik_konular` ders konu listesiyle filtrelenip `hesap.tekrar_ekle` çağrılır, oturum silinir. Döner: şema sonucu.
  - `asistanlar.soru_sor(ayar, kok, ders, mesaj: str) -> dict` — `sohbetler["soru_cevap"]` ile süren oturum; ilk turda tüm `konular.json` özeti istemde, Claude ilgili parçaları kendisi Read ile açar. Şema `{"mesaj": str}`.
  - Oturum kimlikleri `ders.json["sohbetler"]`'de, **ders başına ayrı**.

- [ ] **Step 1: Testleri yaz** (sahte_claude cevapları her test için ayarlanır)

```python
def test_ozet_eklenir(self): ...              # iki parça → ozet/notlar.md içinde "## Parça 01" ve "## Parça 02"
def test_formul_goruntu(self):                # çıktıda "![F=ma](../gorseller/notlar-s3-1.png)"; listede olmayan dosya yok
def test_soru_kaynak_temizlenir(self):        # kaynak "uydurma" → null; "https://x" korunur; model argümanı "haiku"
def test_sinav_ders_basina_oturum(self):
    asistanlar.sinav(ayar, kok, "CS", "başla", ["Döngüler"])
    asistanlar.sinav(ayar, kok, "Math 1", "başla", ["Limit"])
    asistanlar.sinav(ayar, kok, "CS", "cevabım B", None)
    # son çağrıda "--resume", "s-CS" kayıtta; Math 1 oturumu "s-Math 1"
def test_sinav_bitince_tekrar(self):          # bitti=True, eksik ["Limit","Yok"] → tekrar.json'da yalnız "Limit", 3 tarih
```

- [ ] **Step 2: FAIL gör** — `python -m unittest tests.test_asistanlar -v`
- [ ] **Step 3: Uygula + talimat metinlerini yaz** (Türkçe, her biri ≤ 25 satır; Sınavcı: kolay→orta→zor, tek tek sor, cevabı değerlendir, 6–9 soru sonra `bitti`)
- [ ] **Step 4: PASS gör, commit** — `feat: yapay zekâ asistanları`

---

### Task 6: Hesap asistanları (süre, analiz, tekrar, notlar)

**Files:**
- Create: `ofis/hesap.py`, `tests/test_hesap.py`

**Interfaces:**
- Consumes: `dersler.oku/yaz`, `dersler.listele`
- Produces (`simdi: datetime` parametresi testte sabit zaman için):
  - `hesap.sure_basla(kok, ders, simdi) -> None` — **tüm derslerdeki** açık oturumları `simdi` ile kapatır, sonra bu derse yeni oturum açar.
  - `hesap.sure_dur(kok, ders, simdi) -> None`
  - `hesap.sure_analizi(kok, ders, simdi) -> dict` — `{"toplam_saat", "bitti", "kalan", "kalan_gun", "gunluk_ort_saat", "gereken_saat": float|None, "kapasite_saat", "yetisir": bool|None, "yorum": str}`. Açık oturum `simdi`'ye kadar sayılır.
  - `hesap.tekrar_ekle(kok, ders, konular: list[str], bugun: date) -> None` → `tekrar.json`: `[{"konu", "tarih": "YYYY-MM-DD", "yapildi": false}]`, aynı konu+tarih tekrar eklenmez.
  - `hesap.bugun_tekrar(kok, ders, bugun) -> list[dict]` — tarihi ≤ bugün ve yapılmamış
  - `hesap.tekrar_yapildi(kok, ders, konu, bugun) -> None`
  - `hesap.not_ekle(kok, ders, metin: str, simdi) -> None` → `notlar.md`'ye `- [YYYY-MM-DD HH:MM] metin`; `hesap.notlar(kok, ders) -> list[str]`

Süre analizi:
```
hiz = bitti / toplam_saat                       (bitti == 0 veya toplam_saat == 0 → gereken_saat=None, yetisir=None, yorum "Henüz tahmin için veri yok: bir konuyu bitti olarak işaretle.")
gereken_saat = kalan / hiz
gunluk_ort_saat = son 7 günde (simdi dahil) çalışılan saat / 7
kalan_gun = max(0, (sinav_tarihi - simdi.date()).days)
kapasite_saat = kalan_gun * gunluk_ort_saat
yetisir = gereken_saat <= kapasite_saat
yorum: yetisir → "Bu hızla yetişiyorsun (~{gereken:.0f} saat gerekli, ~{kapasite:.0f} saat var)."
       değil → "Bu hızla yetişmiyor: günde ~{(gereken/kalan_gun):.1f} saat çalışman gerekiyor." (kalan_gun 0 → "Sınav bugün/geçti.")
```

- [ ] **Step 1: Testleri yaz**

```python
def test_ders_degisince_sure(self):
    hesap.sure_basla(kok, "CS", t(10, 0)); hesap.sure_basla(kok, "Math 1", t(11, 0))
    self.assertEqual(oturumlar("CS"), [{"basla": "...T10:00", "bitis": "...T11:00"}])
    self.assertIsNone(oturumlar("Math 1")[0]["bitis"])
def test_acik_oturum_kapanir(self): ...      # açık oturum varken (sunucu çöktü) sure_basla → eski kapanır, süre kaybolmaz
def test_analiz(self):
    # 10 konu, 2 bitti, toplam 4 saat (son 7 günde), sınav 30 gün sonra
    # hiz 0.5 konu/saat → gereken 16; günlük ort 4/7; kapasite 30*4/7 ≈ 17.1 → yetisir True
def test_analiz_veri_yok(self): ...           # yetisir None
def test_tekrar(self):
    hesap.tekrar_ekle(kok, "CS", ["Döngüler"], date(2026, 11, 23))
    self.assertEqual([e["tarih"] for e in tekrar], ["2026-11-24", "2026-11-26", "2026-11-30"])
    self.assertEqual(len(hesap.bugun_tekrar(kok, "CS", date(2026, 11, 26))), 2)
```

- [ ] **Step 2: FAIL gör** — `python -m unittest tests.test_hesap -v`
- [ ] **Step 3: Uygula**
- [ ] **Step 4: PASS gör, commit** — `feat: süre, analiz, tekrar, notlar`

---

### Task 7: HTTP sunucu ve başlatıcı

**Files:**
- Create: `ofis/sunucu.py`, `tests/test_sunucu.py`
- Modify: `baslat.ps1`

**Interfaces:**
- Consumes: Task 1–6 hepsi
- Produces (JSON gövde, UTF-8; ders adı URL'de `quote` edilmiş):

| Uç | Gövde | Etki |
|---|---|---|
| `GET /` ve `/web/...` | — | statik dosya (`web/` dışına çıkış yok) |
| `GET /api/dersler` | — | `["CS", "Math 1"]` |
| `POST /api/dersler` | `{ad, sinav_tarihi, konular}` | ders oluştur |
| `GET /api/ders/<ad>` | — | `ders.json` + `{"pdfler": [{ad, tamam, toplam}], "bugun_tekrar": [...], "analiz": {...}, "notlar": [...]}` |
| `POST /api/ders/<ad>/pdf` | ham PDF, başlık `X-Dosya-Adi` (URL-kodlu) | `pdf/<ad>` kaydet, çeviri işini kuyruğa ekle; her parça bitince Özetçi + Formülcü işi kuyruğa |
| `POST /api/ders/<ad>/devam` | — | `durum.json`'u tamamlanmamış her PDF için çeviriyi yeniden kuyruğa ekle |
| `POST /api/ders/<ad>/soru-bul` | `{konular}` | araştırmacı işi |
| `POST /api/ders/<ad>/sinav` | `{mesaj, konular?}` | senkron, `asistanlar.sinav` sonucu (durum olayları yine yayınlanır) |
| `POST /api/ders/<ad>/soru` | `{mesaj}` | senkron, `asistanlar.soru_sor` sonucu |
| `POST /api/ders/<ad>/not` | `{metin}` | not ekle |
| `POST /api/ders/<ad>/konu` | `{konu, bitti}` | konu işaretle |
| `POST /api/ders/<ad>/tekrar` | `{konu}` | tekrar yapıldı |
| `POST /api/ders/<ad>/sure` | `{olay: "basla"|"dur"}` | süre |
| `GET /api/ders/<ad>/dosya/<göreli>` | — | ders klasöründen dosya (`guvenli_dosya`) |
| `GET /api/olaylar` | — | SSE (`text/event-stream`), her olay `data: <json>\n\n`, 15 sn'de bir `: ping` |

Kurallar: `ThreadingHTTPServer(("127.0.0.1", port))`; `GecersizAd` → 400; bilinmeyen ders → 404; PDF en fazla 200 MB, `%PDF` ile başlamıyorsa 400; senkron uçlarda `LimitDolu` → 429 `{"hata": "limit"}`. `X-Dosya-Adi` yalnızca taban adı alınır (`Path(...).name`) ve ad kuralından geçer.

`baslat.ps1` (Task 0 sonrası yapıldı, masaüstü kısayolu "Ders Ofisi" bunu çalıştırır): sunucu kapalıysa gizli `python -m ofis.sunucu` başlatır, ofisi Chrome `--app` penceresinde açar, ders-ofisi klasöründe Windows Terminal içinde Claude Code açar. Bu task'ta yalnızca başa `python -c "import fitz"` yoksa `pip install pymupdf` eklenir. Claude bulunamazsa sunucu açılışta uyarı basar ve `/api/dersler` yanıtına `"uyari"` ekler (ön yüz gösterir).

- [ ] **Step 1: Testleri yaz** (sunucuyu geçici kökte rastgele portta thread'de başlat, `urllib.request` ile)

```python
def test_ders_akisi(self): ...        # POST ders → GET listede; POST not → GET notlarda
def test_yol_kacisi(self):
    for yol in ["/api/ders/..%2F..%2Fofis/dosya/x", "/api/ders/CS/dosya/..%2F..%2Fayarlar.json", "/web/..%2Fayarlar.json"]:
        self.assertIn(durum(yol), (400, 404))
def test_pdf_degil(self): ...         # "merhaba" gövdesi → 400
def test_pdf_yukle_olaylar(self):     # sahte_claude ok; SSE'den ("cevirici","calisiyor") ve ("ozetci","bitti") olaylarını 10 sn içinde gör
def test_limit_429(self): ...         # MOD=limit, /soru → 429
```

- [ ] **Step 2: FAIL gör** — `python -m unittest tests.test_sunucu -v`
- [ ] **Step 3: Uygula**
- [ ] **Step 4: PASS gör; tüm testler** — `python -m unittest discover -s tests -v` → hepsi OK
- [ ] **Step 5: Commit** — `feat: http sunucu ve başlatıcı`

---

### Task 8: 3D NYC ofis ve paneller

**Files:**
- Create: `web/index.html`, `web/stil.css`, `web/ofis.js`, `web/panel.js`, `web/vendor/three.module.js`, `web/vendor/OrbitControls.js`, `web/vendor/marked.esm.js`

**Interfaces:**
- Consumes: Task 7 uçları ve SSE olay biçimi
- Produces: `ofis.js` → `ofisKur(kap: HTMLElement, masaTiklandi: (asistan: string) => void)` döner `{durumAyarla(asistan, durum, dersEtiketi | null)}`; asistan kimlikleri: `ozetci, formulcu, sure, arastirmaci, not, sinavci, tekrar, soru_cevap, mola` (sunucu olaylarında `cevirici` → masada `ozetci` ile birlikte "okuyor" gösterilir).

Kararlar:
- Vendor: `npm pack three marked` ile indirilen paketlerden `build/three.module.js`, `examples/jsm/controls/OrbitControls.js`, `lib/marked.esm.js` kopyalanır; import map ile yüklenir; internetten yükleme yok.
- Sahne (Task 0'da kuruldu; bu task yalnızca panelleri ve gerçek SSE'yi bağlar): tek açık plan kat, büyük cam duvar; dışarıda rastgele yükseklikte 150–250 kutu bina, pencereleri `InstancedMesh` ile yanan küçük dörtgenler; ışık `gunes.js` ile yerel saate göre. 3×3 masa ızgarası, her masada low-poly karakter (gövde silindir + kafa küre, asistana özel renk), monitör ve ad etiketi (sprite). `OrbitControls`: dönme açık, zoom 6–25 birim, kamera zemin altına inemez, pan kapalı.
- Durum gösterimi: `calisiyor` → monitör parlar + başın üstünde zıplayan `…` sprite; `bitti` → `✅` sprite 1 dk; `bekliyor` → `💤`; `hata` → `⚠️`; başka ders için ise sprite altında ders adı.
- Performans: `renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5))`, gölge yok, sadece hareket/olay varken render (`requestAnimationFrame` sprite animasyonu sürerken).
- Raycaster ile masa/karakter tıklaması → sağdan kayan panel.
- Üst çubuk: ders seçici (+ yeni ders formu: ad, sınav tarihi, konular satır satır), PDF bırakma alanı (yükleme ilerlemesi), sayaç (başlat/duraklat; ders değişince `sure: basla` yeni derse), "Devam" düğmesi yalnızca `bekliyor` varken.
- Paneller (`panel.js`, Markdown `marked` ile; görsel yolları `/api/ders/<ad>/dosya/...`'ya çevrilir; görsele tıkla → tam sayfa PNG; formül görselleri yazıya çevrilmez):
  - Özetçi: PDF seçimi + `ozet/<p>.md`; `> ⭐` satırları vurgulu.
  - Formülcü: `formuller/<p>.md`.
  - Süre: analiz değerleri + son 7 gün çubuk grafiği (saf CSS) + konu listesi onay kutuları (`/konu`).
  - Araştırmacı: konu seç + "Soru bul"; sorular zorluğa göre gruplu, kaynak bağlantısı ya da "asistan yazdı" etiketi.
  - Not: metin alanı + liste.
  - Sınavcı: konu seç + "Beni test et" → sohbet; bitince sonuç ve eksik konular.
  - Tekrar: bugünkü liste + "yaptım".
  - Soru-cevap: sohbet.
  - Mola: 50/10 dk; sayaç çalışırken sürer, süre dolunca masada `☕` ve tarayıcı bildirimi (izin varsa) / sesli değil.
- 429 yanıtında panelde "Claude kullanım limiti doldu, limit açılınca tekrar dene."

- [ ] **Step 1: Vendor dosyalarını indir ve kopyala; `index.html` boş sahneyle açılıyor mu** — `python -m ofis.sunucu`, tarayıcıda konsolda hata yok
- [ ] **Step 2: Sahne + masalar + tıklama + durum sprite'ları** — SSE'yi elle tetiklemek için geçici `?demo=1` parametresi her masayı sırayla durumlardan geçirir (kalabilir, zararsız)
- [ ] **Step 3: Üst çubuk + dokuz panel**
- [ ] **Step 4: Elle doğrulama (sahte_claude ile: `ayarlar.json`'da `claude_komutu` geçici olarak sahteye):**
  - Ders oluştur → 45 sayfalık test PDF'i bırak → Özetçi/Formülcü masalarında `…` sonra `✅`; Formülcü panelinde formül **görüntü** olarak görünüyor
  - Ders değiştir, iş sürerken → masada eski ders etiketi; çıktı eski derste
  - Sayaç başlat, ders değiştir → Süre panelinde iki dersin süreleri ayrı
  - Pencere 1366×768'de ve `chrome://` performans panelinde boştayken CPU ~0
- [ ] **Step 5: Commit** — `feat: 3d ofis ve paneller`

---

### Task 9: Gerçek Claude ile uçtan uca deneme

**Files:**
- Modify: `ayarlar.json` (gerçek `claude_komutu`), gerekirse `ofis/claude_calistir.py` (limit mesajı deseni), `talimatlar/*.md`

- [ ] **Step 1: Tek çağrı doğrulaması** — `Dersler/Deneme` içinde elle: `claude.exe -p "parca-01.pdf dosyasını oku" --output-format json --model sonnet --allowedTools Read --json-schema <cevirici şeması>`; çıktıda `structured_output` alanı var mı, adı farklıysa `cagir`'ı düzelt
- [ ] **Step 2: Limit mesajını yakala** — gerçek limit hatası görülürse `result` metnini kaydet ve deseni teste ekle; görülmezse bu adımı "doğrulanmadı" diye not düş
- [ ] **Step 3: 20 sayfalık gerçek bir ders notu PDF'iyle** uçtan uca: kesilen formül görüntülerinin doğru yeri tuttuğunu gözle kontrol et (10 formülden kaçı doğru kesildi?). %70 altındaysa `cevirici.md`'ye kutu talimatını netleştir veya `pay`'ı artır
- [ ] **Step 4: Ölçüm** — 20 sayfa için süre ve `/usage` ile harcanan limit yüzdesi; 150 sayfaya oranla kullanıcıya bildir
- [ ] **Step 5: Commit** — `chore: gerçek claude ile ayar`
