# IDS2018 v3 — kontrollü geliştirme paketi

Başlangıç: `IDS2018_V3_Kaggle_Run_All.ipynb`. Kod notebook içine gömülüdür; ayrı repo yüklenmez.

Kaggle'da `solarmainframe/ids-intrusion-csv` veri kümesini Add Input ile ekleyin. GPU ve Internet açık olsun. Run All yapın. Veri yolu otomatik bulunur. Yalnız ilk GPU kullanılır.

Varsayılan matris: `group_ce` altında E-SNN, ANN, encoded ANN, RF, XGBoost, CatBoost × seed 42/43/44 (18 koşu); `group_weighted` altında E-SNN ve ANN × aynı seed'ler (6 koşu). T=12, en çok 35 epoch, eğitim cap'i 500.000. Ham CSV etiketleri değiştirilmez. Özellik grupları oturum değildir. Zamanlar doğrulanmış sayılmaz.

Önce 24 eğitimin tamamı, sonra değerlendirmeler çalışır. Model dosyası sabitken ham skor / önsel düzeltmesi / önsel+sıcaklık kalibrasyonu karşılaştırılır. Eşikler yalnız kalibrasyonla belirlenir. Bunlar önceden incelenen v2 testinden sonra tasarlandığından geliştirme deneyleridir; bağımsız doğrulama değildir.

Yeni özellikler: grup ve etiket-çelişkisi denetimi; dönüşüm sonrası çakışma sayımı; kararlı log-odds skoru; ayrı olasılık/eşik kalibrasyonu; CE ağırlık davranışı düzeltmesi; eğitim epoch'undan devam; küçük sonuç arşivi. `encoded_ann`, SNN ile aynı kodlayıcılardan gelen girdiyi ileri beslemeli ağla işler.

Dokuz saatlik yumuşak bütçe yalnız yeni işlem başlatmayı sınırlar. Hazırlama, eğitim veya değerlendirme bu süreyi aşabilir. Sabit Kaggle tamamlanma süresi garanti edilmez. Kesilen sinir ağı aynı kaynak ve ortamda son tamamlanan epoch'tan devam eder. Kesilen ağaç eğitimi yeniden başlar. Tamamlanan modeller atlanır.

**Devam:** Save Version ile tam Notebook Output saklanmalı. Sonraki oturuma bu v3 Notebook Output'u Add Input ile ekleyin ve aynı notebook'u Run All yapın. Geri yükleme yalnız aynı paket kimliğini kabul eder. v2 modeli veya v2 çıktı klasörü bu yeni deneyin yerine kullanılamaz.

**Paylaşılacak dosya:** `/kaggle/working/ids2018-v3/IDS2018_REVIEW_LIGHT.zip`. İçinde yalnız raporlar/metaveri vardır; checkpoint ve `.npy` yoktur. Tam Notebook Output devam etmek için saklanır, inceleme için indirilmez.

**Sınırlar:** CatBoost/XGBoost native-input hiperparametre araması, TabM, düzeltilmiş veri uyarlayıcısı, bağımsız dış doğrulama, çoklu GPU zamanlayıcı ve enerji ölçümü bu sürümde tamamlanmış değildir. Kaynak ve çalışma planındaki sınırlar makalede korunmalıdır. Başarılı yazılım testi, gerçek veride başarı artışı anlamına gelmez.

Komut satırı arayüzü: `python -m idsresearch --help`. Gerçek veri olmadan doğrulama: `python -m idsresearch smoke --out /tmp/ids-v3-smoke`. Çıktılar sentetiktir; makalede kullanılmaz.
