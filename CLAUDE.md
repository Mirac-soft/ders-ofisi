# Ders Ofisi

Kullanıcının kişisel ders çalışma ofisi: 3D NYC ofisinde 9 yapay zekâ asistanı. Kullanıcıyla Türkçe konuş, kısa ve pratik ol.

- Tasarım: `docs/tasarim.md` — Plan ve ilerleme: `docs/superpowers/plans/2026-11-23-ders-ofisi.md`, `.superpowers/sdd/2026-11-23-ders-ofisi/progress.md`
- Bu pencere, masaüstündeki "Ders Ofisi" kısayoluyla ofisle birlikte açılır. Görevi: kullanıcının ofisle ilgili isteklerini yapmak (ayar, düzeltme, yeni özellik, "bugün ne çalıştım" gibi sorular).
- Asistan işleri bu pencerede değil, sunucunun başlattığı arka plan `claude -p` süreçlerinde çalışır.
- Ders verileri `Dersler/<ders>/` altında; kullanıcı istemeden silme veya üzerine yazma.
- Işık/saat dilimi: `web/gunes.js` içindeki `KONUM` (şu an Europe/Rome).
- Testler: `python -m unittest discover -s tests -v` ve `node tests/gunes.test.mjs`.
