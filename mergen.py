#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MERGEN v5.1 - Thread Safe Edition
Özellikler: Çoklu Thread Desteği, Profil Analizi, Güvenli DB Bağlantısı
"""

import sys
import os
import sqlite3
import argparse
import logging
import re
import json
import subprocess
from datetime import datetime

# --- RENKLİ TERMİNAL ÇIKTILARI ---
class Renk:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# --- KÜTÜPHANE KONTROLLERİ ---
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
        QMenu, QRadioButton, QButtonGroup, QFileDialog, QCheckBox, QProgressBar,
        QDialog, QScrollArea, QFrame
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
    from PyQt6.QtGui import QFont, QColor, QTextCursor
    GUI_AVAILABLE = True
except ImportError: pass

# --- YAPILANDIRMA ---
LOG_DOSYASI = os.path.join(os.path.expanduser('~'), '.mergen_log')
logging.basicConfig(filename=LOG_DOSYASI, level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger("MergenSystem")
SABIT_KATEGORILER = ["Shell Geçmişi", "Sistem", "Ağ", "Dosya", "Güvenlik", "Konteyner", "Veritabanı", "Git/VCS", "Kullanıcı", "Servis", "Diğer"]

# --- GUI YARDIMCISI ---
if GUI_AVAILABLE:
    class SayisalItem(QTableWidgetItem):
        def __lt__(self, other):
            try: return float(self.text()) < float(other.text())
            except ValueError: return super().__lt__(other)

# --- MODÜL 1: GÜVENLİK KALKANI ---
class GuvenlikKalkan:
    def __init__(self):
        self.gizli_bellek = {}
        self.sayac = 0
        self.desenler = {
            'HASSAS_DEGER': r'(?i)((?:export\s+)?[\w]*(?:key|secret|token|password|passwd|auth)[\w]*)\s*=\s*(["\']?)([^"\s]+)\2',
        }
    def maskele(self, metin: str) -> str:
        if not metin: return ""
        islenmis = metin
        while True:
            bulgu = re.search(self.desenler['HASSAS_DEGER'], islenmis)
            if not bulgu: break
            tam, degisken, _, deger = bulgu.group(0), bulgu.group(1), bulgu.group(2), bulgu.group(3)
            if "GIZLI_" in deger: break 
            token = f"<GIZLI_{self.sayac}>"
            self.gizli_bellek[token] = deger
            self.sayac += 1
            islenmis = islenmis.replace(tam, f"{degisken}={token}")
        return islenmis

# --- MODÜL 2: VERİTABANI ---
class MergenVeritabani:
    def __init__(self):
        self.db_yolu = os.path.join(os.path.expanduser("~"), ".mergen_data.db")
        # Thread hatasını önlemek için her çağrıda yeni bağlantı mantığı
        # Ama burada GUI donmasın diye işçi threadler kendi instance'ını oluşturmalı.
        self.conn = sqlite3.connect(self.db_yolu, check_same_thread=False) 
        self.cursor = self.conn.cursor()
        self._init_db()

    def _init_db(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS komut_gecmisi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ham_komut TEXT UNIQUE, 
                maskelenmis_komut TEXT,
                soru_ozeti TEXT,
                aciklama TEXT,
                kategori TEXT,
                favori INTEGER DEFAULT 0,
                kullanim_sayisi INTEGER DEFAULT 1,
                tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS profil_analizleri (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analiz_raporu TEXT,
                son_islenen_komut_id INTEGER,
                tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Migration
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

    # --- Profil Metodları ---
    def son_profil_getir(self):
        self.cursor.execute("SELECT analiz_raporu, son_islenen_komut_id, tarih FROM profil_analizleri ORDER BY id DESC LIMIT 1")
        return self.cursor.fetchone()

    def profil_kaydet(self, rapor, son_id):
        self.cursor.execute("INSERT INTO profil_analizleri (analiz_raporu, son_islenen_komut_id) VALUES (?, ?)", (rapor, son_id))
        self.conn.commit()

    def analiz_icin_komutlari_getir(self, baslangic_id=0):
        self.cursor.execute("SELECT id, maskelenmis_komut FROM komut_gecmisi WHERE id > ? ORDER BY id ASC", (baslangic_id,))
        return self.cursor.fetchall()

    def son_komut_id(self):
        self.cursor.execute("SELECT MAX(id) FROM komut_gecmisi")
        res = self.cursor.fetchone()
        return res[0] if res[0] else 0

    # --- Standart Metodlar ---
    def komut_ekle(self, ham, maskeli, soru, aciklama, kategori="Diğer", favori=0):
        try:
            self.cursor.execute("SELECT id, kullanim_sayisi FROM komut_gecmisi WHERE ham_komut = ?", (ham,))
            mevcut = self.cursor.fetchone()
            if mevcut:
                self.cursor.execute("UPDATE komut_gecmisi SET kullanim_sayisi = ?, tarih = CURRENT_TIMESTAMP WHERE id = ?", (mevcut[1] + 1, mevcut[0]))
            else:
                self.cursor.execute("INSERT INTO komut_gecmisi (ham_komut, maskelenmis_komut, soru_ozeti, aciklama, kategori, favori, kullanim_sayisi) VALUES (?, ?, ?, ?, ?, ?, ?)", (ham, maskeli, soru, aciklama, kategori, favori, 1))
            self.conn.commit()
        except: pass

    def guncelle(self, id, kol, val):
        if kol in ['maskelenmis_komut', 'soru_ozeti', 'kategori', 'favori']:
            self.cursor.execute(f"UPDATE komut_gecmisi SET {kol} = ? WHERE id = ?", (val, id))
            self.conn.commit()

    def sil(self, id):
        self.cursor.execute("DELETE FROM komut_gecmisi WHERE id = ?", (id,))
        self.conn.commit()
        
    def veritabani_sifirla(self):
        try:
            self.cursor.execute("DELETE FROM komut_gecmisi")
            self.cursor.execute("DELETE FROM profil_analizleri")
            # Auto-increment sayaçlarını da sıfırla (Opsiyonel ama temizlik için iyi)
            self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='komut_gecmisi'")
            self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='profil_analizleri'")
            self.conn.commit()
        except Exception as e:
            print(f"Sıfırlama hatası: {e}")

    def getir(self, filtre="", kat="Tümü", fav=False, en_cok=False):
        q = "SELECT id, maskelenmis_komut, soru_ozeti, kategori, tarih, aciklama, ham_komut, favori, kullanim_sayisi FROM komut_gecmisi WHERE 1=1"
        p = []
        if fav: q += " AND favori = 1"
        if kat != "Tümü": q += " AND kategori = ?"; p.append(kat)
        if filtre: q += " AND (maskelenmis_komut LIKE ? OR soru_ozeti LIKE ? OR aciklama LIKE ?)"; p.extend([f"%{filtre}%"]*3)
        q += " ORDER BY kullanim_sayisi DESC" if en_cok else " ORDER BY id DESC"
        self.cursor.execute(q, p)
        return self.cursor.fetchall()

    def kategoriler(self):
        self.cursor.execute("SELECT DISTINCT kategori FROM komut_gecmisi")
        db = [r[0] for r in self.cursor.fetchall()]
        return [k for k in SABIT_KATEGORILER if k in db] + [k for k in db if k not in SABIT_KATEGORILER]

    def kapat(self):
        self.conn.close()

# --- MODÜL 3: AI ---
class MergenZeka:
    def __init__(self):
        self.api = os.getenv("MERGEN_API_KEY")
        self.client = None
        if self.api:
            try: from google import genai; self.client = genai.Client(api_key=self.api)
            except: pass

    def sor(self, soru):
        if not self.client: return "API_YOK"
        try:
            p = f"Sen Linux Uzmanısın. Format:\n```bash\nKOMUT\n```\nKategori: [{', '.join(SABIT_KATEGORILER)}]\nAÇIKLAMA\nSoru: {soru}"
            return self.client.models.generate_content(model="gemini-3-flash-preview", contents=p).text
        except Exception as e: return f"HATA: {e}"

    def profil_analizi_yap(self, eski_profil, yeni_komutlar):
        if not self.client: return "API_YOK"
        if not yeni_komutlar: return "Yeterli yeni veri yok."
        kl = "\n".join([f"- {k}" for k in yeni_komutlar[:50]]) # Max 50 komut gönder (Token tasarrufu)
        p = (
            "Sen bir Siber Güvenlik Kariyer Koçusun. "
            "Kullanıcının komutlarına bakarak yetkinlik, odak alanı ve eksiklerini analiz et.\n"
            f"--- GEÇMİŞ ---\n{eski_profil}\n"
            f"--- YENİ KOMUTLAR ---\n{kl}\n"
            "Çıktı: 🛡️ GENEL PROFİL, 💪 GÜÇLÜ YANLAR, ⚠️ EKSİKLER, 📈 ÖNERİLER başlıklarıyla ver."
        )
        try: return self.client.models.generate_content(model="gemini-3-flash-preview", contents=p).text
        except Exception as e: return f"HATA: {e}"

    def ayristir(self, txt):
        c = re.search(r'```(?:bash|sh)?\s*(.*?)\s*```', txt, re.DOTALL)
        saf = c.group(1).strip() if c else "Bulunamadı"
        k = re.search(r'Kategori:\s*\[?(.*?)\]?$', txt, re.MULTILINE)
        kat = k.group(1).strip() if k else "Diğer"
        kat = kat.replace("[", "").replace("]", "")
        if kat not in SABIT_KATEGORILER: kat = "Diğer"
        desc = txt.replace(c.group(0) if c else "", "").replace(k.group(0) if k else "", "").strip()
        return saf, desc, kat

# --- MODÜL 4: GUI (THREAD SAFE) ---
if GUI_AVAILABLE:
    class ProfilWorker(QThread):
        sonuc_hazir = pyqtSignal(str, int)
        # DB nesnesini DEĞİL, API Key'i alıyoruz
        def __init__(self, api_key):
            super().__init__()
            self.api_key = api_key
        
        def run(self):
            # Kendi DB bağlantısını oluştur
            yerel_db = MergenVeritabani()
            z = MergenZeka()
            
            try:
                son_profil_data = yerel_db.son_profil_getir()
                eski_rapor = son_profil_data[0] if son_profil_data else ""
                son_islenen_id = son_profil_data[1] if son_profil_data else 0
                
                yeni_veriler = yerel_db.analiz_icin_komutlari_getir(son_islenen_id)
                if not yeni_veriler:
                    self.sonuc_hazir.emit("YENİ_VERİ_YOK", son_islenen_id)
                    return

                yeni_komut_listesi = [x[1] for x in yeni_veriler]
                max_id = yeni_veriler[-1][0]
                
                rapor = z.profil_analizi_yap(eski_rapor, yeni_komut_listesi)
                self.sonuc_hazir.emit(rapor, max_id)
            finally:
                yerel_db.kapat() # Bağlantıyı temizle

    class ProfilPenceresi(QDialog):
        def __init__(self, parent=None, db=None):
            super().__init__(parent)
            self.db = db
            self.setWindowTitle("MERGEN - Kariyer & Kişilik Analizi")
            self.resize(700, 800)
            self.setStyleSheet("background-color: #121212; color: #e0e0e0;")
            
            layout = QVBoxLayout(self)
            lbl = QLabel("🧠 SİBER GÜVENLİK PROFİLİNİZ"); lbl.setFont(QFont("Impact", 20)); lbl.setStyleSheet("color: #9b59b6;"); layout.addWidget(lbl)
            self.txt_rapor = QTextEdit(); self.txt_rapor.setReadOnly(True); self.txt_rapor.setStyleSheet("background: #1e1e1e; border: 1px solid #333; padding: 10px;"); layout.addWidget(self.txt_rapor)
            
            btn_layout = QHBoxLayout()
            self.btn_analiz = QPushButton("🔄 Profili Güncelle"); self.btn_analiz.setStyleSheet("background: #9b59b6; color: white; padding: 10px; font-weight: bold;"); self.btn_analiz.clicked.connect(self.analizi_baslat)
            btn_layout.addWidget(self.btn_analiz); layout.addLayout(btn_layout)
            
            self.pbar = QProgressBar(); self.pbar.setVisible(False); self.pbar.setRange(0, 0); self.pbar.setStyleSheet("QProgressBar::chunk { background: #9b59b6; }"); layout.addWidget(self.pbar)
            self.veriyi_yukle()

        def veriyi_yukle(self):
            data = self.db.son_profil_getir()
            if data: self.txt_rapor.setMarkdown(data[0])
            else: self.txt_rapor.setText("Analiz bekleniyor...")

        def analizi_baslat(self):
            self.btn_analiz.setEnabled(False); self.pbar.setVisible(True)
            # DB nesnesi göndermiyoruz, sadece Key
            self.worker = ProfilWorker(os.getenv("MERGEN_API_KEY"))
            self.worker.sonuc_hazir.connect(self.analiz_bitti)
            self.worker.start()

        def analiz_bitti(self, rapor, son_id):
            self.pbar.setVisible(False); self.btn_analiz.setEnabled(True)
            if rapor == "YENİ_VERİ_YOK": QMessageBox.information(self, "Bilgi", "Yeni veri yok.")
            elif rapor.startswith("HATA"): QMessageBox.critical(self, "Hata", rapor)
            else:
                self.db.profil_kaydet(rapor, son_id)
                self.txt_rapor.setMarkdown(rapor)
                QMessageBox.information(self, "Tamam", "Profil güncellendi.")

    class AIWorker(QThread):
        sonuc_hazir = pyqtSignal(tuple)
        def __init__(self, soru, api_key):
            super().__init__()
            self.soru = soru; self.api_key = api_key
        def run(self):
            z = MergenZeka(); r = z.sor(self.soru); self.sonuc_hazir.emit(z.ayristir(r))

    class MergenGUI(QMainWindow):
        def __init__(self, db):
            super().__init__()
            self.db = db; self.secili = {}; self.aktif_kat = "Tümü"; self.fav_filtre = False
            self.kalkan = GuvenlikKalkan()
            self.setup_ui(); self.load_data()

        def setup_ui(self):
            self.setStyleSheet("""
                QMainWindow { background-color: #121212; }
                QWidget { color: #e0e0e0; font-family: 'Segoe UI', sans-serif; }
                QTableWidget { background-color: #1a1a1a; border: none; gridline-color: #333; }
                QHeaderView::section { background-color: #252525; padding: 5px; border: none; font-weight: bold; }
                QLineEdit { background: #1e1e1e; color: #00ff9d; border: 1px solid #333; padding: 5px; font-family: 'Consolas'; }
                QProgressBar { border: 1px solid #333; text-align: center; }
                QProgressBar::chunk { background-color: #00ff9d; }
            """)
            self.resize(1350, 850)
            central = QWidget(); self.setCentralWidget(central); layout = QVBoxLayout(central)
            
            head = QHBoxLayout()
            lbl = QLabel("MERGEN"); lbl.setFont(QFont("Impact", 24)); lbl.setStyleSheet("color: #00ff9d;"); head.addWidget(lbl)
            self.search = QLineEdit(); self.search.setPlaceholderText("Ara..."); self.search.textChanged.connect(lambda: self.load_data(self.search.text())); head.addWidget(self.search, 1)
            btn_prf = QPushButton("🧠 Profilim"); btn_prf.setStyleSheet("background: #9b59b6; color: white; font-weight: bold;"); btn_prf.clicked.connect(self.profil_ac); head.addWidget(btn_prf)
            btn_imp = QPushButton("📂 İçe Aktar"); btn_imp.clicked.connect(self.do_import); head.addWidget(btn_imp)
            btn_exp = QPushButton("💾 Yedekle"); btn_exp.clicked.connect(self.do_export); head.addWidget(btn_exp)
            btn_clear = QPushButton("🗑️ Sıfırla")
            btn_clear.setStyleSheet("background-color: #c0392b; color: white; font-weight: bold;")
            btn_clear.clicked.connect(self.tam_temizlik)
            head.addWidget(btn_clear)
            layout.addLayout(head)

            filt = QHBoxLayout()
            self.chk_fav = QCheckBox("⭐ Favoriler"); self.chk_fav.stateChanged.connect(self.reload_data); self.chk_fav.setStyleSheet("color: gold; font-weight: bold;"); filt.addWidget(self.chk_fav)
            self.chk_sort = QCheckBox("🔥 En Çok Kullanılanlar"); self.chk_sort.stateChanged.connect(self.reload_data); self.chk_sort.setStyleSheet("color: #ff5555; font-weight: bold; margin-left:15px;"); filt.addWidget(self.chk_sort)
            filt.addWidget(QLabel("| Kategoriler: "))
            self.cat_layout = QHBoxLayout(); self.cat_group = QButtonGroup(); self.cat_group.buttonClicked.connect(self.cat_change); filt.addLayout(self.cat_layout)
            filt.addStretch()
            layout.addLayout(filt)

            split = QSplitter(Qt.Orientation.Vertical)
            self.table = QTableWidget(0, 7)
            self.table.setHorizontalHeaderLabels(["ID", "⭐", "SAYAC", "KOMUT (Düzenle)", "AMAÇ / SORU", "KATEGORİ", "TARİH"])
            h = self.table.horizontalHeader()
            h.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
            h.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
            self.table.setColumnWidth(0, 50); self.table.setColumnWidth(1, 30); self.table.setColumnWidth(2, 60); self.table.setColumnWidth(3, 400)
            self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
            self.table.setAlternatingRowColors(True)
            self.table.verticalHeader().setVisible(False)
            self.table.setSortingEnabled(True)
            
            self.table.itemSelectionChanged.connect(self.on_select)
            self.table.cellChanged.connect(self.on_edit)
            self.table.cellClicked.connect(self.on_click)
            self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.table.customContextMenuRequested.connect(self.context_menu)
            split.addWidget(self.table)

            det_w = QWidget(); det_l = QVBoxLayout(det_w); det_l.setContentsMargins(0,5,0,0)
            h_d = QHBoxLayout(); h_d.addWidget(QLabel("DETAYLAR")); h_d.addStretch()
            btn_cp = QPushButton("Kopyala"); btn_cp.clicked.connect(self.copy_cmd); h_d.addWidget(btn_cp); det_l.addLayout(h_d)
            self.txt_det = QTextEdit(); self.txt_det.setReadOnly(True); det_l.addWidget(self.txt_det)
            split.addWidget(det_w); layout.addWidget(split)

            stat = QHBoxLayout()
            self.prog = QProgressBar(); self.prog.setVisible(False); self.prog.setRange(0,0); stat.addWidget(self.prog)
            self.lbl_st = QLabel("Hazır."); stat.addWidget(self.lbl_st); layout.addLayout(stat)

        def profil_ac(self):
            dlg = ProfilPenceresi(self, self.db)
            dlg.exec()

        def update_cats(self):
            for b in self.cat_group.buttons(): self.cat_group.removeButton(b); b.deleteLater()
            for cat in ["Tümü"] + self.db.kategoriler():
                rb = QRadioButton(cat); self.cat_group.addButton(rb); self.cat_layout.addWidget(rb)
                if cat == self.aktif_kat: rb.setChecked(True)

        def reload_data(self): self.load_data(self.search.text())

        def load_data(self, flt=""):
            self.table.setSortingEnabled(False)
            self.table.setRowCount(0)
            en_cok = self.chk_sort.isChecked()
            is_fav = self.chk_fav.isChecked()
            data = self.db.getir(flt, self.aktif_kat, is_fav, en_cok)
            self.secili = {}
            self.update_cats()

            for r, d in enumerate(data):
                self.table.insertRow(r)
                it_id = SayisalItem(str(d[0])); it_id.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable); self.table.setItem(r, 0, it_id)
                it_fv = QTableWidgetItem("★" if d[7] else "☆"); it_fv.setForeground(QColor("gold") if d[7] else QColor("gray")); it_fv.setTextAlignment(Qt.AlignmentFlag.AlignCenter); it_fv.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable); self.table.setItem(r, 1, it_fv)
                it_cnt = SayisalItem(str(d[8])); it_cnt.setTextAlignment(Qt.AlignmentFlag.AlignCenter); 
                if d[8]>10: it_cnt.setForeground(QColor("#ff5555"))
                it_cnt.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable); self.table.setItem(r, 2, it_cnt)
                it_cmd = QTableWidgetItem(d[1]); it_cmd.setFont(QFont("Consolas",10)); it_cmd.setForeground(QColor("#00ff9d")); self.table.setItem(r, 3, it_cmd)
                self.table.setItem(r, 4, QTableWidgetItem(d[2]))
                self.table.setItem(r, 5, QTableWidgetItem(d[3]))
                it_dt = QTableWidgetItem(str(d[4])[:16]); it_dt.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable); self.table.setItem(r, 6, it_dt)
                self.secili[r] = {'id': d[0], 'msk': d[1], 'soru': d[2], 'desc': d[5], 'fav': d[7]}
            
            self.table.setSortingEnabled(True)
            self.lbl_st.setText(f"Kayıtlar: {len(data)}")

        def on_edit(self, r, c):
            if c not in [3,4,5]: return
            key = {3:'maskelenmis_komut', 4:'soru_ozeti', 5:'kategori'}[c]
            try:
                id = int(self.table.item(r,0).text())
                self.db.guncelle(id, key, self.table.item(r,c).text())
                self.lbl_st.setText("Güncellendi.")
            except: pass

        def on_click(self, r, c):
            if c==1:
                id = int(self.table.item(r,0).text())
                curr = self.table.item(r, 1).text()
                new = 1 if curr == "☆" else 0
                self.db.guncelle(id, 'favori', new)
                self.reload_data()

        def on_select(self):
            rows = self.table.selectionModel().selectedRows()
            if not rows: return
            try:
                r = rows[0].row()
                id_val = int(self.table.item(r, 0).text())
                msk = self.table.item(r, 3).text()
                soru = self.table.item(r, 4).text()
                desc = next((v['desc'] for v in self.secili.values() if v['id'] == id_val), "Bilgi Yok")
                html = f"""<h3 style='color:#00ff9d'>{soru}</h3><div style='background:#111;padding:10px;border-left:3px solid #00ff9d;font-family:Consolas;color:#fff'>{msk}</div><br><div style='color:#ccc'>{desc.replace(chr(10),'<br>')}</div>"""
                self.txt_det.setHtml(html)
            except: pass

        def context_menu(self, pos):
            m = QMenu(); act = m.addAction("Sil"); act.triggered.connect(self.del_row); m.exec(self.table.viewport().mapToGlobal(pos))
        def del_row(self):
            r = self.table.currentRow(); id = int(self.table.item(r,0).text())
            if QMessageBox.question(self,"Sil","Silinsin mi?",QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
                self.db.sil(id); self.reload_data()
        def cat_change(self, b): self.aktif_kat = b.text(); self.reload_data()
        def copy_cmd(self): QApplication.clipboard().setText(self.txt_det.toPlainText().split('\n')[1]); self.lbl_st.setText("Kopyalandı!")
        def do_export(self):
            p,_ = QFileDialog.getSaveFileName(self,"Yedekle", os.path.expanduser("~/mergen.json"),"JSON(*.json)")
            if p: 
                d = self.db.getir()
                json.dump([{'id':x[0],'cmd':x[6],'msk':x[1],'q':x[2],'cat':x[3],'desc':x[5],'fv':x[7],'cnt':x[8]} for x in d], open(p,'w'), indent=2)
                QMessageBox.information(self,"OK","Yedeklendi")
        def do_import(self):
            p,_ = QFileDialog.getOpenFileName(self,"Aç", os.path.expanduser("~"),"JSON(*.json)")
            if p:
                d = json.load(open(p))
                for x in d: self.db.komut_ekle(x.get('cmd'),x.get('msk'),x.get('q'),x.get('desc'),x.get('cat','Genel'),x.get('fv',0))
                self.reload_data(); QMessageBox.information(self,"OK","Yüklendi")
                
        def tam_temizlik(self):
            onay = QMessageBox.critical(
                self, 
                "KRİTİK UYARI: VERİ İMHASI", 
                "TÜM VERİTABANI KALICI OLARAK SİLİNECEK!\n\n"
                "Bu işlem geri alınamaz. Kaydedilen tüm komutlar, geçmiş analizler ve "
                "kişisel profiliniz yok olacak.\n\n"
                "Devam etmek istediğinize emin misiniz?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if onay == QMessageBox.StandardButton.Yes:
                self.db.veritabani_sifirla()
                self.load_data() # Tabloyu yenile (boşalt)
                self.txt_det.clear()
                QMessageBox.information(self, "Temizlendi", "Mergen hafızası fabrika ayarlarına döndürüldü.")

# --- MODÜL 5: SETUP ---
def setup_full():
    print(f"{Renk.HEADER}=== MERGEN KURULUM SİHİRBAZI ==={Renk.ENDC}")
    print(f"\n{Renk.BLUE}[1/5] Kütüphaneler kontrol ediliyor...{Renk.ENDC}")
    pkgs = ["google-genai", "PyQt6"]
    for p in pkgs:
        try: __import__(p.replace("-","_").split("_")[0])
        except ImportError:
            print(f"{p} kuruluyor..."); subprocess.call([sys.executable, "-m", "pip", "install", p, "--break-system-packages"])

    print(f"\n{Renk.BLUE}[2/5] Veritabanı hazırlanıyor...{Renk.ENDC}")
    MergenVeritabani(); print(f"{Renk.GREEN}✓ Veritabanı hazır.{Renk.ENDC}")

    print(f"\n{Renk.BLUE}[3/5] Shell yapılandırması...{Renk.ENDC}")
    shell = os.environ.get("SHELL", "/bin/bash").split("/")[-1]
    rc = None; src = os.path.abspath(sys.argv[0])
    if "zsh" in shell: rc = os.path.expanduser("~/.zshrc"); cmd = f"mergen_track() {{ /usr/bin/python3 {src} --track \"$(fc -ln -1)\" &! }}\nautoload -Uz add-zsh-hook; add-zsh-hook precmd mergen_track"
    elif "bash" in shell: rc = os.path.expanduser("~/.bashrc"); cmd = f"mergen_track() {{ local l=$(history 1 | sed 's/^[ ]*[0-9]\\+[ ]*//'); /usr/bin/python3 {src} --track \"$l\" &>/dev/null & }}\nexport PROMPT_COMMAND=\"mergen_track; $PROMPT_COMMAND\""
    elif "fish" in shell: rc = os.path.expanduser("~/.config/fish/config.fish"); cmd = f"function mergen_track --on-event fish_postexec\n    /usr/bin/python3 {src} --track \"$argv\" &\nend"
    
    if rc:
        try:
            with open(rc, 'r') as f: content = f.read()
            if "mergen_track" not in content:
                with open(rc, 'a') as f: f.write(f"\n# MERGEN HOOK\n{cmd}")
                print(f"{Renk.GREEN}✓ {rc} dosyasına kanca atıldı.{Renk.ENDC}")
            else: print(f"{Renk.WARNING}! Shell zaten yapılandırılmış.{Renk.ENDC}")
        except: pass

    print(f"\n{Renk.BLUE}[4/5] API Anahtarı Ayarı...{Renk.ENDC}")
    current_key = os.getenv("MERGEN_API_KEY")
    if current_key: print(f"{Renk.GREEN}✓ API Anahtarı zaten tanımlı.{Renk.ENDC}")
    else:
        print(f"{Renk.WARNING}API Anahtarı bulunamadı.{Renk.ENDC}")
        key = input(f"{Renk.BOLD}Lütfen Google Gemini API Key'inizi yapıştırın (Atlamak için Enter): {Renk.ENDC}").strip()
        if key and rc:
            with open(rc, "a") as f: f.write(f'\nexport MERGEN_API_KEY="{key}"\n')
            print(f"{Renk.GREEN}✓ API Anahtarı {rc} dosyasına kaydedildi.{Renk.ENDC}")

    print(f"\n{Renk.BLUE}[5/5] Sistem komutu (mergen) oluşturuluyor...{Renk.ENDC}")
    target = "/usr/local/bin/mergen"
    if not os.path.exists(target):
        try: os.symlink(src, target); print(f"{Renk.GREEN}✓ 'mergen' komutu eklendi.{Renk.ENDC}")
        except: print(f"{Renk.FAIL}! Yetki hatası. Lütfen şunu çalıştırın: sudo ln -s {src} {target}{Renk.ENDC}")
    
    print(f"\n{Renk.GREEN}=== KURULUM TAMAMLANDI ==={Renk.ENDC}\nLütfen terminali kapatıp yeniden açın.")

# --- MAIN ---
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("sorgu", nargs="?", help="Soru sor")
    parser.add_argument("--ui", action="store_true", help="GUI Aç")
    parser.add_argument("--setup", action="store_true", help="Otomatik Kurulum")
    parser.add_argument("--track", nargs=1, help="Internal use")
    args = parser.parse_args()
    
    if args.setup: setup_full(); return
    if not check_libs(): print("Lütfen önce kurulumu çalıştırın: python3 mergen.py --setup"); return

    db = MergenVeritabani(); kalkan = GuvenlikKalkan()

    if args.track:
        h = args.track[0].strip()
        if not h or "mergen" in h: return
        db.komut_ekle(h, kalkan.maskele(h), "Shell Geçmişi", "Otomatik Takip", "Shell Geçmişi")
        return

    if args.ui:
        if not GUI_AVAILABLE: print("PyQt6 eksik. Setup çalıştırın."); return
        app = QApplication(sys.argv); app.setStyle("Fusion"); w = MergenGUI(db)
        if args.sorgu:
            w.show(); w.prog.setVisible(True); w.lbl_st.setText("AI...")
            msk = kalkan.maskele(args.sorgu)
            th = AIWorker(msk, os.getenv("MERGEN_API_KEY"))
            def done(r):
                saf,desc,cat = r; w.prog.setVisible(False)
                db.komut_ekle(saf, kalkan.maskele(saf), args.sorgu, desc, cat)
                w.reload_data(); w.lbl_st.setText("Tamam.")
            th.sonuc_hazir.connect(done); th.start(); w.th = th; sys.exit(app.exec())
        w.show(); sys.exit(app.exec())

    if args.sorgu:
        print(f"{Renk.CYAN}Analiz ediliyor...{Renk.ENDC}")
        z = MergenZeka(); r = z.sor(kalkan.maskele(args.sorgu))
        if r=="API_YOK": print(f"{Renk.FAIL}API Key yok.{Renk.ENDC}"); return
        saf,desc,cat = z.ayristir(r)
        print(f"\n{Renk.GREEN}KOMUT: {saf}{Renk.ENDC}\n{Renk.BLUE}KAT: {cat}{Renk.ENDC}\n\n{desc}")
        db.komut_ekle(saf, kalkan.maskele(saf), args.sorgu, desc, cat)
    else: print("Kullanım: mergen \"soru\" | mergen --ui | mergen --setup")

if __name__ == "__main__":
    main()
