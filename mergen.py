#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MERGEN v6.6 - Stable TUI Fix
Özellikler: Curses Bottom-Right Crash Fix, SpecOps UI, Full Stabilite
"""

import sys
import os
import sqlite3
import argparse
import json
import subprocess
import curses
import curses.textpad
import re
import socket
import getpass
import html
import base64
from datetime import datetime

# --- RENKLİ TERMİNAL ---
class Renk:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# --- KONFİGÜRASYON ---
CONFIG_FILE = os.path.join(os.path.expanduser('~'), '.mergen_config.json')

# --- BASİT KRİPTO (Obfuscation) ---
def sifrele(txt):
    if not txt: return ""
    # Basit bir XOR benzeri karıştırma + Base64
    try:
        dummy = "MERGEN_SECURE_KEY_99"
        mixed = "".join([chr(ord(c) ^ ord(dummy[i % len(dummy)])) for i, c in enumerate(txt)])
        return base64.b64encode(mixed.encode()).decode()
    except: return txt

def coz(txt):
    if not txt: return ""
    try:
        dummy = "MERGEN_SECURE_KEY_99"
        raw = base64.b64decode(txt).decode()
        return "".join([chr(ord(c) ^ ord(dummy[i % len(dummy)])) for i, c in enumerate(raw)])
    except: return txt

def load_config():
    defaults = {"db_path": os.path.join(os.path.expanduser('~'), '.mergen_data.db'), "api_key": "", "ai_aktif": True}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f: 
                data = json.load(f)
                # Şifreli keyi çöz
                if data.get("api_key"): data["api_key"] = coz(data["api_key"])
                return {**defaults, **data}
        except: pass
    return defaults

def save_config(config):
    # Kaydederken kopya al ve şifrele
    to_save = config.copy()
    if to_save.get("api_key"): to_save["api_key"] = sifrele(to_save["api_key"])
    with open(CONFIG_FILE, 'w') as f: json.dump(to_save, f, indent=4)

AYARLAR = load_config()
os.environ["MERGEN_API_KEY"] = AYARLAR["api_key"]
SABIT_KATEGORILER = ["Shell Geçmişi", "Sistem", "Ağ", "Dosya", "Güvenlik", "Konteyner", "Veritabanı", "Git/VCS", "Kullanıcı", "Servis", "Diğer"]

# --- GUI KÜTÜPHANE KONTROLÜ ---
def check_libs():
    try: import google.genai
    except ImportError: return False
    return True

GUI_AVAILABLE = False
try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTableWidget, QTableWidgetItem, QTextEdit, QLabel, QHeaderView,
        QSplitter, QMessageBox, QLineEdit, QPushButton, QAbstractItemView,
        QMenu, QRadioButton, QButtonGroup, QFileDialog, QCheckBox, QProgressBar, QDialog
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QColor
    GUI_AVAILABLE = True
except ImportError: pass

if GUI_AVAILABLE:
    class SayisalItem(QTableWidgetItem):
        def __lt__(self, other):
            try: return float(self.text()) < float(other.text())
            except ValueError: return super().__lt__(other)

# --- MODÜLLER ---
class GuvenlikKalkan:
    def __init__(self):
        self.sayac = 0
        self.desenler = {
            # Key=Value şeklindeki hassas veriler (API Key, Password vb.)
            'HASSAS_KEY': r'(?i)((?:export\s+)?[\w]*(?:key|secret|token|password|passwd|auth)[\w]*)\s*=\s*(["\']?)([^"\s]+)\2',
            # IPv4 Adresleri (192.168.1.1 gibi)
            'IPV4': r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        }

    def maskele(self, metin: str) -> str:
        if not metin: return ""
        islenmis = metin
        
        # 1. Aşama: Key/Password Maskeleme
        while True:
            bulgu = re.search(self.desenler['HASSAS_KEY'], islenmis)
            if not bulgu: break
            tam, deg, _, val = bulgu.group(0), bulgu.group(1), bulgu.group(2), bulgu.group(3)
            if "GIZLI_" in val: break 
            islenmis = islenmis.replace(tam, f"{deg}=<GIZLI_KEY_{self.sayac}>")
            self.sayac += 1

        # 2. Aşama: IP Adresi Maskeleme
        # (Halihazırda maskelenmiş etiketleri bozmamak için kontrol ekliyoruz)
        ip_bulgular = re.findall(self.desenler['IPV4'], islenmis)
        for ip in ip_bulgular:
            # Maskeleme etiketlerinin içindeki sayıları IP sanmasın (örn: <GIZLI_0>)
            if "GIZLI" in islenmis and ip in islenmis.split("GIZLI")[1]: continue 
            
            # Localhost (127.0.0.1) bazen gerekli olabilir ama paranoyak modda onu da gizleyelim.
            # IP'yi maskele
            islenmis = islenmis.replace(ip, f"<GIZLI_IP_{self.sayac}>")
            self.sayac += 1
            
        return islenmis

class MergenVeritabani:
    def __init__(self):
        self.db_yolu = AYARLAR["db_path"]
        os.makedirs(os.path.dirname(self.db_yolu), exist_ok=True)
        self.conn = sqlite3.connect(self.db_yolu, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS komut_gecmisi (id INTEGER PRIMARY KEY AUTOINCREMENT, ham_komut TEXT UNIQUE, maskelenmis_komut TEXT, soru_ozeti TEXT, aciklama TEXT, kategori TEXT, favori INTEGER DEFAULT 0, kullanim_sayisi INTEGER DEFAULT 1, tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        self.cursor.execute("""CREATE TABLE IF NOT EXISTS profil_analizleri (id INTEGER PRIMARY KEY AUTOINCREMENT, analiz_raporu TEXT, son_islenen_komut_id INTEGER, tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        cols = {"favori": "INTEGER DEFAULT 0", "kullanim_sayisi": "INTEGER DEFAULT 1", "kategori": "TEXT DEFAULT 'Diğer'"}
        self.cursor.execute("PRAGMA table_info(komut_gecmisi)")
        ex_cols = [row[1] for row in self.cursor.fetchall()]
        for c, d in cols.items():
            if c not in ex_cols: 
                try: self.cursor.execute(f"ALTER TABLE komut_gecmisi ADD COLUMN {c} {d}")
                except: pass
        try: self.cursor.execute("UPDATE komut_gecmisi SET kategori = 'Shell Geçmişi' WHERE kategori = 'History'"); self.conn.commit()
        except: pass
        self.conn.commit()

    def komut_ekle(self, ham, maskeli, soru, aciklama, kategori="Diğer", favori=0):
        try:
            self.cursor.execute("SELECT id, kullanim_sayisi FROM komut_gecmisi WHERE ham_komut = ?", (ham,))
            mevcut = self.cursor.fetchone()
            if mevcut: self.cursor.execute("UPDATE komut_gecmisi SET kullanim_sayisi = ?, tarih = CURRENT_TIMESTAMP WHERE id = ?", (mevcut[1] + 1, mevcut[0]))
            else: self.cursor.execute("INSERT INTO komut_gecmisi (ham_komut, maskelenmis_komut, soru_ozeti, aciklama, kategori, favori, kullanim_sayisi) VALUES (?, ?, ?, ?, ?, ?, ?)", (ham, maskeli, soru, aciklama, kategori, favori, 1))
            self.conn.commit()
        except: pass

    def getir(self, filtre="", kat="Tümü", fav=False, en_cok=False):
        q = "SELECT id, maskelenmis_komut, soru_ozeti, kategori, tarih, aciklama, ham_komut, favori, kullanim_sayisi FROM komut_gecmisi WHERE 1=1"
        p = []
        if fav: q += " AND favori = 1"
        if kat != "Tümü": q += " AND kategori = ?"; p.append(kat)
        if filtre: q += " AND (maskelenmis_komut LIKE ? OR soru_ozeti LIKE ? OR aciklama LIKE ?)"; p.extend([f"%{filtre}%"]*3)
        q += " ORDER BY kullanim_sayisi DESC" if en_cok else " ORDER BY id DESC"
        self.cursor.execute(q, p)
        return self.cursor.fetchall()

    def guncelle(self, id, kol, val):
        if kol in ['maskelenmis_komut', 'soru_ozeti', 'kategori', 'favori']:
            self.cursor.execute(f"UPDATE komut_gecmisi SET {kol} = ? WHERE id = ?", (val, id)); self.conn.commit()
    
    def sil(self, id):
        self.cursor.execute("DELETE FROM komut_gecmisi WHERE id = ?", (id,)); self.conn.commit()

    def son_profil(self):
        self.cursor.execute("SELECT analiz_raporu, son_islenen_komut_id FROM profil_analizleri ORDER BY id DESC LIMIT 1")
        return self.cursor.fetchone()
    
    def profil_kaydet(self, rapor, son_id):
        self.cursor.execute("INSERT INTO profil_analizleri (analiz_raporu, son_islenen_komut_id) VALUES (?, ?)", (rapor, son_id)); self.conn.commit()

    def analiz_verisi(self, start_id=0):
        self.cursor.execute("SELECT id, maskelenmis_komut FROM komut_gecmisi WHERE id > ? ORDER BY id ASC", (start_id,))
        return self.cursor.fetchall()

    def sifirla(self):
        # 1. Mevcut verileri sil
        self.cursor.execute("DELETE FROM komut_gecmisi")
        self.cursor.execute("DELETE FROM profil_analizleri")
        
        # 2. ID Sayaçlarını (AutoIncrement) Sıfırla
        try:
            self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='komut_gecmisi'")
            self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='profil_analizleri'")
        except: pass
        
        self.conn.commit()

    def kategorileri_getir(self):
        self.cursor.execute("SELECT DISTINCT kategori FROM komut_gecmisi")
        db = [r[0] for r in self.cursor.fetchall()]
        return [k for k in SABIT_KATEGORILER if k in db] + [k for k in db if k not in SABIT_KATEGORILER]
        
    def toplu_gecmis_yukle(self, dosya_yolu, kalkan):
        """Dışarıdan gelen shell history dosyasını verimli ve güvenli (Memory Safe) aktarır."""
        if not os.path.exists(dosya_yolu): return 0
        print(f"{Renk.CYAN}Dosya analiz ediliyor...{Renk.ENDC}")
        eklenen = 0
        try:
            # Encoding hatalarını yutarak dosyayı SATIR SATIR oku (RAM Dostu)
            with open(dosya_yolu, 'r', encoding='utf-8', errors='ignore') as f:
                for s in f: # readlines() yerine direkt f üzerinde dönüyoruz
                    s = s.strip()
                    if not s: continue
                    
                    # Zsh/Bash temizliği
                    if s.startswith(":"):
                        m = re.match(r'^: \d+:\d+;(.*)', s)
                        if m: s = m.group(1)
                    elif s.startswith("#") and s[1:].isdigit(): continue

                    try:
                        self.cursor.execute("SELECT id, kullanim_sayisi FROM komut_gecmisi WHERE ham_komut = ?", (s,))
                        mevcut = self.cursor.fetchone()
                        if mevcut:
                            self.cursor.execute("UPDATE komut_gecmisi SET kullanim_sayisi = ? WHERE id = ?", (mevcut[1] + 1, mevcut[0]))
                        else:
                            msk = kalkan.maskele(s)
                            # Kategori varsayılan olarak Shell Geçmişi
                            self.cursor.execute("INSERT INTO komut_gecmisi (ham_komut, maskelenmis_komut, soru_ozeti, aciklama, kategori, kullanim_sayisi) VALUES (?, ?, ?, ?, ?, ?)", (s, msk, "Dış Kaynak", "History Dosyasından", "Shell Geçmişi", 1))
                        eklenen += 1
                    except: pass
            
            self.conn.commit()
        except Exception as e: print(f"{Renk.FAIL}İçe aktarma hatası: {e}{Renk.ENDC}")
        return eklenen
    
    def kapat(self): self.conn.close()

class MergenZeka:
    def __init__(self):
        self.api = AYARLAR["api_key"]; self.client = None
        if self.api:
            try: from google import genai; self.client = genai.Client(api_key=self.api)
            except: pass
    def sor(self, s):
        if not AYARLAR.get("ai_aktif", True): return "AI_KAPALI" # <--- YENİ
        if not self.client: return "AI_DEVRE_DISI"
        if not self.client: return "API_YOK"
        try: return self.client.models.generate_content(model="gemini-3-flash-preview", contents=f"Linux uzmanı olarak cevapla. Format:\n```bash\nKOMUT\n```\nKategori: [{', '.join(SABIT_KATEGORILER)}]\nAÇIKLAMA\nSoru: {s}").text
        except Exception as e: return f"HATA: {e}"
    def profil_analizi_yap(self, eski, yeni):
        if not AYARLAR.get("ai_aktif", True): return "AI_KAPALI"
        if not self.client: return "AI_DEVRE_DISI"
        if not yeni: return "Veri yok"
        
        # DÜZELTME: Önce değişkeni tanımlıyoruz
        new_cmds = "\n".join([f"- {k}" for k in yeni[:50]])
        
        # Sonra kullanıyoruz
        p = f"Siber Güvenlik Kariyer Koçu olarak analiz et:\nGEÇMİŞ:\n{eski}\nYENİ KOMUTLAR:\n{new_cmds}\nBaşlıklar: 🛡️ GENEL, 💪 GÜÇLÜ, ⚠️ EKSİK, 📈 ÖNERİ."
        
        try: return self.client.models.generate_content(model="gemini-3-flash-preview", contents=p).text
        except: return "Hata"
    def ayristir(self, txt):
        c = re.search(r'```(?:bash|sh)?\s*(.*?)\s*```', txt, re.DOTALL); s = c.group(1).strip() if c else "Bulunamadı"
        k = re.search(r'Kategori:\s*\[?(.*?)\]?$', txt, re.MULTILINE); kat = k.group(1).strip().replace("[","").replace("]","") if k else "Diğer"
        if kat not in SABIT_KATEGORILER: kat = "Diğer"
        d = txt.replace(c.group(0) if c else "", "").replace(k.group(0) if k else "", "").strip()
        return s, d, kat

# --- GELISTIRILMIS TUI (SpecOps Edition) ---
class MergenTUI:
    def __init__(self, db):
        self.db = db; self.rows = []; self.sel = 0; self.off = 0; self.query = ""
    def start(self): curses.wrapper(self.run)
    def run(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        
        # Renk Paleti (Cyberpunk)
        curses.init_pair(1, curses.COLOR_GREEN, -1)   # Normal: Yeşil
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_GREEN) # Seçili: Siyah üzerine Yeşil
        curses.init_pair(3, curses.COLOR_CYAN, -1)    # Başlık: Mavi
        curses.init_pair(4, curses.COLOR_MAGENTA, -1) # Kategori 1
        curses.init_pair(5, curses.COLOR_YELLOW, -1)  # Kategori 2 / Uyarı
        curses.init_pair(6, curses.COLOR_RED, -1)     # Sistem / Hata
        
        self.load()
        while True:
            self.draw()
            k = self.stdscr.getch()
            if k == ord('q'): break
            elif k == ord('/'): self.search_mode()
            elif k == curses.KEY_UP and self.sel > 0:
                self.sel -= 1; 
                if self.sel < self.off: self.off -= 1
            elif k == curses.KEY_DOWN and self.sel < len(self.rows) - 1:
                self.sel += 1
                h, _ = self.stdscr.getmaxyx()
                if self.sel >= self.off + h - 9: self.off += 1
            elif k in [10, 13]: self.detail(self.rows[self.sel])

    def search_mode(self):
        curses.curs_set(1)
        h, w = self.stdscr.getmaxyx()
        self.stdscr.attron(curses.color_pair(3))
        self.stdscr.addstr(h-1, 0, " "*(w-1))
        self.stdscr.addstr(h-1, 0, " ARA > ")
        self.stdscr.attroff(curses.color_pair(3))
        self.stdscr.refresh()
        
        win = curses.newwin(1, w-8, h-1, 7)
        box = curses.textpad.Textbox(win)
        self.stdscr.refresh()
        box.edit()
        self.query = box.gather().strip()
        self.load()
        self.sel = 0; self.off = 0
        curses.curs_set(0)

    def load(self):
        d = self.db.getir(self.query)
        self.rows = [{"id":x[0], "cmd":x[1], "q":x[2], "cat":x[3], "desc":x[5]} for x in d]

    def draw(self):
        self.stdscr.clear(); h, w = self.stdscr.getmaxyx()
        
        # --- DASHBOARD HEADER ---
        user = getpass.getuser()
        host = socket.gethostname()
        time_str = datetime.now().strftime("%H:%M")
        
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(0, 0, "┌" + "─"*(w-2) + "┐")
        
        # Info Bar
        info_l = f" USR: {user}@{host}"
        info_r = f"TIME: {time_str} "
        title = " MERGEN OPS CENTER "
        
        self.stdscr.addstr(1, 0, "│")
        self.stdscr.addstr(1, 2, info_l, curses.color_pair(5))
        self.stdscr.addstr(1, (w-len(title))//2, title, curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(1, w-len(info_r)-2, info_r, curses.color_pair(5))
        self.stdscr.addstr(1, w-1, "│")
        
        self.stdscr.addstr(2, 0, "├" + "─"*(w-2) + "┤")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        
        # Sütun Başlıkları
        cols = " {0:<4} | {1:<15} | {2}".format("ID", "KATEGORI", "KOMUT")
        self.stdscr.addstr(3, 1, cols, curses.color_pair(3) | curses.A_UNDERLINE)

        # Liste
        for i in range(h - 9):
            idx = self.off + i
            if idx >= len(self.rows): break
            r = self.rows[idx]
            
            line = " {0:<4} | {1:<15} | {2}".format(str(r['id']), r['cat'][:15], r['cmd'][:w-25])
            
            if idx == self.sel:
                self.stdscr.attron(curses.color_pair(2))
                self.stdscr.addstr(i+4, 1, line.ljust(w-2))
                self.stdscr.attroff(curses.color_pair(2))
            else:
                self.stdscr.addstr(i+4, 1, line)
                # Renklendirme
                self.stdscr.chgat(i+4, 1, 4, curses.color_pair(3)) # ID
                
                # Kategoriye göre renk
                cat_col = curses.color_pair(4)
                if r['cat'] in ["Ağ", "Network"]: cat_col = curses.color_pair(5)
                elif r['cat'] in ["Güvenlik", "Sistem"]: cat_col = curses.color_pair(6)
                
                self.stdscr.chgat(i+4, 8, 15, cat_col)

        # --- FOOTER ---
        self.stdscr.attron(curses.color_pair(3))
        self.stdscr.addstr(h-3, 0, "├" + "─"*(w-2) + "┤")
        self.stdscr.attroff(curses.color_pair(3))
        
        status = f" {len(self.rows)} Kayıt | Filtre: {self.query if self.query else 'YOK'}"
        self.stdscr.addstr(h-2, 2, status, curses.color_pair(1))
        
        keys = " [Q]ÇIKIŞ  [/]ARA  [ENTER]DETAY  [↑/↓]GEZİN "
        self.stdscr.addstr(h-2, w-len(keys)-2, keys, curses.color_pair(2))
        
        self.stdscr.attron(curses.color_pair(3))
        # HATA DÜZELTME: Bottom-right corner crash fix
        try:
            self.stdscr.addstr(h-1, 0, "└" + "─"*(w-2) + "┘")
        except curses.error:
            pass
        self.stdscr.attroff(curses.color_pair(3))
        
        self.stdscr.refresh()

    def detail(self, r):
        h, w = self.stdscr.getmaxyx()
        win = curses.newwin(h-6, w-8, 3, 4)
        win.box()
        win.bkgd(' ', curses.color_pair(1))
        
        win.attron(curses.color_pair(3) | curses.A_BOLD)
        win.addstr(0, 2, f" KOMUT DETAYI [ID: {r['id']}] ")
        win.attroff(curses.color_pair(3) | curses.A_BOLD)
        
        win.addstr(2, 2, "KATEGORİ:", curses.color_pair(5))
        win.addstr(2, 12, r['cat'], curses.A_BOLD)
        
        win.addstr(4, 2, "KOMUT:", curses.color_pair(5))
        win.addstr(5, 4, r['cmd'], curses.color_pair(1) | curses.A_BOLD)
        
        win.addstr(7, 2, "SORU/AMAÇ:", curses.color_pair(5))
        win.addstr(8, 4, r['q'][:w-15] or "-")
        
        win.addstr(10, 2, "AÇIKLAMA:", curses.color_pair(5))
        lines = []
        desc = r['desc'] or "-"
        for line in desc.split('\n'):
            for i in range(0, len(line), w-20): lines.append(line[i:i+(w-20)])
        
        for i, l in enumerate(lines[:h-20]):
            win.addstr(11+i, 4, l)
            
        win.addstr(h-8, 2, "[ENTER] KAPAT", curses.color_pair(2))
        win.refresh()
        while win.getch() not in [10, 13, 27, ord('q')]: pass

if GUI_AVAILABLE:
    class ProfilWorker(QThread):
        sonuc_hazir = pyqtSignal(str, int)
        def __init__(self, key): super().__init__(); self.key = key
        def run(self):
            db = MergenVeritabani(); z = MergenZeka()
            try:
                p = db.son_profil(); eski = p[0] if p else ""; sid = p[1] if p else 0
                yeni = db.analiz_verisi(sid)
                if not yeni: self.sonuc_hazir.emit("YENİ_VERİ_YOK", sid); return
                r = z.profil_analizi_yap(eski, [x[1] for x in yeni])
                self.sonuc_hazir.emit(r, yeni[-1][0])
            finally: db.kapat()

    class ProfilPenceresi(QDialog):
        def __init__(self, parent=None, db=None):
            super().__init__(parent); self.db = db
            self.setWindowTitle("MERGEN - Profil"); self.resize(700, 800)
            self.setStyleSheet("background-color: #121212; color: #e0e0e0;")
            l = QVBoxLayout(self)
            l.addWidget(QLabel("🧠 SİBER GÜVENLİK PROFİLİ"))
            self.txt = QTextEdit(); self.txt.setReadOnly(True); self.txt.setStyleSheet("background: #1e1e1e; border: 1px solid #333; font-family: Consolas;"); l.addWidget(self.txt)
            self.btn = QPushButton("Analiz Et"); self.btn.setStyleSheet("background: #9b59b6; color: white; padding: 10px;"); self.btn.clicked.connect(self.baslat); l.addWidget(self.btn)
            self.pbar = QProgressBar(); self.pbar.setVisible(False); l.addWidget(self.pbar)
            self.yukle()
        def yukle(self):
            d = self.db.son_profil()
            if d: self.txt.setMarkdown(d[0])
        def baslat(self):
            self.pbar.setVisible(True); self.btn.setEnabled(False)
            self.w = ProfilWorker(AYARLAR["api_key"]); self.w.sonuc_hazir.connect(self.bitti); self.w.start()
        def bitti(self, r, i):
            self.pbar.setVisible(False); self.btn.setEnabled(True)
            if r!="YENİ_VERİ_YOK" and not r.startswith("HATA"):
                self.db.profil_kaydet(r, i); self.txt.setMarkdown(r)
            elif r=="YENİ_VERİ_YOK": QMessageBox.information(self,"Bilgi","Yeni veri yok.")

    class AIWorker(QThread):
        sonuc_hazir = pyqtSignal(tuple)
        def __init__(self, soru): super().__init__(); self.soru = soru
        def run(self): z = MergenZeka(); r = z.sor(self.soru); self.sonuc_hazir.emit(z.ayristir(r))

    class MergenGUI(QMainWindow):
        def __init__(self, db):
            super().__init__()
            self.db = db
            self.secili = {}
            self.kat = "Tümü"
            self.fav = False
            self.kalkan = GuvenlikKalkan()  # <--- BU SATIRI MUTLAKA EKLE
            self.setup_ui()
            self.load()

        def setup_ui(self):
            qss = """
            QMainWindow { background-color: #121212; }
            QWidget { color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
            QLineEdit { background-color: #1e1e1e; border: 1px solid #333; border-radius: 4px; padding: 6px; color: #00ff9d; font-family: 'Consolas'; }
            QLineEdit:focus { border: 1px solid #00ff9d; }
            QTableWidget { background-color: #1a1a1a; gridline-color: #333; border: none; selection-background-color: #00332a; selection-color: #00ff9d; }
            QHeaderView::section { background-color: #252525; color: #aaa; padding: 4px; border: none; font-weight: bold; border-bottom: 2px solid #333; }
            QTextEdit { background-color: #151515; border: 1px solid #333; color: #ccc; font-family: 'Consolas'; }
            QPushButton { background-color: #333; border: 1px solid #444; border-radius: 4px; padding: 5px 10px; color: white; }
            QPushButton:hover { background-color: #444; border-color: #00ff9d; }
            QRadioButton { color: #888; spacing: 5px; }
            QRadioButton::indicator:checked { background-color: #00ff9d; border-radius: 6px; border: 2px solid #00ff9d; }
            QCheckBox { color: gold; font-weight: bold; }
            QProgressBar { border: 1px solid #333; text-align: center; }
            QProgressBar::chunk { background-color: #00ff9d; }
            """
            self.setStyleSheet(qss)
            self.resize(1300, 850); cw = QWidget(); self.setCentralWidget(cw); l = QVBoxLayout(cw)
            
            h = QHBoxLayout(); lbl = QLabel("MERGEN"); lbl.setFont(QFont("Impact", 28)); lbl.setStyleSheet("color: #00ff9d; letter-spacing: 2px;"); h.addWidget(lbl)
            self.src = QLineEdit(); self.src.setPlaceholderText("🔍 Komut veritabanında ara... (Regex destekler)"); self.src.textChanged.connect(lambda: self.load(self.src.text())); h.addWidget(self.src, 1)
            
            # --- YENİ: AI GİZLİLİK ANAHTARI ---
            self.chk_ai = QCheckBox("🤖 AI"); 
            self.chk_ai.setChecked(AYARLAR.get("ai_aktif", True))
            self.chk_ai.setToolTip("İşaretlenmezse hiçbir veri Google'a gönderilmez (Ultra Gizlilik)")
            self.chk_ai.stateChanged.connect(self.toggle_ai)
            self.chk_ai.setStyleSheet("QCheckBox { color: #00ff9d; font-weight: bold; margin-right: 10px; } QCheckBox::indicator:checked { background-color: #00ff9d; }")
            h.addWidget(self.chk_ai)
            
            bp = QPushButton("🧠 Profilim"); bp.setStyleSheet("color:#9b59b6; font-weight:bold;"); bp.clicked.connect(self.pro); h.addWidget(bp)
            bi = QPushButton("📂 İçe Aktar"); bi.clicked.connect(self.imp); h.addWidget(bi)
            btn_hist = QPushButton("📜 Geçmiş Yükle")
            btn_hist.setToolTip("Dışarıdan zsh/bash history dosyası yükle")
            btn_hist.clicked.connect(self.import_external_history)
            h.addWidget(btn_hist)
            be = QPushButton("💾 Yedekle"); be.clicked.connect(self.exp); h.addWidget(be)
            bk = QPushButton("🗑️ Sıfırla"); bk.setStyleSheet("background:#c0392b; font-weight:bold;"); bk.clicked.connect(self.kill); h.addWidget(bk)
            l.addLayout(h)

            f = QHBoxLayout()
            cf = QCheckBox("⭐ Sadece Favoriler"); cf.setStyleSheet("color: gold; font-weight: bold;"); cf.stateChanged.connect(self.tf); f.addWidget(cf); self.cf = cf
            cs = QCheckBox("🔥 En Çok Kullanılanlar"); cs.setStyleSheet("color: #ff5555; font-weight: bold; margin-left: 15px;"); cs.stateChanged.connect(self.tf); f.addWidget(cs); self.cs = cs
            f.addWidget(QLabel(" |  Kategoriler:")); bg = QButtonGroup(); bg.buttonClicked.connect(self.tc); self.bg = bg; self.fl = QHBoxLayout(); f.addLayout(self.fl); f.addStretch(); l.addLayout(f)

            s = QSplitter(Qt.Orientation.Vertical)
        
            # --- TABLO VE SÜTUN AYARLARI ---
            s = QSplitter(Qt.Orientation.Vertical)
        
            self.tb = QTableWidget(0, 7)
            self.tb.setHorizontalHeaderLabels(["ID","⭐","CNT","KOMUT (Düzenle)","AMAÇ / SORU","KATEGORİ","TARİH"])
        
            header = self.tb.horizontalHeader()

            # 1. KÜÇÜK SÜTUNLAR (İçeriğe yapışsın)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # ID
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Yıldız
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Sayaç

            # 2. ORTA SÜTUNLAR (Elle ayarlanabilir, sabit başlangıç)
            # Amaç/Soru: İkinci büyük alan (300px)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)
            self.tb.setColumnWidth(4, 300) 
        
            # Kategori ve Tarih: Standart alan
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
            self.tb.setColumnWidth(5, 120)
        
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.Interactive)
            self.tb.setColumnWidth(6, 130)

            # 3. KOMUT SÜTUNU (KRAL) - Kalan tüm boşluğu kaplasın
            # Stretch modu, pencere büyüdükçe burayı otomatik doldurur.
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

            # Tablo Davranışları
            self.tb.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.tb.itemSelectionChanged.connect(self.sel)
            self.tb.cellClicked.connect(self.clk)
            self.tb.cellChanged.connect(self.edt)
            self.tb.setSortingEnabled(True)
            s.addWidget(self.tb)
            # -------------------------------------------------------

            # Analiz Kutusu (Alt kısım)
            dw = QWidget(); dl = QVBoxLayout(dw); dl.setContentsMargins(0,10,0,0)
            dh = QHBoxLayout(); dhl = QLabel("KOMUT ANALİZİ"); dhl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold)); dhl.setStyleSheet("color: #00ff9d;"); dh.addWidget(dhl); dh.addStretch()
            dcp = QPushButton("📋 Kopyala"); dcp.clicked.connect(self.copy_cmd); dh.addWidget(dcp); dl.addLayout(dh)
            self.dt = QTextEdit(); self.dt.setReadOnly(True); dl.addWidget(self.dt); s.addWidget(dw); l.addWidget(s)
        
            # Durum Çubuğu
            self.st = QLabel("Hazır"); l.addWidget(self.st)

        def ucat(self):
            for b in self.bg.buttons(): self.bg.removeButton(b); b.deleteLater()
            for c in ["Tümü"] + self.db.kategorileri_getir():
                r = QRadioButton(c); self.bg.addButton(r); self.fl.addWidget(r); 
                if c == self.kat: r.setChecked(True)
        def tf(self): self.fav = self.cf.isChecked(); self.load(self.src.text())
        def tc(self, b): self.kat = b.text(); self.load(self.src.text())
        def load(self, f=""):
            self.tb.setSortingEnabled(False); self.tb.setRowCount(0)
            
            # Veriyi DB'den çek
            d = self.db.getir(f, self.kat, self.fav, self.cs.isChecked())
            self.secili = {}; self.ucat()
            
            for r, x in enumerate(d):
                self.tb.insertRow(r)
                # ID ve CNT sütunları için SayisalItem kullanıyoruz (Doğru sıralama için)
                self.tb.setItem(r,0,SayisalItem(str(x[0]))); self.tb.setItem(r,1,QTableWidgetItem("★" if x[7] else "☆"))
                self.tb.setItem(r,2,SayisalItem(str(x[8]))); 
                
                ic = QTableWidgetItem(x[1]); ic.setFont(QFont("Consolas", 10)); ic.setForeground(QColor("#00ff9d")); self.tb.setItem(r,3,ic)
                self.tb.setItem(r,4,QTableWidgetItem(x[2])); self.tb.setItem(r,5,QTableWidgetItem(x[3]))
                self.tb.setItem(r,6,QTableWidgetItem(str(x[4])[:16]))
                self.secili[r] = {'desc': x[5], 'msk': x[1], 'q': x[2]}
            
            self.tb.setSortingEnabled(True)
            
            # --- YENİ EKLENEN SIRALAMA MANTIĞI ---
            if self.cs.isChecked():
                # Eğer "En Çok Kullanılanlar" seçiliyse, 3. sütuna (CNT/Index 2) göre AZALAN sırala
                self.tb.sortItems(2, Qt.SortOrder.DescendingOrder)
            else:
                # Değilse, ID sütununa (Index 0) göre AZALAN sırala (En yeni en üstte)
                self.tb.sortItems(0, Qt.SortOrder.DescendingOrder)
            # -------------------------------------
            
            self.st.setText(f"Toplam {len(d)} kayıt listelendi.")
        def sel(self):
            try:
                r = self.tb.currentRow()
                if r in self.secili: 
                    d = self.secili[r]
                    # GÜVENLİK YAMASI: HTML Injection'ı engelle
                    safe_q = html.escape(d['q'])
                    safe_msk = html.escape(d['msk'])
                    safe_desc = html.escape(d['desc']).replace(chr(10), '<br>')
                    
                    html_content = f"<style>.cmd {{ background: #111; color: #00ff9d; padding: 10px; font-family: Consolas; border-left: 3px solid #00ff9d; }}</style><h3>{safe_q}</h3><div class='cmd'>{safe_msk}</div><br><div>{safe_desc}</div>"
                    self.dt.setHtml(html_content)
            except: pass
            
        def import_external_history(self):
            path, _ = QFileDialog.getOpenFileName(self, "Geçmiş Dosyası Seç (.zsh_history, .bash_history)", os.path.expanduser("~"), "All Files (*)")
            if path:
                # Veritabanına eklediğimiz toplu yükleme fonksiyonunu çağırıyoruz
                sayi = self.db.toplu_gecmis_yukle(path, self.kalkan)
                
                if sayi > 0:
                    self.load() # Tabloyu yenile
                    QMessageBox.information(self, "Başarılı", f"✅ {sayi} adet komut geçmiş dosyasından başarıyla veritabanına işlendi.")
                else:
                    QMessageBox.warning(self, "Uyarı", "Dosyadan komut alınamadı veya dosya boş.")
            
        def clk(self, r, c):
            if c==1: id = int(self.tb.item(r,0).text()); cur = self.tb.item(r,1).text(); self.db.guncelle(id, 'favori', 1 if cur=="☆" else 0); self.load(self.src.text())
        def edt(self, r, c):
            if c in [3,4,5]: id = int(self.tb.item(r,0).text()); col = {3:'maskelenmis_komut', 4:'soru_ozeti', 5:'kategori'}[c]; self.db.guncelle(id, col, self.tb.item(r,c).text())
        def kill(self):
            if QMessageBox.question(self,"UYARI","TÜM VERİ SİLİNECEK!",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes: self.db.sifirla(); self.load()
        def imp(self):
            # Dosya açma penceresi
            p, _ = QFileDialog.getOpenFileName(self, "Yedek Yükle", os.path.expanduser("~"), "JSON (*.json)")
            if not p: return
            
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                sayac = 0
                for x in data:
                    # Yeni export formatına uygun anahtarlar ("ham", "msk" vb.)
                    # Geriye dönük uyumluluk için eski anahtarları da kontrol ediyoruz (cmd, q vb.)
                    ham = x.get('ham') or x.get('cmd')
                    msk = x.get('msk') or x.get('maskelenmis_komut')
                    soru = x.get('q') or x.get('soru_ozeti') or "Yedekten Yüklendi"
                    desc = x.get('desc') or x.get('aciklama') or ""
                    cat = x.get('cat') or x.get('kategori') or "Diğer"
                    fav = x.get('fav') or x.get('favori') or 0
                    
                    if ham:
                        self.db.komut_ekle(ham, msk, soru, desc, cat, fav)
                        sayac += 1
                
                self.load() # Tabloyu yenile
                QMessageBox.information(self, "Başarılı", f"✅ {sayac} kayıt başarıyla geri yüklendi.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Yükleme hatası: {str(e)}")
        def toggle_ai(self):
            AYARLAR["ai_aktif"] = self.chk_ai.isChecked()
            save_config(AYARLAR)
            durum = "AÇIK 🟢" if AYARLAR["ai_aktif"] else "KAPALI 🔴 (Gizlilik Modu)"
            self.st.setText(f"AI Modülü: {durum}")
            
        def exp(self):
            # Dosya kaydetme penceresi
            p, _ = QFileDialog.getSaveFileName(self, "Yedekle", os.path.expanduser("~"), "JSON (*.json)")
            if not p: return
            
            try:
                # Arayüzden değil, doğrudan veritabanından HAM veriyi çekiyoruz (En güvenli yol)
                self.db.cursor.execute("SELECT ham_komut, maskelenmis_komut, soru_ozeti, aciklama, kategori, favori FROM komut_gecmisi")
                veriler = self.db.cursor.fetchall()
                
                export_listesi = []
                for v in veriler:
                    export_listesi.append({
                        "ham": v[0],   # Ham Komut
                        "msk": v[1],   # Maskelenmiş
                        "q": v[2],     # Soru
                        "desc": v[3],  # Açıklama
                        "cat": v[4],   # Kategori
                        "fav": v[5]    # Favori
                    })
                
                with open(p, 'w', encoding='utf-8') as f:
                    json.dump(export_listesi, f, indent=4, ensure_ascii=False)
                    
                QMessageBox.information(self, "Başarılı", f"✅ {len(export_listesi)} kayıt yedeklendi.")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Yedekleme hatası: {str(e)}")
        def pro(self):
            d = QDialog(self); d.setWindowTitle("Profil"); d.resize(600,600); l = QVBoxLayout(d)
            t = QTextEdit(); t.setReadOnly(True); l.addWidget(t)
            pd = self.db.son_profil(); t.setMarkdown(pd[0] if pd else "Analiz yok.")
            def start():
                b.setEnabled(False); pb.setVisible(True)
                w = ProfilWorker(AYARLAR["api_key"]); w.sonuc_hazir.connect(end); w.start(); d.w = w
            def end(r, i):
                pb.setVisible(False); b.setEnabled(True)
                if not r.startswith("YENİ"): self.db.profil_kaydet(r, i); t.setMarkdown(r)
                else: QMessageBox.information(d,"Info","Yeni veri yok")
            b = QPushButton("Analiz Et"); b.clicked.connect(start); l.addWidget(b)
            pb = QProgressBar(); pb.setVisible(False); pb.setRange(0,0); l.addWidget(pb); d.exec()
        def copy_cmd(self): QApplication.clipboard().setText(self.dt.toPlainText().split('\n')[1]); self.st.setText("📋 Panoya kopyalandı!")

# --- SETUP VE MAIN ---
def setup_full():
    print(f"{Renk.HEADER}=== MERGEN KURULUM SİHİRBAZI (v6.6) ==={Renk.ENDC}")
    print("Bu sihirbaz gerekli kütüphaneleri kuracak ve ayarları yapılandıracaktır.")
    
    # 1. Kütüphaneler
    print(f"\n{Renk.BLUE}[1/5] Kütüphane Kontrolü...{Renk.ENDC}")
    subprocess.call([sys.executable, "-m", "pip", "install", "google-genai", "PyQt6", "--break-system-packages"])

    # 2. Veritabanı (AKILLI ÖNERİ)
    print(f"\n{Renk.BLUE}[2/5] Veritabanı Yeri...{Renk.ENDC}")
    
    sync_path = os.path.join(os.path.expanduser('~'), 'Sync')
    default_db = os.path.join(os.path.expanduser('~'), '.mergen_data.db')
    
    if os.path.exists(sync_path):
        suggested_db = os.path.join(sync_path, 'mergen.db')
        print(f"{Renk.GREEN}Syncthing klasörü bulundu!{Renk.ENDC}")
        print(f"Önerilen Yol (Telefonda Eşitleme İçin): {Renk.BOLD}{suggested_db}{Renk.ENDC}")
    else:
        suggested_db = default_db
        print(f"Varsayılan: {default_db}")
        
    custom_db = input(f"{Renk.BOLD}Yol (Önerilen için Enter): {Renk.ENDC}").strip()
    final_db_path = custom_db if custom_db else suggested_db
    
    # 3. API Key
    print(f"\n{Renk.BLUE}[3/5] Google Gemini API Key...{Renk.ENDC}")
    key = input(f"{Renk.BOLD}Anahtar (Enter ile atla): {Renk.ENDC}").strip()
    
    save_config({"db_path": final_db_path, "api_key": key})
    MergenVeritabani() # Init
    
    # 3.1 AI Tercihi
    print(f"\n{Renk.BLUE}[Opsiyonel] Gizlilik Ayarı...{Renk.ENDC}")
    ai_choice = input(f"{Renk.BOLD}Yapay Zeka analizi aktif olsun mu? (e/h) [E]: {Renk.ENDC}").strip().lower()
    ai_stat = False if ai_choice == 'h' else True
    
    save_config({"db_path": final_db_path, "api_key": key, "ai_aktif": ai_stat})
    
    # 4. Shell Hook
    print(f"\n{Renk.BLUE}[4/5] Shell Entegrasyonu...{Renk.ENDC}")
    src = os.path.abspath(sys.argv[0]); sh = os.environ.get("SHELL","").split("/")[-1]
    rc = os.path.expanduser(f"~/.{sh}rc") if sh in ["bash","zsh"] else None
    
    if rc:
        try:
            with open(rc, "r") as f: content = f.read()
            if "mergen_track" not in content:
                with open(rc, "a") as f: f.write(f'\nmergen_track() {{ /usr/bin/python3 {src} --track "$(fc -ln -1)" &! }}\nautoload -Uz add-zsh-hook; add-zsh-hook precmd mergen_track\n' if sh=="zsh" else f'\nmergen_track() {{ /usr/bin/python3 {src} --track "$(history 1 | sed \'s/^[ ]*[0-9]\\+[ ]*//\')" &>/dev/null & }}\nexport PROMPT_COMMAND="mergen_track; $PROMPT_COMMAND"\n')
                print(f"{Renk.GREEN}✓ Hook eklendi: {rc}{Renk.ENDC}")
            else: print(f"{Renk.WARNING}! Zaten ekli.{Renk.ENDC}")
        except: print(f"{Renk.FAIL}! Shell dosyasına yazılamadı.{Renk.ENDC}")

    # 5. Symlink
    print(f"\n{Renk.BLUE}[5/5] Sistem Komutu Oluşturuluyor...{Renk.ENDC}")
    try: 
        if not os.path.exists("/usr/local/bin/mergen"): os.symlink(src, "/usr/local/bin/mergen")
        print(f"{Renk.GREEN}✓ 'mergen' komutu eklendi.{Renk.ENDC}")
    except: 
        print(f"{Renk.FAIL}X Yetki hatası! Manuel çalıştırın:{Renk.ENDC}")
        print(f"sudo ln -s {src} /usr/local/bin/mergen")

    print(f"\n{Renk.GREEN}=== KURULUM TAMAMLANDI ==={Renk.ENDC}")
    print("Lütfen terminali kapatıp yeniden açın.")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("sorgu", nargs="?", help="Soru sor veya komut ara")
    p.add_argument("--ui", action="store_true", help="Grafik Arayüzü Aç")
    p.add_argument("--tui", action="store_true", help="Terminal Arayüzü Aç (SSH/Mobil)")
    p.add_argument("--setup", action="store_true", help="Kurulum Sihirbazı")
    p.add_argument("--track", nargs=1, help=argparse.SUPPRESS) # Gizli parametre
    p.add_argument("--import-history", nargs=1, help="Harici history dosyasını (.zsh_history vb.) veritabanına işle")
    a = p.parse_args()

    if a.setup: setup_full(); return
    if not check_libs(): print("Lütfen önce --setup çalıştırın."); return

    db = MergenVeritabani(); k = GuvenlikKalkan()

    if a.track:
        # Bu parametre Shell Hook tarafından otomatik çağrılır
        if a.track[0].strip() and "mergen" not in a.track[0]: db.komut_ekle(a.track[0], k.maskele(a.track[0]), "Shell Geçmişi", "Otomatik", "Shell Geçmişi")
        return
        
    if a.import_history:
        yol = a.import_history[0]
        sayi = db.toplu_gecmis_yukle(yol, kalkan)
        print(f"{Renk.GREEN}✓ Toplam {sayi} komut sızma testi geçmişinden veritabanına işlendi.{Renk.ENDC}")
        return

    if a.tui: MergenTUI(db).start(); return

    if a.ui:
        if not GUI_AVAILABLE: print("PyQt6 yok. --tui kullanın."); return
        app = QApplication(sys.argv); w = MergenGUI(db)
        if a.sorgu:
            w.show(); w.st.setText("AI...")
            th = AIWorker(k.maskele(a.sorgu))
            def fin(r): db.komut_ekle(r[0], k.maskele(r[0]), a.sorgu, r[1], r[2]); w.load(); w.st.setText("OK")
            th.sonuc_hazir.connect(fin); th.start(); w.th = th; sys.exit(app.exec())
        w.show(); sys.exit(app.exec())

    if a.sorgu:
        z = MergenZeka(); print(f"{Renk.CYAN}Analiz...{Renk.ENDC}")
        r = z.sor(k.maskele(a.sorgu))
        if r=="API_YOK": print("API Key yok."); return
        s, d, c = z.ayristir(r)
        print(f"\n{Renk.GREEN}KOMUT: {s}{Renk.ENDC}\n{Renk.BLUE}KAT: {c}{Renk.ENDC}\n\n{d}")
        db.komut_ekle(s, k.maskele(s), a.sorgu, d, c)
    else:
        print("Kullanım: mergen [sorgu] | --ui | --tui | --setup")

if __name__ == "__main__":
    main()
