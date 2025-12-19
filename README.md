# 🦅 MERGEN - AI-Powered Cyber Operations Assistant

![Mergen Banner](https://via.placeholder.com/1200x300/121212/00ff9d?text=MERGEN+-+CYBER+OPERATIONS+CENTER)

> **"Terminalinizin İkinci Beyni."**

**Mergen**, siber güvenlik uzmanları, sızma testi uzmanları (pentesters) ve sistem yöneticileri için tasarlanmış, **Yapay Zeka (Google Gemini)** destekli, **OpSec (Operasyonel Güvenlik)** odaklı bir terminal asistanı ve komut yönetim merkezidir.

Sadece komutlarınızı saklamakla kalmaz; onları analiz eder, kullanım alışkanlıklarınızdan profesyonel yetkinlik profilinizi çıkarır ve terminal geçmişinizi (history) arka planda otomatik olarak öğrenir.

---

## ⚡ Özellikler

### 🧠 1. Yapay Zeka Entegrasyonu (Intelligence)
* **Doğal Dil İşleme:** "80. portu kullanan servisi nasıl bulurum?" gibi soruları saniyeler içinde çalıştırılabilir, parametreleri optimize edilmiş Linux komutlarına dönüştürür.
* **Otomatik Ayrıştırma:** AI cevabından saf komutu, teknik açıklamayı ve kategoriyi (Network, Docker, System vb.) otomatik olarak ayıklar ve veritabanına işler.
* **Kariyer Koçu (Profilim):** Komut geçmişinizi analiz ederek siber güvenlik yetkinlik profilinizi, güçlü/zayıf yönlerinizi ve odaklandığınız alanları (Red Team, Blue Team vb.) raporlar.

### 🛡️ 2. Paranoyak Güvenlik (The Sanitizer)
* **Veri Maskeleme:** AI servisine gönderilen tüm verilerde IP adresleri, E-postalar, Şifreler ve API Anahtarları otomatik olarak `<GIZLI_VERI>` etiketleriyle maskelenir (Regex Sanitization).
* **Yerel Veritabanı:** Tüm veriler `~/.mergen_data.db` içinde şifrelenmemiş (ancak tamamen yerel) SQLite veritabanında tutulur. Dışarıya (Google API hariç) veri sızdırılmaz.
* **Kill Switch (Veri İmhası):** Acil durumlar için tek tıkla tüm veritabanını, geçmişi ve analizleri kalıcı olarak imha etme (Factory Reset) özelliği.

### 👁️ 3. Silent Observer (Otomatik Takip)
* **Shell Hook Entegrasyonu:** Zsh, Bash ve Fish kabuklarına entegre olur. Terminalde yazdığınız her komutu (Mergen kapalıyken bile) arka planda yakalar ve veritabanına "Shell Geçmişi" olarak işler.
* **Frekans Analizi:** Hangi komutu kaç kere kullandığınızı takip eder ve "Sık Kullanılanlar" listenizi otomatik oluşturur.

### 💻 4. Hibrit Arayüz (CLI & GUI)
* **Terminal-First:** Hız için doğrudan terminalden sorgu yapın: `mergen "sorgu"`
* **Cyberpunk GUI:** Detaylı analiz, düzenleme, filtreleme, yedekleme ve görselleştirme için PyQt6 tabanlı, karanlık temalı modern arayüz.

---

## 🚀 Kurulum

Mergen, kurulumu ve sistem entegrasyonunu otomatize eden akıllı bir sihirbaz ile gelir.

### Gereksinimler
* Python 3.8+
* Linux Ortamı (Kali Linux, Ubuntu, Debian, Arch, Fedora vb.)
* Google Gemini API Anahtarı ([Buradan Ücretsiz Alın](https://aistudio.google.com/app/apikey))

### Hızlı Kurulum

1.  **Depoyu Klonlayın:**
    ```bash
    git clone https://github.com/mes41c/linux-mergen.git
    cd mergen
    ```

2.  **Kurulum Sihirbazını Başlatın:**
    ```bash
    python3 mergen.py --setup
    ```
    *Bu komut:*
    * *Gerekli kütüphaneleri (google-genai, PyQt6) kurar.*
    * *Veritabanını oluşturur.*
    * *Kullandığınız Shell'i (Zsh/Bash) algılar ve otomatik takip kancasını ekler.*
    * *API Anahtarınızı sorar ve güvenli bir şekilde kaydeder.*
    * *`mergen` komutunu sisteme (symlink) ekler.*

3.  **Terminali Yeniden Başlatın:**
    Değişikliklerin aktif olması için terminali kapatıp açın.

---

## 📖 Kullanım

### 1. Terminalden Hızlı Sorgu (CLI)
Bir komuta ihtiyacınız olduğunda arayüzü açmanıza gerek yok:

```bash
mergen "tüm docker containerları sil ama volume'ler kalsın"
**Çıktı:** Komutu, risk analizini ve açıklamayı terminale renkli olarak basar ve veritabanına kaydeder.

### 2. Grafik Arayüz (GUI)

Veritabanını yönetmek, düzenlemek ve analizler için:

```bash
mergen --ui
```

Canlı Arama: Regex destekli anlık filtreleme.

Düzenleme: Komutlara veya açıklamalara çift tıklayarak içeriği değiştirin.

Sıralama: ID, Kullanım Sayısı veya Tarih başlıklarına tıklayarak sıralama yapın.

Profilim: "🧠 Profilim" butonuna tıklayarak yapay zekanın sizi analiz etmesini sağlayın.

Veri Yönetimi: Sağ üstteki butonlarla verilerinizi JSON formatında yedekleyin veya geri yükleyin.

3. Otomatik Takip

Kurulumdan sonra hiçbir şey yapmanıza gerek yok. Terminalde çalıştırdığınız araçlar (nmap, sqlmap, burpsuite, ssh vb.) otomatik olarak yakalanır ve "Shell Geçmişi" kategorisine kaydedilir.

🛠️ Teknoloji Yığını

    Core: Python 3

    Database: SQLite3 (Otomatik Migrasyonlu)

    AI Model: Google Gemini 3 Flash

    GUI: PyQt6 (Qt Framework)

    Shell Integration: Zsh / Bash / Fish Hooks (Native implementation)

⚠️ Yasal Uyarı

Bu araç, siber güvenlik profesyonellerine ve öğrencilerine yardımcı olmak, operasyonel verimliliği artırmak amacıyla geliştirilmiştir. Oluşturulan komutların (özellikle sistem dosyalarını etkileyenlerin) çalıştırılmadan önce kontrol edilmesi kullanıcının sorumluluğundadır. Geliştirici, aracın kullanımından doğabilecek veri kayıplarından sorumlu değildir.

Lisans: MIT License
