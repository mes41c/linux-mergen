🦅 MERGEN: The Cyberdeck Command Center

    "Unutulan her komut, kaybedilen zamandır. Mergen, siber güvenlik uzmanları için tasarlanmış merkeziyetsiz, yapay zeka destekli ikinci beyninizdir."

Mergen, siber güvenlik uzmanları ve sistem yöneticileri için geliştirilmiş; CLI, GUI ve TUI arayüzlerine sahip, uçtan uca şifreli senkronizasyon destekleyen yeni nesil bir komut yönetim sistemidir.

Karmaşık nmap, ffmpeg veya kubectl komutlarını bir kez yazın, Mergen maskelesin, saklasın ve tüm cihazlarınıza (PC & Mobil) ışınlasın.
🌟 Öne Çıkan Özellikler
🛡️ Paranoyak Güvenlik (OpSec First)

    Otomatik Maskeleme: Komutların içindeki Şifreler, API Anahtarları ve IP Adresleri (IPv4) veritabanına kaydedilmeden önce otomatik olarak <GIZLI_KEY_1> veya <GIZLI_IP_0> şeklinde maskelenir.

    XSS & Injection Koruması: Tüm girdiler HTML Escape işleminden geçer ve SQL parametreleri ile izole edilir.

    Gizlilik Modu: Tek tıkla AI analizini kapatarak "Air-Gapped" mantığında çalışabilirsiniz.

🧠 Yerel + Yapay Zeka Hibrit Yapı

    Offline First: İnternet olmasa bile veritabanınız yereldir, anında çalışır.

    Gemini AI Entegrasyonu: Komutlarınızın ne işe yaradığını analiz eder veya doğal dille sorduğunuz soruları ("En sessiz nmap taraması nedir?") çalıştırılabilir komutlara çevirir.

📱 Decentralized Mobile Ops (Termux + Syncthing)

    Merkezi sunucu yok. Bulut yok.

    Syncthing ile P2P şifreli veri eşitleme.

    Tailscale ile dünyanın her yerinden evdeki makinenize güvenli tünel.

    Android (Termux) üzerinde çalışan TUI (Terminal User Interface) ile cebinizdeki telefonu bir Cyberdeck'e dönüştürün.

🏗️ Mimari

Mergen, "Decentralized Hybrid Cloud" mimarisini kullanır:
Kod snippet'i

graph TD
    A[KALI LINUX (Ana Üs)] -- Syncthing (P2P Sync) --> B((Veri Havuzu));
    C[ANDROID / TERMUX (Saha)] -- Syncthing (P2P Sync) --> B;
    
    A -- Tailscale (VPN) --> C;
    
    subgraph "Mergen Core"
    D[SQLite DB]
    E[Python Backend]
    F[AI Engine (Optional)]
    end

🚀 Kurulum
1. Linux (Kali/Ubuntu/Debian) - Ana Makine
Bash

# Repoyu klonlayın
git clone https://github.com/mes41c/mergen.git
cd mergen

# Kurulum sihirbazını başlatın
python3 mergen.py --setup

Sihirbaz gerekli kütüphaneleri (PyQt6, google-genai) kuracak ve mergen komutunu sisteminize ekleyecektir.
2. Android (Termux) - Mobil Operasyon

Mobil kurulum, Android'in güvenlik kısıtlamalarını aşmak için özel bir yöntem kullanır.

    Ön Hazırlık:

        Telefona Termux ve Syncthing uygulamalarını kurun.

        PC ve Telefon arasında Syncthing eşitlemesini yapın (Klasör: ~/Download/Mergen önerilir).

        mergen.py ve mergen.db dosyalarının telefona geldiğinden emin olun.

    Termux Ayarları:
    Bash

# Gerekli paketler
pkg update && pkg upgrade
pkg install python rust binutils build-essential clang

# AI Kütüphanesi (Derleme biraz sürebilir)
pip install google-genai

# Dosya izni ver
termux-setup-storage

Mergen Kurulumu (Wrapper):
Bash

    # Klasöre git (Syncthing yolunuz)
    cd /storage/emulated/0/Download/Mergen

    # Kurulumu başlat
    python mergen.py --setup

    # Android "noexec" kısıtlamasını aşmak için Wrapper oluştur
    # (Bu komutu tek seferde yapıştırın)
    echo 'python /storage/emulated/0/Download/Mergen/mergen.py "$@"' > $PREFIX/bin/mergen && chmod +x $PREFIX/bin/mergen

💻 Kullanım Kılavuzu
1. Grafik Arayüz (GUI) - Masaüstü
Bash

mergen --ui

    Dashboard: Tüm komutları filtreleyin, düzenleyin.

    Geçmiş Yükle: Sızma testi makinelerinizden .zsh_history veya .bash_history dosyalarını seçerek toplu analiz yapın.

    AI Analiz: "Profilim" butonu ile yetkinliklerinizi analiz ettirin.

2. Terminal Arayüzü (TUI) - Mobil & SSH
Bash

mergen --tui

    Fare gerektirmez. Klavye ile tam kontrol.

    Hacker estetiğine sahip renkli arayüz.

    / tuşu ile Regex destekli arama.

3. Hızlı Komut (CLI)
Bash

# Soru sor, komut al
mergen "bütün portları tara ama firewall'a takılma"

# History dosyasını terminalden yükle
mergen --import-history /path/to/.zsh_history

⚙️ Yapılandırma & Güvenlik

Ayarlar ~/.mergen_config.json dosyasında saklanır.

    API Key: Google Gemini API anahtarınız base64 tabanlı bir karmaşıklaştırma (obfuscation) ile saklanır.

    AI Toggle: GUI üzerindeki "🤖 AI" kutucuğunu kaldırarak tüm dış veri trafiğini kesebilirsiniz.

⚠️ Yasal Uyarı

Bu araç, siber güvenlik profesyonellerinin operasyonel verimliliğini artırmak için tasarlanmıştır. Elde edilen komutların yasa dışı amaçlarla kullanılmasından kullanıcı sorumludur.

<p align="center"> <sub>Developed by <b>MES</b> | "Code is Poetry, Security is Art."</sub> </p>
